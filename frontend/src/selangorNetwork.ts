import type { TollLocation } from "./locations";

export type NetworkRoute = { id: string; label: string; path: string; labelX: number; labelY: number };
export type NetworkPosition = { x: number; y: number; route: string; webcam?: boolean };

// Deliberately stylized geographic context: this is a dashboard network, not a GIS map.
export const SELANGOR_OUTLINE = "M120 55 L235 34 L360 50 L470 42 L565 86 L640 142 L622 224 L662 292 L604 355 L488 366 L398 342 L294 378 L190 350 L110 284 L72 200 Z";
export const NETWORK_ROUTES: NetworkRoute[] = [
  { id: "LDP", label: "LDP / E11", path: "M112 128 C190 112 250 118 324 154 S452 232 560 282", labelX: 268, labelY: 126 },
  { id: "AKLEH", label: "AKLEH", path: "M340 110 C410 110 450 125 515 155", labelX: 432, labelY: 100 },
  { id: "GRAND_SAGA", label: "Grand Saga", path: "M510 238 C538 264 558 302 592 338", labelX: 593, labelY: 287 },
  { id: "NPE", label: "NPE / E10", path: "M414 178 C466 196 504 220 548 262", labelX: 508, labelY: 198 },
];

const POSITIONS: Record<string, NetworkPosition> = {
  LDP: { x: 29, y: 33, route: "LDP" },
  SIMULATOR: { x: 43, y: 46, route: "LDP", webcam: true },
  AKLEH: { x: 60, y: 32, route: "AKLEH" },
  GRAND_SAGA: { x: 77, y: 75, route: "GRAND_SAGA" },
  NPE: { x: 70, y: 55, route: "NPE" },
};

export function mapPositionForLocation(location: TollLocation): NetworkPosition {
  return POSITIONS[location.code] ?? { x: 50, y: 50, route: "LDP" };
}
