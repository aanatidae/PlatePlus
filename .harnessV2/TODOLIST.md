# PlatePlus Improvement Checklist

## Status Legend

- `[x]` Complete
- `[~]` In progress
- `[ ]` Pending
- `[!]` Blocked or needs user decision

## Current Baseline

The original core implementation is substantially complete.

Existing working baseline includes:

- [x] YOLO car-plate detector.
- [x] PaddleOCR recognition.
- [x] Malaysian plate normalization.
- [x] Confidence gates.
- [x] Still-image ALPR.
- [x] Local webcam ALPR.
- [x] PostgreSQL persistence.
- [x] Administrator authentication.
- [x] Simulated toll payment.
- [x] Duplicate transaction protection.
- [x] Traffic simulation.
- [x] Configurable four-band dynamic pricing.
- [x] Real-time Overview telemetry.
- [x] Plate Recognition page.
- [x] Dynamic Pricing page.
- [x] Simulator sandbox.
- [x] Vercel frontend deployment.
- [x] Remote backend/database deployment.
- [x] Core unit, integration, end-to-end, and UI-contract tests.
- [x] Simulator separated from live Overview telemetry.
- [x] Standalone Traffic Analytics frontend route removed.

The checklist below tracks **improvements**, not the original development phase.

## Multi-Toll Location Foundation

- [x] Create `toll_locations` database model.
- [x] Add location ID.
- [x] Add display name.
- [x] Add highway/route label.
- [x] Add latitude.
- [x] Add longitude.
- [x] Add operational status.
- [x] Add base toll.
- [x] Add road capacity.
- [x] Add simulation profile or equivalent configuration.
- [x] Add timestamps where appropriate.
- [x] Create database migration for toll locations.
- [x] Seed multiple simulated toll locations.
- [x] Add `location_id` to traffic records where appropriate.
- [x] Add `location_id` to toll-price records where appropriate.
- [x] Add `location_id` to detection records where appropriate.
- [x] Add `location_id` to toll transactions where appropriate.
- [x] Add `location_id` to simulation history where appropriate.
- [x] Add indexes for location-aware queries.
- [x] Add foreign-key constraints.
- [x] Verify migration against development PostgreSQL.
- [x] Verify migration against test PostgreSQL.

## Toll Location APIs

- [x] Add API to list toll locations.
- [x] Add API to retrieve one toll location.
- [x] Add API for one location's live operational state.
- [x] Add API for network-wide live state.
- [x] Add location-aware traffic queries.
- [x] Add location-aware pricing queries.
- [x] Add location-aware detection queries.
- [x] Add location-aware transaction queries.
- [x] Add network-level aggregate metrics.
- [x] Validate unknown location IDs safely.
- [x] Ensure one location's records cannot leak into another location's response.

## Interactive Overview Map

- [x] Add multiple simulated toll locations to the Overview map.
- [x] Make each toll marker selectable.
- [x] Track selected toll location in frontend state.
- [x] Use congestion condition to determine marker state.
- [x] Add marker hover/click card.
- [x] Show toll price in location card.
- [x] Show congestion percentage in location card.
- [x] Show congestion category in location card.
- [x] Show vehicles per hour in location card.
- [x] Show average speed in location card.
- [x] Show camera status in location card.
- [x] Show system status in location card.
- [x] Show last update time in location card.
- [x] Make selected marker visually clear.
- [x] Update Overview KPIs when selected location changes.
- [x] Update recent ALPR activity by selected location.
- [x] Update transaction activity by selected location.
- [x] Keep historical charts off the real-time Overview; historical analysis remains in detailed pages.
- [x] Add map behavior for mobile/tablet layouts.
- [x] Add keyboard-accessible alternative to map marker selection.
- [x] Replace abstract map lines with a stylized, pannable Selangor state/network visualization.
- [x] Draw and label only the simulated LDP, DUKE, KESAS, and NPE routes.
- [x] Position compact toll markers along their associated highway routes.
- [x] Add limited zoom and fit/reset network-map controls.

## All Locations Network View

- [x] Add `All Locations` selection.
- [x] Show total simulated traffic flow.
- [x] Show total simulated toll revenue.
- [x] Show network average congestion.
- [x] Show number of severe-congestion locations.
- [x] Show number of locations online.
- [x] Show number of cameras offline.
- [x] Show total detections.
- [x] Show total transactions.
- [x] Show network payment success rate.
- [x] Add network health summary.
- [x] Add network map state that does not incorrectly imply one location is active.
- [ ] Consider side-by-side comparison between two locations.

## Overview Simplification

