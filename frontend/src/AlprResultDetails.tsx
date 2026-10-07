import { ChargeDetails, originLabel } from "./ChargeDetails";

type Box = { left: number; top: number; right: number; bottom: number };
export type AlprResult = {
  status: string; message: string; plate_text?: string | null;
  plate_origin?: string; origin_reason?: string | null;
  detection_confidence?: number | null; ocr_confidence?: number | null;
  bounding_box?: Box | null; payment_status?: string | null;
  payment_amount?: number | null; payment_dynamic_toll_amount?: number | null;
  payment_foreign_vehicle_charge?: number | null; payment_duplicate?: boolean;
};

export function AlprResultDetails({ result }: { result: AlprResult }) {
  return <div className="alpr-result-details">
    <span title={result.origin_reason?.replace(/_/g, " ")}>{originLabel(result.plate_origin)}</span>
    <small>Detection {result.detection_confidence == null ? "unavailable" : `${Math.round(result.detection_confidence * 100)}%`} · OCR {result.ocr_confidence == null ? "unavailable" : `${Math.round(result.ocr_confidence * 100)}%`}</small>
    <span>{result.payment_status ? `Simulated payment: ${result.payment_status.replace(/_/g, " ")}` : "No simulated payment made"}{result.payment_duplicate ? " · Prior event replayed; no new deduction" : ""}</span>
    <ChargeDetails charge={{ amount: result.payment_amount, dynamic_toll_amount: result.payment_dynamic_toll_amount, foreign_vehicle_charge: result.payment_foreign_vehicle_charge, status: result.payment_status }} />
  </div>;
}
