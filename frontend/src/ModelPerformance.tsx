import { useEffect, useRef, useState } from "react";
import { X } from "lucide-react";
import { createPortal } from "react-dom";
import { getJson } from "./locations";

type Evidence = {
  thresholds?: { detection: number; ocr: number };
  evaluation: { detector: { accuracy_percent: number; note: string }; ocr: { exact_matches: number; held_out_samples: number; exact_match_accuracy_percent: number; note: string }; singaporean_detector?: SingaporeanDetectorData | null; origin?: OriginEvidenceData; development?: { exact_matches: number; scorable_samples: number; exact_match_accuracy_percent: number; positive_detector_images: number; positive_detector_false_negatives: number; condition_observations: { label: string; result: string }[] } };
  known_failure_conditions: string[];
};

export type OriginEvidenceData = { samples: number; exact_matches: number; exact_match_percent: number; cross_country_errors: number; ambiguous_rejected: number; unsupported_rejected: number; note: string };
export type SingaporeanDetectorData = { verified: boolean; split: string; images: number; labelled_plates: number; standard_metrics: { recall: number; precision: number; map50: number; map50_95: number }; operational_metrics: { true_positive_plates: number; recall: number }; parameters: { operational_confidence: number }; };
export function SingaporeanDetectorEvidence({ evidence }: { evidence: SingaporeanDetectorData }) {
  if (!evidence.verified) return null;
  const percent = (value: number) => `${(value * 100).toFixed(1)}%`;
  return <section><h3>Singaporean detector transfer evaluation</h3><strong>{percent(evidence.operational_metrics.recall)} recall at runtime gate</strong><p>{evidence.operational_metrics.true_positive_plates} / {evidence.labelled_plates} labelled plates matched at IoU ≥ 0.50 and confidence ≥ {percent(evidence.parameters.operational_confidence)}.</p><dl className="evidence-grid"><div><dt>Precision · best F1</dt><dd>{percent(evidence.standard_metrics.precision)}</dd></div><div><dt>Recall · best F1</dt><dd>{percent(evidence.standard_metrics.recall)}</dd></div><div><dt>mAP50</dt><dd>{percent(evidence.standard_metrics.map50)}</dd></div><div><dt>mAP50–95</dt><dd>{percent(evidence.standard_metrics.map50_95)}</dd></div></dl><p>{evidence.images} images / {evidence.labelled_plates} labelled plates · dataset-provided {evidence.split} split. Existing PlatePlus detector evaluated without Singaporean fine-tuning.</p><p>Localisation only, separate from Malaysian detector, OCR and origin evidence. No representative negative set; general accuracy and false-positive rate are unavailable.</p></section>;
}
export function OriginEvidence({ evidence }: { evidence: OriginEvidenceData }) {
  return <section><h3>Plate-origin classification</h3><strong>{evidence.exact_matches}/{evidence.samples} · {evidence.exact_match_percent}%</strong><p>{evidence.note}</p><p>{evidence.cross_country_errors} cross-country errors; {evidence.ambiguous_rejected} overlapping and {evidence.unsupported_rejected} unsupported patterns safely rejected.</p></section>;
}

export function ModelPerformance() {
  const [open, setOpen] = useState(false); const [evidence, setEvidence] = useState<Evidence | null>(null); const [error, setError] = useState("");
  const triggerRef = useRef<HTMLButtonElement>(null);
  const modalRef = useRef<HTMLElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const close = () => { setOpen(false); window.setTimeout(() => triggerRef.current?.focus(), 0); };
  useEffect(() => { if (!open || evidence || error) return; void getJson<Evidence>("/api/intelligence/summary").then(setEvidence).catch(reason => setError(reason instanceof Error ? reason.message : "Model evidence is unavailable.")); }, [open, evidence, error]);
  useEffect(() => {
    if (!open) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
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
    return () => { document.removeEventListener("keydown", onKeyDown); document.body.style.overflow = previousOverflow; };
  }, [open]);
  return <><button ref={triggerRef} className="model-performance-button secondary-button" onClick={() => setOpen(true)}>Model performance</button>{open && createPortal(<div className="performance-backdrop" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) close(); }}><section ref={modalRef} className="performance-modal" role="dialog" aria-modal="true" aria-labelledby="model-performance-title"><header className="performance-modal-header"><div><p>Evidence for presentation Q&amp;A</p><h2 id="model-performance-title">Model performance</h2></div><button ref={closeRef} className="performance-close" type="button" aria-label="Close model performance" onClick={close}><X size={20} aria-hidden="true" /></button></header><div className="performance-modal-body" role="region" aria-label="Model evaluation evidence" tabIndex={0}>{error && <p className="form-error" role="alert">{error}</p>}{!evidence && !error && <p role="status">Loading verified evaluation evidence…</p>}{evidence && <div className="performance-content"><section><h3>Malaysian detector</h3><strong>{evidence.evaluation.detector.accuracy_percent}%</strong><p>User-reported Malaysian held-out detector result. Precision, recall, and F1 were not exported and are not estimated.</p></section><section><h3>OCR</h3><strong>{evidence.evaluation.ocr.exact_matches}/{evidence.evaluation.ocr.held_out_samples} · {evidence.evaluation.ocr.exact_match_accuracy_percent}%</strong><p>Held-out PaddleOCR exact-match accuracy. The protected 44-crop set was preserved and not used for tuning.</p></section>{evidence.evaluation.singaporean_detector && <SingaporeanDetectorEvidence evidence={evidence.evaluation.singaporean_detector} />}{evidence.evaluation.development && <section><h3>Development review</h3><strong>{evidence.evaluation.development.exact_matches}/{evidence.evaluation.development.scorable_samples} · {evidence.evaluation.development.exact_match_accuracy_percent}%</strong><p>Development-only OCR result; {evidence.evaluation.development.positive_detector_false_negatives} false negatives across {evidence.evaluation.development.positive_detector_images} reviewed plate-present images.</p><ul>{evidence.evaluation.development.condition_observations.map(item => <li key={item.label}><b>{item.label}:</b> {item.result}</li>)}</ul></section>}{evidence.evaluation.origin && <OriginEvidence evidence={evidence.evaluation.origin} />}{evidence.thresholds && <section><h3>Recognition gates</h3><p>Detection threshold {Math.round(evidence.thresholds.detection * 100)}% · OCR threshold {Math.round(evidence.thresholds.ocr * 100)}%. Passing thresholds still requires an unambiguous supported pattern, a matching synthetic vehicle, and sufficient funds.</p></section>}<section><h3>Known limitations</h3><ul>{evidence.known_failure_conditions.map(item => <li key={item}>{item}</li>)}</ul></section></div>}</div></section></div>, document.body)}</>;
}
