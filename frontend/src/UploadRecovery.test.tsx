// @vitest-environment jsdom
import { webcrypto } from "node:crypto";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { SimulatorImageUpload } from "./SimulatorImageUpload";
import { UPLOAD_REQUEST_TIMEOUT_MS, uploadRequestKey } from "./uploadRequest";

vi.mock("./App", () => ({ apiHeaders: () => ({ Authorization: "Bearer fixture" }) }));
beforeEach(() => {
  sessionStorage.clear();
  vi.stubGlobal("crypto", webcrypto);
  vi.stubGlobal("URL", class extends URL { static createObjectURL = () => "blob:fixture"; static revokeObjectURL = vi.fn(); });
});
afterEach(() => { cleanup(); vi.useRealTimers(); vi.unstubAllGlobals(); });

const response = () => new Response(JSON.stringify({ status: "no_plate_detected", message: "No plate found." }));
const choose = (container: HTMLElement, text = "same image", name = "plate.png") => {
  const file = new File([text], name, { type: "image/png" });
  fireEvent.change(container.querySelector('input[type="file"]')!, { target: { files: [file] } });
  fireEvent.click(screen.getByText("Process image"));
};

it("stops a stalled browser request, restores controls and safely reuses its event key", async () => {
  const fetch = vi.fn((_url, options) => new Promise<Response>((_resolve, reject) => {
    options.signal.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")));
  }));
  vi.stubGlobal("fetch", fetch);
  vi.useFakeTimers();
  const { container } = render(<SimulatorImageUpload locationId="sim" />);
  choose(container);
  await vi.waitFor(() => expect(fetch).toHaveBeenCalledTimes(1));
  const firstKey = fetch.mock.calls[0][1].headers["Idempotency-Key"];
  await act(async () => { await vi.advanceTimersByTimeAsync(15_000); });
  expect(screen.getByText(/first scan can take longer/)).toBeTruthy();
  await act(async () => { await vi.advanceTimersByTimeAsync(UPLOAD_REQUEST_TIMEOUT_MS - 15_000); });
  expect(fetch.mock.calls[0][1].signal.aborted).toBe(true);
  expect(screen.getByText(/Retry the same image to safely check its result/)).toBeTruthy();
  expect((screen.getByText("Process image") as HTMLButtonElement).disabled).toBe(false);
  vi.useRealTimers();
  fetch.mockImplementationOnce(async () => response());
  fireEvent.click(screen.getByText("Process image"));
  await screen.findAllByText("No plate found.");
  expect(fetch.mock.calls[1][1].headers["Idempotency-Key"]).toBe(firstKey);
  expect(Object.keys(sessionStorage).filter(key => key.startsWith("plateplus.pending-upload"))).toEqual([]);
});

it("reuses an uncertain upload key after remount/refresh, even if its filename changes", async () => {
  const fetch = vi.fn(async () => { throw new TypeError("Network interrupted."); });
  vi.stubGlobal("fetch", fetch);
  const first = render(<SimulatorImageUpload locationId="sim" />);
  choose(first.container);
  await screen.findByText("Network interrupted.");
  const firstKey = fetch.mock.calls[0][1].headers["Idempotency-Key"];
  first.unmount();
  fetch.mockImplementationOnce(async () => response());
  const second = render(<SimulatorImageUpload locationId="sim" />);
  choose(second.container, "same image", "renamed.png");
  await screen.findAllByText("No plate found.");
  expect(fetch.mock.calls[1][1].headers["Idempotency-Key"]).toBe(firstKey);
});

it("keeps independent event keys for different image content and locations without retaining images", async () => {
  const file = new File(["image one"], "private-file-name.png", { type: "image/png" });
  const first = await uploadRequestKey(file, "sim");
  expect((await uploadRequestKey(file, "sim")).key).toBe(first.key);
  expect((await uploadRequestKey(new File(["image two"], file.name), "sim")).key).not.toBe(first.key);
  expect((await uploadRequestKey(file, "other")).key).not.toBe(first.key);
  expect(JSON.stringify(sessionStorage)).not.toMatch(/private-file-name|image one|image two/);
});

it("aborts on clear and ignores a late response so it cannot overwrite a new selection", async () => {
  let finish: (response: Response) => void;
  const fetch = vi.fn(() => new Promise<Response>(resolve => { finish = resolve; }));
  vi.stubGlobal("fetch", fetch);
  const { container } = render(<SimulatorImageUpload locationId="sim" />);
  choose(container);
  await waitFor(() => expect(fetch).toHaveBeenCalledTimes(1));
  fireEvent.click(screen.getByLabelText("Clear selected plate image"));
  expect(fetch.mock.calls[0][1].signal.aborted).toBe(true);
  finish!(new Response(JSON.stringify({ plate_text: "OLD1234", status: "accepted_for_vehicle_lookup" })));
  await waitFor(() => expect(screen.queryByText("Processing…")).toBeNull());
  expect(screen.queryByText("OLD1234")).toBeNull();
});
