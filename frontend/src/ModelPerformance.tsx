import { useEffect, useRef, useState } from "react";
import { X } from "lucide-react";
import { getJson } from "./locations";

type Evidence = {
  evaluation: { detector: { accuracy_percent: number; note: string }; ocr: { exact_matches: number; held_out_samples: number; exact_match_accuracy_percent: number; note: string }; development?: { exact_matches: number; scorable_samples: number; exact_match_accuracy_percent: number; positive_detector_images: number; positive_detector_false_negatives: number; condition_observations: { label: string; result: string }[] } };
  known_failure_conditions: string[];
};

export function ModelPerformance() {
  const [open, setOpen] = useState(false); const [evidence, setEvidence] = useState<Evidence | null>(null); const [error, setError] = useState("");
  const triggerRef = useRef<HTMLButtonElement>(null);
  const modalRef = useRef<HTMLElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const close = () => { setOpen(false); window.setTimeout(() => triggerRef.current?.focus(), 0); };
  useEffect(() => { if (!open || evidence || error) return; void getJson<Evidence>("/api/intelligence/summary").then(setEvidence).catch(reason => setError(reason instanceof Error ? reason.message : "Model evidence is unavailable.")); }, [open, evidence, error]);
  useEffect(() => {
    if (!open) return;
    closeRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") { event.preventDefault(); close(); return; }
      if (event.key !== "Tab") return;
      const focusable = modalRef.current?.querySelectorAll<HTMLElement>('button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])');
      if (!focusable?.length) return;
      const first = focusable[0]; const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open]);
  return <><button ref={triggerRef} className="model-performance-button secondary-button" onClick={() => setOpen(true)}>Model performance</button>{open && <div className="performance-backdrop" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) close(); }}><section ref={modalRef} className="performance-modal" role="dialog" aria-modal="true" aria-labelledby="model-performance-title"><header className="performance-modal-header"><div><p>Evidence for presentation Q&amp;A</p><h2 id="model-performance-title">Model performance</h2></div><button ref={closeRef} className="performance-close" type="button" aria-label="Close model performance" onClick={close}><X size={20} aria-hidden="true" /></button></header>{error && <p className="form-error" role="alert">{error}</p>}{!evidence && !error && <p role="status">Loading verified evaluation evidence…</p>}{evidence && <div className="performance-content"><section><h3>Plate detection</h3><strong>{evidence.evaluation.detector.accuracy_percent}%</strong><p>Reported held-out detector accuracy. Precision, recall, and F1 were not exported and are not estimated.</p></section><section><h3>OCR</h3><strong>{evidence.evaluation.ocr.exact_matches}/{evidence.evaluation.ocr.held_out_samples} · {evidence.evaluation.ocr.exact_match_accuracy_percent}%</strong><p>Held-out PaddleOCR exact-match accuracy. The protected 44-crop set was preserved and not used for tuning.</p></section>{evidence.evaluation.development && <section><h3>Development review</h3><strong>{evidence.evaluation.development.exact_matches}/{evidence.evaluation.development.scorable_samples} · {evidence.evaluation.development.exact_match_accuracy_percent}%</strong><p>Development-only OCR result; {evidence.evaluation.development.positive_detector_false_negatives} false negatives across {evidence.evaluation.development.positive_detector_images} reviewed plate-present images.</p><ul>{evidence.evaluation.development.condition_observations.map(item => <li key={item.label}><b>{item.label}:</b> {item.result}</li>)}</ul></section>}<section><h3>Known limitations</h3><ul>{evidence.known_failure_conditions.map(item => <li key={item}>{item}</li>)}</ul></section></div>}</section></div>}</>;
}
