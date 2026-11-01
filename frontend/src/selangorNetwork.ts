import type { TollLocation } from "./locations";

export type NetworkRoute = { id: string; label: string; path: string; labelX: number; labelY: number };
export type NetworkPosition = { x: number; y: number; route: string; webcam?: boolean };

// Deliberately stylized geographic context: this is a dashboard network, not a GIS map.
export const SELANGOR_OUTLINE = "M120 55 L235 34 L360 50 L470 42 L565 86 L640 142 L622 224 L662 292 L604 355 L488 366 L398 342 L294 378 L190 350 L110 284 L72 200 Z";
export const NETWORK_ROUTES: NetworkRoute[] = [
  { id: "LDP", label: "LDP / E11", path: "M0 128 C90 128 150 119 203 132 S260 154 284 172 S325 195 354 209 S399 222 425 237 S459 266 486 273 S531 275 560 290 S646 307 700 330", labelX: 367, labelY: 215 },
  { id: "AKLEH", label: "AKLEH", path: "M0 100 C120 92 170 92 220 104 S340 112 395 126 S460 134 503 145 S610 150 700 172", labelX: 459, labelY: 102 },
  { id: "GRAND_SAGA", label: "Grand Saga", path: "M500 0 C505 62 500 112 503 151 S501 211 510 238 C524 253 518 269 529 285 S548 302 555 315 S571 336 592 338 S610 395 622 430", labelX: 605, labelY: 323 },
  { id: "NPE", label: "NPE / E10", path: "M0 258 C130 258 188 234 240 216 S352 167 414 178 C431 180 441 193 455 200 S477 204 490 220 S506 240 521 246 S539 253 548 262 S625 278 700 262", labelX: 605, labelY: 267 },
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
