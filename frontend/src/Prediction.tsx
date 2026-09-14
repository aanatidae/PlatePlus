import { useEffect, useState } from "react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, type TooltipContentProps } from "recharts";
import { advancePlayback, createSimulationFrames, type SimulatorFrame } from "./simulator";
import { locationPath, LocationSelect, useFeed, useLocations } from "./locations";
import { PlatePlusSelect } from "./PlatePlusSelect";

type Batch = { frames: SimulatorFrame[]; duration: number };
type PredictionChartPoint = { timestamp: string; congestion: number; toll: number };
export const predictionDurationOptions = [{ value: "30", label: "30 minutes" }, { value: "60", label: "1 hour" }, { value: "120", label: "2 hours" }, { value: "240", label: "4 hours" }, { value: "360", label: "6 hours" }, { value: "480", label: "8 hours" }, { value: "720", label: "12 hours" }];
export type LiveSnapshot = { location_id?: string; live: { traffic: { congestion_percentage: number; congestion_category: string; current_toll_price: number } | null; price: { amount: number } | null } };

export function currentTelemetryForLocation(snapshot: LiveSnapshot | null, locationId: string) { return snapshot && (!snapshot.location_id || snapshot.location_id === locationId) ? snapshot.live : null; }
const category = (value: string) => value.replace(/_/g, " ");
export const formatRinggit = (value: number) => `RM${Number(value).toFixed(2)}`;
export const formatPredictionTimestamp = (value: string) => new Date(value).toLocaleString("en-MY", { timeZone: "Asia/Kuala_Lumpur", dateStyle: "medium", timeStyle: "short" });
export const formatPredictionAxisTime = (value: string) => new Date(value).toLocaleTimeString("en-MY", { timeZone: "Asia/Kuala_Lumpur", hour: "numeric", minute: "2-digit" });

export function PredictionTooltip({ active, payload }: TooltipContentProps) {
  const point = active ? payload?.[0]?.payload as PredictionChartPoint | undefined : undefined;
  if (!point) return null;
  return <div className="prediction-tooltip"><time>{formatPredictionTimestamp(point.timestamp)}</time><dl><div><dt>Congestion</dt><dd>{point.congestion.toFixed(1)}%</dd></div><div><dt>Toll</dt><dd>{formatRinggit(point.toll)}</dd></div></dl></div>;
}

