# PlatePlus Project Agent Notes

## Instruction Hierarchy

- User requests in the active conversation are authoritative.
- The current repository is `https://github.com/aanatidae/PlatePlus`.
- `AI-Powered Automatic License Plate Recognition and Dynamic Toll Management System.pdf` remains the product documentation and source context.
- `.harnessV2/PLAN.md` defines the current high-level improvement roadmap.
- `.harnessV2/TODOLIST.md` defines the granular improvement checklist and task status.
- The original implementation phase is essentially complete. Future work should focus on product improvement, refinement, realism, scalability, usability, explainability, testing, and capstone presentation quality.
- Do not re-implement completed core features unless an improvement requires a targeted refactor.
- Do not install new dependencies, download models, retrain models, run long model-related commands, or make major environment changes without asking the user first.
- Do not commit, push, open a pull request, merge, or create a release unless the user explicitly approves it.

## Current Repository State

- Workspace root: resolve it as the directory containing `.harness`; do not hard-code a drive letter.
- The project is normally `D:/Capstone Project` on the user's PC and `C:/Capstone Project` on the user's laptop.
- Git remote: `https://github.com/aanatidae/PlatePlus`.
- Default branch: `main`.
- The repository contains:
  - Malaysian car-plate dataset tooling.
  - A trained local YOLO car-plate detector.
  - PaddleOCR-based plate recognition.
  - Malaysian plate normalization and confidence gating.
  - Local webcam FastAPI inference.
  - Still-image ALPR integration.
  - PostgreSQL persistence.
  - Administrator authentication.
  - Simulated toll payment.
  - Configurable traffic simulation.
  - Dynamic toll pricing.
  - React/TypeScript administrator dashboard.
  - Testing and deployment documentation.
  - Vercel frontend deployment and Render backend/database deployment configuration.
- Core implementation, integration, and testing are substantially complete.
- The current project phase is **post-development improvement and capstone hardening**.
- The roadmap phases are optional personal improvements, not mandatory capstone requirements. Resolve milestone requirements with the user before proceeding into implementation.
- The multi-location database foundation and location-aware APIs are complete. The interactive multi-location Overview, shared persisted location selection, All Locations metrics, historical-filter relocation, PlatePlus branding, traffic/pricing refinement, and AI explainability/evaluation capability are implemented. The dedicated AI Intelligence dashboard page has been removed; retain its evidence through backend/evaluation outputs and relevant operational pages. Select the next optional improvement milestone with the user.

## Git Attribution

- Do not use tool, assistant, automation, or AI identities as Git commit authors.
- Codex, ChatGPT, or any automated assistant must never appear as a Git author, committer, co-author, or GitHub contributor.
- Attribute commits to the actual human contributor responsible for the change.
- If an incorrect automated identity appears in a local commit, rewrite it before pushing.

## Repository Workflow

- Keep all PlatePlus improvements in the same repository.
- Treat `main` as the stable project branch.
- Prefer feature branches for substantial improvements, for example:
  - `feature/multi-toll-locations`
  - `feature/interactive-map`
  - `feature/overview-cleanup`
  - `feature/plateplus-branding`
  - `feature/multi-location-simulator`
  - `feature/pricing-improvements`
  - `feature/ai-explainability`
  - `feature/demo-mode`
- Keep commits focused and descriptive.
- After a repository change, update `.harnessV2/AGENTS.md`, `.harnessV2/PLAN.md`, and `.harnessV2/TODOLIST.md` when project state or priorities materially change.
- Do not create a separate PlatePlus v2 repository. Major improvements remain part of the same project history.
- A Git tag or release may be used later to preserve the current stable prototype before major improvement work begins, but only with user approval.

## Product Scope

Project name:

- **PlatePlus**
- Formal capstone title: **AI-Powered Automatic License Plate Recognition and Dynamic Toll Management System**

Prototype boundaries:

- Traffic data remains simulated.
- Toll payments remain simulated.
- Do not integrate real banking systems, Touch 'n Go, government traffic feeds, enforcement systems, or real vehicle-owner tracking unless the user explicitly changes scope.
- Use synthetic/test user, vehicle, account, transaction, and traffic data.
- Real Malaysian toll names or map locations may be used as geographic context, but all operational, congestion, payment, pricing, and vehicle activity shown by PlatePlus must remain clearly identified as simulated.
- Local webcam inference remains local to the machine running it.
- Raw webcam frames and plate crops remain ephemeral by default.
- `Simulator Toll Plaza` is a special live, webcam-driven location on the LDP display route. Its rolling one-hour traffic flow, congestion, and dynamic toll derive only from accepted local-webcam ALPR crossings; it must never receive generated/fallback traffic telemetry. Raw frames and crops remain local and ephemeral, while only the existing processed detection/payment metadata is persisted.
- Scheduled network generation uses each operational non-webcam location's `simulation_profile` for baseline demand, Malaysia-time demand pattern and peak hours, variation, and speed bounds. It calculates a bounded congestion percentage first, then derives the configured category and pricing band from that percentage; it must never select a category from baseline demand before calculating congestion. It writes independent traffic/price history for LDP, DUKE, KESAS, and NPE in one scheduler run; do not route this generated telemetry to Simulator Toll Plaza.
- `app.api.locations._state` is the canonical current-location telemetry boundary: persisted location traffic takes priority, generated locations otherwise receive a deterministic minute-bucketed percentage-first profile fallback, and Simulator Toll Plaza remains webcam-derived. Overview map markers, the selected-location card, and live KPIs must render the same network response state rather than independently recalculating it.

## Current Product Baseline

The following capabilities are already implemented and should normally be improved rather than rebuilt:

### ALPR

- Car-plate-only YOLO detection.
- Plate crop extraction.
- PaddleOCR recognition.
- Malaysian plate normalization.
- Detection and OCR confidence gates.
- Vehicle lookup.
- Safe handling of unknown and low-confidence plates.
- Duplicate recognition and payment protection.
- Still-image and local webcam workflows.

### Simulated Toll Payment

- Synthetic users, accounts, and registered vehicles.
- Toll price retrieval.
- Balance checks.
- Successful and failed simulated payment records.
- Insufficient-balance handling.
- Unknown-vehicle handling.
- Transaction idempotency.

### Traffic and Pricing

- Simulated traffic generation.
- Malaysia-time support.
- Normal, moderate, peak-hour, and severe traffic conditions.
- Configurable four-band pricing.
- Historical traffic and toll-price persistence.
- Simulator isolation from the live Overview.
- Extension point for future prediction models.

### Administrator Dashboard

Protected routes include:

- Overview.
- Plate Recognition.
- Dynamic Pricing.
- Simulator.
- Local Webcam when enabled.

Current dashboard behavior includes:

- Real-time Malaysia-time Overview telemetry.
- Congestion and toll-price metrics.
- ALPR and transaction metrics.
- Recent detections and transactions.
- Charts and historical views.
- Responsive command-centre styling.
- Vercel deployment.
- Remote API deployment that excludes local webcam inference.
- A shared toll-location selector defaults to All Locations, persists across refreshes, and scopes Overview, Plate Recognition, and Dynamic Pricing. Simulator selection remains independent; local webcam retains its explicitly labelled default toll.
- PlatePlus branding and a consistent Simulated Prototype indicator across the dashboard and login.

## Primary Improvement Direction

The main improvement goal is to evolve PlatePlus from a strong single-location prototype into a more complete simulated intelligent toll-management platform.

The highest-priority product improvements are:

1. Add a multi-toll-location data model.
2. Add multiple simulated toll locations to the Overview map.
3. Make the map interactive and location-aware.
4. Make dashboard KPIs update according to the selected toll location.
5. Add an All Locations network view.
6. Remove the hard-coded Penchala Toll Plaza context.
7. Keep the main Overview focused on real-time monitoring only.
8. Apply PlatePlus branding consistently.
9. Add location-specific traffic simulation.
10. Improve pricing realism and explainability.
11. Expand AI explainability and model evaluation presentation.
12. Improve demo reliability and capstone presentation flow.

## Multi-Location Architecture Requirements

The improved architecture should support a `toll_locations` concept with fields such as:

- `id`
- `display_name`
- `highway_or_route`
- `latitude`
- `longitude`
- `status`
- `base_toll`
- `road_capacity`
- `simulation_profile`
- timestamps where appropriate

Location relationships should be added where useful to:

- Traffic records.
- Toll price records.
- Detection records.
- Toll transactions.
- Simulator runs.
- Operational events or alerts.

Requirements:

