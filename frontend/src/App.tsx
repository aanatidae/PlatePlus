import { FormEvent, useEffect, useRef, useState } from "react";
import { Activity, Camera, CircleDollarSign, Gauge, MapPin, Menu, Radar, RefreshCw, SlidersHorizontal, X } from "lucide-react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import HistoryFilters, { historyPath, type HistoryValues } from "./HistoryFilters";
import NetworkOverview, { categoryLabel } from "./NetworkOverview";
import { LocationProvider, LocationSelect, useLocations, locationPath, useFeed } from "./locations";
import { advancePlayback, createSimulationFrames, createSimulatorOutput, scenarioDetails, scenarioTitle, summarizeSimulation, type SimulatorFrame, type SimulatorScenario } from "./simulator";

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
        if (route === "/demo") { /* Demo Mode is an authenticated operational surface. */ }
        else if (!["/dashboard", "/recognition", "/pricing", "/simulator", "/webcam"].includes(route)) navigate("/dashboard", true);
      })
      .catch(() => {
        if (cancelled) return;
        window.sessionStorage.removeItem(AUTH_STORAGE_KEY);
        setSession(null);
        navigate("/login", true);
      })
      .finally(() => { if (!cancelled) setCheckingSession(false); });
    return () => { cancelled = true; };
  }, [route, session?.access_token]);

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
  return <LocationProvider><AdminShell admin={session.admin} route={route} onLogout={handleLogout} /></LocationProvider>;
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
    <p className="eyebrow">Simulated Prototype</p><div className="brand"><Activity size={22} /><span>PlatePlus</span></div><h1 id="login-title">Administrator sign in</h1><p>Use the seeded local administrator account to access the dashboard.</p>
    <form onSubmit={submit}>
      <label>Email<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" required /></label>
      <label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" required /></label>
      {error && <p className="form-error" role="alert">{error}</p>}
      <button type="submit" disabled={submitting}>{submitting ? "Signing in…" : "Sign in"}</button>
    </form>
  </section></main>;
}

function AdminShell({ admin, route, onLogout }: { admin: Admin; route: string; onLogout: () => void }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const { locations, selected, select, error: locationError, ready } = useLocations();
  const activeLocation = locations.find(item => item.id === selected);
  const independent = route === "/simulator" || route === "/webcam";
  const page = route === "/webcam" ? <WebcamPage /> : route === "/simulator" ? <SimulatorPage /> : route === "/recognition" ? <RecognitionPage key={selected} /> : route === "/pricing" ? <TrafficPage /> : route === "/demo" ? <DemoPage /> : <NetworkOverview />;
  const overview = route === "/dashboard";
  return <div className="command-shell">
    <aside className={menuOpen ? "command-sidebar open" : "command-sidebar"}>
      <a className="brand" href="/dashboard" onClick={(event) => { event.preventDefault(); setMenuOpen(false); navigate("/dashboard"); }}><Activity size={20} /> <span>PlatePlus</span></a>
      <p className="sidebar-label">Operations</p>
      <nav aria-label="Administrator navigation" onClick={() => setMenuOpen(false)}>
        <NavLink to="/dashboard" active={overview} icon={<Gauge size={17} />}>Overview</NavLink>
        <NavLink to="/recognition" active={route === "/recognition"} icon={<Radar size={17} />}>Plate recognition</NavLink>
        <NavLink to="/pricing" active={route === "/pricing"} icon={<CircleDollarSign size={17} />}>Dynamic pricing</NavLink>
        <NavLink to="/simulator" active={route === "/simulator"} icon={<SlidersHorizontal size={17} />}>Simulator</NavLink>
        <NavLink to="/demo" active={route === "/demo"} icon={<Activity size={17} />}>Demo Mode</NavLink>
        {LOCAL_WEBCAM_ENABLED && <NavLink to="/webcam" active={route === "/webcam"} icon={<Camera size={17} />}>Local webcam</NavLink>}
      </nav>
      <div className="sidebar-foot"><span className="live-dot" /> <span>Simulated Prototype</span></div>
    </aside>
    <section className="command-stage">
      <header className="top-control-bar"><button className="menu-toggle" aria-label="Toggle navigation" onClick={() => setMenuOpen(!menuOpen)}>{menuOpen ? <X size={19} /> : <Menu size={19} />}</button><div className="location-control"><MapPin size={15} />{independent ? <span>{route === "/simulator" ? "Independent simulator" : `Local webcam · ${locations.find(item => item.code === "PENCHALA")?.display_name ?? "Default toll"}`}</span> : <><LocationSelect value={selected} onChange={select} /><small>{activeLocation?.highway_or_route ?? "Simulated toll network"}</small></>}</div><div className="top-spacer" /><button className="sync-control" aria-label="Sync data" onClick={() => window.dispatchEvent(new Event("dashboard-refresh"))}><RefreshCw size={15} /> Sync data</button><div className="system-health">Simulated Prototype</div><div className="admin-menu"><span>{admin.display_name}</span><button className="secondary-button" onClick={onLogout}>Sign out</button></div></header>
      {locationError && <p className="form-error" role="alert">{locationError}</p>}
       {ready ? <>{page}{["/recognition", "/pricing"].includes(route) && <main className="dashboard-page"><HistoryInsights filters={{}} /></main>}</> : <PageLoading label="Loading PlatePlus toll locations…" />}
    </section>
  </div>;
}

function NavLink({ to, active, icon, children }: { to: string; active: boolean; icon: React.ReactNode; children: React.ReactNode }) {
  return <a className={active ? "nav-link active" : "nav-link"} href={to} onClick={(event) => { event.preventDefault(); navigate(to); }}>{icon}{children}</a>;
}

type Overview = { live: { traffic: { measured_at: string; congestion_percentage: number; congestion_category: string; vehicle_count: number; road_capacity: number; vehicles_per_hour?: number; average_speed_kmh?: number; plaza_status?: string; camera_status?: string; system_status?: string } | null; price: { amount: number; base_amount?: number; multiplier?: number } | null }; metrics: { detections: number; detections_this_hour?: number; transactions: number; successful_transactions: number; failed_transactions: number; revenue: number; average_recognition_confidence: number | null }; traffic_series: { measured_at: string; congestion_percentage: number }[]; price_series: { effective_at: string; amount: number }[]; detections: { items: Detection[]; has_more: boolean }; transactions: { items: Transaction[]; has_more: boolean } };
type Detection = { id: string; location_id: string; detected_at: string; normalized_plate: string | null; status: string; vehicle_id: string | null; detection_confidence: number; ocr_confidence: number | null; review_status?: string; review_note?: string | null };
type Transaction = { id: string; location_id: string; processed_at: string; amount: number; status: string; vehicle_id: string | null; account_id?: string | null; balance_after: number | null; reversed_at?: string | null };

function apiHeaders() { const session = readStoredSession(); return { Authorization: `Bearer ${session?.access_token ?? ""}` }; }
function Metric({ label, value, detail, tone = "" }: { label: string; value: string; detail: string; tone?: string }) { return <article className={`metric ${tone}`}><span>{label}</span><strong>{value}</strong><small>{detail}</small></article>; }
function RecordTable({ title, rows, kind, more, onMore }: { title: string; rows: Array<Detection | Transaction>; kind: "detection" | "transaction"; more: boolean; onMore: () => void }) { const { locations } = useLocations(); return <article className="record-card"><h2>{title}</h2><div className="records">{rows.length === 0 ? <p>No simulated records in this range.</p> : rows.map((row) => <div className="record" key={row.id}><strong>{kind === "detection" ? (row as Detection).normalized_plate ?? "Unread plate" : `RM${Number((row as Transaction).amount).toFixed(2)}`}</strong><span className={`status ${(row as Detection | Transaction).status}`}>{(row as Detection | Transaction).status.replace(/_/g, " ")}</span><small>{locations.find(location => location.id === row.location_id)?.display_name ?? "Unknown location"}<br />{new Date(kind === "detection" ? (row as Detection).detected_at : (row as Transaction).processed_at).toLocaleString("en-MY", { timeZone: "Asia/Kuala_Lumpur" })}</small></div>)}</div>{more && <button className="secondary-button load-more" onClick={onMore}>Load more</button>}</article>; }

type TollPrice = { id: string; location_id: string; effective_at: string; amount: number; congestion_category: string; rule_version?: string };
function PageLoading({ label = "Loading PlatePlus telemetry…" }: { label?: string }) { return <main className="dashboard-page"><section className="empty-admin">{label}</section></main>; }
function PageError({ message }: { message: string }) { return <main className="dashboard-page"><section className="empty-admin"><p className="form-error">{message}</p></section></main>; }

