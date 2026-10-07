import { useEffect, useState, type FormEvent } from "react";
import { apiHeaders } from "./App";
import { requireOk } from "./apiErrors";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
const PATH = `${API_BASE}/api/data/foreign-vehicle-charge`;
function readAmount(body: { amount?: unknown }) {
  const value = Number(body.amount);
  if (body.amount == null || !Number.isFinite(value) || value < 0) throw new Error("The stored simulated foreign charge is unavailable.");
  return value.toFixed(2);
}

function ChargeForm() {
  const [amount, setAmount] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    void (async () => {
      try {
        const response = await fetch(PATH, { headers: apiHeaders(), signal: controller.signal });
        await requireOk(response, "Simulated foreign charge is unavailable.");
        const value = readAmount(await response.json());
        if (!controller.signal.aborted) setAmount(value);
      } catch (reason) {
        if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : "Simulated foreign charge is unavailable.");
      }
    })();
    return () => controller.abort();
  }, []);
  async function save(event: FormEvent) {
    event.preventDefault();
    setError(""); setNotice("");
    if (amount == null || !/^\d+(\.\d{1,2})?$/.test(amount) || Number(amount) > 999999.99) {
      setError("Enter a simulated amount from RM0.00 to RM999,999.99 with at most two decimal places."); return;
    }
    setSaving(true);
    try {
      const response = await fetch(PATH, { method: "PUT", headers: { ...apiHeaders(), "Content-Type": "application/json" }, body: JSON.stringify({ amount }) });
      await requireOk(response, "Unable to save the simulated foreign charge.");
      setAmount(readAmount(await response.json()));
      setNotice("Simulated foreign charge saved and audit logged. Existing transactions and congestion rules are unchanged.");
      window.dispatchEvent(new Event("dashboard-refresh"));
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to save the simulated foreign charge."); }
    finally { setSaving(false); }
  }
  return <form className="admin-card" onSubmit={event => void save(event)}>
    {error && <p className="form-error" role="alert">{error}</p>}
    {notice && <p className="traffic-notice" role="status">{notice}</p>}
    {amount == null ? !error && <p role="status">Loading the stored simulated charge…</p> : <>
      <label>Simulated foreign-vehicle charge (RM)<input type="number" min="0" max="999999.99" step="0.01" required value={amount} disabled={saving} onChange={event => { setAmount(event.target.value); setNotice(""); }} /></label>
      <button disabled={saving}>{saving ? "Saving…" : "Save simulated foreign charge"}</button>
    </>}
  </form>;
}

export function ForeignChargeSettings() {
  const [open, setOpen] = useState(false);
  return <details className="detail-card foreign-charge-settings" onToggle={event => setOpen(event.currentTarget.open)}>
    <summary>Simulated foreign-vehicle charge</summary>
    <p className="field-note">Separate from congestion pricing. Eligible Singaporean transactions add this configured amount after the dynamic toll; Malaysian transactions add zero. It does not change congestion bands, multipliers, or traffic prediction. This is prototype configuration, not a real toll-plaza fee.</p>
    {open && <ChargeForm />}
  </details>;
}