- Historical data from one toll location must not be incorrectly mixed with another.
- Each location should be able to have independent congestion, vehicle flow, average speed, toll price, and operational state.
- The architecture should support network-wide aggregation without losing per-location detail.
- Location selection should be represented consistently between frontend state, API requests, and persisted records.

## Overview and Interactive Map Requirements

The Overview remains a read-only live monitoring screen.

Improvements should:

- Add several simulated toll locations to the interactive map.
- Make map markers selectable.
- Use the selected marker as the active toll context.
- Replace the fixed Penchala top-bar label with the selected location.
- Update location-specific KPIs after selection.
- Show marker state according to congestion.
- Provide a compact location card with:
  - Toll price.
  - Congestion percentage/category.
  - Vehicles per hour.
  - Average speed.
  - Camera status.
  - System status.
  - Last update time.
- Add an `All Locations` view with network-level metrics.
- Optionally support side-by-side comparison between two locations.
- Remove historical filtering controls from the main Overview when they do not affect the real-time endpoint.
- Keep historical analysis in the more appropriate detailed pages.
- Preserve the rule that Simulator actions must not mutate live Overview telemetry.

## PlatePlus Branding Requirements

- Replace temporary or prototype-facing branding such as `TOLL//VISION` with PlatePlus.
- Use PlatePlus consistently across:
  - Login.
  - Sidebar.
  - Browser title.
  - Page headings.
  - Loading and error states.
  - Deployment metadata where applicable.
- Maintain the current dark command-centre visual direction unless the user asks for a redesign.
- Use a consistent short `Simulated Prototype` label instead of excessive repeated disclaimers where possible.
- Keep terminology consistent across frontend and backend.

## Traffic Simulation Improvements

Future simulation improvements should include:

- Location-specific road capacity.
- Location-specific baseline demand.
- Location-specific peak-hour behavior.
- Location-specific average-speed profiles.
- Multiple simultaneous simulated locations.
- Scenario presets such as:
  - Weekday morning peak.
  - Weekday evening peak.
  - Weekend traffic.
  - Event surge.
  - Accident/incident.
  - Roadworks.
  - Unusually low traffic.
- Simulation over a time range.
- Playback speed controls for demo purposes.
- Clear comparison between baseline and dynamically calculated toll prices.
- Simulator state must remain local/sandboxed and must not write into live Overview records.

## Dynamic Pricing Improvements

Implemented policy: retain four editable congestion bands as location-relative multipliers. A price decision uses the selected location's `base_toll`, configured minimum toll and maximum multiplier, prior price context, a minimum change interval, and hysteresis around thresholds. Persisted prices remain the authoritative charge amount. The administrator preview/audit UI must describe this as simulated rule-based pricing, not a prediction or real toll policy.

Keep the current configurable four-band policy as the baseline.

Potential improvements:

- Price-change smoothing.
- Minimum time between price changes.
- Minimum and maximum toll limits.
- Location-specific base tolls.
- Location-specific pricing rules where useful.
- Preview of a pricing-rule change before applying it.
- Clear explanation of each toll adjustment.
- Pricing audit history.
- Manual override history if overrides are introduced.
- Future comparison between current congestion and projected congestion.

Do not silently replace the current rule-based pricing approach with machine learning. If an ML predictor is introduced later, clearly distinguish prediction from pricing policy.

## AI Explainability and Evaluation

Keep explainability and evaluation evidence available through Plate Recognition, Dynamic Pricing, documentation, and read-only backend/evaluation outputs. Do not restore a dedicated AI Intelligence dashboard page unless the user explicitly requests it.

Improvements should include:

- Detection threshold visibility.
- OCR threshold visibility.
- Plate acceptance/charge eligibility explanation.
- Separate detection and OCR metrics.
- Detection precision, recall, and F1.
- OCR exact-match accuracy.
- Common OCR failure patterns.
- Recognition decision traces:
  - Detection.
  - OCR.
  - Normalization.
  - Confidence gate.
  - Vehicle match.
  - Payment result.
- Traffic/pricing decision traces:
  - Simulated traffic input.
  - Congestion result.
  - Pricing policy.
  - Toll result.
- Known failure-condition presentation.

Current known model baseline:

- YOLO car-plate detector: user-reported 93.1% test accuracy.
- PaddleOCR exact-match accuracy: 84.1% on the held-out set.
- PaddleOCR currently meets the 80% prototype OCR target.

Preserve the held-out test set. Further OCR tuning should use a separate development set.

