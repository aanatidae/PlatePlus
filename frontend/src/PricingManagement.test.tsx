// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import PricingManagement from "./PricingManagement";
import { readRules, validateRules } from "./pricingRules";

vi.mock("./App", () => ({ apiHeaders: () => ({ Authorization: "Bearer test" }) }));
vi.mock("./locations", () => ({ useLocations: () => ({ locations: [] }), LocationSelect: () => null }));
const initial = [
  ["normal", "low", "0.00", "30.00", "1.00"],
  ["moderate", "moderate", "30.01", "60.00", "1.50"],
  ["peak_hour", "high", "60.01", "80.00", "2.00"],
  ["severe", "severe", "80.01", "100.00", "2.50"],
].map(([scenario, congestion_category, minimum_percentage, maximum_percentage, multiplier], index) => ({ id: String(index), scenario, congestion_category, minimum_percentage, maximum_percentage, multiplier }));
function mockApi(error?: unknown) {
  const fetch = vi.fn(async (url: string, init?: RequestInit) => {
    if (init?.method === "PUT") {
      if (error) return new Response(JSON.stringify(error), { status: 422 });
      return new Response(JSON.stringify(JSON.parse(String(init.body)).rules.map((rule: object, i: number) => ({ ...initial[i], ...rule }))));
    }
    return new Response(JSON.stringify(url.endsWith("pricing-rules") ? initial : { minimum_toll: "0.50", maximum_toll_multiplier: "3.00", minimum_price_change_minutes: 5, pricing_hysteresis_percentage: "2.00" }));
  });
  vi.stubGlobal("fetch", fetch);
  return fetch;
}
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("congestion pricing form", () => {
  it("accepts hundredth boundaries and decimal multipliers, sends all numeric rules and retains the saved response", async () => {
    const refreshed = vi.fn(); window.addEventListener("dashboard-refresh", refreshed);
    const fetch = mockApi(); render(<PricingManagement />);
    await screen.findByLabelText("moderate minimum");
    for (const [label, value] of [["moderate minimum", "30.01"], ["peak_hour minimum", "60.01"], ["severe minimum", "80.01"], ["peak_hour multiplier", "2.50"], ["severe multiplier", "3.00"]]) {
      const input = screen.getByLabelText(label) as HTMLInputElement;
      fireEvent.change(input, { target: { value } });
      expect(input.step).toBe("0.01"); expect(input.checkValidity()).toBe(true);
      if (label.includes("minimum")) { expect(input.min).toBe("0"); expect(input.max).toBe("100"); }
    }
    fireEvent.click(screen.getByText("Save pricing rules"));
    await screen.findByText("Pricing rules saved and recorded in the audit log.");
    const call = fetch.mock.calls.find(([, init]) => init?.method === "PUT")!;
    const payload = JSON.parse(String(call[1]?.body));
    expect(payload.rules).toHaveLength(4);
    expect(payload.rules.map((r: { minimum_percentage: number }) => r.minimum_percentage)).toEqual([0, 30.01, 60.01, 80.01]);
    expect(payload.rules.map((r: { multiplier: number }) => r.multiplier)).toEqual([1, 1.5, 2.5, 3]);
    expect((screen.getByLabelText("peak_hour multiplier") as HTMLInputElement).valueAsNumber).toBe(2.5);
    expect(fetch.mock.calls.filter(([, init]) => !init?.method)).toHaveLength(2);
    expect(refreshed).toHaveBeenCalledTimes(1);
    window.removeEventListener("dashboard-refresh", refreshed);
  });
  it("renders structured backend errors as useful text", async () => {
    mockApi({ detail: [{ loc: ["body", "rules", 1, "minimum_percentage"], msg: "Must begin at 30.01%" }] });
    render(<PricingManagement />); await screen.findByLabelText("moderate minimum");
    fireEvent.click(screen.getByText("Save pricing rules"));
    await screen.findByText("Unable to save pricing rules: Moderate minimum percentage: Must begin at 30.01%");
    expect(document.body.textContent).not.toContain("[object Object]");
  });
  it("rejects integer gaps before making a save request", async () => {
    const fetch = mockApi(); render(<PricingManagement />); await screen.findByLabelText("moderate minimum");
    fireEvent.change(screen.getByLabelText("moderate minimum"), { target: { value: "31" } });
    fireEvent.click(screen.getByText("Save pricing rules"));
    await waitFor(() => expect(screen.getByRole("status").textContent).toContain("30.01%"));
    expect(fetch.mock.calls.some(([, init]) => init?.method === "PUT")).toBe(false);
  });
  it.each([
    ["minimum_percentage", 30, 1], ["minimum_percentage", 35, 1], ["maximum_percentage", 105, 3],
    ["multiplier", -1, 2], ["minimum_percentage", 30.001, 1], ["maximum_percentage", 99.99, 3],
  ])("rejects invalid %s=%s", (field, value, index) => {
    const rules = readRules(initial); rules[index] = { ...rules[index], [field]: value };
    expect(validateRules(rules)).toBeTruthy();
  });
});
