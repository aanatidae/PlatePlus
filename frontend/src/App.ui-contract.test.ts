import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

const appSource = readFileSync(resolve(import.meta.dirname, "App.tsx"), "utf8");
const styles = readFileSync(resolve(import.meta.dirname, "styles.css"), "utf8");

describe("administrator dashboard UI contract", () => {
  it("keeps every protected operational destination in navigation", () => {
    for (const route of ["/dashboard", "/recognition", "/pricing", "/intelligence", "/simulator"]) {
      expect(appSource).toContain(`to=\"${route}\"`);
    }
    expect(appSource).toContain('LOCAL_WEBCAM_ENABLED && <NavLink to="/webcam"');
  });

  it("communicates loading, errors, simulation scope, and the local-only inference boundary", () => {
    expect(appSource).toContain("Loading command telemetry");
    expect(appSource).toContain("form-error");
    expect(appSource).toContain("SIMULATED TOLL PROTOTYPE");
    expect(appSource).toContain("Image upload is unavailable here by design");
  });

  it("preserves keyboard and screen-reader labels for primary controls", () => {
    expect(appSource).toContain('aria-label="Administrator navigation"');
    expect(appSource).toContain('aria-label="Toggle navigation"');
    expect(appSource).toContain('aria-live="polite"');
    expect(appSource).toContain('aria-label="Local webcam preview"');
  });

  it("defines responsive layouts at tablet and mobile breakpoints", () => {
    expect(styles).toContain("@media (max-width: 820px)");
    expect(styles).toContain("@media (max-width: 560px)");
    expect(styles).toContain(".command-sidebar.open");
    expect(styles).toContain(".data-table-wrap");
    expect(styles).toContain("prefers-reduced-motion");
  });
});
