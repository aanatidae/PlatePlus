import { FormEvent, useEffect, useRef, useState } from "react";
import { Activity, Camera, Gauge, MapPin, SlidersHorizontal } from "lucide-react";
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

type BoundingBox = { left: number; top: number; right: number; bottom: number };
type FrameResult = { status: string; message: string; plate_text?: string; detection_confidence?: number; ocr_confidence?: number; bounding_box?: BoundingBox; charge_eligible: boolean; payment_status?: string; payment_amount?: number; payment_balance_after?: number; payment_duplicate: boolean };
type Admin = { id: string; email: string; display_name: string };
type LoginResponse = { access_token: string; token_type: string; expires_at: string; admin: Admin };

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
const LOCAL_WEBCAM_ENABLED = import.meta.env.VITE_ENABLE_LOCAL_WEBCAM !== "false";
const AUTH_STORAGE_KEY = "capstone-alpr.admin-session";

function readStoredSession(): LoginResponse | null {
  try {
    const stored = window.sessionStorage.getItem(AUTH_STORAGE_KEY);
    return stored ? (JSON.parse(stored) as LoginResponse) : null;
  } catch {
    window.sessionStorage.removeItem(AUTH_STORAGE_KEY);
    return null;
  }
}

function navigate(path: string, replace = false) {
  window.history[replace ? "replaceState" : "pushState"]({}, "", path);
  window.dispatchEvent(new PopStateEvent("popstate"));
}

function App() {
  const [session, setSession] = useState<LoginResponse | null>(readStoredSession);
  const [route, setRoute] = useState(window.location.pathname);
  const [checkingSession, setCheckingSession] = useState(Boolean(readStoredSession()));

  useEffect(() => {
    const onPopState = () => setRoute(window.location.pathname);
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  useEffect(() => {
    if (!session) {
      if (route !== "/login") navigate("/login", true);
      setCheckingSession(false);
      return;
    }

    if (!LOCAL_WEBCAM_ENABLED && route === "/webcam") {
      navigate("/dashboard", true);
      return;
    }

    let cancelled = false;
    void fetch(`${API_BASE_URL}/api/auth/me`, { headers: { Authorization: `Bearer ${session.access_token}` } })
      .then((response) => {
        if (!response.ok) throw new Error("Your administrator session has expired.");
        return response.json() as Promise<Admin>;
      })
      .then((admin) => {
        if (cancelled) return;
        const refreshed = { ...session, admin };
        window.sessionStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(refreshed));
        setSession(refreshed);
        if (!["/dashboard", "/webcam", "/traffic"].includes(route)) navigate("/dashboard", true);
      })
      .catch(() => {
        if (cancelled) return;
        window.sessionStorage.removeItem(AUTH_STORAGE_KEY);
        setSession(null);
        navigate("/login", true);
      })
      .finally(() => { if (!cancelled) setCheckingSession(false); });
    return () => { cancelled = true; };
  }, [session?.access_token]);

  function handleLogin(nextSession: LoginResponse) {
    window.sessionStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(nextSession));
    setSession(nextSession);
    navigate("/dashboard", true);
  }

  function handleLogout() {
    window.sessionStorage.removeItem(AUTH_STORAGE_KEY);
    setSession(null);
    navigate("/login", true);
  }

  if (checkingSession) return <main className="auth-shell"><p>Checking administrator access…</p></main>;
  if (!session) return <LoginView onLogin={handleLogin} />;
  return <AdminShell admin={session.admin} route={route} onLogout={handleLogout} />;
}

