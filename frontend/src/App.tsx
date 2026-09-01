import { useEffect, useRef, useState } from "react";

type BoundingBox = { left: number; top: number; right: number; bottom: number };
type FrameResult = {
  status: string;
  message: string;
  plate_text?: string;
  detection_confidence?: number;
  ocr_confidence?: number;
  bounding_box?: BoundingBox;
  charge_eligible: boolean;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export function App() {
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
    setState("starting");
    setMessage("Requesting local camera permission…");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment", width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });
      const sessionResponse = await fetch(`${API_BASE_URL}/api/webcam/sessions`, { method: "POST" });
      if (!sessionResponse.ok) throw new Error("The local ALPR service could not start a webcam session.");
      const session = (await sessionResponse.json()) as { session_id: string; frame_interval_ms: number };
      streamRef.current = stream;
      sessionRef.current = session.session_id;
      if (!videoRef.current) throw new Error("Camera preview is unavailable.");
      videoRef.current.srcObject = stream;
      await videoRef.current.play();
      intervalRef.current = window.setInterval(() => void sendFrame(), session.frame_interval_ms);
      setState("running");
      setMessage("Camera is running locally. Toll and traffic results are simulated.");
    } catch (error) {
      await stopCamera();
      setState("error");
      setMessage(error instanceof Error ? error.message : "Camera access could not be started.");
    }
  }

  async function stopCamera() {
    if (intervalRef.current !== null) window.clearInterval(intervalRef.current);
    intervalRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    const sessionId = sessionRef.current;
    sessionRef.current = null;
    if (sessionId) await fetch(`${API_BASE_URL}/api/webcam/sessions/${sessionId}`, { method: "DELETE" }).catch(() => undefined);
    inFlightRef.current = false;
    if (state !== "error") {
      setState("idle");
      setMessage("Camera is off. Frames stay on this laptop.");
    }
  }

  async function sendFrame() {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    const sessionId = sessionRef.current;
    if (!video || !canvas || !sessionId || inFlightRef.current || video.videoWidth === 0) return;
    inFlightRef.current = true;
    try {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      canvas.getContext("2d")?.drawImage(video, 0, 0);
      const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.82));
      if (!blob) throw new Error("A webcam frame could not be captured.");
      const form = new FormData();
      form.append("frame", blob, "webcam-frame.jpg");
      const response = await fetch(`${API_BASE_URL}/api/webcam/sessions/${sessionId}/frames`, { method: "POST", body: form });
      if (!response.ok) throw new Error((await response.json()).detail ?? "Frame processing failed.");
      setResult((await response.json()) as FrameResult);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Frame processing failed.");
    } finally {
      inFlightRef.current = false;
    }
  }

  const box = result?.bounding_box;
  const label = result?.plate_text ? `${result.plate_text} · ${result.status}` : result?.status;
  return (
    <main>
      <header><p className="eyebrow">SIMULATED TOLL PROTOTYPE</p><h1>Local Webcam ALPR</h1><p>{message}</p></header>
      <section className="camera-panel" aria-live="polite">
        <div className="preview">
          <video ref={videoRef} muted playsInline aria-label="Local webcam preview" />
          {box && <div className="box" style={{ left: `${(box.left / (videoRef.current?.videoWidth || 1)) * 100}%`, top: `${(box.top / (videoRef.current?.videoHeight || 1)) * 100}%`, width: `${((box.right - box.left) / (videoRef.current?.videoWidth || 1)) * 100}%`, height: `${((box.bottom - box.top) / (videoRef.current?.videoHeight || 1)) * 100}%` }}><span>{label}</span></div>}
        </div>
        <button onClick={() => void (state === "running" ? stopCamera() : startCamera())} disabled={state === "starting"}>{state === "running" ? "Stop camera" : "Start camera"}</button>
        <canvas ref={canvasRef} hidden />
      </section>
      <section className="result" aria-label="Recognition result">
        <h2>Latest recognition</h2>
        <p><strong>{result?.plate_text ?? "—"}</strong></p>
        <p>{result?.message ?? "No frame has been processed."}</p>
        {result && <dl><div><dt>Detection</dt><dd>{result.detection_confidence ? `${(result.detection_confidence * 100).toFixed(1)}%` : "—"}</dd></div><div><dt>OCR</dt><dd>{result.ocr_confidence ? `${(result.ocr_confidence * 100).toFixed(1)}%` : "—"}</dd></div><div><dt>Charge status</dt><dd>{result.charge_eligible ? "Eligible for simulated lookup" : "Not eligible"}</dd></div></dl>}
      </section>
    </main>
  );
}
