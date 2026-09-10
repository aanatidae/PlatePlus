import { FormEvent, useEffect, useState } from "react";
import { Activity, CircleDollarSign, Gauge, LineChart, MapPin, Menu, RefreshCw, X } from "lucide-react";
import NetworkOverview from "./NetworkOverview";
import PricingManagement from "./PricingManagement";
import Prediction from "./Prediction";
import { ModelPerformance } from "./ModelPerformance";
import { LocationProvider, LocationSelect, useLocations } from "./locations";

type Admin = { id: string; email: string; display_name: string };
type LoginResponse = { access_token: string; token_type: string; expires_at: string; admin: Admin };
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
const AUTH_STORAGE_KEY = "capstone-alpr.admin-session";
const DASHBOARD_ROUTES = ["/dashboard", "/pricing", "/prediction"];

function readStoredSession(): LoginResponse | null { try { const value = sessionStorage.getItem(AUTH_STORAGE_KEY); return value ? JSON.parse(value) as LoginResponse : null; } catch { return null; } }
export function navigate(path: string, replace = false) { history[replace ? "replaceState" : "pushState"]({}, "", path); dispatchEvent(new PopStateEvent("popstate")); }

function Login({ onLogin, returnTo = "/dashboard" }: { onLogin: (session: LoginResponse) => void; returnTo?: string }) {
  const [email, setEmail] = useState(""); const [password, setPassword] = useState(""); const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent) { event.preventDefault(); setBusy(true); setError(""); try { const response = await fetch(`${API_BASE_URL}/api/auth/login`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, password }) }); if (!response.ok) throw new Error("Email or password is incorrect."); onLogin(await response.json() as LoginResponse); navigate(returnTo, true); } catch (reason) { setError(reason instanceof Error ? reason.message : "Sign-in could not be completed."); } finally { setBusy(false); } }
  return <main className="auth-shell"><section className="login-card"><div className="brand"><Activity size={22} /><span>PlatePlus</span></div><h1>Administrator sign in</h1><p>Local capstone demonstration access.</p><form onSubmit={submit}><label>Email<input type="email" value={email} onChange={event => setEmail(event.target.value)} required /></label><label>Password<input type="password" value={password} onChange={event => setPassword(event.target.value)} required /></label>{error && <p className="form-error" role="alert">{error}</p>}<button disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button></form></section></main>;
}

function Shell({ admin, route, onLogout }: { admin: Admin; route: string; onLogout: () => void }) {
  const [menuOpen, setMenuOpen] = useState(false); const { selected, select, locations, ready, error } = useLocations(); const active = locations.find(location => location.id === selected);
  const page = route === "/pricing" ? <PricingManagement /> : route === "/prediction" ? <Prediction /> : <NetworkOverview />;
  return <div className="command-shell"><aside className={menuOpen ? "command-sidebar open" : "command-sidebar"}><a className="brand" href="/dashboard" onClick={event => { event.preventDefault(); navigate("/dashboard"); }}><Activity size={20} /><span>PlatePlus</span></a><p className="sidebar-label">Operations</p><nav aria-label="Administrator navigation" onClick={() => setMenuOpen(false)}><Nav to="/dashboard" active={route === "/dashboard"} icon={<Gauge size={17} />}>Overview</Nav><Nav to="/pricing" active={route === "/pricing"} icon={<CircleDollarSign size={17} />}>Dynamic Pricing Management</Nav><Nav to="/prediction" active={route === "/prediction"} icon={<LineChart size={17} />}>Prediction</Nav></nav><div className="sidebar-foot"><span className="live-dot" /> Simulated Prototype</div></aside><section className="command-stage"><header className="top-control-bar"><button className="menu-toggle" aria-label="Toggle navigation" onClick={() => setMenuOpen(!menuOpen)}>{menuOpen ? <X size={19} /> : <Menu size={19} />}</button><div className="location-control"><MapPin size={15} /><LocationSelect value={selected} onChange={select} /><small>{active?.highway_or_route ?? "Simulated toll network"}</small></div><div className="top-spacer" /><ModelPerformance /><button className="sync-control" aria-label="Sync data" onClick={() => dispatchEvent(new Event("dashboard-refresh"))}><RefreshCw size={15} /> Sync</button><span className="system-health">Local demo</span><div className="admin-menu"><span>{admin.display_name}</span><button className="secondary-button" onClick={onLogout}>Sign out</button></div></header>{error && <p className="form-error" role="alert">{error}</p>}{ready ? page : <main className="dashboard-page"><p className="empty-admin">Loading PlatePlus toll locations…</p></main>}</section></div>;
}

function Nav({ to, active, icon, children }: { to: string; active: boolean; icon: React.ReactNode; children: React.ReactNode }) { return <a className={active ? "nav-link active" : "nav-link"} href={to} onClick={event => { event.preventDefault(); navigate(to); }}>{icon}{children}</a>; }
export function apiHeaders() { return { Authorization: `Bearer ${readStoredSession()?.access_token ?? ""}` }; }
export function ruleMultiplier(amount: number, normalAmount: number) { return normalAmount > 0 ? Number((amount / normalAmount).toFixed(2)) : 1; }

export function App() {
  const [session, setSession] = useState<LoginResponse | null>(readStoredSession); const [route, setRoute] = useState(location.pathname);
  useEffect(() => { const onPop = () => setRoute(location.pathname); addEventListener("popstate", onPop); return () => removeEventListener("popstate", onPop); }, []);
  useEffect(() => { if (!session) { if (route !== "/login") navigate("/login", true); return; } if (!DASHBOARD_ROUTES.includes(route)) navigate("/dashboard", true); }, [route, session]);
  if (!session) return <Login onLogin={next => { sessionStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(next)); setSession(next); }} />;
  return <LocationProvider><Shell admin={session.admin} route={route} onLogout={() => { sessionStorage.removeItem(AUTH_STORAGE_KEY); setSession(null); navigate("/login", true); }} /></LocationProvider>;
}
