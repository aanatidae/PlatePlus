// @vitest-environment jsdom
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { ForeignChargeSettings } from "./ForeignChargeSettings";

vi.mock("./App", () => ({ apiHeaders: () => ({ Authorization: "Bearer test" }) }));
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
function open(container: HTMLElement) {
  const details = container.querySelector("details")!;
  details.open = true;
  fireEvent(details, new Event("toggle"));
}

it("loads and saves the separate configured charge without calling congestion APIs", async () => {
  const fetch = vi.fn(async (_url: string, init?: RequestInit) => new Response(JSON.stringify({ amount: init?.method === "PUT" ? "12.50" : "20.00" })));
  vi.stubGlobal("fetch", fetch);
  const { container } = render(<ForeignChargeSettings />);
  expect(fetch).not.toHaveBeenCalled();
  expect(screen.getByText(/Separate from congestion pricing/)).toBeTruthy();
  open(container);
  const input = await screen.findByLabelText("Simulated foreign-vehicle charge (RM)") as HTMLInputElement;
  expect(input.value).toBe("20.00");
  fireEvent.change(input, { target: { value: "12.50" } });
  fireEvent.click(screen.getByText("Save simulated foreign charge"));
  await screen.findByText(/Existing transactions and congestion rules are unchanged/);
  expect(fetch.mock.calls).toHaveLength(2);
  expect(fetch.mock.calls.every(([url]) => url.endsWith("/api/data/foreign-vehicle-charge"))).toBe(true);
  expect(JSON.parse(String(fetch.mock.calls[1][1]?.body))).toEqual({ amount: "12.50" });
  expect(input.value).toBe("12.50");
});

it("reports save errors without pretending that a draft was persisted", async () => {
  vi.stubGlobal("fetch", vi.fn(async (_url: string, init?: RequestInit) => init?.method === "PUT"
    ? new Response(JSON.stringify({ detail: "Simulated charge setting is unavailable" }), { status: 503 })
    : new Response(JSON.stringify({ amount: "20.00" }))));
  const { container } = render(<ForeignChargeSettings />); open(container);
  fireEvent.change(await screen.findByLabelText("Simulated foreign-vehicle charge (RM)"), { target: { value: "10.00" } });
  fireEvent.click(screen.getByText("Save simulated foreign charge"));
  expect(await screen.findByRole("alert")).toHaveProperty("textContent", "Simulated charge setting is unavailable");
  expect(screen.queryByText(/saved and audit logged/)).toBeNull();
});

it("does not substitute a demo fee when the persisted setting is missing", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ detail: "Run migrations" }), { status: 503 })));
  const { container } = render(<ForeignChargeSettings />); open(container);
  expect(await screen.findByRole("alert")).toHaveProperty("textContent", "Run migrations");
  expect(screen.queryByLabelText("Simulated foreign-vehicle charge (RM)")).toBeNull();
});
