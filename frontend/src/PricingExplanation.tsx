type PricingTelemetry = {
  congestion_percentage: number;
  congestion_category: string;
  current_toll_price: number;
  base_toll_price?: number;
  congestion_multiplier?: number;
  active_crossings?: number;
  road_capacity?: number;
};

const label = (value: string) => ({ normal: "Normal", low: "Normal", moderate: "Moderate", high: "Peak hour", peak_hour: "Peak hour", severe: "Severe" }[value] ?? value);
const money = (value: number) => `RM${Number(value).toFixed(2)}`;

/** Displays the server-provided decision inputs; it never recalculates a price. */
export function PricingExplanation({ telemetry, source, compact = false }: { telemetry: PricingTelemetry; source: string; compact?: boolean }) {
  const webcam = source === "webcam_alpr";
  const base = Number(telemetry.base_toll_price ?? 0);
  const multiplier = Number(telemetry.congestion_multiplier ?? 0);
  return <details className={`pricing-explanation ${compact ? "compact" : ""}`}>
    <summary>Why this price?</summary>
    <div className="price-chain" aria-label="Current toll pricing decision">
      {webcam ? <div><span>Webcam crossings</span><strong>{telemetry.active_crossings ?? 0} active / {telemetry.road_capacity ?? 10} capacity</strong></div> : <div><span>{source === "pricing_preview" ? "Preview input" : "Traffic source"}</span><strong>{source === "pricing_preview" ? "Administrator-selected congestion" : "Simulated time-profile estimate"}</strong></div>}
      <span className="chain-arrow" aria-hidden="true">↓</span>
      <div><span>Congestion</span><strong>{Number(telemetry.congestion_percentage).toFixed(1)}%</strong></div>
      <span className="chain-arrow" aria-hidden="true">↓</span>
      <div><span>Pricing band</span><strong>{label(telemetry.congestion_category)}</strong></div>
      <span className="chain-arrow" aria-hidden="true">↓</span>
      <div><span>Applied rule</span><strong>{base > 0 && multiplier > 0 ? `${money(base)} × ${multiplier.toFixed(2)}` : "Authoritative pricing rule"}</strong></div>
      <span className="chain-arrow" aria-hidden="true">↓</span>
      <div className="price-chain-result"><span>Current toll</span><strong>{money(telemetry.current_toll_price)}</strong></div>
    </div>
  </details>;
}
