import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
export const LOCATION_KEY = "plateplus.location.v1";
export type TollLocation = { id: string; code: string; display_name: string; highway_or_route: string; latitude: number; longitude: number; status: string; base_toll: number; road_capacity: number };
export function locationPath(path: string, locationId: string) {
  return `${path}${path.includes("?") ? "&" : "?"}${locationId === "all" ? "scope=all_locations" : `location_id=${encodeURIComponent(locationId)}`}`;
}
export function storedLocation(storage?: Pick<Storage, "getItem">) {
  try { return (storage ?? window.localStorage).getItem(LOCATION_KEY) || "all"; } catch { return "all"; }
}
export function headers() {
  try { return { Authorization: `Bearer ${JSON.parse(sessionStorage.getItem("capstone-alpr.admin-session") || "null")?.access_token ?? ""}` }; }
  catch { return { Authorization: "Bearer " }; }
}
export async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { headers: headers(), signal });
  if (!response.ok) throw new Error(`PlatePlus data is unavailable (${response.status}). Use Sync data to retry.`);
  return response.json() as Promise<T>;
}

/** Abort old scopes and serialize refreshes so late responses cannot replace current data. */
export function useFeed<T>(path: string, enabled = true) {
  const [state, setState] = useState<{ path: string; data: T | null; error: string; receivedAt: number }>({ path, data: null, error: "", receivedAt: 0 });
  useEffect(() => {
    if (!enabled) return;
    let disposed = false;
    let controller: AbortController | undefined;
    const load = async () => {
      controller?.abort();
      const request = new AbortController();
      controller = request;
      const timeout = window.setTimeout(() => {
        if (disposed || request.signal.aborted) return;
        request.abort();
        setState(previous => ({ path, data: previous.path === path ? previous.data : null,
          receivedAt: previous.path === path ? previous.receivedAt : 0,
          error: "PlatePlus is taking too long to respond. Use Sync data to retry." }));
      }, 15_000);
      try {
        const data = await getJson<T>(path, request.signal);
        if (!disposed && !request.signal.aborted) setState({ path, data, error: "", receivedAt: Date.now() });
      } catch (reason) {
        if (!disposed && !request.signal.aborted) setState(previous => ({
          path, data: previous.path === path ? previous.data : null,
          receivedAt: previous.path === path ? previous.receivedAt : 0,
          error: reason instanceof TypeError ? "PlatePlus cannot reach the API. Use Sync data to retry." : reason instanceof Error ? reason.message : "PlatePlus data is unavailable.",
        }));
      } finally { window.clearTimeout(timeout); }
    };
    void load();
    const timer = window.setInterval(() => void load(), 30_000);
    const refresh = () => void load();
    window.addEventListener("dashboard-refresh", refresh);
    return () => { disposed = true; controller?.abort(); window.clearInterval(timer); window.removeEventListener("dashboard-refresh", refresh); };
  }, [path, enabled]);
  return state.path === path ? state : { path, data: null, error: "", receivedAt: 0 };
}

type Context = { locations: TollLocation[]; selected: string; select: (id: string) => void; error: string; ready: boolean };
const LocationContext = createContext<Context | null>(null);
export function LocationProvider({ children }: { children: ReactNode }) {
  const [selected, setSelected] = useState(storedLocation);
  const { data, error } = useFeed<TollLocation[]>("/api/locations");
  const effective = data && selected !== "all" && !data.some(location => location.id === selected) ? "all" : selected;
  useEffect(() => { try { localStorage.setItem(LOCATION_KEY, effective); } catch { /* Selection remains available in memory. */ } }, [effective]);
  return <LocationContext.Provider value={{ locations: data ?? [], selected: effective, select: setSelected, error, ready: data !== null }}>{children}</LocationContext.Provider>;
}
export function useLocations() {
  const value = useContext(LocationContext);
  if (!value) throw new Error("LocationProvider is required.");
  return value;
}
export function LocationSelect({ value, onChange, all = true, label = "Toll location" }: { value: string; onChange: (id: string) => void; all?: boolean; label?: string }) {
  const { locations, ready } = useLocations();
  return <label className="location-select">{label}<select aria-label={label} value={value} onChange={event => onChange(event.target.value)} disabled={!ready}>
    {all && <option value="all">All Locations</option>}
    {!all && !value && <option value="">Select a toll location</option>}
    {locations.map(location => <option key={location.id} value={location.id}>{location.display_name}</option>)}
  </select></label>;
}
