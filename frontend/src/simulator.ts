export type SimulatorScenario =
  | "normal"
  | "moderate"
  | "peak_hour"
  | "severe"
  | "weekday_morning_peak"
  | "weekday_evening_peak"
  | "weekend"
  | "event_surge"
  | "incident"
  | "roadworks"
  | "low_traffic"
  | "custom";

export type SimulatorLocation = {
  id: string;
  code: string;
  display_name: string;
  base_toll: number;
  road_capacity: number;
};

export type SimulatorParameters = { congestion: number; lanes: number; baseToll: number };
export type SimulatorOutput = {
  locationId: string;
  locationName: string;
  scenario: SimulatorScenario;
  volume: number;
  capacity: number;
  congestion: number;
  speed: number;
  baseToll: number;
  dynamicToll: number;
  multiplier: number;
};

export const scenarioDetails: Record<Exclude<SimulatorScenario, "custom">, { title: string; congestion: number; speed: number; multiplier: number; description: string }> = {
  normal: { title: "Normal traffic", congestion: 24, speed: 70, multiplier: 1, description: "Free-flowing toll approach" },
  moderate: { title: "Moderate traffic", congestion: 55, speed: 48, multiplier: 1.5, description: "Steady weekday demand" },
  peak_hour: { title: "Peak hour", congestion: 76, speed: 31, multiplier: 2, description: "Rush-hour demand" },
  severe: { title: "Severe congestion", congestion: 92, speed: 21, multiplier: 2.5, description: "Near-capacity road demand" },
  weekday_morning_peak: { title: "Weekday morning peak", congestion: 84, speed: 27, multiplier: 2.5, description: "Inbound commuter demand" },
  weekday_evening_peak: { title: "Weekday evening peak", congestion: 88, speed: 24, multiplier: 2.5, description: "Outbound commuter demand" },
  weekend: { title: "Weekend traffic", congestion: 42, speed: 57, multiplier: 1.5, description: "Moderate leisure demand" },
  event_surge: { title: "Event surge", congestion: 91, speed: 22, multiplier: 2.5, description: "Short-lived venue or event demand" },
  incident: { title: "Accident / incident", congestion: 95, speed: 18, multiplier: 2.5, description: "Incident-constrained road flow" },
  roadworks: { title: "Roadworks", congestion: 80, speed: 29, multiplier: 2, description: "Lane restrictions reduce throughput" },
  low_traffic: { title: "Low traffic", congestion: 16, speed: 76, multiplier: 1, description: "Off-peak light demand" },
};

function codeAdjustment(code: string) {
  return (Array.from(code).reduce((sum, character) => sum + character.charCodeAt(0), 0) % 9) - 4;
}

export function scenarioTitle(scenario: SimulatorScenario) {
  return scenario === "custom" ? "Custom scenario" : scenarioDetails[scenario].title;
}

export function createSimulatorOutput(location: SimulatorLocation, scenario: SimulatorScenario, parameters: SimulatorParameters): SimulatorOutput {
  const detail = scenario === "custom" ? null : scenarioDetails[scenario];
  const capacity = Math.max(1, scenario === "custom" ? Math.round(Number(location.road_capacity) * Math.min(4, Math.max(1, parameters.lanes)) / 4) : Number(location.road_capacity));
  const baseToll = scenario === "custom" ? parameters.baseToll : Number(location.base_toll);
  const congestion = Math.max(0, Math.min(100, Number((detail ? detail.congestion + codeAdjustment(location.code) : (parameters.congestion / capacity) * 100).toFixed(1))));
  const multiplier = detail?.multiplier ?? (congestion > 80 ? 2.5 : congestion > 60 ? 2 : congestion > 30 ? 1.5 : 1);
  const volume = Math.min(capacity, Math.round(capacity * congestion / 100));
  const speed = detail ? Math.max(15, detail.speed - Math.round(codeAdjustment(location.code) / 2)) : Math.max(18, Math.round(82 - congestion * .62));
  return { locationId: location.id, locationName: location.display_name, scenario, volume, capacity, congestion, speed, baseToll, dynamicToll: Number((baseToll * multiplier).toFixed(2)), multiplier };
}

export function createTimeline(start: string, durationMinutes: number, playbackSpeed: number) {
  const first = new Date(start).getTime();
  const stepMinutes = Math.max(5, 15 / playbackSpeed);
  const count = Math.max(1, Math.floor(durationMinutes / stepMinutes) + 1);
  return Array.from({ length: count }, (_, index) => new Date(first + index * stepMinutes * 60_000).toISOString());
}
