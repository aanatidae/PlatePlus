// @vitest-environment jsdom
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import PricingManagement from "./PricingManagement";
import { LocationProvider, useFeed } from "./locations";

vi.mock("./App", () => ({ apiHeaders: () => ({ Authorization: "Bearer test" }) }));
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

function CurrentPrice() {
  const { data } = useFeed<{ telemetry: { current_toll_price: string } }>("/api/locations/p/live");
  return <output aria-label="canonical current toll">{data ? `RM${data.telemetry.current_toll_price}` : "Loading"}</output>;
}

it("a successful policy save immediately refreshes and renders backend canonical pricing", async () => {
  let price = "3.00";
  let liveReads = 0;
  const rules = [
    { id: "0", scenario: "normal", congestion_category: "low", minimum_percentage: "0", maximum_percentage: "30", multiplier: "1" },
    { id: "1", scenario: "moderate", congestion_category: "moderate", minimum_percentage: "30.01", maximum_percentage: "60", multiplier: "1.5" },
    { id: "2", scenario: "peak_hour", congestion_category: "high", minimum_percentage: "60.01", maximum_percentage: "80", multiplier: "2" },
    { id: "3", scenario: "severe", congestion_category: "severe", minimum_percentage: "80.01", maximum_percentage: "100", multiplier: "2.5" },
  ];
  vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
    if (url.endsWith("/live")) { liveReads++; return new Response(JSON.stringify({ telemetry: { current_toll_price: price } })); }
    if (init?.method === "PUT") {
      price = "4.00"; // Price comes from the backend response flow, not React multiplication.
      return new Response(JSON.stringify(JSON.parse(String(init.body)).rules.map((row: object, i: number) => ({ ...rules[i], ...row }))));
    }
    const data = url.endsWith("pricing-rules") ? rules : url.endsWith("settings") ? {
      minimum_toll: ".50", maximum_toll_multiplier: "3", minimum_price_change_minutes: 5, pricing_hysteresis_percentage: "2",
    } : [{ id: "p", code: "PENCHALA", display_name: "Test Plaza", base_toll: "2.00" }];
    return new Response(JSON.stringify(data));
  }));
  render(<LocationProvider><PricingManagement /><CurrentPrice /></LocationProvider>);
  await screen.findByText("RM3.00");
  await screen.findByLabelText("moderate multiplier");
  fireEvent.change(screen.getByLabelText("moderate multiplier"), { target: { value: "2.00" } });
  fireEvent.click(screen.getByText("Save pricing rules"));
  await screen.findByText("Pricing rules saved and recorded in the audit log.");
  await screen.findByText("RM4.00");
  expect(liveReads).toBe(2); // Immediate invalidation, without waiting for the five-second poll.
});
