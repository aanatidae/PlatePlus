import { describe, expect, it } from "vitest";
import { createSimulationFrames, createTimeline, scenarioDetails } from "./simulator";

const ldp = { id: "ldp", code: "LDP", display_name: "Simulated LDP Toll Plaza", base_toll: 2, road_capacity: 1000, simulation_profile: { baseline_demand: .48, peak_hours: [8, 18], speed_free_flow_kmh: 72, speed_floor_kmh: 20, variation: .05 } };
const duke = { id: "duke", code: "DUKE", display_name: "Simulated DUKE Toll Plaza", base_toll: 2.4, road_capacity: 1200, simulation_profile: { baseline_demand: .56, peak_hours: [7, 17], speed_free_flow_kmh: 68, speed_floor_kmh: 18, variation: .08 } };
const parameters = { congestion: 550, lanes: 3, baseToll: 2 };
const outputs = (scenario: keyof typeof scenarioDetails | "custom", start = "2026-09-07T07:00", duration = 240) => createSimulationFrames([ldp], scenario, parameters, start, duration).map(frame => frame.outputs[0]);

describe("time-dependent simulator frames", () => {
  it("uses a fixed five-minute simulation interval independent of playback", () => {
    const timeline = createTimeline("2026-09-07T07:00", 240);
    expect(timeline).toHaveLength(49);
    expect(new Date(timeline[1]).getTime() - new Date(timeline[0]).getTime()).toBe(5 * 60_000);
  });

  it("changes a moderate run's traffic, congestion, and speed over frames", () => {
    const frames = outputs("moderate");
    expect(new Set(frames.map(frame => frame.volume)).size).toBeGreaterThan(1);
    expect(new Set(frames.map(frame => frame.congestion)).size).toBeGreaterThan(1);
    expect(new Set(frames.map(frame => frame.speed)).size).toBeGreaterThan(1);
  });

  it("is deterministic for the same configuration", () => {
    expect(outputs("weekday_morning_peak")).toEqual(outputs("weekday_morning_peak"));
  });

  it("updates pricing when time-dependent congestion crosses a band", () => {
    const frames = outputs("weekday_morning_peak", "2026-09-07T06:00", 240);
    expect(new Set(frames.map(frame => frame.dynamicToll)).size).toBeGreaterThan(1);
    expect(new Set(frames.map(frame => frame.category)).size).toBeGreaterThan(1);
  });

  it("gives generated locations independent frame states at the same timestamp", () => {
    const firstFrame = createSimulationFrames([ldp, duke], "moderate", parameters, "2026-09-07T07:00", 60)[0];
    expect(firstFrame.outputs[0].congestion).not.toBe(firstFrame.outputs[1].congestion);
    expect(firstFrame.outputs[0].speed).not.toBe(firstFrame.outputs[1].speed);
  });

  it("models scenario-specific time patterns and capacity constraints", () => {
    const morning = outputs("weekday_morning_peak", "2026-09-07T06:00", 240);
    expect(Math.max(...morning.map(frame => frame.congestion))).toBeGreaterThan(morning[0].congestion);
    expect(morning.at(-1)!.congestion).toBeLessThan(Math.max(...morning.map(frame => frame.congestion)));
    const incident = outputs("incident", "2026-09-07T07:00", 120);
    const roadworks = outputs("roadworks", "2026-09-07T07:00", 120);
    expect(Math.min(...incident.map(frame => frame.capacity))).toBe(680);
    expect(Math.min(...roadworks.map(frame => frame.capacity))).toBe(700);
    expect(Math.max(...outputs("low_traffic").map(frame => frame.congestion))).toBeLessThan(35);
  });

  it("retains every requested named scenario preset", () => {
    expect(Object.keys(scenarioDetails)).toEqual(expect.arrayContaining(["weekday_evening_peak", "weekend", "event_surge", "incident", "roadworks", "low_traffic"]));
  });
});
