type MoneyValue = number | string;
export type ChargeComponents = {
  amount?: MoneyValue | null;
  dynamic_toll_amount?: MoneyValue | null;
  foreign_vehicle_charge?: MoneyValue | null;
  status?: string | null;
};

export const originLabel = (origin?: string | null) => ({
  malaysian: "Malaysian pattern", singaporean: "Singaporean pattern",
  unknown: "Unknown / unsupported pattern",
}[origin ?? "unknown"] ?? "Unknown / unsupported pattern");
const money = (value: MoneyValue) => `RM${Number(value).toFixed(2)}`;

/** Render stored charge components, never compute a toll or infer vehicle nationality. */
export function ChargeDetails({ charge, compact = false }: { charge: ChargeComponents; compact?: boolean }) {
  if (charge.amount == null) return null;
  const totalLabel = charge.status === "successful" ? "Final simulated total" : "Attempted simulated total";
  if (Number(charge.foreign_vehicle_charge ?? 0) === 0) {
    return compact ? null : <span className="charge-total">{totalLabel}: {money(charge.amount)}</span>;
  }
  return <dl className="charge-breakdown" aria-label="Simulated charge breakdown">
    <div><dt>Dynamic toll</dt><dd>{charge.dynamic_toll_amount == null ? "Unavailable" : money(charge.dynamic_toll_amount)}</dd></div>
    <div><dt>Simulated foreign-vehicle charge</dt><dd>{money(charge.foreign_vehicle_charge!)}</dd></div>
    <div><dt>{totalLabel}</dt><dd>{money(charge.amount)}</dd></div>
  </dl>;
}