## ALPR Improvement Rules

Focus on robustness and measurable improvement rather than replacing the pipeline without justification.

Potential improvements:

- Malaysian plate-format validation.
- Carefully constrained OCR confusion correction.
- Accuracy breakdown by image condition.
- Error-analysis dashboards.
- Separate tracking for:
  - False positives.
  - False negatives.
  - Low-confidence results.
  - Rejected results.
  - Unknown vehicles.
- Keep raw webcam frames ephemeral by default.
- Do not move webcam inference to third-party cloud processing unless explicitly approved.

## Simulated Payment Improvements

Potential improvements:

- More synthetic account scenarios.
- Simulated account top-up.
- Simulated refund/reversal flow.
- Wallet ledger.
- Per-location revenue.
- Per-location transaction statistics.
- Simulated user notifications.
- Manual-review state for low-confidence recognitions.

No real payment integration should be introduced.

## Alerts and Operational Events

Potential improvements:

- Severe congestion alerts.
- Camera-offline alerts.
- Low ALPR confidence alerts.
- Repeated failed-payment alerts.
- API/database error alerts.
- Severity levels.
- Per-location filtering.
- Alert acknowledgement.
- Operational event log.

All operational alerts remain part of the simulated prototype.

## Historical Analysis

Do not reintroduce a standalone Traffic Analytics page unless the user explicitly requests it.

Instead:

- Keep traffic/pricing history inside Dynamic Pricing.
- Keep recognition trends inside Plate Recognition.
- Keep payment/revenue history inside operations or transaction views.
- Add toll-location filters to historical views.
- Add congestion-versus-price comparison.
- Add recognition trends.
- Add transaction success-rate and simulated revenue trends.
- Add scenario comparisons.

## Demo and Capstone Hardening

The final PlatePlus demo should be reliable and understandable.

Potential improvements:

- One-click Demo Mode.
- Reset-to-demo-data action.
- Pre-seeded multi-location network.
- Pre-seeded vehicles and balances.
- Pre-seeded traffic scenarios.
- Guided demo flow:
  1. Select a toll location.
  2. Show live Overview.
  3. Run a traffic scenario.
  4. Observe dynamic price.
  5. Perform ALPR recognition.
  6. Show simulated payment.
  7. Inspect detection, transaction, and AI decision trace.
- Reliable empty/loading/error/offline states.
- Fallback demo data if the physical webcam cannot be used.
- System-information panel explaining:
  - Local components.
  - Deployed components.
  - Simulated components.
- Final documentation screenshots after the UI stabilizes.

Do not run the final physical browser-webcam permission/inference verification unless the user explicitly asks for it.

## Testing Strategy for Improvements

Add new tests as improvement work is introduced.

Priority areas:

- Toll-location model and relationships.
- Per-location traffic generation.
- Per-location toll pricing.
- Location-aware API responses.
- Cross-location data isolation.
- Network-level aggregation.
- Map marker selection.
- Dynamic top-bar location context.
- All Locations view.
- Multi-location Simulator.
- Pricing smoothing.
- Alerts.
- Demo Mode.
- Accessibility.
- Slow/failing API behavior.
- Responsive map behavior.
- Performance with larger history and multiple locations.

Existing core tests should remain passing.

## Future Agent Operating Rules

## Local Presentation Dashboard Architecture — 2026-09-09

- The local administrator dashboard has exactly three top-level pages: Overview (`/dashboard`), Dynamic Pricing Management (`/pricing`), and Prediction (`/prediction`). Retired direct routes redirect safely to Overview.
- Overview is the live operations surface. Normal generated toll locations may receive explicitly labelled `demo_generated` synthetic crossings through the local presentation feed; their existing congestion controls crossing cadence, never the reverse.
- The local feed is administrator-controlled (start, pause, reset), singleton per backend process, rate-limited with bounded jitter, and never targets Simulator Toll Plaza. Reset removes only feed-created records and reverses only their synthetic wallet effect.
- Simulator Toll Plaza is webcam-only. Its accepted local-webcam crossings remain historically persisted but contribute to its live congestion only for a rolling 60-second window at a capacity of 10 crossings. Do not fabricate its speed or send it generated/fallback crossings.
- The Overview selected-location panel exposes a compact local laptop-camera PiP only for Simulator Toll Plaza. It preserves local YOLO/PaddleOCR processing, duplicate protection, and simulated-payment logic without persisting raw frames or crops.
- Dynamic Pricing Management owns editable pricing bands, safeguards, preview, and audit behavior. Prediction is a time-based, browser-local forecast demo for normal locations only and must never alter live telemetry, prices, detections, transactions, or the demo feed.
- Localhost (React, FastAPI, PostgreSQL, local model runtime, browser webcam) is the primary capstone presentation architecture. Preserve deployment compatibility where practical, but do not require Vercel, Render, or internet connectivity for the local demo.
- The normal-toll local feed uses a seeded fleet of 96 unique, plausible Malaysian-style synthetic vehicles. Selection suppresses the prior 16 plates per location and the most recent four global choices; do not reduce this presentation diversity or create obvious short-term repeats.
- Simulator Toll Plaza uses a compact floating/minimizable/resizable laptop-camera PiP, never a half-screen drawer. It must leave the Overview usable so map, selected metrics, detections, and transactions remain observable during a scan.