- [x] Remove historical date filtering from the live Overview if it does not affect the live endpoint.
- [x] Remove congestion-history filtering from the live Overview if it does not affect current telemetry.
- [x] Remove plate-history filtering from the live Overview if it does not affect current telemetry.
- [x] Remove transaction-history filtering from the live Overview if it does not affect current telemetry.
- [x] Move relevant filters to Plate Recognition.
- [x] Move relevant filters to Dynamic Pricing.
- [x] Keep Overview focused on current state.
- [x] Add `Last updated` indicator.
- [x] Add data freshness/stale-data state.
- [x] Keep Simulator state isolated from Overview.
- [x] Verify live Overview remains read-only.

## Dynamic Toll Location Context

- [x] Remove hard-coded `Penchala Toll Plaza` from the top bar.
- [x] Remove hard-coded `LDP / E11` from the top bar.
- [x] Show selected toll location name.
- [x] Show selected location route/highway.
- [x] Show appropriate label for `All Locations`.
- [x] Keep selected location consistent while navigating relevant pages where useful.
- [x] Decide whether selected location should persist across browser refreshes.
- [x] Verify selected-location context in browser navigation and refresh checks; unit-test scope request construction.

## PlatePlus Branding

- [x] Replace `TOLL//VISION` with `PlatePlus`.
- [x] Update sidebar brand.
- [x] Update login branding.
- [x] Update browser/document title.
- [x] Update browser title/description and API product name; retain existing deployed infrastructure resource identifiers.
- [x] Update major page headings if needed.
- [x] Update loading states.
- [x] Update error states.
- [x] Add a PlatePlus wordmark/logo treatment.
- [x] Keep branding consistent on mobile navigation.
- [x] Standardize `Simulated Prototype` label.
- [x] Remove redundant long simulation warnings where a shorter consistent label is sufficient.
- [x] Standardize terminology across frontend.
- [x] Standardize terminology across backend/API messages.
- [x] Standardize congestion category capitalization.

## Multi-Location Traffic Profiles

- [x] Add location-specific road capacity.
- [x] Add location-specific baseline traffic demand.
- [x] Add location-specific peak periods.
- [x] Add location-specific average speed profile.
- [x] Add location-specific variation parameters.
- [x] Generate independent traffic state per location.
- [x] Verify one location can be low congestion while another is severe.
- [x] Persist location-specific traffic history.
- [x] Add deterministic location-aware simulation for tests.

## Webcam-Driven Simulator Toll Plaza

- [x] Add `Simulator Toll Plaza` as a live, selectable map location on LDP.
- [x] Set its demonstration road capacity to 10 vehicles per hour.
- [x] Associate local webcam ALPR detections and simulated payments with this location.
- [x] Derive rolling-hour traffic flow, congestion, category, and dynamic price from accepted webcam crossings.
- [x] Exclude this location from generated/fallback traffic telemetry.
- [x] Keep average speed unavailable rather than fabricated.
- [x] Keep raw webcam frames/crops local and ephemeral.
- [x] Test rolling-window, rejected-result, congestion-cap, and pricing behavior.

## Multi-Location Simulator

- [x] Add toll-location selector to Simulator.
- [x] Allow custom scenario for one selected location.
- [x] Support multiple locations in one simulation run.
- [x] Add weekday morning peak preset.
- [x] Add weekday evening peak preset.
- [x] Add weekend traffic preset.
- [x] Add event surge preset.
- [x] Add accident/incident preset.
- [x] Add roadworks preset.
- [x] Add low-traffic preset.
- [x] Add Time-based traffic preset using a prototype Malaysia daily traffic profile.
- [x] Derive Time-based traffic frames from simulated `Asia/Kuala_Lumpur` time with deterministic location variation and smooth hourly-band transitions.
- [x] Add simulation start time.
- [x] Add simulation duration/time range.
- [x] Add playback-speed control.
- [x] Generate a complete deterministic location state for every simulated time frame.
- [x] Recalculate traffic volume, congestion, speed, congestion band, and dynamic toll when the active frame changes.
- [x] Keep playback speed independent from simulated timestamps and frame data.
- [x] Use a fixed five-minute frame interval for time-range runs.
- [x] Stop playback at the final frame without looping.
- [x] Retain completed frame data and show a summary derived from the entire run.
- [x] Add Replay for the same generated frames and keep Reset separate.
- [x] Summarize location/network congestion, traffic, speed, dynamic tolls, and price changes.
- [x] Show baseline toll.
- [x] Show dynamic toll.
- [x] Show before/after pricing comparison.
- [x] Show per-location output.
- [x] Keep Simulator state local/sandboxed.
- [x] Confirm Simulator never writes live Overview traffic.
- [x] Confirm Simulator never writes live Overview toll price.
- [x] Confirm Simulator never creates live payment transactions.
- [x] Unit-test deterministic per-frame progression, pricing-band changes, location independence, and scenario-specific time patterns.
- [x] Unit-test summary aggregation, peak timestamps, toll-change counts, and multi-location summaries.

