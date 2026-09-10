import { describe, expect, it } from "vitest";
import { currentTelemetryForLocation, type LiveSnapshot } from "./Prediction";

describe("Prediction current telemetry", () => {
  it("uses the selected toll's canonical snapshot and rejects an old location", () => {
    const penchala: LiveSnapshot = { location_id: "penchala", live: { traffic: { congestion_percentage: 24, congestion_category: "normal", current_toll_price: 2 }, price: { amount: 2 } } };
    const duke: LiveSnapshot = { location_id: "duke", live: { traffic: { congestion_percentage: 36.4, congestion_category: "moderate", current_toll_price: 3 }, price: { amount: 3 } } };
    expect(currentTelemetryForLocation(penchala, "penchala")?.traffic?.congestion_percentage).toBe(24);
    expect(currentTelemetryForLocation(duke, "duke")?.traffic?.congestion_percentage).toBe(36.4);
    expect(currentTelemetryForLocation(penchala, "duke")).toBeNull();
    expect(currentTelemetryForLocation(duke, "duke")?.price?.amount).toBe(3);
    expect(currentTelemetryForLocation(duke, "duke")?.traffic?.congestion_category).toBe("moderate");
  });
});
