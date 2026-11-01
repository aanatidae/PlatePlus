# Stable map viewport and continuous highway routes

Completed 2026-11-01.

## Changes

The network grid previously stretched the map to match the growing selected-location
panel. Both items now align to the top, and the map has a bounded responsive height.
Upload previews, long recognition messages and charge breakdowns expand independently;
all details remain available through normal page scrolling.

All four highway paths were redrawn to continue through the Selangor outline. Their
endpoints lie beyond the outline; a uniquely identified SVG clip path trims each road
at the boundary. The boundary is drawn over the road edges. No route starts or ends
at an arbitrary interior point. This remains a schematic, not-to-scale network;
paths do not claim surveyed or official road alignments.

Roads use a dark pavement surface, narrow edges, dashed centre markings and subdued
selection highlighting. Non-scaling SVG strokes preserve line weights through zoom.
Route labels use HTML so their lettering does not stretch with the responsive SVG.
Existing markers, location selection, pan/zoom/fit controls and processing logic are
preserved. Focused styles live in `frontend/src/network-map.css`.

## Verification

Installed Edge ran in a separate headless browser with synthetic API responses.
The existing upload UI selected a generated one-pixel fixture and received a long
mock recognition/payment result. No real inference, database writes, camera access
or external image transmission occurred.

| Viewport | Map height before/after | Details height before/after |
| --- | --- | --- |
| 1920x1080 | 560 / 560 px | 540 / 910 px |
| 1366x768 | 464.44 / 464.44 px | 596 / 1047 px |
| 1024x768 | 500 / 500 px | 542 / 875 px |
| 390x844 | 425 / 425 px | 598 / 1049 px |

At each size, Fit Network leaves all five markers contained and non-overlapping,
with no horizontal page overflow. Geometry sampling confirms every route crosses
the outline exactly twice and has both endpoints outside it, yielding one continuous
visible segment per highway. Screenshots were visually reviewed on desktop/mobile.
Ignored fixtures, screenshots, checks and exact results are under
`.plateplus-demo/qa-map-layout/`.

All 110 frontend tests passed in 21 files. TypeScript and production build passed;
the existing large-bundle warning remains. React review and `git diff --check`
passed. The existing Vite server serves the changes without a backend restart.
No dependencies, map service, backend policy or processing changes were introduced.
