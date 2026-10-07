// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { ChargeDetails } from "./ChargeDetails";
import { RecentActivity } from "./RecentActivity";
import { AlprResultDetails } from "./AlprResultDetails";
import { PricingExplanation } from "./PricingExplanation";
import { OriginEvidence } from "./ModelPerformance";
import { SimulatorImageUpload } from "./SimulatorImageUpload";

vi.mock("./App", () => ({ apiHeaders: () => ({ Authorization: "Bearer test" }) }));
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("V3 information within the existing presentation pages", () => {
  it("renders stored string components as separate charges and the final total", () => {
    render(<ChargeDetails charge={{ amount: "23.60", dynamic_toll_amount: "3.60", foreign_vehicle_charge: "20.00", status: "successful" }} />);
    const breakdown = screen.getByLabelText("Simulated charge breakdown");
    for (const text of ["Dynamic toll", "RM3.60", "Simulated foreign-vehicle charge", "RM20.00", "Final simulated total", "RM23.60"]) expect(within(breakdown).getByText(text)).toBeTruthy();
  });
  it("does not present a failed attempted charge as a successful debit", () => {
    render(<ChargeDetails charge={{ amount: 23, dynamic_toll_amount: 3, foreign_vehicle_charge: 20, status: "insufficient_balance" }} />);
    expect(screen.getByText("Attempted simulated total")).toBeTruthy();
    expect(screen.queryByText("Final simulated total")).toBeNull();
  });
  it("keeps Malaysian transaction rows compact without a zero foreign-charge breakdown", () => {
    render(<RecentActivity kind="transactions" locationName="LDP" item={{ id: "t", location_id: "ldp", processed_at: "2026-10-07T01:00:00Z", amount: "2.00", dynamic_toll_amount: "2.00", foreign_vehicle_charge: "0.00", status: "successful" }} />);
    expect(screen.getByText("RM2.00")).toBeTruthy();
    expect(screen.getByText("Final simulated total")).toBeTruthy();
    expect(screen.queryByLabelText("Simulated charge breakdown")).toBeNull();
  });
  it.each(["malaysian", "singaporean", "unknown"])("names the %s pattern in recent detections", origin => {
    render(<RecentActivity kind="detections" locationName="Simulator Toll Plaza" item={{ id: "d", location_id: "sim", normalized_plate: "TEST1234", plate_origin: origin, status: "accepted", detected_at: "2026-10-07T01:00:00Z", source: "uploaded_image" }} />);
    expect(screen.getByText(origin === "unknown" ? "Unknown / unsupported pattern" : `${origin[0].toUpperCase()}${origin.slice(1)} pattern`)).toBeTruthy();
  });
  it("separates the congestion pricing explanation from the transaction-only foreign charge", () => {
    render(<PricingExplanation source="webcam_alpr" telemetry={{ congestion_percentage: 70, congestion_category: "moderate", base_toll_price: 2, congestion_multiplier: 1.5, current_toll_price: 3, active_crossings: 7, road_capacity: 10 }} />);
    expect(screen.getByText("Local ALPR crossings")).toBeTruthy();
    expect(screen.getByText("Moderate")).toBeTruthy();
    expect(screen.getByText("RM3.00")).toBeTruthy();
    expect(screen.getByText(/Plate origin does not change its band or multiplier/)).toBeTruthy();
    expect(screen.queryByText("RM20.00")).toBeNull();
  });
  it("marks classification fixture evidence as separate from OCR and field accuracy", () => {
    render(<OriginEvidence evidence={{ samples: 32, exact_matches: 25, exact_match_percent: 78.1, cross_country_errors: 0, ambiguous_rejected: 7, unsupported_rejected: 8, note: "Selected synthetic text fixture only, separate from OCR. Not field accuracy, nationality, ownership, or registration verification." }} />);
    expect(screen.getByText("25/32 · 78.1%")).toBeTruthy();
    expect(screen.getByText(/Not field accuracy/)).toBeTruthy();
  });
  it("shares origin, outcome and charge rendering in the camera result", () => {
    render(<AlprResultDetails result={{ status: "accepted_for_vehicle_lookup", message: "Accepted", plate_origin: "singaporean", payment_status: "successful", payment_amount: 22, payment_dynamic_toll_amount: 2, payment_foreign_vehicle_charge: 20, payment_duplicate: true }} />);
    expect(screen.getByText("Singaporean pattern")).toBeTruthy();
    expect(screen.getByText(/Prior event replayed; no new deduction/)).toBeTruthy();
    expect(screen.getByText("RM22.00")).toBeTruthy();
  });
  it("shows upload origin and payment components and removes its ephemeral preview on clear", async () => {
    const revoke = vi.fn();
    vi.stubGlobal("URL", class extends URL { static createObjectURL = vi.fn(() => "blob:local-test"); static revokeObjectURL = revoke; });
    const fetch = vi.fn(async () => new Response(JSON.stringify({ status: "accepted_for_vehicle_lookup", message: "Accepted", plate_text: "GBC1234R", plate_origin: "singaporean", payment_status: "successful", payment_amount: 22, payment_dynamic_toll_amount: 2, payment_foreign_vehicle_charge: 20 })));
    vi.stubGlobal("fetch", fetch);
    const { container } = render(<SimulatorImageUpload locationId="simulator" />);
    fireEvent.change(container.querySelector('input[type="file"]')!, { target: { files: [new File(["image"], "plate.png", { type: "image/png" })] } });
    fireEvent.click(screen.getByText("Process image"));
    await screen.findByText("Singaporean pattern");
    expect(screen.getByText("RM20.00")).toBeTruthy();
    expect(screen.getByText("RM22.00")).toBeTruthy();
    expect(fetch.mock.calls[0][0]).toContain("/api/webcam/images?location_id=simulator");
    fireEvent.click(screen.getByLabelText("Clear selected plate image"));
    expect(screen.queryByAltText("Selected plate image preview")).toBeNull();
    expect(screen.queryByText("Singaporean pattern")).toBeNull();
    expect(revoke).toHaveBeenCalledWith("blob:local-test");
  });
});
