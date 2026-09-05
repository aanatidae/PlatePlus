import { useEffect, useState } from "react";
import { MapPin } from "lucide-react";
import { locationPath, useFeed, useLocations, type TollLocation } from "./locations";

type Telemetry = { measured_at: string; congestion_percentage: number; congestion_category: string; vehicles_per_hour: number; average_speed_kmh: number; current_toll_price: number; camera_status: string; system_status: string };
type LocationState = { location: TollLocation; telemetry: Telemetry | null; telemetry_source: string };
type RecordItem = { id: string; location_id: string; normalized_plate?: string; detected_at?: string; processed_at?: string; amount?: number; status: string };
export type NetworkData = {
  generated_at: string; locations: LocationState[];
  live: { traffic: Telemetry | null; price: { amount: number } | null };
  metrics: { detections: number; transactions: number; successful_transactions: number; revenue: number; locations_online: number; locations_total: number; locations_reporting: number; severe_locations: number; cameras_offline: number };
  detections: { items: RecordItem[] }; transactions: { items: RecordItem[] };
};
const money = (value: number) => `RM${Number(value).toFixed(2)}`;
export const categoryLabel = (value: string) => ({ normal: "Normal", low: "Normal", moderate: "Moderate", high: "Peak hour", peak_hour: "Peak hour", severe: "Severe" }[value] ?? value);
const time = (value: string) => new Date(value).toLocaleString("en-MY", { timeZone: "Asia/Kuala_Lumpur", dateStyle: "medium", timeStyle: "short" });
function Stat({ label, value, detail }: { label: string; value: string; detail: string }) {
  return <article className="metric"><span>{label}</span><strong>{value}</strong><small>{detail}</small></article>;
}

function LocationCard({ state }: { state: LocationState }) {
  const telemetry = state.telemetry;
  return <article className="location-card"><p className="eyebrow">SELECTED LOCATION</p><h2>{state.location.display_name}</h2><p>{state.location.highway_or_route}</p>
    {telemetry ? <><span className={`status ${telemetry.congestion_category}`}>{categoryLabel(telemetry.congestion_category)} · {Number(telemetry.congestion_percentage).toFixed(1)}%</span>
      <dl className="location-facts"><div><dt>Current toll</dt><dd>{money(telemetry.current_toll_price)}</dd></div><div><dt>Vehicles / hour</dt><dd>{telemetry.vehicles_per_hour.toLocaleString()}</dd></div><div><dt>Average speed</dt><dd>{telemetry.average_speed_kmh} km/h</dd></div><div><dt>Camera</dt><dd>{telemetry.camera_status}</dd></div><div><dt>System</dt><dd>{telemetry.system_status}</dd></div><div><dt>Last measurement</dt><dd>{time(telemetry.measured_at)}</dd></div></dl>
      <p className="field-note">{state.telemetry_source === "fallback" ? "Simulated time-profile estimate" : state.telemetry_source === "mixed" ? "Simulated estimate with recorded toll" : "Latest recorded simulation · speed estimated"}</p></> : <p>Telemetry unavailable for this location.</p>}
  </article>;
}