type DemoGuide = { mode: string; guide: string[]; fallback_alpr: string; boundaries: string[] };
function DemoPage() {
  const guide = useFeed<DemoGuide>("/api/operations/demo"); const [notice, setNotice] = useState(""); const [resetting, setResetting] = useState(false);
  async function restore() { if (!window.confirm("Restore the safe synthetic Demo Mode baseline? Demo wallet changes and prior Demo Mode records will be reset.")) return; setResetting(true); try { const response = await fetch(`${API_BASE_URL}/api/operations/demo/reset`, { method: "POST", headers: apiHeaders() }); const body = await response.json().catch(() => null) as { seeded_recognitions?: number; detail?: string } | null; if (!response.ok) throw new Error(body?.detail ?? "Demo Mode could not be restored."); setNotice(`Demo Mode is ready with ${body?.seeded_recognitions ?? 0} seeded recognition examples.`); window.dispatchEvent(new Event("dashboard-refresh")); } catch (error) { setNotice(error instanceof Error ? error.message : "Demo Mode could not be restored."); } finally { setResetting(false); } }
  return <main className="dashboard-page"><section className="page-heading"><div><p className="eyebrow">PRESENTATION READY</p><h1>Demo Mode</h1><p>Restore a safe simulated baseline, then follow the guided capstone walkthrough.</p></div><span className="refresh-note">SIMULATED ONLY</span></section>{notice && <p className="traffic-notice">{notice}</p>}{guide.error && <p className="form-error">{guide.error}</p>}<section className="detail-card"><div className="section-title"><div><p className="eyebrow">RESET-TO-DEMO-DATA</p><h2>Prepare the walkthrough</h2></div><button onClick={() => void restore()} disabled={resetting}>{resetting ? "Restoring…" : "Restore Demo Mode"}</button></div><p className="field-note">This is idempotent: it restores balances for the synthetic `@example.test` accounts and replaces only records explicitly created by Demo Mode. Administrator access, toll-location configuration, and normal operational history are preserved.</p></section><section className="traffic-grid"><article className="admin-card"><h2>Guided flow</h2><ol className="demo-steps">{guide.data?.guide.map(item => <li key={item}>{item}</li>) ?? <li>Loading the presentation guide…</li>}</ol></article><article className="admin-card"><h2>Fallback ALPR</h2><p>{guide.data?.fallback_alpr ?? "Loading fallback instructions…"}</p><a href="/recognition" onClick={(event) => { event.preventDefault(); navigate("/recognition"); }}>Open Plate Recognition</a></article></section><section className="detail-card"><div className="section-title"><div><p className="eyebrow">SYSTEM INFORMATION</p><h2>Presentation boundaries</h2></div></div><ul className="demo-boundaries">{guide.data?.boundaries.map(item => <li key={item}>{item}</li>) ?? <li>Loading system information…</li>}</ul><p className="field-note">Overview reads live simulated telemetry; Simulator remains browser-local and never mutates it.</p></section></main>;
}

type HistoryAnalytics = { series: { date: string; average_toll: number | null; average_congestion: number | null; detections: number; low_confidence: number; transactions: number; payment_success_rate: number | null; simulated_revenue: number }[]; locations: { location_id: string; display_name: string; average_toll: number | null; average_congestion: number | null; price_records: number; traffic_records: number }[]; scenario_comparison: { scenario: string; records: number; average_congestion: number }[] };
function HistoryInsights({ filters }: { filters: HistoryValues }) {
  const { selected } = useLocations(); const path = locationPath(historyPath("/api/data/history/analytics", filters), selected); const analytics = useFeed<HistoryAnalytics>(path); const series = analytics.data?.series ?? [];
  async function exportCsv() { const response = await fetch(`${API_BASE_URL}${locationPath(historyPath("/api/data/history/export.csv", filters), selected)}`, { headers: apiHeaders() }); if (!response.ok) return; const url = URL.createObjectURL(await response.blob()); const link = document.createElement("a"); link.href = url; link.download = "plateplus-simulated-history.csv"; link.click(); URL.revokeObjectURL(url); }
  return <section className="detail-card history-insights"><div className="section-title"><div><p className="eyebrow">LOCATION-AWARE HISTORY</p><h2>Congestion, toll, recognition, and payment trends</h2></div><button className="secondary-button" onClick={() => void exportCsv()}>Export CSV</button></div>{analytics.error && <p className="form-error">{analytics.error}</p>}{!analytics.data ? <p>Loading historical analysis…</p> : <><div className="history-chart">{series.length ? <ResponsiveContainer width="100%" height={260}><LineChart data={series}><CartesianGrid strokeDasharray="3 3" stroke="#24444a" /><XAxis dataKey="date" stroke="#8baaa6" /><YAxis yAxisId="left" stroke="#8baaa6" /><YAxis yAxisId="right" orientation="right" stroke="#8baaa6" /><Tooltip /><Legend /><Line yAxisId="left" type="monotone" dataKey="average_congestion" name="Avg. congestion %" stroke="#e5b04d" connectNulls /><Line yAxisId="right" type="monotone" dataKey="average_toll" name="Avg. toll (RM)" stroke="#62dec4" connectNulls /></LineChart></ResponsiveContainer> : <p>No simulated history matches these filters yet.</p>}</div><div className="data-table-wrap"><table><thead><tr><th>Location</th><th>Average congestion</th><th>Average toll</th><th>Traffic records</th></tr></thead><tbody>{analytics.data.locations.length ? analytics.data.locations.map(row => <tr key={row.location_id}><td>{row.display_name}</td><td>{row.average_congestion == null ? "—" : `${Number(row.average_congestion).toFixed(1)}%`}</td><td>{row.average_toll == null ? "—" : `RM${Number(row.average_toll).toFixed(2)}`}</td><td>{row.traffic_records}</td></tr>) : <tr><td colSpan={4}>No location history matches these filters.</td></tr>}</tbody></table></div><div className="scenario-summary">{analytics.data.scenario_comparison.map(row => <span key={row.scenario}>{row.scenario.replace(/_/g, " ")} · {Number(row.average_congestion).toFixed(1)}% average congestion ({row.records})</span>)}</div></>}</section>;
}

