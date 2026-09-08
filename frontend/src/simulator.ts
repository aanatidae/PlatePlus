export type SimulatorScenario = "normal" | "moderate" | "peak_hour" | "severe" | "weekday_morning_peak" | "weekday_evening_peak" | "weekend" | "event_surge" | "incident" | "roadworks" | "low_traffic" | "time_based" | "custom";
export type SimulatorLocation = { id: string; code: string; display_name: string; base_toll: number; road_capacity: number; simulation_profile?: Record<string, unknown> };
export type SimulatorParameters = { congestion: number; lanes: number; baseToll: number };
export type SimulatorOutput = { locationId: string; locationName: string; scenario: SimulatorScenario; volume: number; capacity: number; congestion: number; category: "normal" | "moderate" | "peak_hour" | "severe"; speed: number; baseToll: number; dynamicToll: number; multiplier: number };
export type SimulatorFrame = { timestamp: string; outputs: SimulatorOutput[] };
export type LocationSimulationSummary = { locationId: string; locationName: string; baselineToll: number; averageVolume: number; minVolume: number; maxVolume: number; averageCongestion: number; minCongestion: number; maxCongestion: number; peakCategory: SimulatorOutput["category"]; peakTimestamp: string; averageSpeed: number; minSpeed: number; maxSpeed: number; averageToll: number; minToll: number; maxToll: number; priceChanges: number; highestTollTimestamp: string };
export type SimulationSummary = { locations: LocationSimulationSummary[]; networkAverageCongestion: number; mostCongestedLocation: LocationSimulationSummary | null; highestCongestion: number; highestTrafficLocation: LocationSimulationSummary | null; highestTollLocation: LocationSimulationSummary | null };
export type PlaybackStatus = "idle" | "running" | "completed";

export const scenarioDetails: Record<Exclude<SimulatorScenario, "custom">, { title: string; description: string }> = {
  normal: { title: "Normal traffic", description: "Free-flowing toll approach" }, moderate: { title: "Moderate traffic", description: "Steady weekday demand" }, peak_hour: { title: "Peak hour", description: "Rush-hour demand" }, severe: { title: "Severe congestion", description: "Near-capacity road demand" }, weekday_morning_peak: { title: "Weekday morning peak", description: "Inbound commuter demand" }, weekday_evening_peak: { title: "Weekday evening peak", description: "Outbound commuter demand" }, weekend: { title: "Weekend traffic", description: "Later, flatter leisure demand" }, event_surge: { title: "Event surge", description: "Temporary venue or event demand" }, incident: { title: "Accident / incident", description: "Temporary constrained road flow" }, roadworks: { title: "Roadworks", description: "Reduced capacity across the window" }, low_traffic: { title: "Low traffic", description: "Off-peak light demand" }, time_based: { title: "Time-based traffic", description: "Estimated Malaysia daily profile from simulated time" },
};

/** Simulated prototype estimate, not a live or official Malaysian traffic feed. */
export const malaysiaDailyTrafficProfile: SimulatorOutput["category"][] = ["normal", "normal", "normal", "normal", "normal", "moderate", "peak_hour", "severe", "severe", "peak_hour", "moderate", "moderate", "moderate", "moderate", "moderate", "moderate", "peak_hour", "severe", "severe", "peak_hour", "moderate", "moderate", "normal", "normal"];
const categoryTargets = { normal: 20, moderate: 46, peak_hour: 70, severe: 88 } as const;

const clamp = (value: number, low = 0, high = 100) => Math.min(high, Math.max(low, value));
const gaussian = (value: number, center: number, width: number) => Math.exp(-((value - center) ** 2) / (2 * width ** 2));
const hash = (value: string) => Array.from(value).reduce((sum, character) => (sum * 31 + character.charCodeAt(0)) >>> 0, 17);
export function scenarioTitle(scenario: SimulatorScenario) { return scenario === "custom" ? "Custom scenario" : scenarioDetails[scenario].title; }

/** Frame timestamps are Malaysia time; playback speed deliberately does not affect frame data. */
export function createTimeline(start: string, durationMinutes: number, _playbackSpeed?: number) {
  const isoStart = start.includes("Z") || /[+-]\d\d:\d\d$/.test(start) ? start : `${start}:00+08:00`;
  const first = new Date(isoStart).getTime();
  return Array.from({ length: Math.max(1, Math.floor(durationMinutes / 5) + 1) }, (_, index) => new Date(first + index * 300_000).toISOString());
}

/** Bounded playback transition; never wraps the final simulation frame back to zero. */
export function advancePlayback(frameIndex: number, frameCount: number): { frameIndex: number; status: PlaybackStatus } {
  if (frameCount <= 1 || frameIndex >= frameCount - 1) return { frameIndex: Math.max(0, frameCount - 1), status: "completed" };
  const nextIndex = frameIndex + 1;
  return { frameIndex: nextIndex, status: nextIndex === frameCount - 1 ? "completed" : "running" };
}

