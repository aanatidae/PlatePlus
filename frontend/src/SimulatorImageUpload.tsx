import { useEffect, useRef, useState } from "react";
import { X } from "lucide-react";
import { apiHeaders } from "./App";
import type { CameraResult } from "./CameraCapture";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
const MAX_BYTES = 5_000_000;
const TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);
const EXTENSIONS = /\.(jpe?g|png|webp)$/i;

export function SimulatorImageUpload({ locationId }: { locationId: string }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [processing, setProcessing] = useState(false);
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);
  const clear = () => { if (preview) URL.revokeObjectURL(preview); setPreview(null); setFile(null); setMessage(""); if (inputRef.current) inputRef.current.value = ""; };
  const choose = (next: File | undefined) => {
    clear();
    if (!next) return;
    if (!TYPES.has(next.type) || !EXTENSIONS.test(next.name)) { setMessage("Choose a JPG, JPEG, PNG, or WebP image."); return; }
    if (next.size > MAX_BYTES) { setMessage("Image must be 5 MB or smaller."); return; }
    setFile(next); setPreview(URL.createObjectURL(next)); setMessage("Ready to detect the plate.");
  };
  const submit = async () => {
    if (!file || processing) return;
    setProcessing(true); setMessage("Uploading… Detecting plate…");
    try {
      const form = new FormData(); form.append("image", file, file.name);
      const response = await fetch(`${API_BASE}/api/webcam/images?location_id=${encodeURIComponent(locationId)}`, { method: "POST", headers: { ...apiHeaders(), "Idempotency-Key": crypto.randomUUID() }, body: form });
      const body = await response.json() as CameraResult | { detail?: string };
      if (!response.ok) throw new Error("detail" in body ? body.detail : "Image processing could not be completed.");
      const result = body as CameraResult;
      if (result.status === "accepted_for_vehicle_lookup" && !result.payment_duplicate) {
        setMessage(`Plate accepted: ${result.plate_text ?? "recognized plate"}`);
        dispatchEvent(new CustomEvent("simulator-crossing-accepted", { detail: result }));
      } else setMessage(result.message || result.status.replace(/_/g, " "));
      dispatchEvent(new Event("dashboard-refresh"));
    } catch (error) { setMessage(error instanceof Error ? error.message : "Image processing could not be completed."); }
    finally { setProcessing(false); }
  };
  return <div className="simulator-upload"><div className="simulator-alpr-actions"><button type="button" className="secondary-button" onClick={() => inputRef.current?.click()} disabled={processing}>Upload Plate Image</button>{file && <button type="button" onClick={() => void submit()} disabled={processing}>{processing ? "Processing…" : "Process image"}</button>}</div><input ref={inputRef} type="file" accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp" hidden onChange={event => choose(event.target.files?.[0])} />{(preview || message) && <div className="upload-preview" aria-live="polite">{preview && <img src={preview} alt="Selected plate image preview" />}<div><strong>{file?.name ?? "Upload plate image"}</strong><span>{message}</span></div><button type="button" className="camera-icon" aria-label="Clear selected plate image" onClick={clear}><X size={16} /></button></div>}</div>;
}
