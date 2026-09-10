import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const app = readFileSync(resolve(import.meta.dirname, "App.tsx"), "utf8");
const overview = readFileSync(resolve(import.meta.dirname, "NetworkOverview.tsx"), "utf8");
const prediction = readFileSync(resolve(import.meta.dirname, "Prediction.tsx"), "utf8");
const camera = readFileSync(resolve(import.meta.dirname, "CameraCapture.tsx"), "utf8");
const pricingExplanation = readFileSync(resolve(import.meta.dirname, "PricingExplanation.tsx"), "utf8");
const performance = readFileSync(resolve(import.meta.dirname, "ModelPerformance.tsx"), "utf8");
const feedback = readFileSync(resolve(import.meta.dirname, "presentationFeedback.ts"), "utf8");

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
  it("makes an accepted webcam crossing a focused presentation event", () => {
    expect(camera).toContain('"simulator-crossing-accepted"');
    expect(camera).toContain("payment_duplicate");
    expect(overview).toContain("crossing-pulse");
    expect(overview).toContain("new-webcam-record");
    expect(overview).toContain("simulatorPricingFeedback");
    expect(feedback).toContain("Congestion increased to");
    expect(feedback).toContain("Congestion dropped to");
    expect(feedback).toContain("Toll adjusted");
    expect(feedback).toContain("Toll remains");
  });
  it("uses authoritative telemetry for the pricing explanation", () => {
    expect(overview).toContain("PricingExplanation");
    expect(pricingExplanation).toContain("active_crossings");
    expect(pricingExplanation).toContain("current_toll_price");
    expect(pricingExplanation).not.toContain("dynamicToll");
  });
  it("puts current and predicted states together without changing live state", () => {
    expect(prediction).toContain("Now vs future");
    expect(prediction).toContain("CURRENT");
    expect(prediction).toContain("PREDICTED");
    expect(prediction).toContain("useFeed<LiveSnapshot>");
  });
  it("keeps compact model evidence in a modal instead of restoring a route", () => {
    expect(app).toContain("ModelPerformance");
    expect(performance).toContain('role="dialog"');
    expect(performance).toContain("preserved and not used for tuning");
    expect(performance).toContain("Precision, recall, and F1 were not exported");
  });
});
