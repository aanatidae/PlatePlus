// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { App } from "./App";

vi.mock("./NetworkOverview", () => ({ default: () => <main>Overview content</main> }));
vi.mock("./PricingManagement", () => ({ default: () => <main>Pricing content</main> }));
vi.mock("./Prediction", () => ({ default: () => <main>Prediction content</main> }));
vi.mock("./locations", () => ({
  LocationProvider: ({ children }: { children: React.ReactNode }) => children,
  LocationSelect: () => null,
  useLocations: () => ({ selected: "all", select: vi.fn(), locations: [], ready: true, error: "" }),
  getJson: async () => ({ evaluation: {
    detector: { accuracy_percent: 93.1 }, ocr: { exact_matches: 37, held_out_samples: 44, exact_match_accuracy_percent: 84.1 },
    origin: { samples: 32, exact_matches: 25, exact_match_percent: 78.1, cross_country_errors: 0, ambiguous_rejected: 7, unsupported_rejected: 8, note: "Synthetic text fixture only, not field accuracy." },
  }, known_failure_conditions: ["Unknown origin is safely rejected."] }),
}));

beforeEach(() => {
  sessionStorage.setItem("capstone-alpr.admin-session", JSON.stringify({ access_token: "test", admin: { display_name: "Demo Administrator" } }));
  history.replaceState({}, "", "/dashboard");
});
afterEach(() => { cleanup(); sessionStorage.clear(); });

describe("three-page dashboard structure", () => {
  it("navigates only Overview, pricing management and Prediction", async () => {
    render(<App />);
    const nav = within(screen.getByRole("navigation", { name: "Administrator navigation" }));
    expect(nav.getAllByRole("link").map(link => link.textContent)).toEqual(["Overview", "Dynamic Pricing Management", "Prediction"]);
    fireEvent.click(nav.getByRole("link", { name: "Prediction" }));
    expect(await screen.findByText("Prediction content")).toBeTruthy();
    expect(location.pathname).toBe("/prediction");
    fireEvent.click(nav.getByRole("link", { name: "Dynamic Pricing Management" }));
    expect(await screen.findByText("Pricing content")).toBeTruthy();
    expect(location.pathname).toBe("/pricing");
  });
  it.each(["/recognition", "/simulator", "/webcam", "/demo", "/intelligence", "/traffic"])("redirects retired %s to Overview", async route => {
    history.replaceState({}, "", route);
    render(<App />);
    await waitFor(() => expect(location.pathname).toBe("/dashboard"));
    expect(screen.getByText("Overview content")).toBeTruthy();
  });
  it("opens evaluation evidence in a modal, closes on Escape, and restores focus without navigating", async () => {
    render(<App />);
    const trigger = screen.getByRole("button", { name: "Model performance" });
    fireEvent.click(trigger);
    const modal = await screen.findByRole("dialog", { name: "Model performance" });
    expect(await within(modal).findByText("Plate-origin classification")).toBeTruthy();
    expect(within(modal).getByText(/not field accuracy/)).toBeTruthy();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("dialog")).toBeNull();
    await waitFor(() => expect(document.activeElement).toBe(trigger));
    expect(location.pathname).toBe("/dashboard");
  });
});
