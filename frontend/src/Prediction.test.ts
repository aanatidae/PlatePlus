import { describe, expect, it } from "vitest";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { PredictionTooltip, currentTelemetryForLocation, formatPredictionTimestamp, formatRinggit, predictionDurationOptions, type LiveSnapshot } from "./Prediction";
import { createSimulationFrames } from "./simulator";

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

  it("offers a complete 12-hour horizon and formats tooltip values for Malaysia", () => {
    expect(predictionDurationOptions.map(option => option.value)).toEqual(["30", "60", "120", "240", "360", "480", "720"]);
    expect(formatRinggit(3)).toBe("RM3.00");
    expect(formatPredictionTimestamp("2026-09-14T19:19:00.000Z")).toMatch(/15 Sep/);
  });

  it("renders the custom themed tooltip with an exact timestamp, congestion, and Ringgit toll", () => {
    const props = { active: true, payload: [{ payload: { timestamp: "2026-09-14T21:19:00.000Z", congestion: 46.6, toll: 3 } }] } as Parameters<typeof PredictionTooltip>[0];
    const tooltip = renderToStaticMarkup(createElement(PredictionTooltip, props));
    expect(tooltip).toContain("prediction-tooltip");
    expect(tooltip).toMatch(/15 Sep/);
    expect(tooltip).toContain("46.6%");
    expect(tooltip).toContain("RM3.00");
  });

  it("retains five-minute frames, pricing, and the Malaysia date rollover for a 12-hour prediction", () => {
    const location = { id: "ldp", code: "LDP", display_name: "LDP", base_toll: 2, road_capacity: 1000 };
    const frames = createSimulationFrames([location], "time_based", { congestion: 0, lanes: 3, baseToll: 2 }, "2026-09-14T15:00", 720);
    expect(frames).toHaveLength(145);
    expect(frames.at(-1)?.timestamp).toBe("2026-09-14T19:00:00.000Z");
    expect(formatPredictionTimestamp(frames.at(-1)!.timestamp)).toMatch(/15 Sep/);
    expect(new Set(frames.map(frame => frame.outputs[0].congestion)).size).toBeGreaterThan(1);
    expect(new Set(frames.map(frame => frame.outputs[0].dynamicToll)).size).toBeGreaterThan(1);
  });
});