function RecognitionPage() {
  const { selected, locations } = useLocations();
  const [filters, setFilters] = useState<HistoryValues>({});
  const detectionFeed = useFeed<Detection[]>(locationPath(historyPath("/api/data/detections?limit=50", filters), selected));
  const transactionFeed = useFeed<Transaction[]>(locationPath(historyPath("/api/data/transactions?limit=50", filters), selected));
  const detections = detectionFeed.data ?? []; const transactions = transactionFeed.data ?? [];
  const [error, setError] = useState(""); const [uploadResult, setUploadResult] = useState<FrameResult | null>(null); const [uploading, setUploading] = useState(false);
  async function submitImage(event: FormEvent<HTMLFormElement>) { event.preventDefault(); if (selected === "all") { setError("Select a toll location before running recognition."); return; } const image = new FormData(event.currentTarget).get("image"); if (!(image instanceof File) || image.size === 0) { setError("Choose a JPEG, PNG, or WebP image first."); return; } setError(""); setUploading(true); try { const form = new FormData(); form.append("image", image); const response = await fetch(`${API_BASE_URL}${locationPath("/api/webcam/images", selected)}`, { method: "POST", headers: { ...apiHeaders(), "Idempotency-Key": crypto.randomUUID() }, body: form }); const body = await response.json().catch(() => null) as FrameResult | { detail?: string } | null; if (!response.ok) throw new Error(body && "detail" in body ? body.detail : "Image recognition failed."); setUploadResult(body as FrameResult); window.dispatchEvent(new Event("dashboard-refresh")); } catch (reason) { setError(reason instanceof Error ? reason.message : "Image recognition failed."); } finally { setUploading(false); } }

  const accepted = detections.filter((item) => item.status === "accepted").length;
  return <main className="dashboard-page"><section className="page-heading"><div><p className="eyebrow">ALPR OPERATIONS</p><h1>Plate recognition</h1><p>{LOCAL_WEBCAM_ENABLED ? "Upload a still image for local-only ALPR, or review persisted simulated results. Image bytes are never retained." : "Review persisted simulated ALPR results. Local image inference remains on the operator machine and is not exposed through this cloud dashboard."}</p></div><span className="refresh-note"><span className="live-dot" /> Protected data feed</span></section><HistoryFilters values={filters} change={setFilters} />{(error || detectionFeed.error || transactionFeed.error) && <p className="form-error" role="alert">{error || detectionFeed.error || transactionFeed.error}</p>}{(!detectionFeed.data || !transactionFeed.data) && <p role="status">Loading PlatePlus history…</p>}{LOCAL_WEBCAM_ENABLED ? <section className="detail-card"><div className="section-title"><div><p className="eyebrow">STILL-IMAGE TEST</p><h2>Run local ALPR once</h2></div><span>JPEG, PNG, or WebP · max 5 MB</span></div><form className="upload-form" onSubmit={(event) => void submitImage(event)}><input name="image" type="file" accept="image/jpeg,image/png,image/webp" required /><button disabled={uploading || selected === "all"}>{uploading ? "Processing locally…" : "Recognize image"}</button></form>{selected === "all" && <p className="field-note">Select a toll location in the top bar before running recognition.</p>}{uploadResult && <p className="traffic-notice"><strong>{uploadResult.plate_text ?? "No plate read"}</strong> · {uploadResult.message}{uploadResult.payment_status ? ` Simulated payment: ${uploadResult.payment_status}.` : ""}</p>}</section> : <section className="detail-card"><div className="section-title"><div><p className="eyebrow">LOCAL INFERENCE</p><h2>Run ALPR on the operator machine</h2></div><span>Cloud dashboard</span></div><p className="field-note">Image upload is unavailable here by design: the production API does not receive raw images, YOLO weights, or PaddleOCR models. Start the local backend and dashboard with <code>VITE_ENABLE_LOCAL_WEBCAM=true</code> to run a one-time image recognition.</p></section>}<section className="metric-grid page-metrics"><Metric tone="teal" label="Total detections" value={String(detections.length)} detail="Latest 50 records" /><Metric tone="teal" label="Accepted reads" value={String(accepted)} detail="Passed confidence gate" /><Metric label="Manual review" value={String(detections.filter(item => item.review_status === "pending").length)} detail="Uncertain reads awaiting review" /><Metric label="Payments linked" value={String(transactions.length)} detail="Latest 50 transactions" /></section><section className="detail-card"><div className="section-title"><div><p className="eyebrow">DETECTION LOG</p><h2>Latest roadside recognitions</h2></div><span>Malaysia time</span></div><div className="data-table-wrap"><table><thead><tr><th>Location</th><th>Plate</th><th>Recognition</th><th>Review</th><th>Vehicle</th><th>Captured</th></tr></thead><tbody>{detections.length ? detections.map((item) => <tr key={item.id}><td>{locations.find(location => location.id === item.location_id)?.display_name ?? "Unknown location"}</td><td><strong>{item.normalized_plate ?? "Unread plate"}</strong></td><td><span className={`status ${item.status}`}>{item.status.replace(/_/g, " ")}</span></td><td>{item.review_status === "pending" ? "Pending" : item.review_status?.replace(/_/g, " ") ?? "Not required"}</td><td>{item.vehicle_id ? "Registered" : "Unknown"}</td><td>{new Date(item.detected_at).toLocaleString("en-MY", { timeZone: "Asia/Kuala_Lumpur" })}</td></tr>) : <tr><td colSpan={6}>No simulated detection records are available.</td></tr>}</tbody></table></div></section><PaymentOperations transactions={transactions} /><RecordTable title="Transaction history · latest 50 matches" rows={transactions} kind="transaction" more={false} onMore={() => undefined} /></main>;
}

type WalletAccount = { id: string; balance: number; opening_balance: number };
type PaymentSummary = { transaction_count: number; successful_count: number; net_revenue: number; reversed_amount: number; by_location: { location_id: string; display_name: string; transactions: number; revenue: number }[] };
type PaymentNotification = { id: string; notification_type: string; message: string; created_at: string };
function PaymentOperations({ transactions }: { transactions: Transaction[] }) {
  const { selected } = useLocations(); const accountsFeed = useFeed<WalletAccount[]>("/api/data/accounts");
  const summaryFeed = useFeed<PaymentSummary>(locationPath("/api/data/payment-summary", selected));
  const notificationsFeed = useFeed<PaymentNotification[]>("/api/data/payment-notifications?limit=5");
  const [accountId, setAccountId] = useState(""); const [amount, setAmount] = useState("10.00"); const [notice, setNotice] = useState("");
  useEffect(() => { if (!accountId && accountsFeed.data?.[0]) setAccountId(accountsFeed.data[0].id); }, [accountId, accountsFeed.data]);
  async function request(path: string, init?: RequestInit) { const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers: { ...apiHeaders(), "Content-Type": "application/json", ...(init?.headers ?? {}) } }); if (!response.ok) throw new Error((await response.json().catch(() => null) as { detail?: string } | null)?.detail ?? "Payment request failed."); return response.json(); }
  async function topUp(event: FormEvent) { event.preventDefault(); try { await request(`/api/data/accounts/${accountId}/top-ups`, { method: "POST", body: JSON.stringify({ amount: Number(amount), idempotency_key: crypto.randomUUID() }) }); setNotice("Simulated top-up recorded."); window.dispatchEvent(new Event("dashboard-refresh")); } catch (error) { setNotice(error instanceof Error ? error.message : "Top-up failed."); } }
  async function reverse(transaction: Transaction) { const reason = window.prompt("Reason for this simulated reversal:", "Demo correction"); if (!reason) return; try { await request(`/api/data/transactions/${transaction.id}/reversal`, { method: "POST", body: JSON.stringify({ reason, idempotency_key: crypto.randomUUID() }) }); setNotice("Simulated reversal recorded."); window.dispatchEvent(new Event("dashboard-refresh")); } catch (error) { setNotice(error instanceof Error ? error.message : "Reversal failed."); } }
  const summary = summaryFeed.data;
  return <section className="detail-card"><div className="section-title"><div><p className="eyebrow">SIMULATED WALLET OPERATIONS</p><h2>Payments, balances, and notifications</h2></div><span>Prototype only</span></div>{notice && <p className="traffic-notice">{notice}</p>}<section className="metric-grid page-metrics"><Metric label="Transactions" value={String(summary?.transaction_count ?? "—")} detail="Selected scope" /><Metric tone="teal" label="Net revenue" value={summary ? `RM${Number(summary.net_revenue).toFixed(2)}` : "—"} detail="Successful less reversals" /><Metric label="Reversed" value={summary ? `RM${Number(summary.reversed_amount).toFixed(2)}` : "—"} detail="Simulated corrections" /></section><div className="traffic-grid"><form className="admin-card" onSubmit={topUp}><h2>Wallet top-up</h2><label>Simulated account<select value={accountId} onChange={event => setAccountId(event.target.value)}>{(accountsFeed.data ?? []).map(account => <option key={account.id} value={account.id}>RM{Number(account.balance).toFixed(2)} current · opening RM{Number(account.opening_balance).toFixed(2)}</option>)}</select></label><label>Amount (RM)<input type="number" min=".01" step=".01" value={amount} onChange={event => setAmount(event.target.value)} /></label><button>Record simulated top-up</button></form><article className="admin-card"><h2>Recent notifications</h2><div className="audit-list">{(notificationsFeed.data ?? []).map(item => <div key={item.id}><strong>{item.notification_type.replace(/_/g, " ")}</strong><span>{item.message}</span></div>)}{!notificationsFeed.data?.length && <p>No simulated payment notifications yet.</p>}</div></article></div><div className="data-table-wrap"><table><thead><tr><th>Location</th><th>Transactions</th><th>Net simulated revenue</th></tr></thead><tbody>{summary?.by_location.map(row => <tr key={row.location_id}><td>{row.display_name}</td><td>{row.transactions}</td><td>RM{Number(row.revenue).toFixed(2)}</td></tr>) ?? <tr><td colSpan={3}>Loading location payment statistics…</td></tr>}</tbody></table></div><div className="audit-list">{transactions.filter(transaction => transaction.status === "successful").slice(0, 5).map(transaction => <div key={transaction.id}><strong>RM{Number(transaction.amount).toFixed(2)} · {transaction.reversed_at ? "reversed" : "successful"}</strong>{!transaction.reversed_at && <button className="secondary-button" onClick={() => void reverse(transaction)}>Reverse</button>}</div>)}</div></section>;
}

function ruleMultiplier(amount: number, normalAmount: number) { return normalAmount > 0 ? Number((amount / normalAmount).toFixed(2)) : 1; }

