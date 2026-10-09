import { ChargeDetails, originLabel } from "./ChargeDetails";

type Box = { left: number; top: number; right: number; bottom: number };
export type AlprResult = {
  status: string; message: string; plate_text?: string | null;
  plate_origin?: string; origin_reason?: string | null;
  recognition_source?: string; origin_source?: string; origin_country?: string | null;
  fallback_used?: boolean; fallback_status?: string; fallback_provider?: string | null;
  detection_confidence?: number | null; ocr_confidence?: number | null;
  bounding_box?: Box | null; payment_status?: string | null;
  payment_amount?: number | null; payment_dynamic_toll_amount?: number | null;
  payment_foreign_vehicle_charge?: number | null; payment_duplicate?: boolean;
};

export function AlprResultDetails({ result }: { result: AlprResult }) {
  return <div className="alpr-result-details">
    <span>Recognition: {result.status.replace(/_/g, " ")}</span>
    <span>{result.message}</span>
    {result.fallback_used && <span>Optional external fallback: Gemini · {result.fallback_status?.replace(/_/g, " ")}</span>}
    <span>Recognition source: {result.recognition_source === "gemini_fallback" ? "Gemini vision fallback" : "Local ALPR"} · Origin source: {result.origin_source === "gemini_fallback" ? "Gemini fallback, validated by PlatePlus" : "Local rules"}</span>
    <span title={result.origin_reason?.replace(/_/g, " ")}>{originLabel(result.plate_origin)}</span>
    {result.origin_country && <span>Likely registration country: {result.origin_country}</span>}
    <small>Detection {result.detection_confidence == null ? "unavailable" : `${Math.round(result.detection_confidence * 100)}%`} · OCR {result.ocr_confidence == null ? "unavailable" : `${Math.round(result.ocr_confidence * 100)}%`}</small>
    <span>{result.payment_status ? `Simulated payment: ${result.payment_status.replace(/_/g, " ")}` : "No simulated payment made"}{result.payment_duplicate ? " · Prior event replayed; no new deduction" : ""}</span>
    <ChargeDetails charge={{ amount: result.payment_amount, dynamic_toll_amount: result.payment_dynamic_toll_amount, foreign_vehicle_charge: result.payment_foreign_vehicle_charge, status: result.payment_status }} />
  </div>;
}