export default function Prediction() {
  const { locations, selected, select } = useLocations();
  const [start, setStart] = useState(() => new Date().toISOString().slice(0, 16));
  const [duration, setDuration] = useState(60); const [speed, setSpeed] = useState(1);
  const [batch, setBatch] = useState<Batch | null>(null); const [index, setIndex] = useState(0); const [running, setRunning] = useState(false);
  const available = locations.filter(location => location.code !== "SIMULATOR");
  const locationId = selected !== "all" && available.some(location => location.id === selected) ? selected : available[0]?.id ?? "";
  const current = useFeed<LiveSnapshot>(locationId ? locationPath("/api/live/overview", locationId) : "/api/live/overview?scope=all_locations", Boolean(locationId));
  useEffect(() => { setBatch(null); setIndex(0); setRunning(false); }, [locationId]);
  useEffect(() => { if (!batch || !running) return; const timer = setInterval(() => setIndex(previous => { const next = advancePlayback(previous, batch.frames.length); if (next.status === "completed") setRunning(false); return next.frameIndex; }), Math.max(350, 1100 / speed)); return () => clearInterval(timer); }, [batch, running, speed]);
  const output = batch?.frames[index]?.outputs[0];
  const run = () => { const location = available.find(item => item.id === locationId); if (!location) return; const frames = createSimulationFrames([location], "time_based", { congestion: 0, lanes: 3, baseToll: Number(location.base_toll) }, start, duration); setBatch({ frames, duration }); setIndex(0); setRunning(frames.length > 1); };
  const currentLive = currentTelemetryForLocation(current.data, locationId); const live = currentLive?.traffic;
  const chartData: PredictionChartPoint[] = batch?.frames.map(frame => ({ timestamp: frame.timestamp, congestion: frame.outputs[0].congestion, toll: frame.outputs[0].dynamicToll })) ?? [];
  return <main className="dashboard-page">
    <section className="page-heading"><div><h1>Now vs future</h1><p>See what is happening at the selected simulated toll now, then explore its browser-local time-profile forecast. Prediction never writes to live traffic, prices, detections, or transactions.</p></div></section>
    <section className="detail-card simulator-controls">
      <LocationSelect all={false} label="Toll location" value={locationId} onChange={select} />
      <label>Malaysia start time<input type="datetime-local" value={start} onChange={event => setStart(event.target.value)} /></label>
      <PlatePlusSelect label="Duration" value={String(duration)} onChange={value => setDuration(Number(value))} options={predictionDurationOptions} />
      <PlatePlusSelect label="Playback speed" value={String(speed)} onChange={value => setSpeed(Number(value))} options={[{ value: ".5", label: "0.5×" }, { value: "1", label: "1×" }, { value: "2", label: "2×" }, { value: "4", label: "4×" }]} />
      <button onClick={run} disabled={!locationId}>Run prediction</button>
    </section>
    <p className="field-note">Simulator Toll Plaza is excluded: its live congestion comes only from accepted local webcam crossings.</p>
    <section className="now-future" aria-live="polite">
      <article><span>CURRENT</span><strong>{live ? `${Number(live.congestion_percentage).toFixed(0)}%` : "—"}</strong><small>{live ? category(live.congestion_category) : "Loading current telemetry"} · {currentLive?.price ? formatRinggit(currentLive.price.amount) : "—"}</small></article>
      <span className="future-arrow" aria-hidden="true">→</span>
      <article className={output ? "predicted active" : "predicted"}><span>{output ? `PREDICTED · ${formatPredictionTimestamp(batch!.frames[index].timestamp)}` : "PREDICTED"}</span><strong>{output ? `${output.congestion}%` : "Run a prediction"}</strong><small>{output ? `${category(output.category)} · ${formatRinggit(output.dynamicToll)}` : "The forecast side updates during playback."}</small></article>
      {live && output && <p className="prediction-delta">Congestion {output.congestion - Number(live.congestion_percentage) >= 0 ? "+" : ""}{(output.congestion - Number(live.congestion_percentage)).toFixed(0)} percentage points · Toll {(output.dynamicToll - Number(currentLive?.price?.amount ?? 0)) >= 0 ? "+" : ""}{formatRinggit(Math.abs(output.dynamicToll - Number(currentLive?.price?.amount ?? 0)))}</p>}
    </section>
    {batch && output && <section className="simulation-outcomes"><div className="section-title"><div><h2>Forecast progression</h2><p>{formatPredictionTimestamp(batch.frames[index].timestamp)} · frame {index + 1} of {batch.frames.length}</p></div></div>
      <section className="metric-grid page-metrics"><article className="metric"><span>Congestion</span><strong>{output.congestion}%</strong><small>{category(output.category)}</small></article><article className="metric"><span>Estimated flow</span><strong>{output.volume.toLocaleString()}</strong><small>vehicles / hour</small></article><article className="metric"><span>Predicted toll</span><strong>{formatRinggit(output.dynamicToll)}</strong><small>Base {formatRinggit(output.baseToll)}</small></article></section>
      <div className="summary-chart"><ResponsiveContainer width="100%" height={270}><LineChart data={chartData} margin={{ top: 8, right: 8, bottom: 4, left: -12 }}><XAxis dataKey="timestamp" minTickGap={56} tickFormatter={formatPredictionAxisTime} /><YAxis yAxisId="congestion" domain={[0, 100]} /><YAxis yAxisId="toll" orientation="right" tickFormatter={value => formatRinggit(Number(value))} /><Tooltip content={PredictionTooltip} cursor={{ stroke: "var(--line)", strokeWidth: 1 }} /><Line yAxisId="congestion" dataKey="congestion" name="Congestion" stroke="var(--accent)" dot={false} /><Line yAxisId="toll" dataKey="toll" name="Toll" stroke="var(--warning)" dot={false} /></LineChart></ResponsiveContainer></div>
    </section>}
  </main>;
}
