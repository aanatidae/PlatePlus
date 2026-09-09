import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const app = readFileSync(resolve(import.meta.dirname, "App.tsx"), "utf8");
const overview = readFileSync(resolve(import.meta.dirname, "NetworkOverview.tsx"), "utf8");
const prediction = readFileSync(resolve(import.meta.dirname, "Prediction.tsx"), "utf8");
const camera = readFileSync(resolve(import.meta.dirname, "CameraCapture.tsx"), "utf8");

describe("simplified local-demo dashboard", () => {
  it("keeps exactly the three presentation pages in sidebar navigation", () => {
    for (const route of ["/dashboard", "/pricing", "/prediction"]) expect(app).toContain(`to="${route}"`);
    for (const removed of ["/recognition", "/simulator", "/webcam", "/demo", "/intelligence"]) expect(app).not.toContain(`to="${removed}"`);
  });
  it("safely redirects retired standalone routes", () => {
    expect(app).toContain('const DASHBOARD_ROUTES = ["/dashboard", "/pricing", "/prediction"]');
    expect(app).toContain('if (!DASHBOARD_ROUTES.includes(route)) navigate("/dashboard", true)');
  });
  it("places demo feed and webcam access in Overview with transparent labels", () => {
    expect(overview).toContain("Start Live Feed");
    expect(overview).toContain("Pause Live Feed");
    expect(overview).toContain("Reset Demo Activity");
    expect(overview).toContain("Open Camera");
    expect(overview).toContain("Simulated live feed");
    expect(overview).toContain("Local webcam ALPR");
    expect(camera).toContain('"camera-pip"');
    expect(overview).not.toContain("WebcamDrawer");
  });
  it("keeps the compact laptop camera on the shared local frame path", () => {
    expect(camera).toContain('/api/webcam/sessions');
    expect(camera).toContain('/frames');
    expect(camera).toContain("Laptop camera");
  });
  it("keeps prediction time-profile-only and isolated", () => {
    expect(prediction).toContain('"time_based"');
    expect(prediction).toContain("never writes to live traffic, prices, detections, or transactions");
    expect(prediction).toContain('location.code !== "SIMULATOR"');
  });
});
