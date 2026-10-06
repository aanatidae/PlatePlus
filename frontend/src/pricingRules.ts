export type Rule = { id: string; scenario: string; congestion_category: string; minimum_percentage: number; maximum_percentage: number; multiplier: number };
export type WireRule = Omit<Rule, "minimum_percentage" | "maximum_percentage" | "multiplier"> & { minimum_percentage: number | string; maximum_percentage: number | string; multiplier: number | string };
export const bandLabel = (rule: Rule) => ({ normal: "Low", moderate: "Moderate", peak_hour: "High", severe: "Severe" }[rule.scenario] ?? rule.congestion_category);
export const readRules = (rules: WireRule[]): Rule[] => rules.map(rule => ({ ...rule, minimum_percentage: Number(rule.minimum_percentage), maximum_percentage: Number(rule.maximum_percentage), multiplier: Number(rule.multiplier) }));
const hundredths = (value: number) => Number.isFinite(value) && /^\d+(\.\d{1,2})?$/.test(String(value)) ? Math.round(value * 100) : null;

export function validateRules(rules: Rule[]): string | null {
  const scenarios = ["normal", "moderate", "peak_hour", "severe"];
  if (rules.length !== 4 || scenarios.some(scenario => rules.filter(rule => rule.scenario === scenario).length !== 1)) return "Exactly one rule for each of the four congestion bands is required.";
  for (const rule of rules) {
    for (const [field, value] of [["minimum percentage", rule.minimum_percentage], ["maximum percentage", rule.maximum_percentage]] as const) {
      if (hundredths(value) === null || value < 0 || value > 100) return `${bandLabel(rule)} ${field} must be between 0 and 100 with at most two decimal places.`;
    }
    if (rule.minimum_percentage > rule.maximum_percentage) return `${bandLabel(rule)} minimum percentage cannot exceed its maximum percentage.`;
    if (hundredths(rule.multiplier) === null || rule.multiplier <= 0 || rule.multiplier > 10) return `${bandLabel(rule)} multiplier must be greater than 0 and at most 10 with at most two decimal places.`;
  }
  const ordered = [...rules].sort((a, b) => a.minimum_percentage - b.minimum_percentage);
  if (ordered[0].minimum_percentage !== 0) return `${bandLabel(ordered[0])} minimum percentage must begin at 0.00%.`;
  if (ordered[3].maximum_percentage !== 100) return `${bandLabel(ordered[3])} maximum percentage must end at 100.00%.`;
  for (let i = 1; i < ordered.length; i++) {
    const expected = hundredths(ordered[i - 1].maximum_percentage)! + 1;
    if (hundredths(ordered[i].minimum_percentage) !== expected) return `${bandLabel(ordered[i])} minimum percentage must begin at ${(expected / 100).toFixed(2)}% to avoid overlaps or gaps.`;
  }
  return null;
}

export function rulesPayload(rules: Rule[]) {
  return { rules: rules.map(({ scenario, minimum_percentage, maximum_percentage, multiplier }) => ({ scenario, minimum_percentage, maximum_percentage, multiplier })) };
}
