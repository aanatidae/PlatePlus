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
    {pricing ? <label>Congestion<select value={values.congestion_category ?? ""} onChange={event => set("congestion_category", event.target.value)}><option value="">All</option><option value="low">Normal</option><option value="moderate">Moderate</option><option value="high">Peak hour</option><option value="severe">Severe</option></select></label> : <>
      <label>Plate<input value={values.plate ?? ""} placeholder="VAA1234" onChange={event => set("plate", event.target.value)} /></label>
      <label>Registration<select value={values.registration ?? ""} onChange={event => set("registration", event.target.value)}><option value="">All</option><option value="registered">Registered</option><option value="unknown">Unknown</option></select></label>
      <label>Detection<select value={values.detection_status ?? ""} onChange={event => set("detection_status", event.target.value)}><option value="">All</option>{["accepted", "low_confidence", "unknown_vehicle", "duplicate", "error"].map(value => <option key={value} value={value}>{value.replace(/_/g, " ")}</option>)}</select></label>
      <label>Transaction<select value={values.transaction_status ?? ""} onChange={event => set("transaction_status", event.target.value)}><option value="">All</option>{["successful", "failed", "insufficient_balance", "low_confidence", "unknown_vehicle"].map(value => <option key={value} value={value}>{value.replace(/_/g, " ")}</option>)}</select></label>
      <label>Minimum toll (RM)<input type="number" min="0" step="0.01" value={values.minimum_amount ?? ""} onChange={event => set("minimum_amount", event.target.value)} /></label>
    </>}
    <button className="secondary-button" onClick={() => change({})}>Clear filters</button>
  </section>;
}