- Start future work by reading `.harnessV2/AGENTS.md`, `.harnessV2/PLAN.md`, and `.harnessV2/TODOLIST.md`.
- Treat the repository state as the source of truth for what is already implemented.
- Do not blindly follow stale completed tasks from older documentation.
- Prioritize improvement work according to `.harnessV2/PLAN.md`.
- Keep granular task status in `.harnessV2/TODOLIST.md`.
- Keep `.harnessV2/PLAN.md` high-level.
- Update harness documentation after meaningful architecture, scope, or priority changes.
- Preserve modular boundaries so ALPR, OCR, payment, traffic, pricing, persistence, frontend, and deployment can evolve independently.
- Do not imply simulated data is real.
- Do not use real vehicle-owner data.
- Do not push changes without user approval.


## Verified Improvement Milestone — 2026-09-05

- Retain the existing dark command-centre design and four seeded toll locations. Run broader design suggestions by the user before implementing them.
- Overview uses a responsive, keyboard-selectable schematic map, explicitly labelled not to scale. It has no historical filters or historical charts.
- Overview now uses a pannable, limited-zoom stylized Selangor silhouette with the four simulated highway routes (LDP, DUKE, KESAS, NPE) and compact markers placed on their routes. It is intentionally a dashboard visualization, not a GIS map; do not add unrelated roads, tiles, POIs, or a heavy map dependency without user approval.
- `/api/live/overview?scope=all_locations` returns network monitoring data; `location_id` returns one location. Activity metrics and recent records cover the last hour. Congestion is capacity-weighted; network toll is an arithmetic mean of reporting locations.
- History filters operate server-side before pagination in Recognition and Dynamic Pricing, with Malaysia-time date boundaries. A still-image recognition requires a specific frontend location and persists its detection/payment at that location.
- Polling is every 30 seconds, requests time out after 15 seconds, and previous-location responses are cancelled. Overview distinguishes stale measurements (older than two minutes), unavailable telemetry, and partial network coverage.
- Camera/system states are simulated from location operational status; average speed remains an estimate. Normal generated locations use tuned, independent Malaysia-time profiles with low overnight demand, distinct commuter peaks, and bounded deterministic variation; pricing smoothing is complete separately.
- Verified: 52 backend tests including PostgreSQL integration, 8 frontend tests, production build, and desktop/mobile browser checks with disposable synthetic fixtures. Physical webcam/model inference was not run.
- Docker Desktop and PostgreSQL development/test containers are available and healthy. Development schema is at `20260904_0004`. Test fixtures recreate only `capstone_alpr_test` on port 5433.
- No dependencies installed, no real data or payment integration, and no commits, pushes, or deployments performed.

## Verified Simulator Milestone — 2026-09-06

