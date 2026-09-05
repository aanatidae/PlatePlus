import type { TollLocation } from "./locations";

export type NetworkRoute = { id: string; label: string; path: string; labelX: number; labelY: number };
export type NetworkPosition = { x: number; y: number; route: string; webcam?: boolean };

// Deliberately stylized geographic context: this is a dashboard network, not a GIS map.
export const SELANGOR_OUTLINE = "M120 55 L235 34 L360 50 L470 42 L565 86 L640 142 L622 224 L662 292 L604 355 L488 366 L398 342 L294 378 L190 350 L110 284 L72 200 Z";
export const NETWORK_ROUTES: NetworkRoute[] = [
  { id: "LDP", label: "LDP / E11", path: "M112 128 C190 112 250 118 324 154 S452 232 560 282", labelX: 268, labelY: 126 },
  { id: "DUKE", label: "DUKE / E33", path: "M174 86 C270 92 348 110 470 144", labelX: 330, labelY: 91 },
  { id: "KESAS", label: "KESAS / E5", path: "M126 274 C230 246 332 238 468 258 S568 282 624 310", labelX: 372, labelY: 235 },
  { id: "NPE", label: "NPE / E10", path: "M414 178 C466 196 504 220 548 262", labelX: 508, labelY: 198 },
];

const POSITIONS: Record<string, NetworkPosition> = {
  PENCHALA: { x: 29, y: 33, route: "LDP" },
  SIMULATOR: { x: 43, y: 46, route: "LDP", webcam: true },
  DUKE: { x: 54, y: 28, route: "DUKE" },
  KESAS: { x: 43, y: 67, route: "KESAS" },
  NPE: { x: 70, y: 55, route: "NPE" },
};

export function mapPositionForLocation(location: TollLocation): NetworkPosition {
  return POSITIONS[location.code] ?? { x: 50, y: 50, route: "LDP" };
}
