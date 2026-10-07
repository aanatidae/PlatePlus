// @vitest-environment jsdom
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { PricingHistory } from "./PricingHistory";

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => children,
  LineChart: () => <div>History chart</div>, Line: () => null, Tooltip: () => null,
  XAxis: () => null, YAxis: () => null,
}));
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

it("loads history only on expansion, filters in Malaysia time, changes location without stale data, and never writes", async () => {
  const fetch = vi.fn(async (url: string, _init?: RequestInit) => {
    const amount = url.includes("location_id=npe") ? "4.20" : "3.60";
    const data = url.includes("history/analytics") ? { series: [{ date: "2026-10-07", average_congestion: "45.00", average_toll: amount }] }
      : url.includes("toll-prices") ? [{ id: "price", effective_at: "2026-10-07T01:00:00Z", amount, congestion_category: "moderate", rule_version: "v3" }]
      : [{ id: "audit", created_at: "2026-10-07T01:00:00Z", action: "pricing_rules_updated" }];
    return new Response(JSON.stringify(data));
  });
  vi.stubGlobal("fetch", fetch);
  const { container, rerender } = render(<PricingHistory locationId="akleh" locationName="AKLEH" />);
  expect(fetch).not.toHaveBeenCalled();
  const details = container.querySelector("details")!;
  details.open = true;
  fireEvent(details, new Event("toggle"));
  const traffic = await screen.findByRole("table", { name: "Recorded daily traffic and toll averages" });
  expect(within(traffic).getByText("45.0%")).toBeTruthy();
  expect(within(traffic).getByText("RM3.60")).toBeTruthy();
  expect(screen.getByText("pricing rules updated")).toBeTruthy();
  fireEvent.change(screen.getByLabelText("From (Malaysia)"), { target: { value: "2026-10-07" } });
  await waitFor(() => expect(fetch.mock.calls.some(([url]) => new URL(url).searchParams.get("start_at") === "2026-10-07T00:00:00+08:00")).toBe(true));
  rerender(<PricingHistory locationId="npe" locationName="NPE" />);
  await waitFor(() => expect(within(screen.getByRole("table", { name: "Recorded daily traffic and toll averages" })).getByText("RM4.20")).toBeTruthy());
  expect(screen.queryByText("RM3.60")).toBeNull();
  expect(fetch.mock.calls.every(([, init]) => !init?.method || init.method === "GET")).toBe(true);
});

it("shows missing recorded history without inventing congestion or toll values", async () => {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => new Response(JSON.stringify(url.includes("analytics") ? { series: [] } : []))));
  const { container } = render(<PricingHistory locationId="ldp" locationName="LDP" />);
  const details = container.querySelector("details")!;
  details.open = true;
  fireEvent(details, new Event("toggle"));
  expect(await screen.findByText("No recorded history matches these filters.")).toBeTruthy();
  expect(screen.queryByText("RM0.00")).toBeNull();
});
