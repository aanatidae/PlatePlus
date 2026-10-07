// @vitest-environment jsdom
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { LocationProvider, LocationSelect } from "./locations";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); localStorage.clear(); });

it("offers only the four active V3 highways in the rendered Prediction selector", async () => {
  const names = ["LDP", "AKLEH", "NPE", "Grand Saga", "Simulator Toll Plaza", "DUKE", "KESAS"];
  const codes = ["LDP", "AKLEH", "NPE", "GRAND_SAGA", "SIMULATOR", "DUKE", "KESAS"];
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(names.map((display_name, index) => ({
    id: codes[index], code: codes[index], display_name, status: index > 4 ? "retired" : "operational",
  }))))));
  const select = vi.fn();
  render(<LocationProvider><LocationSelect value="LDP" onChange={select} all={false} excludeSimulator /></LocationProvider>);
  const trigger = screen.getByRole("button", { name: "Toll location" });
  await screen.findByText("LDP");
  fireEvent.click(trigger);
  const menu = await screen.findByRole("listbox", { name: "Toll location" });
  expect(within(menu).getAllByRole("option").map(option => option.textContent)).toEqual(["LDP", "AKLEH", "NPE", "Grand Saga"]);
  fireEvent.click(within(menu).getByRole("option", { name: "Grand Saga" }));
  expect(select).toHaveBeenCalledWith("GRAND_SAGA");
  expect(screen.queryByRole("listbox")).toBeNull();
});