## Dynamic Pricing Refinement

Status: `[x]` Complete — location-relative multiplier pricing, persisted safeguards, preview/explanation, audit visibility, migration verification, and targeted tests are implemented.

- [x] Preserve current configurable four-band policy.
- [x] Add location-specific base toll.
- [x] Add configurable minimum toll.
- [x] Add configurable maximum toll.
- [x] Add minimum time between toll changes.
- [x] Add price-change smoothing or hysteresis.
- [x] Prevent rapid threshold oscillation.
- [x] Add previous toll price to decision context.
- [x] Add pricing explanation.
- [x] Show congestion percentage used in decision.
- [x] Show congestion category used in decision.
- [x] Show base toll.
- [x] Show multiplier/band.
- [x] Show previous toll.
- [x] Show new toll.
- [x] Add pricing rule preview.
- [x] Add pricing-rule audit history.
- [x] Add manual override history if overrides are introduced. (No manual override was introduced.)
- [x] Keep rule-based pricing clearly identified as rule-based.
- [x] Leave prediction model as optional future extension.

## AI Explainability and Evaluation

- [x] Remove the dedicated AI Intelligence dashboard page, navigation entry, route, frontend API calls, and page-only styles; `/intelligence` safely redirects to `/dashboard`.
- [x] Retain AI evaluation evidence, ALPR decision traces, and pricing decision traces in backend/evaluation outputs for future placement in existing pages or documentation.

- [x] Show current detection confidence threshold.
- [x] Show current OCR confidence threshold.
- [x] Explain charge eligibility.
- [x] Show YOLO detection metrics.
- [x] Show detection precision. (Explicitly displayed as not recorded; it must not be inferred from reported accuracy.)
- [x] Show detection recall. (Explicitly displayed as not recorded; it must not be inferred from reported accuracy.)
- [x] Show detection F1 score. (Explicitly displayed as not recorded; it must not be inferred from reported accuracy.)
- [x] Show OCR exact-match accuracy.
- [x] Keep detection and OCR metrics separate.
- [x] Add ALPR decision trace.
- [x] Show detector result.
- [x] Show OCR raw result.
- [x] Show normalized plate.
- [x] Show confidence-gate result.
- [x] Show vehicle-match result.
- [x] Show payment outcome.
- [x] Add traffic/pricing decision trace.
- [x] Show simulated traffic inputs.
- [x] Show calculated congestion.
- [x] Show pricing policy decision.
- [x] Show resulting toll price.
- [x] Add known ALPR failure conditions.
- [x] Add common OCR confusion patterns.
- [x] Clearly distinguish current rule-based pricing from future ML prediction.

## ALPR Robustness and Error Analysis

- [x] Add Malaysian plate-format validation improvements.
- [x] Define accepted Malaysian plate patterns.
- [x] Reject implausible normalized plate strings safely.
- [x] Identify common OCR character confusions.
- [x] Add controlled correction rules only when output remains plausible.
- [x] Create labelled OCR development set separate from held-out test set. (150 human-reviewed non-held-out scenes; 146 have a verified single-target OCR ground truth and 4 are explicitly non-scorable challenging scenes.)
- [x] Preserve current held-out test set unchanged.
- [x] Evaluate clear-image recognition accuracy. (93/111 exact matches, 83.8% on the development set.)
- [x] Evaluate angled-plate recognition accuracy. (30/31 exact matches, 96.8%.)
- [x] Evaluate low-light recognition accuracy. (14/16 exact matches, 87.5%.)
- [ ] Evaluate motion-blur recognition accuracy. (The one reviewed sample has no verified plate text and is excluded from OCR scoring.)
- [ ] Evaluate partial-obstruction recognition accuracy. (Only 1 scorable sample, 1/1 exact match; insufficient for a robustness conclusion.)
- [ ] Evaluate unusual-format recognition accuracy. (No scorable human-verified unusual-format scene with a single unambiguous target plate is available.)
- [ ] Track false positives. (No human-labelled negative examples are in the current set, so false-positive rate remains unmeasured.)
- [x] Track false negatives. (0/146 in the reviewed positive detector set; four non-scorable challenging scenes are excluded.)
- [x] Track low-confidence recognitions.
- [x] Track rejected recognitions.
- [x] Track unknown-vehicle outcomes.
- [x] Add rejected-recognition/error-analysis view.
- [x] Keep webcam frames ephemeral by default.
- [x] Keep webcam inference local.

