# PlatePlus High-Level Improvement Roadmap

## Current Baseline

PlatePlus is no longer in its initial development phase. The repository already contains a working capstone prototype with:

- YOLO-based Malaysian license-plate detection.
- PaddleOCR-based recognition and normalization.
- Local webcam and still-image ALPR workflows.
- Confidence gates and safe failure handling.
- PostgreSQL persistence.
- Administrator authentication.
- Simulated toll payment.
- Configurable traffic simulation.
- Dynamic toll pricing.
- Protected React/TypeScript administrator dashboard.
- Real-time Malaysia-time Overview telemetry.
- Plate Recognition, Dynamic Pricing, AI Intelligence, Simulator, and local-webcam routes.
- Automated testing for core backend, ML, payment, traffic, integration, and frontend behavior.
- Vercel frontend deployment and remote backend/database deployment.

The next project phase is **post-development improvement and capstone hardening**.

The roadmap is a set of optional personal improvements, not a list of mandatory capstone requirements. Select implementation milestones with the user. The multi-location database foundation and location-aware APIs are complete; the interactive multi-location Overview and PlatePlus branding milestone is now implemented.

The purpose of this roadmap is to improve realism, scalability, clarity, explainability, and demo quality without expanding into real banking, government traffic feeds, real enforcement, or real vehicle-owner tracking.

## Phase 1: Multi-Toll Location Foundation

Goal: evolve PlatePlus from a single-location prototype into a simulated toll network.

High-level work:

- Add a `toll_locations` model.
- Add several simulated Malaysian toll locations.
- Add location relationships to traffic, pricing, detection, transaction, and related records where appropriate.
- Add APIs for:
  - Listing toll locations.
  - Retrieving one location.
  - Retrieving location-specific live metrics.
  - Retrieving network-wide aggregates.
- Preserve cross-location data isolation.
- Support independent traffic and pricing state per location.
- Keep all operational data simulated.

Success condition:

- PlatePlus can represent multiple toll locations without mixing their data.
- The selected location can drive dashboard context and location-specific metrics.

## Phase 2: Interactive Multi-Location Overview

Goal: make the Overview function as a real-time network operations screen.

High-level work:

- Add multiple toll markers to the interactive map.
- Make markers selectable.
- Use marker state to show congestion condition.
- Add compact location details on marker interaction.
- Replace the hard-coded Penchala Toll Plaza top-bar context.
- Add an `All Locations` network view.
- Add network-level health and congestion summaries.
- Update current KPIs based on selected toll location.
- Optionally allow two-location comparison.
- Add clear data-freshness indicators.
- Keep the Overview read-only.

Overview simplification:

- Remove historical filters from the main Overview when they do not affect live telemetry.
- Keep only real-time operational information on the main screen.
- Move historical filtering to detailed pages.
- Preserve the Simulator/live separation.

Success condition:

- A user can understand the live simulated state of the entire toll network from the Overview and drill into one location by selecting it on the map.

## Phase 3: PlatePlus Branding and UI Consistency

Goal: present the prototype as one coherent product.

High-level work:

- Replace `TOLL//VISION` and other temporary naming with PlatePlus.
- Apply consistent PlatePlus naming across:
  - Login.
  - Sidebar.
  - Browser title.
  - Headings.
  - Loading states.
  - Error states.
  - Deployment metadata.
- Create or apply a simple PlatePlus wordmark/logo treatment.
- Standardize terminology and congestion labels.
- Use a consistent `Simulated Prototype` indicator.
- Preserve the current dark command-centre design unless a redesign is explicitly requested.

Success condition:

- All major interfaces clearly look and read as one PlatePlus product.

## Phase 4: Multi-Location Traffic Simulation

Goal: improve realism by giving each toll location its own simulated traffic behavior.

High-level work:

- Add location-specific:
  - Capacity.
  - Baseline demand.
  - Peak hours.
  - Speed profile.
  - Traffic variance.