function PricingPage() {
  const { selected, locations } = useLocations();
  const [filters, setFilters] = useState<HistoryValues>({});
  const priceFeed = useFeed<TollPrice[]>(locationPath(historyPath("/api/data/toll-prices?limit=50", filters), selected));
  const rulesFeed = useFeed<PricingRule[]>("/api/traffic/pricing-rules");
  const overviewFeed = useFeed<Overview>(locationPath("/api/live/overview", selected));
  const prices = priceFeed.data ?? []; const rules = rulesFeed.data ?? []; const overview = overviewFeed.data;
  const error = priceFeed.error || rulesFeed.error || overviewFeed.error;
  const livePrice = overview?.live.price; const liveTraffic = overview?.live.traffic;
  return <main className="dashboard-page"><section className="page-heading"><div><p className="eyebrow">LIVE TOLL MANAGEMENT</p><h1>Dynamic toll pricing</h1><p>Current toll decisions are calculated from live Malaysia-time traffic telemetry.</p></div><span className="refresh-note"><span className="live-dot" /> LIVE DATA</span></section>{error && <p className="form-error" role="alert">{error}</p>}{!overview && <p role="status">Loading PlatePlus telemetry…</p>}<section className="pricing-hero"><div><span className={`status ${liveTraffic?.congestion_category ?? ""}`}>{categoryLabel(liveTraffic?.congestion_category ?? "Awaiting traffic")}</span><strong>{livePrice ? `RM${Number(livePrice.amount).toFixed(2)}` : "N/A"}</strong><p>{selected === "all" ? "Network average toll" : "Current toll price"}</p></div><dl><div><dt>Current congestion</dt><dd>{liveTraffic ? `${Number(liveTraffic.congestion_percentage).toFixed(1)}%` : "N/A"}</dd></div><div><dt>Vehicle load</dt><dd>{liveTraffic ? `${liveTraffic.vehicle_count} / ${liveTraffic.road_capacity}` : "N/A"}</dd></div><div><dt>{selected === "all" ? "Previous recorded toll (any location)" : "Previous recorded toll"}</dt><dd>{prices[1] ? `RM${Number(prices[1].amount).toFixed(2)}` : "No prior record"}</dd></div></dl></section><section className="detail-card"><div className="section-title"><div><p className="eyebrow">ACTIVE BANDS</p><h2>Congestion-to-toll rules</h2></div><a href="/simulator" onClick={(event) => { event.preventDefault(); navigate("/simulator"); }}>Open simulator</a></div><div className="rule-grid">{rules.map((rule) => <article key={rule.id} className={`price-rule ${rule.congestion_category}`}><span>{categoryLabel(rule.congestion_category)}</span><strong>{selected === "all" ? `${(ruleMultiplier(Number(rule.amount), Number(rules.find(item => item.scenario === "normal")?.amount ?? 0))).toFixed(2)}× base` : `RM${(Number(locations.find(item => item.id === selected)?.base_toll ?? 0) * ruleMultiplier(Number(rule.amount), Number(rules.find(item => item.scenario === "normal")?.amount ?? 0))).toFixed(2)}`}</strong><small>{rule.minimum_percentage}% to {rule.maximum_percentage}% congestion</small></article>)}</div></section><section className="detail-card"><div className="section-title"><div><p className="eyebrow">PRICE HISTORY</p><h2>Recent price decisions · latest 50 matches</h2></div></div><HistoryFilters values={filters} change={setFilters} pricing /><div className="data-table-wrap"><table><thead><tr><th>Location</th><th>Effective time</th><th>Congestion</th><th>Toll price</th><th>Rule version</th></tr></thead><tbody>{prices.length ? prices.map((price) => <tr key={price.id}><td>{locations.find(location => location.id === price.location_id)?.display_name ?? "Unknown location"}</td><td>{new Date(price.effective_at).toLocaleString("en-MY", { timeZone: "Asia/Kuala_Lumpur" })}</td><td><span className={`status ${price.congestion_category}`}>{categoryLabel(price.congestion_category)}</span></td><td><strong>RM{Number(price.amount).toFixed(2)}</strong></td><td>{price.rule_version ?? "N/A"}</td></tr>) : <tr><td colSpan={5}>No live price history is available.</td></tr>}</tbody></table></div></section></main>;
}

type SimulatorBatch = { timestamp: string; scenario: SimulatorScenario; start: string; duration: number; playbackSpeed: number; frames: SimulatorFrame[] };