export default function NetworkOverview() {
  const { locations, selected, select } = useLocations();
  const network = useFeed<NetworkData>("/api/live/overview?scope=all_locations");
  const scoped = useFeed<NetworkData>(locationPath("/api/live/overview", selected), selected !== "all");
  const { data, error, receivedAt } = selected === "all" ? network : scoped;
  const [now, setNow] = useState(Date.now());
  useEffect(() => { const timer = window.setInterval(() => setNow(Date.now()), 10_000); return () => window.clearInterval(timer); }, []);
  const states = network.data?.locations ?? [];
  const current = data?.locations.find(state => state.location.id === selected);
  const metrics = data?.metrics;
  const oldMeasurement = data?.live.traffic && now - new Date(data.live.traffic.measured_at).getTime() > 120_000;
  const stale = Boolean(error || network.error || (receivedAt && now - receivedAt > 65_000) || oldMeasurement);
  const title = selected === "all" ? "Network operations" : locations.find(item => item.id === selected)?.display_name ?? "Toll operations";
  const values = metrics ? [
    { label: "Traffic flow", value: data?.live.traffic ? Number(data.live.traffic.vehicles_per_hour).toLocaleString() : "—", detail: "Simulated vehicles / hour" },
    { label: selected === "all" ? "Average congestion" : "Congestion", value: data?.live.traffic ? `${Number(data.live.traffic.congestion_percentage).toFixed(1)}%` : "—", detail: selected === "all" ? "Weighted by road capacity" : categoryLabel(data?.live.traffic?.congestion_category ?? "Unavailable") },
    { label: selected === "all" ? "Average toll" : "Current toll", value: data?.live.price ? money(data.live.price.amount) : "—", detail: selected === "all" ? "Mean across reporting locations" : "Simulated toll price" },
    { label: "Simulated revenue", value: money(metrics.revenue), detail: "Successful payments · last hour" },
    { label: "Detections", value: String(metrics.detections), detail: "Last hour" },
    { label: "Transactions", value: String(metrics.transactions), detail: "All payment outcomes · last hour" },
    { label: "Payment success", value: metrics.transactions ? `${(100 * metrics.successful_transactions / metrics.transactions).toFixed(1)}%` : "—", detail: metrics.transactions ? "Last hour" : "No transactions this hour" },
    { label: "Locations online", value: `${metrics.locations_online} / ${metrics.locations_total}`, detail: `${metrics.severe_locations} severe · ${metrics.cameras_offline} cameras offline` },
  ] : [];
  return <main className="dashboard-page"><section className="page-heading"><div><p className="eyebrow">REAL-TIME TELEMETRY</p><h1>{title}</h1><p>Current traffic, recognition and simulated toll operations.</p></div><div className="refresh-note" role="status">{stale ? "STALE / RECONNECTING" : data ? "MONITORING" : "LOADING"}<br />Last updated: {receivedAt ? time(new Date(receivedAt).toISOString()) : "Awaiting data"}</div></section>
    {(error || network.error) && <p className="form-error" role="alert">{error || network.error}</p>}
    {oldMeasurement && <p className="traffic-notice">The latest traffic measurement is more than two minutes old. Values below are the last available simulated state.</p>}
    {!data && !error && <p role="status">Loading PlatePlus telemetry…</p>}
    {metrics && metrics.locations_reporting < metrics.locations_total && <p className="traffic-notice">Partial telemetry: {metrics.locations_reporting} of {metrics.locations_total} locations reporting. Traffic averages exclude unavailable locations.</p>}
    <section className="metric-grid network-metrics">{values.map(value => <Stat key={value.label} {...value} />)}</section>
    <section className="detail-card"><div className="section-title"><div><p className="eyebrow">SIMULATED TOLL NETWORK</p><h2>Select a toll location</h2></div><button className="secondary-button" aria-pressed={selected === "all"} onClick={() => select("all")}>All Locations</button></div>
      <div className="network-layout"><div className="network-map" aria-label="Toll network schematic">
        <svg className="network-roads" viewBox="0 0 700 400" preserveAspectRatio="none" aria-hidden="true"><path d="M 90 60 C 200 40 220 130 260 150 S 380 220 430 260 S 510 310 595 340" /><path d="M 20 140 L 185 140 L 310 30 M 240 390 L 350 225 L 680 200" /></svg>
        <span className="schematic-label">MALAYSIA · SCHEMATIC · NOT TO SCALE</span>
        {[...locations].sort((a, b) => Number(b.latitude) - Number(a.latitude)).map((location, index) => {
          const state = states.find(item => item.location.id === location.id);
          const tone = state?.telemetry?.congestion_category ?? "unavailable";
          const fraction = locations.length > 1 ? index / (locations.length - 1) : .5;
          return <button key={location.id} className={`network-marker ${tone} ${selected === location.id ? "selected" : ""}`} style={{ left: `${15 + fraction * 65}%`, top: `${20 + fraction * 60}%` }} aria-pressed={selected === location.id} aria-label={`${location.display_name}, ${categoryLabel(tone)}${state?.telemetry ? `, ${state.telemetry.congestion_percentage}% congestion` : ""}`} onClick={() => select(location.id)} title={`${location.display_name} · ${categoryLabel(tone)}`}><MapPin size={22} /><strong>{location.display_name}</strong><small>{state?.telemetry ? `${Number(state.telemetry.congestion_percentage).toFixed(1)}% · ${categoryLabel(tone)}` : "Unavailable"}</small></button>;
        })}
        {!locations.length && <p className="map-empty">No toll locations available.</p>}
      </div>{current ? <LocationCard state={current} /> : <article className="location-card"><p className="eyebrow">{selected === "all" ? "ALL LOCATIONS" : "LOCATION TELEMETRY"}</p><h2>{selected === "all" ? "Network health" : "Loading selected location…"}</h2><p>{selected === "all" ? "Select a marker or use the toll selector in the top bar to inspect one location." : "Waiting for this location’s current state."}</p>{selected === "all" && metrics && <dl className="location-facts"><div><dt>Online locations</dt><dd>{metrics.locations_online} / {metrics.locations_total}</dd></div><div><dt>Severe congestion</dt><dd>{metrics.severe_locations}</dd></div><div><dt>Cameras offline</dt><dd>{metrics.cameras_offline}</dd></div><div><dt>Telemetry reporting</dt><dd>{metrics.locations_reporting} / {metrics.locations_total}</dd></div></dl>}</article>}</div>
      <p className="map-legend">Normal · Moderate · Peak hour · Severe · Unavailable — marker text identifies every state.</p>
    </section>
    <section className="table-grid">{(["detections", "transactions"] as const).map(kind => <article className="record-card" key={kind}><h2>Recent {kind} · last hour</h2><div className="records">{data?.[kind].items.length ? data[kind].items.map(item => <div className="record" key={item.id}><strong>{kind === "detections" ? item.normalized_plate ?? "Unread plate" : money(item.amount ?? 0)}</strong><span className={`status ${item.status}`}>{item.status.replace(/_/g, " ")}</span><small>{locations.find(location => location.id === item.location_id)?.display_name ?? "Unknown location"}<br />{time(item.detected_at ?? item.processed_at ?? "")}</small></div>) : <p>{data ? "No simulated activity in the last hour." : "Waiting for activity data."}</p>}</div></article>)}</section>
  </main>;
}
