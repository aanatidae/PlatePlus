import { PlatePlusSelect } from "./PlatePlusSelect";
export type HistoryValues = Record<string, string>;
export function historyPath(path: string, values: HistoryValues) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(values)) {
    if (value) params.set(key, key === "start_at" ? `${value}T00:00:00+08:00` : key === "end_at" ? `${value}T23:59:59.999999+08:00` : value);
  }
  return `${path}${path.includes("?") ? "&" : "?"}${params.toString()}`;
}
export default function HistoryFilters({ values, change, pricing = false }: { values: HistoryValues; change: (values: HistoryValues) => void; pricing?: boolean }) {
  const set = (name: string, value: string) => change({ ...values, [name]: value });
  return <section className="filter-bar history-filters" aria-label={pricing ? "Pricing history filters" : "Recognition and transaction history filters"}>
    <label>From (Malaysia)<input type="date" value={values.start_at ?? ""} max={values.end_at || undefined} onChange={event => set("start_at", event.target.value)} /></label>
    <label>To (Malaysia)<input type="date" value={values.end_at ?? ""} min={values.start_at || undefined} onChange={event => set("end_at", event.target.value)} /></label>
    {pricing ? <PlatePlusSelect label="Congestion" value={values.congestion_category ?? ""} onChange={value => set("congestion_category", value)} options={[{ value: "", label: "All" }, { value: "low", label: "Normal" }, { value: "moderate", label: "Moderate" }, { value: "high", label: "Peak hour" }, { value: "severe", label: "Severe" }]} /> : <>
      <label>Plate<input value={values.plate ?? ""} placeholder="VAA1234" onChange={event => set("plate", event.target.value)} /></label>
      <PlatePlusSelect label="Registration" value={values.registration ?? ""} onChange={value => set("registration", value)} options={[{ value: "", label: "All" }, { value: "registered", label: "Registered" }, { value: "unknown", label: "Unknown" }]} />
      <PlatePlusSelect label="Detection" value={values.detection_status ?? ""} onChange={value => set("detection_status", value)} options={["", "accepted", "low_confidence", "unknown_vehicle", "duplicate", "error"].map(value => ({ value, label: value ? value.replace(/_/g, " ") : "All" }))} />
      <PlatePlusSelect label="Transaction" value={values.transaction_status ?? ""} onChange={value => set("transaction_status", value)} options={["", "successful", "failed", "insufficient_balance", "low_confidence", "unknown_vehicle"].map(value => ({ value, label: value ? value.replace(/_/g, " ") : "All" }))} />
      <label>Minimum toll (RM)<input type="number" min="0" step="0.01" value={values.minimum_amount ?? ""} onChange={event => set("minimum_amount", event.target.value)} /></label>
    </>}
    <button className="secondary-button" onClick={() => change({})}>Clear filters</button>
  </section>;
}