function LoginView({ onLogin }: { onLogin: (session: LoginResponse) => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/login`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, password }) });
      if (!response.ok) throw new Error("Email or password is incorrect.");
      onLogin((await response.json()) as LoginResponse);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Sign-in could not be completed.");
    } finally {
      setSubmitting(false);
    }
  }

  return <main className="auth-shell"><section className="login-card" aria-labelledby="login-title">
    <p className="eyebrow">SIMULATED TOLL PROTOTYPE</p><h1 id="login-title">Administrator sign in</h1><p>Use the seeded local administrator account to access the dashboard.</p>
    <form onSubmit={submit}>
      <label>Email<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" required /></label>
      <label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" required /></label>
      {error && <p className="form-error" role="alert">{error}</p>}
      <button type="submit" disabled={submitting}>{submitting ? "Signing in…" : "Sign in"}</button>
    </form>
  </section></main>;
}

function AdminShell({ admin, route, onLogout }: { admin: Admin; route: string; onLogout: () => void }) {
  const page = route === "/webcam" ? <WebcamPage /> : route === "/traffic" ? <TrafficPage /> : <OverviewPage />;
  return <><header className="app-nav"><a className="brand" href="/dashboard" onClick={(event) => { event.preventDefault(); navigate("/dashboard"); }}><Activity size={20} /> TOLL//VISION</a><nav aria-label="Administrator navigation"><NavLink to="/dashboard" active={route === "/dashboard"} icon={<Gauge size={16} />}>Overview</NavLink><NavLink to="/traffic" active={route === "/traffic"} icon={<SlidersHorizontal size={16} />}>Traffic</NavLink>{LOCAL_WEBCAM_ENABLED && <NavLink to="/webcam" active={route === "/webcam"} icon={<Camera size={16} />}>Local webcam</NavLink>}</nav><div className="admin-menu"><span>{admin.display_name}</span><button className="secondary-button" onClick={onLogout}>Sign out</button></div></header>{page}</>;
}

function NavLink({ to, active, icon, children }: { to: string; active: boolean; icon: React.ReactNode; children: React.ReactNode }) {
  return <a className={active ? "nav-link active" : "nav-link"} href={to} onClick={(event) => { event.preventDefault(); navigate(to); }}>{icon}{children}</a>;
}

type Overview = { live: { traffic: { measured_at: string; congestion_percentage: number; congestion_category: string; vehicle_count: number; road_capacity: number } | null; price: { amount: number } | null }; metrics: { detections: number; transactions: number; successful_transactions: number; failed_transactions: number; revenue: number; average_recognition_confidence: number | null }; traffic_series: { measured_at: string; congestion_percentage: number }[]; price_series: { effective_at: string; amount: number }[]; detections: { items: Detection[]; has_more: boolean }; transactions: { items: Transaction[]; has_more: boolean } };
type Detection = { id: string; detected_at: string; normalized_plate: string | null; status: string; vehicle_id: string | null; detection_confidence: number; ocr_confidence: number | null };
type Transaction = { id: string; processed_at: string; amount: number; status: string; vehicle_id: string | null; balance_after: number | null };

function apiHeaders() { const session = readStoredSession(); return { Authorization: `Bearer ${session?.access_token ?? ""}` }; }
function malaysiaDate(date: Date) { return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kuala_Lumpur" }).format(date); }

function OverviewPage() {
  const [data, setData] = useState<Overview | null>(null); const [error, setError] = useState(""); const [hologram, setHologram] = useState(false);
  const [filters, setFilters] = useState({ start: malaysiaDate(new Date(Date.now() - 86_400_000)), end: malaysiaDate(new Date()), congestionCategory: "", plate: "", detectionStatus: "", registration: "", transactionStatus: "", minimumAmount: "" });
  const [offsets, setOffsets] = useState({ detection: 0, transaction: 0 });
  async function load(nextOffsets = offsets) { try { const params = new URLSearchParams({ start_at: `${filters.start}T00:00:00+08:00`, end_at: `${filters.end}T23:59:59+08:00`, detection_offset: String(nextOffsets.detection), transaction_offset: String(nextOffsets.transaction), limit: "8" }); if (filters.congestionCategory) params.set("congestion_category", filters.congestionCategory); if (filters.plate) params.set("plate", filters.plate); if (filters.detectionStatus) params.set("detection_status", filters.detectionStatus); if (filters.registration) params.set("registration", filters.registration); if (filters.transactionStatus) params.set("transaction_status", filters.transactionStatus); if (filters.minimumAmount) params.set("minimum_amount", filters.minimumAmount); const response = await fetch(`${API_BASE_URL}/api/dashboard/overview?${params}`, { headers: apiHeaders() }); if (!response.ok) throw new Error("Dashboard data is unavailable."); setData(await response.json() as Overview); setError(""); } catch (reason) { setError(reason instanceof Error ? reason.message : "Dashboard data is unavailable."); } }
  useEffect(() => { void load({ detection: 0, transaction: 0 }); const timer = window.setInterval(() => void load(), 30_000); return () => window.clearInterval(timer); }, [filters.start, filters.end, filters.congestionCategory, filters.plate, filters.detectionStatus, filters.registration, filters.transactionStatus, filters.minimumAmount]);
  const traffic = data?.live.traffic; const tone = traffic?.congestion_category ?? "low";
  return <main className="dashboard-page"><section className="page-heading"><div><p className="eyebrow">PENCHALA TOLL PLAZA · LDP / E11</p><h1>Traffic operations overview</h1><p>All traffic, pricing, and payments shown here are simulated.</p></div><span className="refresh-note">Refreshes every 30 seconds · Malaysia time</span></section>
    <section className="filter-bar" aria-label="Dashboard filters"><label>From<input type="date" value={filters.start} onChange={(e) => setFilters({ ...filters, start: e.target.value })} /></label><label>To<input type="date" value={filters.end} onChange={(e) => setFilters({ ...filters, end: e.target.value })} /></label><label>Congestion<select value={filters.congestionCategory} onChange={(e) => setFilters({ ...filters, congestionCategory: e.target.value })}><option value="">All</option><option value="low">Low</option><option value="moderate">Moderate</option><option value="high">High</option><option value="severe">Severe</option></select></label><label>Plate<input placeholder="VAA1234" value={filters.plate} onChange={(e) => setFilters({ ...filters, plate: e.target.value })} /></label><label>Registration<select value={filters.registration} onChange={(e) => setFilters({ ...filters, registration: e.target.value })}><option value="">All</option><option value="registered">Registered</option><option value="unknown">Unknown</option></select></label><label>Detection<select value={filters.detectionStatus} onChange={(e) => setFilters({ ...filters, detectionStatus: e.target.value })}><option value="">All</option><option value="accepted">Accepted</option><option value="low_confidence">Low confidence</option><option value="unknown_vehicle">Unknown</option></select></label><label>Transaction<select value={filters.transactionStatus} onChange={(e) => setFilters({ ...filters, transactionStatus: e.target.value })}><option value="">All</option><option value="successful">Successful</option><option value="failed">Failed</option><option value="insufficient_balance">Insufficient balance</option></select></label><label>Min. toll (RM)<input type="number" min="0" step="0.01" placeholder="0.00" value={filters.minimumAmount} onChange={(e) => setFilters({ ...filters, minimumAmount: e.target.value })} /></label></section>
    {error && <p className="form-error">{error}</p>}
    <section className="metric-grid"><Metric label="Current toll" value={data?.live.price ? `RM${Number(data.live.price.amount).toFixed(2)}` : "—"} /><Metric label="Detections" value={String(data?.metrics.detections ?? 0)} /><Metric label="Transactions" value={String(data?.metrics.transactions ?? 0)} /><Metric label="Simulated revenue" value={`RM${Number(data?.metrics.revenue ?? 0).toFixed(2)}`} /><Metric label="Recognition confidence" value={data?.metrics.average_recognition_confidence ? `${(Number(data.metrics.average_recognition_confidence) * 100).toFixed(1)}%` : "—"} /></section>
    <section className={hologram ? `toll-map expanded ${tone}` : `toll-map ${tone}`}><button className="map-button" onClick={() => setHologram(!hologram)} aria-expanded={hologram}><span className="map-road ldp">LDP / E11</span><span className="map-road branch">Penchala Link</span><span className="toll-pin"><MapPin size={24} /><b>Penchala Toll Plaza</b><small>{traffic ? `${traffic.congestion_category} · ${traffic.congestion_percentage}%` : "Awaiting simulation"}</small></span></button><div className={hologram ? "hologram visible" : "hologram"} aria-live="polite" aria-hidden={!hologram}><div className="gantry"><i /><i /><i /><span className="scan-beam" /><span className="gantry-vehicle vehicle-one" /><span className="gantry-vehicle vehicle-two" /></div><div><p className="eyebrow">LIVE SIMULATED TOLL</p><h2>Penchala ERP-style gantry</h2><dl><div><dt>Congestion</dt><dd>{traffic ? `${traffic.congestion_percentage}% · ${traffic.congestion_category}` : "—"}</dd></div><div><dt>Current toll</dt><dd>{data?.live.price ? `RM${Number(data.live.price.amount).toFixed(2)}` : "—"}</dd></div><div><dt>Vehicle load</dt><dd>{traffic ? `${traffic.vehicle_count} / ${traffic.road_capacity}` : "—"}</dd></div><div><dt>Latest simulation</dt><dd>{traffic ? new Date(traffic.measured_at).toLocaleString("en-MY", { timeZone: "Asia/Kuala_Lumpur" }) : "—"}</dd></div></dl></div></div></section>
    <section className="chart-grid"><ChartCard title="Congestion trend"><ResponsiveContainer width="100%" height={220}><AreaChart data={data?.traffic_series ?? []}><XAxis dataKey="measured_at" tickFormatter={(v) => new Date(v).toLocaleTimeString("en-MY", { timeZone: "Asia/Kuala_Lumpur", hour: "2-digit", minute: "2-digit" })} /><YAxis /><Tooltip /><Area type="monotone" dataKey="congestion_percentage" stroke="#47d7ba" fill="#47d7ba33" /></AreaChart></ResponsiveContainer></ChartCard><ChartCard title="Toll price trend"><ResponsiveContainer width="100%" height={220}><AreaChart data={data?.price_series ?? []}><XAxis dataKey="effective_at" tickFormatter={(v) => new Date(v).toLocaleTimeString("en-MY", { timeZone: "Asia/Kuala_Lumpur", hour: "2-digit", minute: "2-digit" })} /><YAxis /><Tooltip /><Area type="step" dataKey="amount" stroke="#8b7bff" fill="#8b7bff33" /></AreaChart></ResponsiveContainer></ChartCard></section>
    <section className="table-grid"><RecordTable title="Recent detections" rows={data?.detections.items ?? []} kind="detection" more={Boolean(data?.detections.has_more)} onMore={() => { const next = { ...offsets, detection: offsets.detection + 8 }; setOffsets(next); void load(next); }} /><RecordTable title="Recent transactions" rows={data?.transactions.items ?? []} kind="transaction" more={Boolean(data?.transactions.has_more)} onMore={() => { const next = { ...offsets, transaction: offsets.transaction + 8 }; setOffsets(next); void load(next); }} /></section></main>;
}

function Metric({ label, value }: { label: string; value: string }) { return <article className="metric"><span>{label}</span><strong>{value}</strong></article>; }
function ChartCard({ title, children }: { title: string; children: React.ReactNode }) { return <article className="chart-card"><h2>{title}</h2>{children}</article>; }
function RecordTable({ title, rows, kind, more, onMore }: { title: string; rows: Array<Detection | Transaction>; kind: "detection" | "transaction"; more: boolean; onMore: () => void }) { return <article className="record-card"><h2>{title}</h2><div className="records">{rows.length === 0 ? <p>No simulated records in this range.</p> : rows.map((row) => <div className="record" key={row.id}><strong>{kind === "detection" ? (row as Detection).normalized_plate ?? "Unread plate" : `RM${Number((row as Transaction).amount).toFixed(2)}`}</strong><span className={`status ${(row as Detection | Transaction).status}`}>{(row as Detection | Transaction).status.replace(/_/g, " ")}</span><small>{new Date(kind === "detection" ? (row as Detection).detected_at : (row as Transaction).processed_at).toLocaleString("en-MY", { timeZone: "Asia/Kuala_Lumpur" })}</small></div>)}</div>{more && <button className="secondary-button load-more" onClick={onMore}>Load more</button>}</article>; }

type TrafficSettings = { is_enabled: boolean; interval_minutes: 1 | 5 | 15; simulation_mode: "time_patterned" | "fixed_scenario"; fixed_scenario: "normal" | "moderate" | "peak_hour" | "severe"; time_mode: "real" | "simulated"; simulated_time: string | null; current_simulation_time: string; pricing_rule_version: number };
type PricingRule = { id: string; scenario: "normal" | "moderate" | "peak_hour" | "severe"; congestion_category: string; minimum_percentage: number; maximum_percentage: number; amount: number };
type Audit = { id: string; action: string; created_at: string; details_json: string };

function TrafficPage() {
  const [settings, setSettings] = useState<TrafficSettings | null>(null); const [rules, setRules] = useState<PricingRule[]>([]); const [audit, setAudit] = useState<Audit[]>([]); const [notice, setNotice] = useState(""); const [busy, setBusy] = useState(false);
  async function request(path: string, init?: RequestInit) { const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers: { ...apiHeaders(), "Content-Type": "application/json", ...(init?.headers ?? {}) } }); if (!response.ok) { const body = await response.json().catch(() => null) as { detail?: string } | null; throw new Error(body?.detail ?? "Traffic administration request failed."); } return response.json(); }
  async function load() { try { const [nextSettings, nextRules, nextAudit] = await Promise.all([request("/api/traffic/settings"), request("/api/traffic/pricing-rules"), request("/api/traffic/audit-logs")]); setSettings(nextSettings as TrafficSettings); setRules(nextRules as PricingRule[]); setAudit(nextAudit as Audit[]); } catch (reason) { setNotice(reason instanceof Error ? reason.message : "Traffic administration is unavailable."); } }
  useEffect(() => { void load(); }, []);
  async function saveSettings(event: FormEvent<HTMLFormElement>) { event.preventDefault(); if (!settings) return; setBusy(true); try { const saved = await request("/api/traffic/settings", { method: "PUT", body: JSON.stringify({ ...settings, simulated_time: settings.time_mode === "simulated" ? settings.simulated_time : null }) }); setSettings(saved as TrafficSettings); setNotice("Simulation settings saved."); void load(); } catch (reason) { setNotice(reason instanceof Error ? reason.message : "Settings could not be saved."); } finally { setBusy(false); } }
  async function saveRules(event: FormEvent<HTMLFormElement>) { event.preventDefault(); setBusy(true); try { const saved = await request("/api/traffic/pricing-rules", { method: "PUT", body: JSON.stringify({ rules: rules.map(({ scenario, minimum_percentage, maximum_percentage, amount }) => ({ scenario, minimum_percentage, maximum_percentage, amount })) }) }); setRules(saved as PricingRule[]); setNotice("Pricing rules saved and versioned."); void load(); } catch (reason) { setNotice(reason instanceof Error ? reason.message : "Pricing rules could not be saved."); } finally { setBusy(false); } }
  async function runNow() { setBusy(true); try { const result = await request("/api/traffic/simulate", { method: "POST", body: "{}" }) as { scenario: string; congestion_percentage: number; amount: number }; setNotice(`Simulated ${result.scenario.replace(/_/g, " ")} traffic at ${result.congestion_percentage}% — RM${Number(result.amount).toFixed(2)}.`); void load(); } catch (reason) { setNotice(reason instanceof Error ? reason.message : "Simulation could not run."); } finally { setBusy(false); } }
  return <main className="dashboard-page"><section className="page-heading"><div><p className="eyebrow">SIMULATED TRAFFIC CONTROL</p><h1>Traffic & pricing administration</h1><p>All adjustments and runs are simulated and recorded in the audit history.</p></div><button onClick={() => void runNow()} disabled={busy || !settings}>Run simulation now</button></section>{notice && <p className="traffic-notice" role="status">{notice}</p>}<section className="traffic-grid"><form className="admin-card" onSubmit={saveSettings}><h2>Simulation settings</h2>{!settings ? <p>Loading settings…</p> : <><label className="toggle-row"><input type="checkbox" checked={settings.is_enabled} onChange={(e) => setSettings({ ...settings, is_enabled: e.target.checked })} /> Enable scheduled simulation</label><label>Interval<select value={settings.interval_minutes} onChange={(e) => setSettings({ ...settings, interval_minutes: Number(e.target.value) as 1 | 5 | 15 })}><option value={1}>Every 1 minute</option><option value={5}>Every 5 minutes</option><option value={15}>Every 15 minutes</option></select></label><label>Simulation mode<select value={settings.simulation_mode} onChange={(e) => setSettings({ ...settings, simulation_mode: e.target.value as TrafficSettings["simulation_mode"] })}><option value="time_patterned">Malaysia time pattern</option><option value="fixed_scenario">Fixed scenario</option></select></label>{settings.simulation_mode === "fixed_scenario" && <label>Fixed scenario<select value={settings.fixed_scenario} onChange={(e) => setSettings({ ...settings, fixed_scenario: e.target.value as TrafficSettings["fixed_scenario"] })}><option value="normal">Normal / low</option><option value="moderate">Moderate</option><option value="peak_hour">Peak hour / high</option><option value="severe">Severe</option></select></label>}<label>Clock mode<select value={settings.time_mode} onChange={(e) => setSettings({ ...settings, time_mode: e.target.value as TrafficSettings["time_mode"] })}><option value="real">Real Malaysia time</option><option value="simulated">Advancing simulated time</option></select></label>{settings.time_mode === "simulated" && <label>Simulated start time<input type="datetime-local" value={settings.simulated_time ? settings.simulated_time.slice(0, 16) : ""} onChange={(e) => setSettings({ ...settings, simulated_time: e.target.value ? `${e.target.value}:00+08:00` : null })} required /></label>}<p className="field-note">Current simulation clock: {new Date(settings.current_simulation_time).toLocaleString("en-MY", { timeZone: "Asia/Kuala_Lumpur" })}</p><button disabled={busy}>Save settings</button></>}</form><form className="admin-card" onSubmit={saveRules}><h2>Dynamic pricing bands <small>v{settings?.pricing_rule_version ?? "—"}</small></h2><div className="pricing-head"><span>Scenario</span><span>Congestion range</span><span>Price</span></div>{rules.map((rule, index) => <div className="pricing-row" key={rule.id}><strong>{rule.scenario.replace(/_/g, " ")}</strong><span><input aria-label={`${rule.scenario} minimum congestion`} type="number" min="0" max="100" step="0.01" value={rule.minimum_percentage} onChange={(e) => setRules(rules.map((item, i) => i === index ? { ...item, minimum_percentage: Number(e.target.value) } : item))} /> – <input aria-label={`${rule.scenario} maximum congestion`} type="number" min="0" max="100" step="0.01" value={rule.maximum_percentage} onChange={(e) => setRules(rules.map((item, i) => i === index ? { ...item, maximum_percentage: Number(e.target.value) } : item))} />%</span><label>RM<input aria-label={`${rule.scenario} price`} type="number" min="0" step="0.01" value={rule.amount} onChange={(e) => setRules(rules.map((item, i) => i === index ? { ...item, amount: Number(e.target.value) } : item))} /></label></div>)}<button disabled={busy || rules.length !== 4}>Save pricing rules</button></form></section><section className="admin-card audit-card"><h2>Recent configuration activity</h2><div className="audit-list">{audit.length === 0 ? <p>No activity recorded yet.</p> : audit.slice(0, 8).map((item) => <div key={item.id}><strong>{item.action.replace(/_/g, " ")}</strong><span>{new Date(item.created_at).toLocaleString("en-MY", { timeZone: "Asia/Kuala_Lumpur" })}</span></div>)}</div></section></main>;
}

function WebcamPage() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const intervalRef = useRef<number | null>(null);
  const sessionRef = useRef<string | null>(null);
  const inFlightRef = useRef(false);
  const [state, setState] = useState<"idle" | "starting" | "running" | "error">("idle");
  const [result, setResult] = useState<FrameResult | null>(null);
  const [message, setMessage] = useState("Camera is off. Frames stay on this laptop.");

  useEffect(() => () => void stopCamera(), []);

  async function startCamera() {
    setState("starting"); setMessage("Requesting local camera permission…");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment", width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false });
      const sessionResponse = await fetch(`${API_BASE_URL}/api/webcam/sessions`, { method: "POST" });
      if (!sessionResponse.ok) throw new Error("The local ALPR service could not start a webcam session.");
      const cameraSession = (await sessionResponse.json()) as { session_id: string; frame_interval_ms: number };
      streamRef.current = stream; sessionRef.current = cameraSession.session_id;
      if (!videoRef.current) throw new Error("Camera preview is unavailable.");
      videoRef.current.srcObject = stream; await videoRef.current.play();
      intervalRef.current = window.setInterval(() => void sendFrame(), cameraSession.frame_interval_ms);
      setState("running"); setMessage("Camera is running locally. Toll and traffic results are simulated.");
    } catch (error) {
      await stopCamera(); setState("error"); setMessage(error instanceof Error ? error.message : "Camera access could not be started.");
    }
  }

  async function stopCamera() {
    if (intervalRef.current !== null) window.clearInterval(intervalRef.current);
    intervalRef.current = null; streamRef.current?.getTracks().forEach((track) => track.stop()); streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    const sessionId = sessionRef.current; sessionRef.current = null;
    if (sessionId) await fetch(`${API_BASE_URL}/api/webcam/sessions/${sessionId}`, { method: "DELETE" }).catch(() => undefined);
    inFlightRef.current = false; setState("idle"); setMessage("Camera is off. Frames stay on this laptop.");
  }

  async function sendFrame() {
    const video = videoRef.current; const canvas = canvasRef.current; const sessionId = sessionRef.current;
    if (!video || !canvas || !sessionId || inFlightRef.current || video.videoWidth === 0) return;
    inFlightRef.current = true;
    try {
      canvas.width = video.videoWidth; canvas.height = video.videoHeight; canvas.getContext("2d")?.drawImage(video, 0, 0);
      const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.82));
      if (!blob) throw new Error("A webcam frame could not be captured.");
      const form = new FormData(); form.append("frame", blob, "webcam-frame.jpg");
      const response = await fetch(`${API_BASE_URL}/api/webcam/sessions/${sessionId}/frames`, { method: "POST", headers: { "Idempotency-Key": crypto.randomUUID() }, body: form });
      if (!response.ok) throw new Error((await response.json()).detail ?? "Frame processing failed.");
      setResult((await response.json()) as FrameResult);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Frame processing failed.");
    } finally { inFlightRef.current = false; }
  }

  const box = result?.bounding_box;
  const label = result?.plate_text ? `${result.plate_text} · ${result.status}` : result?.status;
  return <main className="dashboard-page">
    <header className="page-heading"><div><p className="eyebrow">LOCAL-ONLY ALPR</p><h1>Local Webcam ALPR</h1><p>{message}</p></div></header>
    <section className="camera-panel" aria-live="polite"><div className="preview"><video ref={videoRef} muted playsInline aria-label="Local webcam preview" />{box && <div className="box" style={{ left: `${(box.left / (videoRef.current?.videoWidth || 1)) * 100}%`, top: `${(box.top / (videoRef.current?.videoHeight || 1)) * 100}%`, width: `${((box.right - box.left) / (videoRef.current?.videoWidth || 1)) * 100}%`, height: `${((box.bottom - box.top) / (videoRef.current?.videoHeight || 1)) * 100}%` }}><span>{label}</span></div>}</div><button onClick={() => void (state === "running" ? stopCamera() : startCamera())} disabled={state === "starting"}>{state === "running" ? "Stop camera" : "Start camera"}</button><canvas ref={canvasRef} hidden /></section>
    <section className="result" aria-label="Recognition result"><h2>Latest recognition</h2><p><strong>{result?.plate_text ?? "—"}</strong></p><p>{result?.message ?? "No frame has been processed."}</p>{result && <dl><div><dt>Detection</dt><dd>{result.detection_confidence ? `${(result.detection_confidence * 100).toFixed(1)}%` : "—"}</dd></div><div><dt>OCR</dt><dd>{result.ocr_confidence ? `${(result.ocr_confidence * 100).toFixed(1)}%` : "—"}</dd></div><div><dt>Simulated payment</dt><dd>{result.payment_status ?? "Not processed"}</dd></div>{result.payment_amount !== undefined && <div><dt>Toll amount</dt><dd>RM{result.payment_amount.toFixed(2)}</dd></div>}{result.payment_balance_after !== undefined && <div><dt>Balance after</dt><dd>RM{result.payment_balance_after.toFixed(2)}</dd></div>}</dl>}</section>
  </main>;
}

export { App };
