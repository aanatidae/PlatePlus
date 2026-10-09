// @vitest-environment jsdom
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import NetworkOverview from "./NetworkOverview";

const fixture = vi.hoisted(() => ({ data: null as any, locations: [] as any[] }));
vi.mock("./App", () => ({ apiHeaders: () => ({ Authorization: "Bearer fixture" }) }));
vi.mock("./locations", () => ({
  useLocations: () => ({ locations: fixture.locations, selected: "sim", select: vi.fn() }),
  locationPath: (path: string) => path,
  useFeed: (path: string) => ({ data: path.startsWith("/api/live/overview") ? fixture.data : path.endsWith("/feed") ? { running: false } : [], error: "", receivedAt: Date.now() }),
}));
afterEach(() => cleanup());

it("renders backend congestion and toll together, including arrival and expiry feedback", () => {
  const location = { id: "sim", code: "SIMULATOR", display_name: "Simulator Toll Plaza", highway_or_route: "LDP", base_toll: 2 };
  fixture.locations = [location];
  const data = (congestion: number, toll: number, category: string, multiplier: number) => {
    const telemetry = { measured_at: new Date().toISOString(), congestion_percentage: congestion, current_toll_price: toll, congestion_category: category, base_toll_price: 2, congestion_multiplier: multiplier, active_crossings: congestion / 10, vehicles_per_hour: congestion / 10, road_capacity: 10, average_speed_kmh: null, camera_status: "online", system_status: "healthy" };
    return { locations: [{ location, telemetry, telemetry_source: "webcam_alpr" }], metrics: { detections: 0, transactions: 0, successful_transactions: 0, revenue: 0, locations_online: 1, locations_total: 1, severe_locations: 0, cameras_offline: 0 }, detections: { items: [] }, transactions: { items: [] }, live: { traffic: telemetry, price: { amount: toll } } };
  };
  fixture.data = data(30, 2, "low", 1);
  const view = render(<NetworkOverview />);
  expect(screen.getAllByText("RM2.00").length).toBeGreaterThan(0);
  window.dispatchEvent(new Event("simulator-crossing-accepted"));
  fixture.data = data(40, 3, "moderate", 1.5);
  view.rerender(<NetworkOverview />);
  expect(screen.getAllByText("40.0%").length).toBeGreaterThan(0);
  expect(screen.getAllByText("RM3.00").length).toBeGreaterThan(0);
  expect(screen.getByText("Congestion increased to 40% → Toll adjusted from RM2.00 to RM3.00")).toBeTruthy();
  fixture.data = data(20, 2, "low", 1);
  view.rerender(<NetworkOverview />);
  expect(screen.getByText("Congestion decreased to 20% → Toll adjusted from RM3.00 to RM2.00")).toBeTruthy();
});