- Allow the Simulator to choose a toll location.
- Support multiple simultaneous simulated locations.
- Add scenario presets:
  - Weekday morning peak.
  - Weekday evening peak.
  - Weekend traffic.
  - Event surge.
  - Accident/incident.
  - Roadworks.
  - Low traffic.
- Allow simulation across a time range.
- Add playback-speed controls.
- Compare baseline and dynamically calculated toll prices.
- Keep the Simulator sandbox isolated from live Overview data.

Success condition:

- Different toll locations can produce meaningfully different congestion and pricing behavior under the same or different scenarios.

## Phase 5: Dynamic Pricing Refinement

Goal: make dynamic pricing more realistic, stable, and explainable.

High-level work:

- Keep the current four-band pricing system as the baseline.
- Add price smoothing/hysteresis where appropriate.
- Add minimum time between price changes.
- Add configurable minimum and maximum toll values.
- Add location-specific base tolls.
- Add rule preview before applying changes.
- Add pricing decision explanations.
- Add pricing change audit history.
- Add manual override history if manual override is introduced.
- Keep the architecture open for future predicted congestion.

Success condition:

- PlatePlus can explain why a toll price changed and avoids unrealistic rapid price switching.

## Phase 6: AI Intelligence and Explainability

Goal: strengthen the academic and demonstration value of the AI components.

High-level work:

- Show separate detection and OCR metrics.
- Show detection precision, recall, and F1.
- Show OCR exact-match accuracy.
- Show active confidence thresholds.
- Explain charge eligibility.
- Add ALPR decision traces:
  - Detection.
  - OCR.
  - Normalization.
  - Confidence gate.
  - Vehicle match.
  - Payment result.
- Add traffic/pricing decision traces.
- Clearly identify the current pricing logic as rule-based.
- Add failure-condition summaries.
- Add common OCR confusion/error analysis.

Success condition:

- Evaluators can understand how PlatePlus makes ALPR and pricing decisions instead of seeing only final outputs.

## Phase 7: ALPR Robustness Improvements

Goal: improve recognition quality through targeted, measurable refinement.

High-level work:

- Add Malaysian plate-format validation.
- Add carefully controlled correction for common OCR confusion.
- Measure recognition accuracy by condition:
  - Clear image.
  - Angled plate.
  - Low light.
  - Motion blur.
  - Partial obstruction.
  - Unusual format.
- Separate outcome reporting:
  - False positive.
  - False negative.
  - Rejected.
  - Low confidence.
  - Unknown vehicle.
- Add an error-analysis or rejected-recognition view.
- Use a separate development set for further tuning.
- Preserve the held-out test set.
- Preserve local webcam privacy boundaries.

Success condition:

- ALPR improvements can be demonstrated with clear before/after measurements rather than subjective claims.

## Phase 8: Simulated Payment and Operations Improvements

Goal: make the financial simulation more complete without introducing real payments.

High-level work:

- Add more synthetic account scenarios.
- Add simulated top-up.
- Add simulated reversal/refund.
- Add wallet ledger/history.
- Add per-location transaction statistics.
- Add per-location simulated revenue.
- Add simulated payment notifications.
- Add manual-review status for uncertain recognitions.

Success condition:

- PlatePlus can demonstrate richer payment states while remaining fully synthetic.

## Phase 9: Alerts and System Health

Goal: make the administrator dashboard behave more like an operational command centre.

High-level work:

- Add alerts for:
  - Severe congestion.
  - Camera offline.
  - Repeated low ALPR confidence.
  - Repeated failed payments.
  - API errors.
  - Database errors.
- Add severity levels.
- Add location filtering.
- Add alert acknowledgement.
- Add operational event history.
- Add compact network health summary to the Overview.

Success condition:

- Administrators can identify simulated problems without manually inspecting every metric.

## Phase 10: Location-Aware Historical Analysis

Goal: improve analysis without restoring the removed standalone Traffic Analytics page.

High-level work:

- Add location filters to Dynamic Pricing history.
- Add congestion-versus-price charts.
- Add recognition trends to Plate Recognition or AI Intelligence.
- Add payment success-rate and simulated revenue trends.
- Add scenario comparison.
- Optionally add CSV export if useful for the final capstone demo.

