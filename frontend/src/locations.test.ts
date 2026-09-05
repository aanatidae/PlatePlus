import { describe, expect, it } from "vitest";
import { locationPath, storedLocation } from "./locations";
import { ruleMultiplier } from "./App";
import { historyPath } from "./HistoryFilters";

describe("location and history requests", () => {
  it("distinguishes explicit network scope from one location without dropping filters", () => {
    expect(locationPath("/api/live/overview", "all")).toBe("/api/live/overview?scope=all_locations");
    expect(locationPath("/api/data/detections?limit=50", "toll-2")).toBe("/api/data/detections?limit=50&location_id=toll-2");
  });
  it("defaults safely when storage is empty or unavailable", () => {
    expect(storedLocation({ getItem: () => null })).toBe("all");
    expect(storedLocation({ getItem: () => { throw new Error("disabled"); } })).toBe("all");
    expect(storedLocation({ getItem: () => "toll-2" })).toBe("toll-2");
  });
  it("keeps Malaysian date boundaries and escapes plate search text", () => {
    const url = new URL(historyPath("https://test.local/history?limit=50", { start_at: "2026-09-05", end_at: "2026-09-05", plate: "A&B" }));
    expect(url.searchParams.get("start_at")).toBe("2026-09-05T00:00:00+08:00");
    expect(url.searchParams.get("end_at")).toBe("2026-09-05T23:59:59.999999+08:00");
    expect(url.searchParams.get("plate")).toBe("A&B");
    expect(url.searchParams.get("limit")).toBe("50");
  });
});


describe("location pricing display", () => {
  it("matches backend multiplier rounding and handles a zero normal toll", () => {
    expect(ruleMultiplier(3.1, 1.23)).toBe(2.52);
    expect(ruleMultiplier(3, 0)).toBe(1);
    expect(ruleMultiplier(0, 0)).toBe(1);
  });
});