function locationProfile(location: SimulatorLocation) {
  const profile = location.simulation_profile ?? {};
  const defaults: Record<string, { baseline: number; peaks: number[]; freeFlow: number; floor: number }> = { LDP: { baseline: .48, peaks: [7.5, 8.5, 17.5, 18.5], freeFlow: 72, floor: 20 }, DUKE: { baseline: .56, peaks: [7, 8, 17, 18], freeFlow: 68, floor: 18 }, KESAS: { baseline: .38, peaks: [7.5, 17.5], freeFlow: 70, floor: 22 }, NPE: { baseline: .46, peaks: [8, 18], freeFlow: 74, floor: 22 } };
  const fallback = defaults[location.code] ?? { baseline: .48, peaks: [8, 18], freeFlow: 72, floor: 20 };
  return { baseline: Number(profile.baseline_demand ?? fallback.baseline), peaks: (profile.peak_hours as number[] | undefined)?.map(Number) ?? fallback.peaks, freeFlow: Number(profile.speed_free_flow_kmh ?? fallback.freeFlow), floor: Number(profile.speed_floor_kmh ?? fallback.floor), variation: Number(profile.variation ?? .05) };
}
function malaysiaHour(timestamp: string) { const pieces = new Intl.DateTimeFormat("en-GB", { timeZone: "Asia/Kuala_Lumpur", hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).formatToParts(new Date(timestamp)); const read = (type: string) => Number(pieces.find(piece => piece.type === type)?.value ?? 0); return read("hour") + read("minute") / 60; }
function categoryFor(congestion: number): SimulatorOutput["category"] { return congestion > 80 ? "severe" : congestion > 60 ? "peak_hour" : congestion > 30 ? "moderate" : "normal"; }
function multiplierFor(category: SimulatorOutput["category"]) { return category === "severe" ? 2.5 : category === "peak_hour" ? 2 : category === "moderate" ? 1.5 : 1; }
export function timeBasedTrafficTarget(timestamp: string) { const hour = malaysiaHour(timestamp); const start = Math.floor(hour); const progress = hour - start; const transition = clamp((progress - .66) / .34, 0, 1); const eased = transition * transition * (3 - 2 * transition); const current = malaysiaDailyTrafficProfile[start]; const next = malaysiaDailyTrafficProfile[(start + 1) % 24]; return categoryTargets[current] + (categoryTargets[next] - categoryTargets[current]) * eased; }
export function timeBasedTrafficCategory(timestamp: string) { return categoryFor(timeBasedTrafficTarget(timestamp)); }

function congestionForFrame(location: SimulatorLocation, scenario: SimulatorScenario, parameters: SimulatorParameters, timestamp: string, progress: number) {
  const profile = locationProfile(location); const hour = malaysiaHour(timestamp); const profilePeak = profile.peaks.reduce((total, peak) => total + gaussian(hour, peak, 1.15), 0); const dayDemand = profile.baseline * 100 + profilePeak * 24; const variation = Math.sin((new Date(timestamp).getTime() / 300_000 + hash(location.code) % 29) * .81) * profile.variation * 100; const morning = gaussian(hour, 8.2, 1.2); const evening = gaussian(hour, 17.8, 1.35); const midday = gaussian(hour, 13, 3.5); const surge = gaussian(progress, .5, .16); let congestion: number; let capacityFactor = 1;
  switch (scenario) {
    case "normal": congestion = 18 + dayDemand * .28 + variation; break;
    case "moderate": congestion = 31 + dayDemand * .42 + variation; break;
    case "peak_hour": congestion = 52 + dayDemand * .35 + (morning + evening) * 13 + variation; break;
    case "severe": congestion = 72 + dayDemand * .23 + (morning + evening) * 10 + variation; break;
    case "weekday_morning_peak": congestion = 32 + dayDemand * .2 + morning * 48 + variation; break;
    case "weekday_evening_peak": congestion = 34 + dayDemand * .2 + evening * 49 + variation; break;
    case "weekend": congestion = 24 + dayDemand * .22 + gaussian(hour, 14, 3) * 18 + variation; break;
    case "event_surge": congestion = 35 + dayDemand * .24 + surge * 52 + variation; break;
    case "incident": congestion = 37 + dayDemand * .25 + surge * 58 + variation; capacityFactor = .68; break;
    case "roadworks": congestion = 42 + dayDemand * .31 + midday * 12 + variation; capacityFactor = .7; break;
    case "low_traffic": congestion = 8 + dayDemand * .16 + variation * .35; break;
    case "time_based": congestion = timeBasedTrafficTarget(timestamp) + (profile.baseline - .48) * 18 + variation; break;
    case "custom": congestion = parameters.congestion / Math.max(1, location.road_capacity * Math.min(4, Math.max(1, parameters.lanes)) / 4) * 100 + (profilePeak * 10 + variation) * .45; capacityFactor = Math.min(4, Math.max(1, parameters.lanes)) / 4; break;
  }
  return { congestion: Number(clamp(congestion).toFixed(1)), capacityFactor, profile };
}

export function createSimulationFrames(locations: SimulatorLocation[], scenario: SimulatorScenario, parameters: SimulatorParameters, start: string, durationMinutes: number): SimulatorFrame[] {
  const timeline = createTimeline(start, durationMinutes);
  return timeline.map((timestamp, frameIndex) => ({ timestamp, outputs: locations.map(location => { const { congestion, capacityFactor, profile } = congestionForFrame(location, scenario, parameters, timestamp, timeline.length === 1 ? 0 : frameIndex / (timeline.length - 1)); const capacity = Math.max(1, Math.round(location.road_capacity * capacityFactor)); const category = categoryFor(congestion); const multiplier = multiplierFor(category); const baseToll = scenario === "custom" ? parameters.baseToll : Number(location.base_toll); return { locationId: location.id, locationName: location.display_name, scenario, volume: Math.min(capacity, Math.round(capacity * congestion / 100)), capacity, congestion, category, speed: Number(Math.max(profile.floor, profile.freeFlow - congestion * .55).toFixed(1)), baseToll, dynamicToll: Number((baseToll * multiplier).toFixed(2)), multiplier }; }) }));
}

/** Compatibility helper for the retired single-snapshot component; new UI uses createSimulationFrames. */
export function createSimulatorOutput(location: SimulatorLocation, scenario: SimulatorScenario, parameters: SimulatorParameters): SimulatorOutput {
  return createSimulationFrames([location], scenario, parameters, "2026-09-07T08:00", 0)[0].outputs[0];
}

const average = (values: number[]) => values.reduce((sum, value) => sum + value, 0) / values.length;
const categoryRank = { normal: 0, moderate: 1, peak_hour: 2, severe: 3 } as const;

/** Summaries consume stored frame data only; they never rerun the traffic model. */
export function summarizeSimulation(frames: SimulatorFrame[]): SimulationSummary {
  const byLocation = new Map<string, { name: string; values: Array<SimulatorOutput & { timestamp: string }> }>();
  for (const frame of frames) for (const output of frame.outputs) {
    const item = byLocation.get(output.locationId) ?? { name: output.locationName, values: [] };
    item.values.push({ ...output, timestamp: frame.timestamp }); byLocation.set(output.locationId, item);
  }
  const locations = Array.from(byLocation, ([locationId, item]) => {
    const values = item.values; const volumes = values.map(value => value.volume); const congestions = values.map(value => value.congestion); const speeds = values.map(value => value.speed); const tolls = values.map(value => value.dynamicToll); const peak = values.reduce((best, value) => value.congestion > best.congestion ? value : best); const highToll = values.reduce((best, value) => value.dynamicToll > best.dynamicToll ? value : best); const peakCategory = values.reduce((best, value) => categoryRank[value.category] > categoryRank[best] ? value.category : best, "normal" as SimulatorOutput["category"]); const priceChanges = values.slice(1).filter((value, index) => value.dynamicToll !== values[index].dynamicToll).length;
    return { locationId, locationName: item.name, baselineToll: values[0].baseToll, averageVolume: average(volumes), minVolume: Math.min(...volumes), maxVolume: Math.max(...volumes), averageCongestion: average(congestions), minCongestion: Math.min(...congestions), maxCongestion: Math.max(...congestions), peakCategory, peakTimestamp: peak.timestamp, averageSpeed: average(speeds), minSpeed: Math.min(...speeds), maxSpeed: Math.max(...speeds), averageToll: average(tolls), minToll: Math.min(...tolls), maxToll: Math.max(...tolls), priceChanges, highestTollTimestamp: highToll.timestamp };
  });
  const mostCongestedLocation = locations.reduce<LocationSimulationSummary | null>((best, value) => !best || value.maxCongestion > best.maxCongestion ? value : best, null);
  const highestTrafficLocation = locations.reduce<LocationSimulationSummary | null>((best, value) => !best || value.maxVolume > best.maxVolume ? value : best, null);
  const highestTollLocation = locations.reduce<LocationSimulationSummary | null>((best, value) => !best || value.maxToll > best.maxToll ? value : best, null);
  return { locations, networkAverageCongestion: locations.length ? average(locations.map(location => location.averageCongestion)) : 0, mostCongestedLocation, highestCongestion: mostCongestedLocation?.maxCongestion ?? 0, highestTrafficLocation, highestTollLocation };
}
