import { describe, expect, it } from "vitest";
import { nextEnabledOptionIndex, type PlatePlusOption } from "./PlatePlusSelect";

const options: PlatePlusOption[] = [
  { value: "all", label: "All Locations" },
  { value: "penchala", label: "Penchala Toll Plaza" },
  { value: "duke", label: "Simulated DUKE Toll Plaza" },
  { value: "simulator", label: "Simulator Toll Plaza", disabled: true },
];

describe("PlatePlusSelect keyboard behavior", () => {
  it("moves through enabled options and preserves disabled choices", () => {
    expect(nextEnabledOptionIndex(options, 1, 1)).toBe(2);
    expect(nextEnabledOptionIndex(options, 2, 1)).toBe(0);
    expect(nextEnabledOptionIndex(options, 0, -1)).toBe(2);
  });
});
