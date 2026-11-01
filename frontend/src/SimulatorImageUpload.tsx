import { useEffect, useRef, useState } from "react";
import { X } from "lucide-react";
import { apiHeaders } from "./App";
import type { CameraResult } from "./CameraCapture";
import { AlprResultDetails } from "./AlprResultDetails";
import { completeUploadRequest, uploadRequestKey, UPLOAD_REQUEST_TIMEOUT_MS, type UploadRequestKey } from "./uploadRequest";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
const MAX_BYTES = 5_000_000;
const TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);
const EXTENSIONS = /\.(jpe?g|png|webp)$/i;

export function SimulatorImageUpload({ locationId }: { locationId: string }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const request = useRef<AbortController | null>(null);
  const eventKey = useRef<{ file: File; locationId: string; value: UploadRequestKey } | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [processing, setProcessing] = useState(false);
  const [result, setResult] = useState<CameraResult | null>(null);
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);
  useEffect(() => () => { const active = request.current; request.current = null; active?.abort(); }, [locationId]);
  const clear = () => { const active = request.current; request.current = null; active?.abort(); eventKey.current = null; setProcessing(false); if (preview) URL.revokeObjectURL(preview); setPreview(null); setFile(null); setMessage(""); setResult(null); if (inputRef.current) inputRef.current.value = ""; };
  const choose = (next: File | undefined) => {
    clear();
    if (!next) return;
    if (!TYPES.has(next.type) || !EXTENSIONS.test(next.name)) { setMessage("Choose a JPG, JPEG, PNG, or WebP image."); return; }
    if (next.size > MAX_BYTES) { setMessage("Image must be 5 MB or smaller."); return; }
    setFile(next); setPreview(URL.createObjectURL(next)); setMessage("Ready to detect the plate.");
  };
  const submit = async () => {
    if (!file || processing || request.current) return;
    const controller = new AbortController();
    request.current = controller;
    let timedOut = false;
    const deadline = window.setTimeout(() => { timedOut = true; controller.abort(); }, UPLOAD_REQUEST_TIMEOUT_MS);
    const warmingUp = window.setTimeout(() => { if (request.current === controller) setMessage("Still processing. The first scan can take longer while the local models warm up."); }, 15_000);
    setProcessing(true); setResult(null); setMessage("Uploading… Detecting plate…");
    try {
      if (eventKey.current?.file !== file || eventKey.current.locationId !== locationId) {
        const value = await uploadRequestKey(file, locationId);
        if (controller.signal.aborted || request.current !== controller) return;
        eventKey.current = { file, locationId, value };
      }
      if (controller.signal.aborted || request.current !== controller) return;
      const key = eventKey.current.value;
      const form = new FormData(); form.append("image", file, file.name);
      const response = await fetch(`${API_BASE}/api/webcam/images?location_id=${encodeURIComponent(locationId)}`, { method: "POST", headers: { ...apiHeaders(), "Idempotency-Key": key.key }, body: form, signal: controller.signal });
      const body = await response.json() as CameraResult | { detail?: string };
      if (controller.signal.aborted || request.current !== controller) return;
      if (!response.ok) throw new Error("detail" in body ? body.detail : "Image processing could not be completed.");
      completeUploadRequest(key);
      eventKey.current = null;
      const result = body as CameraResult;
      setResult(result);
      if (result.status === "accepted_for_vehicle_lookup" && !result.payment_duplicate) {
        setMessage(`Plate accepted: ${result.plate_text ?? "recognized plate"}`);
        dispatchEvent(new CustomEvent("simulator-crossing-accepted", { detail: result }));
      } else setMessage(result.message || result.status.replace(/_/g, " "));
      dispatchEvent(new Event("dashboard-refresh"));
    } catch (error) {
      if (request.current === controller) setMessage(timedOut ? "The upload took too long. Retry the same image to safely check its result." : error instanceof Error ? error.message : "Image processing could not be completed.");
    } finally {
      window.clearTimeout(deadline); window.clearTimeout(warmingUp);
      if (request.current === controller) { request.current = null; setProcessing(false); }
    }
  };
  return <div className="simulator-upload"><p className="field-note">Local ALPR first. If optional Gemini fallback is enabled, unresolved uploads may be sent to Gemini. PlatePlus does not save images.</p><div className="simulator-alpr-actions"><button type="button" className="secondary-button" onClick={() => inputRef.current?.click()} disabled={processing}>Upload Plate Image</button>{file && <button type="button" onClick={() => void submit()} disabled={processing}>{processing ? "Processing…" : "Process image"}</button>}</div><input ref={inputRef} type="file" accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp" hidden onChange={event => choose(event.target.files?.[0])} />{(preview || message) && <div className="upload-preview" aria-live="polite">{preview && <img src={preview} alt="Selected plate image preview" />}<div><strong>{file?.name ?? "Upload plate image"}</strong><span>{message}</span></div><button type="button" className="camera-icon" aria-label="Clear selected plate image" onClick={clear}><X size={16} /></button></div>}{result && <div className="upload-result" aria-live="polite"><strong>{result.plate_text ?? "Unread plate"}</strong><AlprResultDetails result={result} /></div>}</div>;
}
