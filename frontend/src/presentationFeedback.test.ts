import { describe, expect, it } from "vitest";
import { simulatorPricingFeedback } from "./presentationFeedback";

describe("Simulator Toll presentation feedback", () => {
  it("uses canonical values for an accepted crossing without a price-band change", () => expect(simulatorPricingFeedback({ congestion_percentage: 30, current_toll_price: 3 }, { congestion_percentage: 40, current_toll_price: 3 }, true)).toBe("Congestion increased to 40% → Toll remains RM3.00"));
  it("distinguishes an authoritative pricing adjustment", () => expect(simulatorPricingFeedback({ congestion_percentage: 60, current_toll_price: 3 }, { congestion_percentage: 70, current_toll_price: 4 }, true)).toBe("Congestion increased to 70% → Toll adjusted from RM3.00 to RM4.00"));
  it("reports an expired crossing's downward adjustment", () => expect(simulatorPricingFeedback({ congestion_percentage: 60, current_toll_price: 4 }, { congestion_percentage: 50, current_toll_price: 3 }, false)).toBe("Congestion dropped to 50% → Toll adjusted to RM3.00"));
  it("does not duplicate feedback for an unchanged state", () => expect(simulatorPricingFeedback({ congestion_percentage: 40, current_toll_price: 3 }, { congestion_percentage: 40, current_toll_price: 3 }, true)).toBeNull());
});