## Synthetic Payment Improvements

- [x] Add additional synthetic users.
- [x] Add additional synthetic vehicles.
- [x] Add more varied synthetic balances.
- [x] Add more vehicle types.
- [x] Add simulated account top-up.
- [x] Add simulated refund/reversal.
- [x] Add wallet ledger.
- [x] Show opening balance.
- [x] Show toll deductions.
- [x] Show top-ups.
- [x] Show refunds.
- [x] Show ending balance.
- [x] Add per-location revenue statistics.
- [x] Add per-location transaction counts.
- [x] Add simulated payment notifications.
- [x] Add manual-review status for uncertain recognition.
- [x] Ensure no real payment provider is integrated.

## Alerts and Operational Events

- [ ] Add severe-congestion alert.
- [ ] Add camera-offline alert.
- [ ] Add repeated low-confidence ALPR alert.
- [ ] Add repeated failed-payment alert.
- [ ] Add backend/API error alert.
- [ ] Add database error alert.
- [ ] Add information severity.
- [ ] Add warning severity.
- [ ] Add critical severity.
- [ ] Filter alerts by toll location.
- [ ] Show alert start time.
- [ ] Add acknowledgement state.
- [ ] Add alert history.
- [ ] Add simulation-run event logs.
- [ ] Add pricing-change event logs.
- [ ] Add camera-state event logs.
- [ ] Add administrator action event logs where appropriate.
- [ ] Keep all alert behavior within simulated prototype scope.

## Location-Aware Historical Analysis

- [x] Add location filter to Dynamic Pricing history.
- [x] Add date filter to Dynamic Pricing history.
- [ ] Add congestion-versus-price chart.
- [ ] Add per-location congestion history.
- [ ] Add per-location toll-price history.
- [ ] Add recognition accuracy trend.
- [ ] Add low-confidence trend.
- [ ] Add transaction success-rate trend.
- [ ] Add per-location simulated revenue trend.
- [ ] Add normal/moderate/peak/severe scenario comparison.
- [x] Keep historical analysis inside relevant existing pages.
- [x] Do not restore standalone Traffic Analytics page unless explicitly requested.
- [ ] Decide whether CSV export is useful for capstone presentation.

## Demo Mode

- [ ] Add one-click Demo Mode.
- [ ] Seed demo toll locations.
- [ ] Seed demo users.
- [ ] Seed demo vehicles.
- [ ] Seed demo balances.
- [ ] Seed demo traffic scenarios.
- [ ] Seed demo transaction history.
- [ ] Seed demo recognition history.
- [ ] Add reset-to-demo-data action.
- [ ] Make reset action idempotent/safe.
- [ ] Add guided demo sequence.
- [ ] Add fallback ALPR example when webcam is unavailable.
- [ ] Add system-information panel.
- [ ] Explain which components are local.
- [ ] Explain which components are remote/deployed.
- [ ] Explain which values are simulated.
- [ ] Add presentation-friendly empty states.
- [ ] Add presentation-friendly loading states.
- [ ] Add presentation-friendly offline states.
- [ ] Add presentation-friendly error states.
- [ ] Prepare final demo walkthrough.
- [ ] Capture final screenshots after UI is stable.

## Testing for Improvements

### Backend / Data

- [ ] Unit test toll-location creation and validation.
- [ ] Unit test per-location pricing selection.
- [x] Unit test per-location traffic generation.
- [x] Unit test network aggregation.
- [x] Integration test location-aware traffic persistence.
- [x] Integration test location-aware pricing persistence.
- [ ] Integration test location-aware detection persistence.
- [ ] Integration test location-aware transaction persistence.
- [x] Integration test cross-location isolation.
- [x] Integration test All Locations aggregation.

### Frontend

- [x] Test map marker selection.
- [x] Test selected-location state.
- [x] Test All Locations state.
- [x] Test dynamic top-bar location.
- [x] Test location-aware KPIs.
- [x] Test map card content.
- [ ] Test alert states.
- [x] Test responsive map layout.
- [x] Test mobile location selection.
- [x] Test Simulator location selection.

### Accessibility

- [x] Test keyboard navigation.
- [x] Test visible focus states.
- [ ] Test form and button labels.
- [ ] Test colour contrast.
- [x] Add accessible non-map alternative for toll selection.
- [x] Test screen-reader labels for location status.

### Reliability / Performance

- [ ] Test slow live-overview API.
- [x] Test temporary backend failure.
- [ ] Test database failure state.
- [x] Test stale telemetry handling.
- [ ] Test multiple toll locations with larger history.
- [x] Test map rendering with all seeded locations.
- [x] Confirm existing core tests remain passing.

