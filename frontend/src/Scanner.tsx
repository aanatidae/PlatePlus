import { Activity } from "lucide-react";
import { CameraCapture } from "./CameraCapture";

export default function Scanner() {
  return <main className="scanner-shell"><section className="scanner-card"><div className="brand"><Activity size={21} /><span>PlatePlus</span></div><h1>Simulator Toll Plaza</h1><p>Local phone scanner. Sampled frames travel only to this laptop’s FastAPI ALPR service and are not stored.</p><CameraCapture source="phone" /><p className="scanner-note">Keep this page open while scanning. A successful accepted read creates the same simulated crossing, payment, and 60-second congestion effect as the laptop camera.</p></section></main>;
}
