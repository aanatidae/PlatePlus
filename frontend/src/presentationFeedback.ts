export type SimulatorTelemetry = { congestion_percentage: number; current_toll_price: number };
const money = (value: number) => `RM${Number(value).toFixed(2)}`;

/** Copy for a canonical Simulator Toll telemetry transition; does not calculate pricing. */
export function simulatorPricingFeedback(previous: SimulatorTelemetry, next: SimulatorTelemetry, acceptedCrossing: boolean) {
  if (Number(previous.congestion_percentage) === Number(next.congestion_percentage)) return null;
  const rising = Number(next.congestion_percentage) > Number(previous.congestion_percentage);
  const tollChanged = Number(previous.current_toll_price) !== Number(next.current_toll_price);
  if (acceptedCrossing && rising) return `Congestion increased to ${Number(next.congestion_percentage).toFixed(0)}% → ${tollChanged ? `Toll adjusted from ${money(previous.current_toll_price)} to ${money(next.current_toll_price)}` : `Toll remains ${money(next.current_toll_price)}`}`;
  if (!rising) return `Congestion dropped to ${Number(next.congestion_percentage).toFixed(0)}% → ${tollChanged ? `Toll adjusted to ${money(next.current_toll_price)}` : `Toll remains ${money(next.current_toll_price)}`}`;
  return null;
}
