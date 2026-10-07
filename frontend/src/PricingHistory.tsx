import { useState } from "react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useFeed } from "./locations";
import HistoryFilters, { historyPath, type HistoryValues } from "./HistoryFilters";

type SeriesRow = { date: string; average_congestion: string | number | null; average_toll: string | number | null };
type StoredPrice = { id: string; effective_at: string; amount: string | number; congestion_category: string; rule_version: string };
type Audit = { id: string; action: string; created_at: string };
const timestamp = (value: string) => new Date(value).toLocaleString("en-MY", { timeZone: "Asia/Kuala_Lumpur", dateStyle: "medium", timeStyle: "short" });
const money = (value: number | string | null) => value == null ? "Unavailable" : `RM${Number(value).toFixed(2)}`;

function HistoryBody({ locationId }: { locationId: string }) {
  const [filters, setFilters] = useState<HistoryValues>({});
  const query = `location_id=${encodeURIComponent(locationId)}`;
  const analytics = useFeed<{ series: SeriesRow[] }>(historyPath(`/api/data/history/analytics?${query}`, filters));
  const prices = useFeed<StoredPrice[]>(historyPath(`/api/data/toll-prices?limit=50&${query}`, filters));
  const audit = useFeed<Audit[]>("/api/traffic/audit-logs");
  const policyChanges = audit.data?.filter(entry => ["pricing_rules_updated", "traffic_settings_updated"].includes(entry.action)).slice(0, 10) ?? [];
  const rows = analytics.data?.series ?? [];
  const chart = rows.map(row => ({ date: row.date, congestion: row.average_congestion == null ? null : Number(row.average_congestion), toll: row.average_toll == null ? null : Number(row.average_toll) }));
  return <>
    <HistoryFilters values={filters} change={setFilters} pricing />
    <p className="field-note">Dates use Malaysia time. Daily averages use up to 1,000 records per type; the table below shows the latest 50 matching toll decisions. These toll prices exclude transaction-only foreign charges.</p>
    {[analytics.error, prices.error, audit.error].filter(Boolean).map((error, index) => <p key={index} className="form-error" role="alert">{error}</p>)}
    {!analytics.data && !analytics.error && <p role="status">Loading recorded congestion and pricing history…</p>}
    {rows.length > 0 ? <>
      <div className="summary-chart" aria-label="Recorded daily congestion and dynamic toll chart"><ResponsiveContainer width="100%" height={240}><LineChart data={chart}><XAxis dataKey="date" /><YAxis yAxisId="congestion" domain={[0, 100]} /><YAxis yAxisId="toll" orientation="right" /><Tooltip contentStyle={{ background: "var(--raised)", border: "1px solid var(--line)", color: "var(--text)" }} /><Line yAxisId="congestion" dataKey="congestion" name="Congestion (%)" stroke="var(--accent)" dot={false} /><Line yAxisId="toll" dataKey="toll" name="Dynamic toll (RM)" stroke="var(--warning)" dot={false} /></LineChart></ResponsiveContainer></div>
      <div className="history-table-wrap"><table className="history-table"><caption>Recorded daily traffic and toll averages</caption><thead><tr><th scope="col">Malaysia date</th><th scope="col">Congestion</th><th scope="col">Dynamic toll</th></tr></thead><tbody>{rows.map(row => <tr key={row.date}><td>{row.date}</td><td>{row.average_congestion == null ? "Unavailable" : `${Number(row.average_congestion).toFixed(1)}%`}</td><td>{money(row.average_toll)}</td></tr>)}</tbody></table></div>
    </> : analytics.data && <p>No recorded history matches these filters.</p>}
    <h3>Stored toll decisions</h3>
    {prices.data?.length ? <div className="history-table-wrap"><table className="history-table"><caption>Location-specific stored dynamic tolls</caption><thead><tr><th scope="col">Malaysia time</th><th scope="col">Band</th><th scope="col">Dynamic toll</th><th scope="col">Policy version</th></tr></thead><tbody>{prices.data.map(price => <tr key={price.id}><td>{timestamp(price.effective_at)}</td><td>{price.congestion_category.replace(/_/g, " ")}</td><td>{money(price.amount)}</td><td>{price.rule_version}</td></tr>)}</tbody></table></div> : <p>{prices.data ? "No stored toll decisions match these filters." : "Loading stored prices…"}</p>}
    <h3>Network pricing-policy audit</h3>
    <p className="field-note">Recent policy changes apply across operational locations and are separate from the location/date filters above.</p>
    <div className="records">{policyChanges.length ? policyChanges.map(entry => <div className="record" key={entry.id}><strong>{entry.action.replace(/_/g, " ")}</strong><small>{timestamp(entry.created_at)}</small></div>) : <p>{audit.data ? "No pricing-policy changes recorded." : "Loading policy audit…"}</p>}</div>
  </>;
}

export function PricingHistory({ locationId, locationName }: { locationId: string; locationName: string }) {
  const [open, setOpen] = useState(false);
  return <details className="detail-card pricing-history" onToggle={event => setOpen(event.currentTarget.open)}>
    <summary>Recorded congestion, toll history and policy audit</summary>
    <p className="field-note">{locationName ? `History for ${locationName}. Change the pricing-preview location to inspect another plaza.` : "Select a pricing-preview location to inspect its history."}</p>
    {open && locationId && <HistoryBody key={locationId} locationId={locationId} />}
  </details>;
}
