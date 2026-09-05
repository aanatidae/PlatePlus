import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { mapPositionForLocation, NETWORK_ROUTES, SELANGOR_OUTLINE } from "./selangorNetwork";

const styles = readFileSync(resolve(import.meta.dirname, "styles.css"), "utf8");

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
  it("preserves the marker anchor translation for hover and active visual states", () => {
    expect(styles).toContain(".network-marker:hover:not(:disabled) { transform: translate(-50%, -50%) scale(1.015); }");
    expect(styles).toContain(".network-marker:active:not(:disabled) { transform: translate(-50%, -50%) scale(.995); }");
  });
});
