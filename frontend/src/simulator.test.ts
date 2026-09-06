import { describe, expect, it } from "vitest";
import { createSimulatorOutput, createTimeline, scenarioDetails } from "./simulator";

const location = { id: "ldp", code: "LDP", display_name: "Simulated LDP Toll Plaza", base_toll: 2.1, road_capacity: 1000 };

describe("simulator sandbox calculations", () => {
  it("keeps a location-specific baseline and exposes a dynamic comparison", () => {
    const output = createSimulatorOutput(location, "weekday_morning_peak", { congestion: 0, lanes: 3, baseToll: 0 });
    expect(output.baseToll).toBe(2.1);
    expect(output.dynamicToll).toBe(5.25);
    expect(output.volume).toBeLessThanOrEqual(output.capacity);
  });

  it("supports every requested named scenario preset", () => {
    expect(Object.keys(scenarioDetails)).toEqual(expect.arrayContaining([
      "weekday_evening_peak", "weekend", "event_surge", "incident", "roadworks", "low_traffic",
    ]));
  });

  it("generates a bounded local timeline from the configured range and playback speed", () => {
    const timeline = createTimeline("2026-09-06T08:00", 30, 2);
    expect(timeline).toHaveLength(5);
    expect(new Date(timeline.at(-1)!).getTime() - new Date(timeline[0]).getTime()).toBe(30 * 60_000);
  });
});