function SimulatorPage() {
  const { locations } = useLocations();
  const [simLocation, setSimLocation] = useState("");
  const [runNetwork, setRunNetwork] = useState(false);
  const [scenario, setScenario] = useState<SimulatorScenario>("moderate");
  const [start, setStart] = useState(() => new Date().toISOString().slice(0, 16));
  const [duration, setDuration] = useState(60);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [custom, setCustom] = useState({ congestion: 0, lanes: 3, baseToll: 0 });
  const [batch, setBatch] = useState<SimulatorBatch | null>(null);
  const [history, setHistory] = useState<SimulatorBatch[]>([]);
  const [playhead, setPlayhead] = useState(0);
  const [simulationStatus, setSimulationStatus] = useState<"idle" | "running" | "completed">("idle");

  useEffect(() => {
    if (!simLocation && locations[0]) setSimLocation(locations[0].id);
  }, [locations, simLocation]);

  useEffect(() => {
    const location = locations.find(item => item.id === simLocation);
    if (!location) return;
    setCustom({ congestion: Math.round(Number(location.road_capacity) * .55), lanes: 3, baseToll: Number(location.base_toll) });
  }, [simLocation, locations]);

  useEffect(() => {
    if (!batch || simulationStatus !== "running" || batch.frames.length < 2) return;
    const timer = window.setInterval(() => setPlayhead(previous => {
      const next = advancePlayback(previous, batch.frames.length);
      if (next.status === "completed") setSimulationStatus("completed");
      return next.frameIndex;
    }), Math.max(350, 1100 / playbackSpeed));
    return () => window.clearInterval(timer);
  }, [batch, playbackSpeed, simulationStatus]);

  const selectedLocation = locations.find(item => item.id === simLocation);
  const generatedLocations = locations.filter(item => item.code !== "SIMULATOR");
  const targets = runNetwork ? generatedLocations : selectedLocation ? [selectedLocation] : [];
  const isWebcamLocation = selectedLocation?.code === "SIMULATOR";
  const currentFrame = batch?.frames[playhead];
  const selectedOutput = currentFrame?.outputs.find(item => item.locationId === simLocation) ?? currentFrame?.outputs[0];
  const summary = batch && simulationStatus === "completed" ? summarizeSimulation(batch.frames) : null;
  const malaysiaTime = (timestamp: string) => new Date(timestamp).toLocaleTimeString("en-MY", { timeZone: "Asia/Kuala_Lumpur", hour: "2-digit", minute: "2-digit" });
  const namedScenarios = Object.keys(scenarioDetails) as Exclude<SimulatorScenario, "custom">[];

  function run() {
    if (!targets.length) return;
    const frames = createSimulationFrames(targets, scenario, custom, start, duration);
    const next: SimulatorBatch = { timestamp: new Date().toISOString(), scenario, start, duration, playbackSpeed, frames };
    setBatch(next);
    setHistory(items => [next, ...items].slice(0, 6));
    setPlayhead(0);
    setSimulationStatus(frames.length === 1 ? "completed" : "running");
  }

  function reset() {
    setScenario("moderate");
    setRunNetwork(false);
    setBatch(null);
    setPlayhead(0);
    setSimulationStatus("idle");
  }
  function replay() { if (!batch) return; setPlayhead(0); setSimulationStatus(batch.frames.length === 1 ? "completed" : "running"); }

  return <main className="dashboard-page">
    <section className="page-heading"><div><p className="eyebrow">SANDBOX ENVIRONMENT</p><h1>Traffic & toll simulator</h1><p>Model location-specific hypothetical traffic without altering live telemetry, toll prices, records, or transactions.</p></div><span className="refresh-note">Local-only simulation state</span></section>
    <section className="detail-card simulator-controls"><LocationSelect all={false} label="Simulator toll location" value={simLocation} onChange={setSimLocation} /><label className="toggle-row"><input type="checkbox" checked={runNetwork} onChange={event => setRunNetwork(event.target.checked)} disabled={isWebcamLocation} /> Run all generated toll locations</label><label>Simulation start time<input type="datetime-local" value={start} onChange={event => setStart(event.target.value)} /></label><label>Duration<select value={duration} onChange={event => setDuration(Number(event.target.value))}><option value={30}>30 minutes</option><option value={60}>1 hour</option><option value={120}>2 hours</option><option value={240}>4 hours</option></select></label><label>Playback speed<select value={playbackSpeed} onChange={event => setPlaybackSpeed(Number(event.target.value))}><option value={.5}>0.5×</option><option value={1}>1×</option><option value={2}>2×</option><option value={4}>4×</option></select></label></section>
    {isWebcamLocation && <p className="traffic-notice">Simulator Toll Plaza is webcam-derived in live monitoring. This is a local projection only and never creates webcam or live telemetry.</p>}
    {scenario === "time_based" && <p className="traffic-notice">Prototype Malaysia time profile: each frame follows estimated daily traffic conditions from its simulated Asia/Kuala_Lumpur timestamp, not live traffic data.</p>}
    <section className="sim-steps"><article><span>STEP 1</span><h2>Simulation scope</h2><strong>{runNetwork ? `${targets.length} locations` : selectedLocation?.display_name ?? "Loading"}</strong><small>{runNetwork ? "LDP, DUKE, KESAS and NPE · webcam plaza excluded" : `${selectedLocation?.road_capacity ?? 0} vehicles/hour capacity`}</small></article><article><span>STEP 2</span><h2>Scenario window</h2><strong>{scenarioTitle(scenario)}</strong><small>{duration} minutes from {start ? new Date(start).toLocaleTimeString("en-MY", { hour: "2-digit", minute: "2-digit" }) : "select a start"} · {playbackSpeed}× playback</small></article><article className="impact"><span>STEP 3</span><h2>Projected outcome</h2><strong>{selectedOutput ? `RM${selectedOutput.dynamicToll.toFixed(2)}` : "Run simulation"}</strong><small>{selectedOutput ? `${selectedOutput.congestion}% congestion · RM${selectedOutput.baseToll.toFixed(2)} baseline` : "Rule-based estimate pending"}</small></article></section>
    <section className="scenario-strip simulator-scenarios">{namedScenarios.map(key => <button key={key} className={scenario === key ? "scenario-card active" : "scenario-card"} onClick={() => setScenario(key)}><strong>{scenarioDetails[key].title}</strong><span>{scenarioDetails[key].description}</span></button>)}<button className={scenario === "custom" ? "scenario-card active" : "scenario-card"} onClick={() => setScenario("custom")}><strong>Custom scenario</strong><span>Configure traffic, lanes and baseline toll</span></button></section>
    {scenario === "custom" && <section className="detail-card custom-inputs"><div className="section-title"><div><p className="eyebrow">CUSTOM PARAMETERS</p><h2>Configure hypothetical conditions</h2></div></div><label>Vehicles per hour<input type="number" min={0} max={selectedLocation?.road_capacity ?? 5000} value={custom.congestion} onChange={event => setCustom({ ...custom, congestion: Number(event.target.value) })} /></label><label>Active lanes<input type="number" min={1} max={4} value={custom.lanes} onChange={event => setCustom({ ...custom, lanes: Number(event.target.value) })} /></label><label>Base toll (RM)<input type="number" min={0} max={20} step=".01" value={custom.baseToll} onChange={event => setCustom({ ...custom, baseToll: Number(event.target.value) })} /></label></section>}
    <section className="sim-actions"><button onClick={run} disabled={!targets.length}>Run simulation</button>{simulationStatus === "completed" && <button className="secondary-button" onClick={replay}>Replay simulation</button>}<button className="secondary-button" onClick={reset}>Reset simulation</button></section>
    {batch && currentFrame && <section className="simulation-outcomes"><div className="section-title"><div><p className="eyebrow">SIMULATION OUTCOMES</p><h2>{runNetwork ? "Network comparison" : "Location comparison"}</h2></div><span className="refresh-note">{simulationStatus === "completed" ? `Simulation complete · ${batch.frames.length} frames processed` : `Frame ${playhead + 1} / ${batch.frames.length} · ${malaysiaTime(currentFrame.timestamp)}`}</span></div><section className="metric-grid page-metrics"><Metric label="Locations modeled" value={`${currentFrame.outputs.length}`} detail="Sandbox-only outputs" /><Metric label="Scenario" value={scenarioTitle(batch.scenario)} detail={`${batch.duration}-minute window`} /><Metric tone="teal" label="Baseline toll" value={`RM${(selectedOutput?.baseToll ?? 0).toFixed(2)}`} detail="Selected location before scenario" /><Metric label="Dynamic toll" value={`RM${(selectedOutput?.dynamicToll ?? 0).toFixed(2)}`} detail={selectedOutput ? `${selectedOutput.category.replace(/_/g, " ")} · ${selectedOutput.multiplier.toFixed(1)}× multiplier` : "Awaiting scenario"} /></section><div className="data-table-wrap"><table><thead><tr><th>Location</th><th>Traffic volume</th><th>Congestion</th><th>Band</th><th>Speed</th><th>Baseline toll</th><th>Dynamic toll</th><th>Change</th></tr></thead><tbody>{currentFrame.outputs.map(output => <tr key={output.locationId}><td>{output.locationName}</td><td>{output.volume.toLocaleString()} / {output.capacity.toLocaleString()}</td><td>{output.congestion}%</td><td>{output.category.replace(/_/g, " ")}</td><td>{output.speed} km/h</td><td>RM{output.baseToll.toFixed(2)}</td><td>RM{output.dynamicToll.toFixed(2)}</td><td>+RM{(output.dynamicToll - output.baseToll).toFixed(2)}</td></tr>)}</tbody></table></div><section className="rationale"><div><p className="eyebrow">PRICING RATIONALE · CURRENT FRAME</p><h2>{selectedOutput ? `${selectedOutput.category.replace(/_/g, " ")} band · RM${selectedOutput.baseToll.toFixed(2)} × ${selectedOutput.multiplier.toFixed(1)} = RM${selectedOutput.dynamicToll.toFixed(2)}` : "Awaiting output"}</h2><p>Every displayed value is calculated from this frame’s Malaysia-time timestamp, location profile, scenario pattern, deterministic variation, and congestion band. No history, payment, price, or Overview record is written.</p></div><div className="severity-scale"><span style={{ width: `${selectedOutput?.congestion ?? 0}%` }} /><small>Normal → Moderate → Peak Hour → Severe</small></div></section></section>}
    {summary && batch && <section className="simulation-summary"><div className="section-title"><div><p className="eyebrow">SIMULATION COMPLETE</p><h2>Simulation summary</h2><p>{malaysiaTime(batch.frames[0].timestamp)} – {malaysiaTime(batch.frames[batch.frames.length - 1].timestamp)} · {batch.duration}-minute simulation · {batch.frames.length} five-minute frames</p></div><span className="refresh-note">{scenarioTitle(batch.scenario)}</span></div>{summary.locations.length === 1 ? <><section className="metric-grid page-metrics"><Metric label="Average traffic" value={`${summary.locations[0].averageVolume.toFixed(0)} / hour`} detail={`Peak ${summary.locations[0].maxVolume.toLocaleString()} / hour`} /><Metric label="Average congestion" value={`${summary.locations[0].averageCongestion.toFixed(1)}%`} detail={`Peak ${summary.locations[0].maxCongestion.toFixed(1)}% at ${malaysiaTime(summary.locations[0].peakTimestamp)}`} /><Metric tone="teal" label="Average speed" value={`${summary.locations[0].averageSpeed.toFixed(1)} km/h`} detail={`Lowest ${summary.locations[0].minSpeed.toFixed(1)} km/h`} /><Metric label="Dynamic toll" value={`RM${summary.locations[0].averageToll.toFixed(2)}`} detail={`RM${summary.locations[0].minToll.toFixed(2)}–RM${summary.locations[0].maxToll.toFixed(2)} · ${summary.locations[0].priceChanges} changes`} /></section><div className="summary-chart"><h3>Congestion and dynamic toll over time</h3><ResponsiveContainer width="100%" height={250}><LineChart data={batch.frames.map(frame => { const output = frame.outputs[0]; return { time: malaysiaTime(frame.timestamp), congestion: output.congestion, toll: output.dynamicToll }; })}><CartesianGrid stroke="#285159" strokeDasharray="3 3" /><XAxis dataKey="time" stroke="#8aa5a2" fontSize={11} minTickGap={24} /><YAxis yAxisId="congestion" stroke="#8aa5a2" fontSize={11} domain={[0, 100]} /><YAxis yAxisId="toll" orientation="right" stroke="#8aa5a2" fontSize={11} /><Tooltip contentStyle={{ background: "#0a1a1e", border: "1px solid #34766e" }} /><Legend /><Line yAxisId="congestion" type="monotone" dataKey="congestion" name="Congestion %" stroke="#68ecd3" strokeWidth={2} dot={false} /><Line yAxisId="toll" type="stepAfter" dataKey="toll" name="Dynamic toll (RM)" stroke="#e5b04d" strokeWidth={2} dot={false} /></LineChart></ResponsiveContainer></div></> : <><section className="metric-grid page-metrics"><Metric label="Network average congestion" value={`${summary.networkAverageCongestion.toFixed(1)}%`} detail="Mean of location averages" /><Metric label="Most congested location" value={summary.mostCongestedLocation?.locationName ?? "—"} detail={`${summary.highestCongestion.toFixed(1)}% peak`} /><Metric tone="teal" label="Highest traffic" value={summary.highestTrafficLocation?.locationName ?? "—"} detail={`${summary.highestTrafficLocation?.maxVolume.toLocaleString() ?? 0} vehicles/hour`} /><Metric label="Highest dynamic toll" value={summary.highestTollLocation?.locationName ?? "—"} detail={`RM${summary.highestTollLocation?.maxToll.toFixed(2) ?? "0.00"}`} /></section><div className="data-table-wrap"><table><thead><tr><th>Location</th><th>Avg congestion</th><th>Peak / state</th><th>Avg speed</th><th>Max toll</th><th>Price changes</th></tr></thead><tbody>{summary.locations.map(location => <tr key={location.locationId}><td>{location.locationName}</td><td>{location.averageCongestion.toFixed(1)}%</td><td>{location.maxCongestion.toFixed(1)}% · {location.peakCategory.replace(/_/g, " ")}</td><td>{location.averageSpeed.toFixed(1)} km/h</td><td>RM{location.maxToll.toFixed(2)}</td><td>{location.priceChanges}</td></tr>)}</tbody></table></div></>}</section>}
    <section className="detail-card"><div className="section-title"><div><p className="eyebrow">SIMULATION HISTORY</p><h2>Local sandbox runs</h2></div></div><div className="data-table-wrap"><table><thead><tr><th>Timestamp</th><th>Scope</th><th>Scenario</th><th>Time range</th><th>Playback</th><th>Frames</th></tr></thead><tbody>{history.length ? history.map(item => <tr key={item.timestamp}><td>{new Date(item.timestamp).toLocaleTimeString("en-MY")}</td><td>{item.frames[0]?.outputs.length ?? 0} location{item.frames[0]?.outputs.length === 1 ? "" : "s"}</td><td>{scenarioTitle(item.scenario)}</td><td>{item.duration} min</td><td>{item.playbackSpeed}×</td><td>{item.frames.length} deterministic states</td></tr>) : <tr><td colSpan={6}>Run a sandbox scenario to record deterministic frame states locally. Live data remains unchanged.</td></tr>}</tbody></table></div></section>
  </main>;
}