## Documentation and Capstone

- [ ] Update README for multi-location architecture.
- [ ] Update setup documentation if schema/API changes.
- [ ] Update database documentation.
- [ ] Update API documentation.
- [ ] Update testing/evaluation documentation.
- [ ] Update architecture diagram.
- [ ] Update project limitations.
- [ ] Update future-enhancement section to reflect completed improvements.
- [ ] Document multi-location simulation behavior.
- [ ] Document pricing explanation logic.
- [ ] Document AI decision trace.
- [ ] Document Demo Mode.
- [ ] Prepare final screenshots.
- [ ] Prepare final presentation/demo flow.

## Release / Git Hygiene

- [ ] Decide whether to tag current stable prototype as `v1.0.0`.
- [ ] Create feature branch for multi-location work.
- [ ] Keep `main` stable during major improvement work.
- [ ] Use focused commits.
- [ ] Do not commit model binaries that remain intentionally Git-ignored.
- [ ] Do not use AI/tool identities as commit authors.
- [ ] Do not push without user approval.
- [x] Update `.harnessV2` files after this milestone.

## Highest-Priority Next Tasks

1. [x] Add `toll_locations` model and migration.
2. [x] Seed multiple simulated toll locations.
3. [x] Add location-aware relationships and APIs.
4. [x] Add multiple locations to the Overview map.
5. [x] Make map markers interactive.
6. [x] Make Overview KPIs location-aware.
7. [x] Add `All Locations` network view.
8. [x] Replace hard-coded Penchala top-bar context.
9. [x] Remove historical filters from the live Overview.
10. [x] Replace `TOLL//VISION` with PlatePlus branding.


## Current Follow-Up — 2026-09-05

- [x] Complete the agreed Overview/context/branding milestone using the existing design and seeded locations.
- [x] Verify Docker and development/test PostgreSQL are healthy; development migration is at head.
- [x] Pass 52 backend tests including PostgreSQL integration and 8 frontend tests; production build passes.
- [x] Browser-verify desktop/mobile, keyboard selection, refresh persistence, page context, functional plate filtering, Simulator isolation, and outage/stale-state behavior using disposable synthetic fixtures.
- [x] Complete Multi-Location Traffic Profiles with independent scheduled traffic for LDP, DUKE, KESAS, and NPE; Simulator Toll Plaza remains webcam-only.
- [x] Complete Multi-Location Simulator with local-only network runs, scenario presets, time-window/playback controls, and per-location baseline/dynamic toll comparison; generated network runs exclude Simulator Toll Plaza.
- [x] Refactor generated fallback and scheduled time-patterned traffic to calculate deterministic location-specific congestion percentages before deriving category and dynamic-pricing band; retain persisted-traffic priority and Simulator Toll Plaza webcam-only telemetry.
- [x] Tune Penchala, DUKE, NPE, and KESAS profile parameters for distinct Malaysia-time daily curves; verify a representative 24-hour matrix, congestion-to-pricing handoff, speed response, determinism, and Simulator Toll Plaza isolation.
- [x] Complete AI explainability and evaluation capability with read-only evidence endpoints, active confidence thresholds, held-out evaluation evidence, latest ALPR and per-location pricing traces, charge-eligibility rules, and known limitations; remove the dedicated frontend AI Intelligence page while retaining backend/evaluation capability.
- [x] Implement ALPR format gating, controlled OCR-confusion correction, raw-versus-normalized audit evidence, and an error-analysis/evaluation workflow without modifying the preserved held-out set.
- [x] Run the human-reviewed development-set OCR and positive-image detector evaluation; preserve the 44-crop held-out test set untouched.
- [x] Distinguish reviewed, valid-plate-present, OCR-scorable, verified-ground-truth, and detector-evaluation-role fields so challenging scenes do not distort OCR or detector metrics.
- [ ] Add human-labelled negative images plus further motion-blur, partial-obstruction, glare, and unusual-format samples before claiming full condition coverage or a false-positive rate.
- [x] Complete Synthetic Payment Improvements with an auditable simulated-wallet ledger, top-ups, reversals, per-location revenue/count summaries, payment notifications, additional synthetic account scenarios, and pending/resolved review status for uncertain recognitions. Migration `20260908_0010` is required before use.

Browser checks above are manual verification, not a new automated browser test suite. Comprehensive accessibility, larger-history performance, model evaluation, two-location comparison, independent traffic profiles, pricing smoothing, and later roadmap features remain pending. The physical webcam check was not requested or run.
