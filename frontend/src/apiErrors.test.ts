import { describe, expect, it } from "vitest";
import { formatApiError } from "./apiErrors";

describe("shared API errors", () => {
  it("handles strings, FastAPI validation arrays and nested detail safely", () => {
    expect(formatApiError({ detail: "Rules are unavailable." })).toBe("Rules are unavailable.");
    expect(formatApiError({ detail: [
      { loc: ["body", "rules", 1, "minimum_percentage"], msg: "Must begin at 30.01%", type: "value_error" },
      { loc: ["body", "rules", 3, "maximum_percentage"], msg: "Must end at 100%" },
    ] })).toBe("Moderate minimum percentage: Must begin at 30.01%; Severe maximum percentage: Must end at 100%");
    expect(formatApiError({ detail: [{ msg: "Value error, Moderate minimum percentage must begin at 30.01%", ctx: { error: {} } }] })).toBe("Moderate minimum percentage must begin at 30.01%");
  });
  it.each([null, {}, { detail: {} }, { detail: [ {} ] }, { detail: "[object Object]" }])("never coerces an unknown object: %j", body => {
    expect(formatApiError(body)).toBe("Request failed.");
  });
});