type SandboxScenario = "normal" | "moderate" | "peak_hour" | "severe" | "custom";
type SandboxRun = { timestamp: string; scenario: SandboxScenario; volume: number; congestion: number; toll: number };

function LegacySimulatorPage() {
  const { locations } = useLocations();
  const [simLocation, setSimLocation] = useState(locations[0]?.id ?? "");
  const location = locations.find(item => item.id === simLocation);
  const baseline = useFeed<Overview>(locationPath("/api/live/overview", simLocation), Boolean(simLocation));
  const live = baseline.data;
  const capacity = Number(location?.road_capacity ?? 5000);
  const locationBase = Number(location?.base_toll ?? 2);
 const [scenario, setScenario] = useState<SandboxScenario>("moderate"); const [custom, setCustom] = useState({ congestion: Math.round(capacity * .55), lanes: 3, base: locationBase }); const [result, setResult] = useState<SandboxRun | null>(null); const [history, setHistory] = useState<SandboxRun[]>([]);
  const presets: Record<Exclude<SandboxScenario, "custom">, { title: string; volume: number; speed: number; congestion: number; description: string }> = { normal: { title: "Normal traffic", volume: 1500, speed: 70, congestion: 24, description: "Free-flowing toll approach" }, moderate: { title: "Moderate traffic", volume: 2800, speed: 48, congestion: 55, description: "Steady weekday demand" }, peak_hour: { title: "Peak hour", volume: 4100, speed: 31, congestion: 76, description: "Morning or evening rush" }, severe: { title: "Severe congestion", volume: 4850, speed: 21, congestion: 92, description: "Near-capacity road demand" } };
  const customVolume = Math.min(capacity, Math.max(0, custom.congestion)); const customCongestion = Number(((customVolume / capacity) * 100).toFixed(2)); const source = scenario === "custom" ? { title: "Custom scenario", volume: customVolume, speed: Math.round(Math.max(18, 82 - customCongestion * .62)), congestion: customCongestion, description: "Operator configured" } : { ...presets[scenario], volume: Math.round(capacity * presets[scenario].congestion / 100) };
  const base = scenario === "custom" ? custom.base : locationBase; const fixedTolls: Record<Exclude<SandboxScenario, "custom">, number> = { normal: locationBase, moderate: locationBase * 1.5, peak_hour: locationBase * 2, severe: locationBase * 2.5 }; const priceIncrease = source.congestion > 80 ? 3 : source.congestion > 60 ? 2 : source.congestion > 30 ? 1 : 0; const multiplier = base ? Number(((base + priceIncrease) / base).toFixed(2)) : 1; const recommended = scenario === "custom" ? Number((base + priceIncrease).toFixed(2)) : fixedTolls[scenario];
  function run() { if (!location) return; const next = { timestamp: new Date().toISOString(), scenario, volume: source.volume, congestion: source.congestion, toll: recommended }; setResult(next); setHistory((items) => [next, ...items].slice(0, 6)); }
  function reset() { setScenario("moderate"); setCustom({ congestion: Math.round(capacity * .55), lanes: 3, base: locationBase }); setResult(null); }
  const baselineVolume = live?.live.traffic?.vehicle_count ?? 0; const baselineCongestion = live?.live.traffic?.congestion_percentage ?? 0; const baselineToll = Number(live?.live.price?.amount ?? 0);
  return <main className="dashboard-page"><section className="page-heading"><div><p className="eyebrow">SANDBOX ENVIRONMENT</p><h1>Traffic & toll simulator</h1><p>What would happen if traffic conditions changed? Runs here never alter live telemetry, toll prices, records, or transactions.</p></div><span className="refresh-note">Independent simulation state</span></section><section className="detail-card"><LocationSelect all={false} label="Simulator toll location" value={simLocation} onChange={(id) => { setSimLocation(id); setResult(null); setHistory([]); const next = locations.find(item => item.id === id); setCustom({ congestion: Math.round(Number(next?.road_capacity ?? 5000) * .55), lanes: 3, base: Number(next?.base_toll ?? 2) }); }} /></section>{baseline.error && <p className="form-error" role="alert">{baseline.error}</p>}<section className="sim-steps"><article><span>STEP 1</span><h2>Baseline</h2><strong>{live ? `${Number(baselineCongestion).toFixed(1)}%` : "Unavailable"}</strong><small>{baselineVolume} vehicles/hour · RM{baselineToll.toFixed(2)} base state</small></article><article><span>STEP 2</span><h2>Selected scenario</h2><strong>{source.title}</strong><small>{source.volume} vehicles/hour · {source.speed} km/h</small></article><article className="impact"><span>STEP 3</span><h2>Projected impact</h2><strong>{result ? `RM${result.toll.toFixed(2)}` : "Run simulation"}</strong><small>{result ? `${result.congestion}% predicted congestion` : "Rule-based estimate pending"}</small></article></section><section className="scenario-strip">{(["normal", "moderate", "peak_hour", "severe", "custom"] as SandboxScenario[]).map((key) => <button key={key} className={scenario === key ? "scenario-card active" : "scenario-card"} onClick={() => setScenario(key)}><strong>{key === "custom" ? "Custom scenario" : presets[key].title}</strong><span>{key === "custom" ? "Configure congestion, lanes, and base toll" : `${Math.round(capacity * presets[key].congestion / 100).toLocaleString()} vehicles/hour · RM${fixedTolls[key].toFixed(2)}`}</span></button>)}</section>{scenario === "custom" && <section className="detail-card custom-inputs"><div className="section-title"><div><p className="eyebrow">CUSTOM PARAMETERS</p><h2>Configure hypothetical conditions</h2></div></div>{([ ["congestion", "Vehicles per hour", 0, capacity], ["lanes", "Active lanes", 1, 8], ["base", "Base toll (RM)", 0, 20] ] as const).map(([key, label, min, max]) => <label key={key}>{label}<input type="number" min={min} max={max} value={custom[key]} onChange={(event) => setCustom({ ...custom, [key]: Number(event.target.value) })} /></label>)}</section>}<section className="sim-actions"><button onClick={run}>Run simulation</button><button className="secondary-button" onClick={reset}>Reset simulation</button></section>{result && <section className="simulation-outcomes"><div className="section-title"><div><p className="eyebrow">SIMULATION OUTCOMES</p><h2>Projected impact</h2></div><span className={`status ${result.congestion >= 84 ? "severe" : result.congestion >= 61 ? "high" : result.congestion >= 31 ? "moderate" : "normal"}`}>{result.congestion >= 84 ? "Severe" : result.congestion >= 61 ? "Peak hour" : result.congestion >= 31 ? "Moderate" : "Normal"}</span></div><section className="metric-grid page-metrics"><Metric label="Predicted congestion" value={`${result.congestion}%`} detail="Hypothetical traffic state" /><Metric label="Traffic volume" value={`${result.volume.toLocaleString()}`} detail="Calculated vehicles per hour" /><Metric tone="teal" label="Rule-based toll" value={`RM${result.toll.toFixed(2)}`} detail={scenario === "custom" ? `RM${base.toFixed(2)} × ${multiplier.toFixed(2)}` : "Matches fixed toll pricing rule"} /><Metric label="Price change" value={`+RM${(result.toll - base).toFixed(2)}`} detail={base ? `${((result.toll / base - 1) * 100).toFixed(0)}% toll adjustment` : "Zero base toll"} /></section><section className="rationale"><div><p className="eyebrow">PRICING RATIONALE</p><h2>{scenario === "custom" ? `RM${base.toFixed(2)} × ${multiplier.toFixed(2)} = RM${result.toll.toFixed(2)}` : `${source.title} pricing rule = RM${result.toll.toFixed(2)}`}</h2><p>{source.title} estimates {result.volume.toLocaleString()} vehicles/hour at {source.speed} km/h and {result.congestion}% congestion. The sandbox pricing is independent from the live system.</p></div><div className="severity-scale"><span style={{ width: `${result.congestion}%` }} /><small>Normal → Moderate → Peak Hour → Severe</small></div></section></section>}<section className="detail-card"><div className="section-title"><div><p className="eyebrow">SIMULATION HISTORY</p><h2>Local sandbox runs</h2></div></div><div className="data-table-wrap"><table><thead><tr><th>Timestamp</th><th>Scenario</th><th>Traffic volume</th><th>Congestion</th><th>Recommended toll</th></tr></thead><tbody>{history.length ? history.map((item) => <tr key={item.timestamp}><td>{new Date(item.timestamp).toLocaleTimeString("en-MY")}</td><td>{item.scenario.replace(/_/g, " ")}</td><td>{item.volume.toLocaleString()} / hour</td><td>{item.congestion}%</td><td>RM{item.toll.toFixed(2)}</td></tr>) : <tr><td colSpan={5}>Run a sandbox scenario to record it here. Live data remains unchanged.</td></tr>}</tbody></table></div></section></main>;
}

