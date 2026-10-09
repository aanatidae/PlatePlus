import { ChargeDetails, originLabel, type ChargeComponents } from "./ChargeDetails";

export type ActivityRecord = ChargeComponents & {
  id: string; location_id: string; detection_id?: string | null;
  normalized_plate?: string | null; plate_origin?: string; origin_reason?: string | null;
  recognition_source?: string; origin_source?: string; origin_country?: string | null; fallback_used?: boolean;
  detected_at?: string; processed_at?: string; status: string; source?: string;
};
const time = (value: string) => new Date(value).toLocaleString("en-MY", { timeZone: "Asia/Kuala_Lumpur", dateStyle: "medium", timeStyle: "short" });

export function RecentActivity({ item, kind, locationName, highlighted = false }: { item: ActivityRecord; kind: "detections" | "transactions"; locationName: string; highlighted?: boolean }) {
  const source = item.source === "demo_generated" ? "Simulated live feed" : item.source === "uploaded_image" ? "Uploaded image ALPR" : (item.source === "webcam" || item.source === "webcam_alpr") ? "Local webcam ALPR" : "Simulated record";
  return <div className={`record ${highlighted ? "new-webcam-record" : ""}`}>
    <strong>{kind === "detections" ? item.normalized_plate ?? "Unread plate" : `RM${Number(item.amount ?? 0).toFixed(2)}`}</strong>
    <span className={`status ${item.status}`}>{item.status.replace(/_/g, " ")}</span>
    {kind === "detections" ? <small title={item.origin_reason?.replace(/_/g, " ")}>{item.plate_origin ? originLabel(item.plate_origin) : "Origin not recorded"}</small> : <>
      <small>{item.status === "successful" ? "Final simulated total" : "Attempted simulated total"}</small>
      <ChargeDetails charge={item} compact />
    </>}
    {kind === "detections" && item.fallback_used && <small>Gemini fallback · {item.origin_country ?? "Origin unresolved"}</small>}
    <small>{locationName} · {source}<br />{time(item.detected_at ?? item.processed_at ?? "")}</small>
  </div>;
}
