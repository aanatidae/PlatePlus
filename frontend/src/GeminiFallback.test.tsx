// @vitest-environment jsdom
// Provider results are synthetic; the browser never contacts Gemini.
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { AlprResultDetails } from "./AlprResultDetails";
import { SimulatorImageUpload } from "./SimulatorImageUpload";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

it("shows external recognition and origin evidence separately from local confidence", () => {
  render(<AlprResultDetails result={{ status: "accepted_for_vehicle_lookup", message: "Validated fallback", plate_origin: "foreign_other", origin_country: "United Kingdom", recognition_source: "gemini_fallback", origin_source: "gemini_fallback", fallback_used: true, fallback_status: "gemini_resolved", payment_status: "successful", payment_amount: 22, payment_dynamic_toll_amount: 2, payment_foreign_vehicle_charge: 20 }} />);
  expect(screen.getByText(/Gemini vision fallback/)).toBeTruthy();
  expect(screen.getByText("Other foreign pattern")).toBeTruthy();
  expect(screen.getByText(/United Kingdom/)).toBeTruthy();
  expect(screen.getByText("Detection unavailable · OCR unavailable")).toBeTruthy();
  expect(screen.getByText("RM22.00")).toBeTruthy();
});

it("discloses external processing and sends uploads only to PlatePlus", async () => {
  vi.stubGlobal("URL", class extends URL { static createObjectURL = () => "blob:fixture"; static revokeObjectURL = vi.fn(); });
  const fetch = vi.fn(async () => new Response(JSON.stringify({ status: "no_plate_detected", message: "Gemini fallback unavailable. No simulated payment made.", fallback_status: "gemini_unavailable" })));
  vi.stubGlobal("fetch", fetch);
  const { container } = render(<SimulatorImageUpload locationId="simulator" />);
  expect(screen.getByText(/unresolved uploads may be sent to Gemini/)).toBeTruthy();
  fireEvent.change(container.querySelector('input[type="file"]')!, { target: { files: [new File(["image"], "plate.png", { type: "image/png" })] } });
  fireEvent.click(screen.getByText("Process image"));
  await screen.findAllByText(/Gemini fallback unavailable/);
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(fetch.mock.calls[0][0]).toContain("/api/webcam/images?location_id=simulator");
  expect(JSON.stringify(fetch.mock.calls)).not.toContain("generativelanguage.googleapis.com");
});