type TrafficSettings = { is_enabled: boolean; interval_minutes: 1 | 5 | 15; simulation_mode: "time_patterned" | "fixed_scenario"; fixed_scenario: "normal" | "moderate" | "peak_hour" | "severe"; time_mode: "real" | "simulated"; simulated_time: string | null; current_simulation_time: string; pricing_rule_version: number; minimum_toll: number; maximum_toll_multiplier: number; minimum_price_change_minutes: number; pricing_hysteresis_percentage: number };
type PricingRule = { id: string; scenario: "normal" | "moderate" | "peak_hour" | "severe"; congestion_category: string; minimum_percentage: number; maximum_percentage: number; multiplier: number; amount?: number };
type Audit = { id: string; action: string; created_at: string; details_json: string };

function LegacyTrafficPage() {
  const [settings, setSettings] = useState<TrafficSettings | null>(null); const [rules, setRules] = useState<PricingRule[]>([]); const [audit, setAudit] = useState<Audit[]>([]); const [notice, setNotice] = useState(""); const [busy, setBusy] = useState(false);
  async function request(path: string, init?: RequestInit) { const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers: { ...apiHeaders(), "Content-Type": "application/json", ...(init?.headers ?? {}) } }); if (!response.ok) { const body = await response.json().catch(() => null) as { detail?: string } | null; throw new Error(body?.detail ?? "Traffic administration request failed."); } return response.json(); }
  async function load() { try { const [nextSettings, nextRules, nextAudit] = await Promise.all([request("/api/traffic/settings"), request("/api/traffic/pricing-rules"), request("/api/traffic/audit-logs")]); setSettings(nextSettings as TrafficSettings); setRules(nextRules as PricingRule[]); setAudit(nextAudit as Audit[]); } catch (reason) { setNotice(reason instanceof Error ? reason.message : "Traffic administration is unavailable."); } }
  useEffect(() => { void load(); }, []);
  async function saveSettings(event: FormEvent<HTMLFormElement>) { event.preventDefault(); if (!settings) return; setBusy(true); try { const saved = await request("/api/traffic/settings", { method: "PUT", body: JSON.stringify({ ...settings, simulated_time: settings.time_mode === "simulated" ? settings.simulated_time : null }) }); setSettings(saved as TrafficSettings); setNotice("Simulation settings saved."); void load(); } catch (reason) { setNotice(reason instanceof Error ? reason.message : "Settings could not be saved."); } finally { setBusy(false); } }
  async function saveRules(event: FormEvent<HTMLFormElement>) { event.preventDefault(); setBusy(true); try { const saved = await request("/api/traffic/pricing-rules", { method: "PUT", body: JSON.stringify({ rules: rules.map(({ scenario, minimum_percentage, maximum_percentage, multiplier }) => ({ scenario, minimum_percentage, maximum_percentage, multiplier })) }) }); setRules(saved as PricingRule[]); setNotice("Pricing multipliers saved and versioned."); void load(); } catch (reason) { setNotice(reason instanceof Error ? reason.message : "Pricing rules could not be saved."); } finally { setBusy(false); } }
  async function runNow() { setBusy(true); try { const result = await request("/api/traffic/simulate", { method: "POST", body: "{}" }) as { scenario: string; congestion_percentage: number; amount: number }; setNotice(`Simulated ${result.scenario.replace(/_/g, " ")} traffic at ${result.congestion_percentage}%. Current toll: RM${Number(result.amount).toFixed(2)}.`); void load(); } catch (reason) { setNotice(reason instanceof Error ? reason.message : "Simulation could not run."); } finally { setBusy(false); } }
  return <main className="dashboard-page"><section className="page-heading"><div><p className="eyebrow">SIMULATED TRAFFIC CONTROL</p><h1>Traffic & pricing administration</h1><p>All adjustments and runs are simulated and recorded in the audit history.</p></div><button onClick={() => void runNow()} disabled={busy || !settings}>Run simulation now</button></section>{notice && <p className="traffic-notice" role="status">{notice}</p>}<section className="traffic-grid"><form className="admin-card" onSubmit={saveSettings}><h2>Simulation settings</h2>{!settings ? <p>Loading settings…</p> : <><label className="toggle-row"><input type="checkbox" checked={settings.is_enabled} onChange={(e) => setSettings({ ...settings, is_enabled: e.target.checked })} /> Enable scheduled simulation</label><label>Interval<select value={settings.interval_minutes} onChange={(e) => setSettings({ ...settings, interval_minutes: Number(e.target.value) as 1 | 5 | 15 })}><option value={1}>Every 1 minute</option><option value={5}>Every 5 minutes</option><option value={15}>Every 15 minutes</option></select></label><label>Simulation mode<select value={settings.simulation_mode} onChange={(e) => setSettings({ ...settings, simulation_mode: e.target.value as TrafficSettings["simulation_mode"] })}><option value="time_patterned">Malaysia time pattern</option><option value="fixed_scenario">Fixed scenario</option></select></label>{settings.simulation_mode === "fixed_scenario" && <label>Fixed scenario<select value={settings.fixed_scenario} onChange={(e) => setSettings({ ...settings, fixed_scenario: e.target.value as TrafficSettings["fixed_scenario"] })}><option value="normal">Normal / low</option><option value="moderate">Moderate</option><option value="peak_hour">Peak hour / high</option><option value="severe">Severe</option></select></label>}<label>Clock mode<select value={settings.time_mode} onChange={(e) => setSettings({ ...settings, time_mode: e.target.value as TrafficSettings["time_mode"] })}><option value="real">Real Malaysia time</option><option value="simulated">Advancing simulated time</option></select></label>{settings.time_mode === "simulated" && <label>Simulated start time<input type="datetime-local" value={settings.simulated_time ? settings.simulated_time.slice(0, 16) : ""} onChange={(e) => setSettings({ ...settings, simulated_time: e.target.value ? `${e.target.value}:00+08:00` : null })} required /></label>}<p className="field-note">Current simulation clock: {new Date(settings.current_simulation_time).toLocaleString("en-MY", { timeZone: "Asia/Kuala_Lumpur" })}</p><button disabled={busy}>Save settings</button></>}</form><form className="admin-card" onSubmit={saveRules}><h2>Dynamic pricing bands <small>v{settings?.pricing_rule_version ?? "—"}</small></h2><div className="pricing-head"><span>Scenario</span><span>Congestion range</span><span>Price</span></div>{rules.map((rule, index) => <div className="pricing-row" key={rule.id}><strong>{rule.scenario.replace(/_/g, " ")}</strong><span><input aria-label={`${rule.scenario} minimum congestion`} type="number" min="0" max="100" step="0.01" value={rule.minimum_percentage} onChange={(e) => setRules(rules.map((item, i) => i === index ? { ...item, minimum_percentage: Number(e.target.value) } : item))} /> – <input aria-label={`${rule.scenario} maximum congestion`} type="number" min="0" max="100" step="0.01" value={rule.maximum_percentage} onChange={(e) => setRules(rules.map((item, i) => i === index ? { ...item, maximum_percentage: Number(e.target.value) } : item))} />%</span><label>RM<input aria-label={`${rule.scenario} price`} type="number" min="0" step="0.01" value={rule.amount} onChange={(e) => setRules(rules.map((item, i) => i === index ? { ...item, amount: Number(e.target.value) } : item))} /></label></div>)}<button disabled={busy || rules.length !== 4}>Save pricing rules</button></form></section><section className="admin-card audit-card"><h2>Recent configuration activity</h2><div className="audit-list">{audit.length === 0 ? <p>No activity recorded yet.</p> : audit.slice(0, 8).map((item) => <div key={item.id}><strong>{item.action.replace(/_/g, " ")}</strong><span>{new Date(item.created_at).toLocaleString("en-MY", { timeZone: "Asia/Kuala_Lumpur" })}</span></div>)}</div></section></main>;
}

