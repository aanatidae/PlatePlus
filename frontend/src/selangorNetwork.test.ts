import { describe, expect, it } from "vitest";
import { mapPositionForLocation, NETWORK_ROUTES, SELANGOR_OUTLINE } from "./selangorNetwork";

describe("Selangor toll-road network", () => {
  it("renders only the four simulated highway routes inside a state outline", () => {
    expect(SELANGOR_OUTLINE).toContain("M120");
    expect(NETWORK_ROUTES.map(route => route.id)).toEqual(["LDP", "DUKE", "KESAS", "NPE"]);
  });
  it("keeps each seeded plaza on its intended highway and identifies webcam telemetry", () => {
    const location = (code: string) => ({ code } as never);
    expect(mapPositionForLocation(location("PENCHALA")).route).toBe("LDP");
    expect(mapPositionForLocation(location("DUKE")).route).toBe("DUKE");
    expect(mapPositionForLocation(location("KESAS")).route).toBe("KESAS");
    expect(mapPositionForLocation(location("NPE")).route).toBe("NPE");
    expect(mapPositionForLocation(location("SIMULATOR")).webcam).toBe(true);
  });
});
