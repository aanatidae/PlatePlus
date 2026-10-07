// @vitest-environment jsdom
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import NetworkOverview from "./NetworkOverview";
const state = vi.hoisted(() => ({ locations: [] }));

vi.mock("./App", () => ({ apiHeaders: () => ({ Authorization: "Bearer test" }) }));
vi.mock("./locations", () => ({
  useLocations: () => ({ locations: state.locations, selected: "all", select: vi.fn() }),
  locationPath: (path: string) => path,
  useFeed: (path: string) => ({ error: "", receivedAt: Date.now(), data:
    path.includes("/alerts") ? [
      { id: "a", title: "Active origin rollup", status: "active", acknowledged_at: null, message: "3 patterns safely rejected", severity: "warning", started_at: "2026-10-07T01:00:00Z" },
      { id: "r", title: "Recovered origin rollup", status: "resolved", acknowledged_at: null, message: "Window cleared", severity: "warning", started_at: "2026-10-07T01:00:00Z" },
      { id: "k", title: "Acknowledged origin rollup", status: "acknowledged", acknowledged_at: "2026-10-07T01:00:00Z", message: "Acknowledged", severity: "warning", started_at: "2026-10-07T01:00:00Z" },
    ] : path.includes("/events") ? [] : path.includes("/demo/feed") ? { running: false } : {
      locations: [], live: { traffic: null, price: null },
      metrics: { detections: 0, transactions: 0, successful_transactions: 0, revenue: 0, locations_online: 0, locations_total: 0, locations_reporting: 0, severe_locations: 0, cameras_offline: 0 },
      detections: { items: [] }, transactions: { items: [] },
    },
  }),
}));
afterEach(cleanup);

it("removes recovered and acknowledged incidents from active issues while retaining their history", () => {
  render(<NetworkOverview />);
  const active = within(screen.getByRole("heading", { name: "Current operational issues" }).closest("section")!);
  expect(active.getByText("Active origin rollup")).toBeTruthy();
  expect(active.queryByText("Recovered origin rollup")).toBeNull();
  expect(active.queryByText("Acknowledged origin rollup")).toBeNull();
  const history = within(screen.getByRole("heading", { name: "Recorded alerts and transitions" }).closest("section")!);
  expect(history.getByText(/Recovered origin rollup/)).toBeTruthy();
  expect(history.getByText(/Acknowledged origin rollup/)).toBeTruthy();
});