function TrafficPage() {
  const { locations } = useLocations(); const [settings, setSettings] = useState<TrafficSettings | null>(null); const [rules, setRules] = useState<PricingRule[]>([]); const [audit, setAudit] = useState<Audit[]>([]); const [locationId, setLocationId] = useState(""); const [congestion, setCongestion] = useState(55); const [preview, setPreview] = useState<{ congestion_category: string; base_toll: number; multiplier: number; previous_toll: number | null; new_toll: number; reason: string } | null>(null); const [notice, setNotice] = useState("");
  async function request(path: string, init?: RequestInit) { const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers: { ...apiHeaders(), "Content-Type": "application/json", ...(init?.headers ?? {}) } }); if (!response.ok) throw new Error((await response.json().catch(() => null) as { detail?: string } | null)?.detail ?? "Pricing request failed."); return response.json(); }
  async function load() { try { const [nextSettings, nextRules, nextAudit] = await Promise.all([request("/api/traffic/settings"), request("/api/traffic/pricing-rules"), request("/api/traffic/audit-logs")]); setSettings(nextSettings as TrafficSettings); setRules(nextRules as PricingRule[]); setAudit(nextAudit as Audit[]); } catch (error) { setNotice(error instanceof Error ? error.message : "Pricing administration is unavailable."); } }
  useEffect(() => { void load(); }, []); useEffect(() => { if (!locationId && locations[0]) setLocationId(locations[0].id); }, [locations, locationId]);
  async function saveSettings(event: FormEvent) { event.preventDefault(); if (!settings) return; await request("/api/traffic/settings", { method: "PUT", body: JSON.stringify(settings) }); setNotice("Pricing safeguards saved."); void load(); }
  async function saveRules(event: FormEvent) { event.preventDefault(); await request("/api/traffic/pricing-rules", { method: "PUT", body: JSON.stringify({ rules: rules.map(({ scenario, minimum_percentage, maximum_percentage, multiplier }) => ({ scenario, minimum_percentage, maximum_percentage, multiplier })) }) }); setNotice("Pricing multipliers saved and versioned."); void load(); }
  async function showPreview() { if (!locationId) return; try { setPreview(await request(`/api/traffic/pricing-preview?location_id=${encodeURIComponent(locationId)}&congestion_percentage=${congestion}`)); } catch (error) { setNotice(error instanceof Error ? error.message : "Preview is unavailable."); } }
  return <main className="dashboard-page"><section className="page-heading"><div><p className="eyebrow">RULE-BASED PRICING</p><h1>Dynamic toll pricing</h1><p>Location base toll × congestion multiplier, with explicit stability safeguards.</p></div></section>{notice && <p className="traffic-notice">{notice}</p>}<section className="traffic-grid"><form className="admin-card" onSubmit={saveSettings}><h2>Pricing safeguards</h2>{settings && <><label>Minimum toll (RM)<input type="number" min="0" step=".01" value={settings.minimum_toll} onChange={e => setSettings({ ...settings, minimum_toll: Number(e.target.value) })} /></label><label>Maximum base-toll multiplier<input type="number" min="1" step=".01" value={settings.maximum_toll_multiplier} onChange={e => setSettings({ ...settings, maximum_toll_multiplier: Number(e.target.value) })} /></label><label>Minimum change interval (minutes)<input type="number" min="0" value={settings.minimum_price_change_minutes} onChange={e => setSettings({ ...settings, minimum_price_change_minutes: Number(e.target.value) })} /></label><label>Hysteresis around boundary (%)<input type="number" min="0" step=".01" value={settings.pricing_hysteresis_percentage} onChange={e => setSettings({ ...settings, pricing_hysteresis_percentage: Number(e.target.value) })} /></label><button>Save safeguards</button></>}</form><form className="admin-card" onSubmit={saveRules}><h2>Four congestion multipliers</h2>{rules.map((rule, index) => <label key={rule.id}>{rule.scenario.replace(/_/g, " ")} · {rule.minimum_percentage}–{rule.maximum_percentage}%<input aria-label={`${rule.scenario} multiplier`} type="number" min=".01" step=".01" value={rule.multiplier} onChange={e => setRules(rules.map((item, i) => i === index ? { ...item, multiplier: Number(e.target.value) } : item))} /></label>)}<button>Save multipliers</button></form></section><section className="detail-card"><div className="section-title"><div><p className="eyebrow">RULE PREVIEW</p><h2>Explain a proposed price</h2></div></div><div className="pricing-preview"><LocationSelect all={false} label="Toll location" value={locationId} onChange={setLocationId} /><label>Congestion %<input type="number" min="0" max="100" step=".01" value={congestion} onChange={e => setCongestion(Number(e.target.value))} /></label><button onClick={() => void showPreview()}>Preview price</button></div>{preview && <dl className="evidence-grid"><div><dt>Decision</dt><dd>{categoryLabel(preview.congestion_category)} at {congestion.toFixed(1)}%</dd></div><div><dt>Base × multiplier</dt><dd>RM{Number(preview.base_toll).toFixed(2)} × {Number(preview.multiplier).toFixed(2)}</dd></div><div><dt>Previous toll</dt><dd>{preview.previous_toll == null ? "No previous toll" : `RM${Number(preview.previous_toll).toFixed(2)}`}</dd></div><div><dt>New toll</dt><dd>RM{Number(preview.new_toll).toFixed(2)} · {preview.reason}</dd></div></dl>}</section><section className="admin-card audit-card"><h2>Pricing audit history</h2><div className="audit-list">{audit.filter(item => item.action.includes("pricing")).map(item => <div key={item.id}><strong>{item.action.replace(/_/g, " ")}</strong><span>{new Date(item.created_at).toLocaleString("en-MY", { timeZone: "Asia/Kuala_Lumpur" })}</span></div>)}</div></section></main>;
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
      const sessionResponse = await fetch(`${API_BASE_URL}/api/webcam/sessions`, { method: "POST", headers: apiHeaders() });
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
    if (sessionId) await fetch(`${API_BASE_URL}/api/webcam/sessions/${sessionId}`, { method: "DELETE", headers: apiHeaders() }).catch(() => undefined);
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
      const response = await fetch(`${API_BASE_URL}/api/webcam/sessions/${sessionId}/frames`, { method: "POST", headers: { ...apiHeaders(), "Idempotency-Key": crypto.randomUUID() }, body: form });
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
    <section className="result" aria-label="Recognition result"><h2>Latest recognition</h2><p><strong>{result?.plate_text ?? "—"}</strong></p><p>{result?.message ?? "No frame has been processed."}</p>{result && <dl><div><dt>Detection</dt><dd>{result.detection_confidence ? `${(result.detection_confidence * 100).toFixed(1)}%` : "—"}</dd></div><div><dt>OCR</dt><dd>{result.ocr_confidence ? `${(result.ocr_confidence * 100).toFixed(1)}%` : "—"}</dd></div><div><dt>Simulated payment</dt><dd>{result.payment_status ?? "Not processed"}</dd></div>{typeof result.payment_amount === "number" && <div><dt>Toll amount</dt><dd>RM{result.payment_amount.toFixed(2)}</dd></div>}{typeof result.payment_balance_after === "number" && <div><dt>Balance after</dt><dd>RM{result.payment_balance_after.toFixed(2)}</dd></div>}</dl>}</section>
  </main>;
}

export { App, ruleMultiplier };