- The Traffic & toll simulator is a browser-local sandbox. It supports individual locations and a generated-network run across LDP, DUKE, KESAS, and NPE; it never calls a write API or persists simulated output. Each five-minute simulation frame is the complete deterministic source of truth for the displayed timestamp, traffic, congestion, speed, pricing band, and dynamic toll. Playback speed changes only how quickly frames advance in the browser. Runs are finite: the final frame transitions to a completed state, and all summary metrics must be derived from the stored frame sequence rather than a rerun of the model.
- `Time-based traffic` is a simulator-only prototype estimate. It uses the simulated frame's `Asia/Kuala_Lumpur` clock and a deterministic, smooth 24-hour category profile; it must never be presented as live, official, or government traffic data.
- Network runs exclude Simulator Toll Plaza. The plaza can be selected for an individual hypothetical projection, but its live telemetry remains exclusively local-webcam-derived.
- Available sandbox presets are normal, moderate, peak hour, severe, weekday morning/evening peak, weekend, event surge, accident/incident, roadworks, low traffic, and custom conditions. The interface exposes simulation start time, duration, playback speed, and each location’s capacity, traffic, congestion, speed, baseline toll, dynamic toll, and price change.
- Frontend verification passed: 19 tests and a production build. Automated browser verification was unavailable because the local `agent-browser` executable is not installed.

## Verified AI Explainability and Evaluation Capability — 2026-09-07

- A read-only authenticated evidence endpoint exposes active detection/OCR thresholds, documented held-out evaluation evidence, charge-eligibility rules, a latest persisted ALPR trace, a selected-location traffic/pricing trace, and known failure conditions without rerunning models or writing data. The dedicated AI Intelligence dashboard page was later removed; retain this capability for evaluation and appropriate future operational/documentation surfaces.
- The detector’s reported 93.1% held-out accuracy and PaddleOCR’s 37/44 (84.1%) exact-match result are shown separately. Detector precision, recall, and F1 are visibly marked as not recorded because the original training artifacts did not export them; they must not be fabricated from accuracy.
- The ALPR trace covers detector result, raw OCR result, normalization, confidence/charge gate, vehicle match, and simulated payment outcome. The pricing trace covers simulated traffic input, calculated congestion, selected policy/band plus safeguards, and resulting toll. Dynamic pricing remains explicitly presented as a simulated rule-based policy, not a prediction model or real toll policy.

## ALPR Robustness Evaluation Protocol — 2026-09-07

- Charge eligibility now additionally requires a plausible common Malaysian plate layout. The pipeline preserves raw OCR separately and may correct only common character confusions that produce exactly one valid layout; ambiguous text is never silently substituted.
- `ml/evaluation/development/labels.csv` contains 150 unverified review candidates (138 training, 12 validation) selected deterministically from 459 eligible images. It has zero path overlap with the 44 protected held-out entries in `ml/datasets/car_plate_test_manifest.txt`; no source image or held-out label was modified.
- Human review filled the manifest without altering the protected test set. The local development run scored 125/146 OCR exact matches (85.6%) and detected all 146 reviewed positive detector-evaluation images. The manifest explicitly distinguishes `review_status`, `valid_plate_present`, `ocr_scorable`, verified ground truth, and `detection_evaluation_role`; four challenging non-scorable scenes are excluded from both OCR and detector rates. Treat all values as development-only: there are no negative images, motion-blur OCR has no readable ground truth, unusual-format OCR has no scorable single-target sample, and partial-obstruction has only one scored sample. Do not claim a false-positive rate or complete per-condition coverage until additional human-labelled samples are added.

## Verified Synthetic Payment Milestone — 2026-09-08

- The payment system remains entirely synthetic. `20260908_0010` adds immutable wallet-ledger entries, simulated payment notifications, opening-balance tracking, reversal metadata, and manual-review metadata for uncertain recognitions.
- Successful tolls create a linked debit entry and simulated notification atomically. Top-ups and reversals credit the same wallet with idempotency protection; only successful unreversed tolls with an available simulated account can be reversed.
- The protected data API exposes ledger history, top-up, reversal, pending-review resolution, notifications, and per-location/network payment summaries. The Plate Recognition page provides wallet top-up, selected-scope revenue/count visibility, recent notices, and reversal controls.
- Demo seed data now contains six synthetic drivers, varied balances, and car, pickup, EV, and motorcycle examples. Do not substitute real payment accounts, real customer records, or a payment provider.

## Historical Analysis and Demo Mode — 2026-09-08

- Historical analytics are location-aware and remain within existing operational context; the protected endpoint also provides a CSV export of the current simulated scope.
- Demo Mode is authenticated and simulated-only. Its restore action must preserve administrator access, toll-location configuration, and non-Demo Mode operational history while restoring the synthetic demo-wallet baseline and replacing explicitly Demo Mode-created records.
- Do not represent Demo Mode records, scenario output, fallback ALPR evidence, or exported data as real-world toll, payment, traffic, or vehicle data.