Success condition:

- Historical analysis remains useful while navigation stays simple.

## Phase 11: Demo Mode and Capstone Hardening

Goal: make the final project demonstration reliable and easy to follow.

High-level work:

- Add one-click Demo Mode.
- Add reset-to-demo-data.
- Pre-seed:
  - Toll locations.
  - Vehicles.
  - Account balances.
  - Traffic scenarios.
  - Transactions.
- Create a guided demonstration sequence.
- Add clear loading, empty, offline, and error states.
- Add fallback demo data when the webcam cannot be used.
- Add a system-information panel explaining local, remote, and simulated components.
- Capture final screenshots once the interface is stable.
- Prepare a final capstone demo walkthrough.

Success condition:

- A full demonstration can be completed reliably even if a local service or physical camera is unavailable.

## Phase 12: Improvement Testing and Quality Assurance

Goal: ensure new improvements do not reduce current system reliability.

High-level work:

- Add unit tests for:
  - Toll-location logic.
  - Per-location traffic.
  - Per-location pricing.
  - Network aggregation.
- Add integration tests for:
  - Cross-location data isolation.
  - Location-aware APIs.
  - Multi-location transactions.
  - Multi-location history.
- Add UI tests for:
  - Map markers.
  - Selected location.
  - All Locations.
  - Alerts.
  - Responsive map behavior.
- Add accessibility checks:
  - Keyboard navigation.
  - Focus states.
  - Labels.
  - Colour contrast.
  - Map alternatives.
- Add slow/failing API behavior tests.
- Add performance checks for larger histories and multiple locations.

Success condition:

- Existing core tests continue passing and new multi-location behavior is covered.

## Recommended Implementation Order

### Stage A — Highest Impact

1. Multi-location database model.
2. Location-aware APIs.
3. Multiple toll locations.
4. Interactive map selection.
5. Dynamic top-bar location.
6. All Locations network view.
7. Simplified real-time Overview.
8. PlatePlus branding.

### Stage B — Simulation and Intelligence

9. Location-specific traffic profiles.
10. Multi-location Simulator.
11. Pricing smoothing and explanations.
12. Pricing audit history.
13. AI decision traces.
14. Model metrics and recognition error analysis.

### Stage C — Operational and Demo Polish

15. Richer synthetic payment behavior.
16. Alerts and event history.
17. Location-aware historical comparison.
18. Demo Mode.
19. Reset-to-demo-data.
20. Accessibility, failure-state, performance, and multi-location testing.
21. Final screenshots and presentation walkthrough.

## Definition of Success

The improved PlatePlus prototype should:

- Represent a simulated network of toll locations rather than only one station.
- Allow users to interact with toll locations through the Overview map.
- Show independent traffic, pricing, ALPR, and transaction context per location.
- Provide useful network-wide metrics.
- Explain ALPR and pricing decisions.
- Preserve the separation between live monitoring and Simulator sandbox state.
- Preserve simulated-only financial and traffic scope.
- Preserve local-webcam privacy boundaries.
- Remain reliable and understandable during the final capstone demonstration.


## Milestone Status — 2026-09-05

Phases 1–3 are implemented for the agreed scope: four existing locations, selectable schematic map, location-aware KPIs and activity, network aggregates, persisted shared selection, real-time Overview cleanup, and PlatePlus branding. Two-location comparison remains optional and unimplemented.

The Simulator has its own location selector and uses that location’s capacity/base toll. Full multi-location scenario runs and richer profiles remain future work. Recognition and pricing now have functional location/date/history filters. A targeted still-image integration change preserves location ownership through payment.

Validation passed: 52 backend tests (including PostgreSQL), 8 frontend tests, and production build. Browser checks covered desktop/mobile layout, marker and keyboard selection, refresh persistence, relevant-page context, Simulator isolation, and stale/offline states. No physical webcam inference was performed.

The next milestone is a user choice among the remaining personal improvements; do not automatically start all later roadmap phases.
