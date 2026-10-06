# PlatePlus `.harnessV3` Agent Instructions

## 1. Authority and Purpose

This folder is the authoritative Codex guidance for the current PlatePlus capstone hardening phase.

Instruction order:

1. The user's latest explicit request.
2. `.harnessV3/AGENTS.md`
3. `.harnessV3/PLAN.md`
4. `.harnessV3/TODOLIST.md`
5. Current repository code and tests.
6. Older `.harnessV2/` and `.harness/` files as historical context only.

Do not silently restore requirements that the user has explicitly removed from the product. In particular, the administrator UI remains intentionally simplified to three top-level pages unless the user explicitly changes that decision.

Repository:

- GitHub: `https://github.com/aanatidae/PlatePlus`
- Stable branch: `main`
- Repository state audited for this V3 harness: `main` at commit `d2c5c9e61b0ab2f8ca555768f62571e641c03e63`
- Formal project title: **PlatePlus: AI-Powered Automatic License Plate Recognition and Dynamic Toll Management System**

The current phase is not a rebuild. It is a proposal-alignment, capstone-hardening, and final-integration phase.

## 2. Git and Change-Control Rules

- Keep `main` stable.
- Prefer a feature branch for substantial V3 work. The active V3 branch is `feature/sgimplementation`.
- Do not commit, push, merge, open a pull request, tag, release, or modify `main` unless the user explicitly approves it.
- Never use Codex, ChatGPT, AI, bot, or automation identities as Git authors, committers, or co-authors.
- Do not commit trained model binaries or other intentionally Git-ignored local assets.
- Keep commits focused if/when the user later approves commits.
- Update `.harnessV3` when the implementation state materially changes.
- Do not modify legacy `.harness/` or `.harnessV2/` unless the user explicitly asks.

## 3. Current Implemented Baseline

Treat the following as already implemented unless repository inspection proves otherwise.

### ALPR

- One-class YOLO11 car-plate detection.
- Plate crop extraction.
- PaddleOCR recognition.
- Uppercase/alphanumeric normalization.
- Malaysian-style plate plausibility checks and constrained OCR-confusion correction.
- Detection/OCR confidence gates.
- Safe handling of unknown vehicles and low-confidence recognition.
- Duplicate/idempotency protection.
- Local laptop-webcam inference.
- Local still-image upload through the same Simulator Toll Plaza workflow.
- Uploaded image source tagging as `uploaded_image`.
- Webcam source tagging as `webcam_alpr`.
- Raw local webcam frames, uploaded images, and plate crops remain ephemeral by default.
- A separate deterministic plate-origin stage now runs after OCR normalization and confidence gates. It returns `malaysian`, `singaporean`, or `unknown`; overlapping supported shapes fail safely. Its outcome and reason are persisted on detection records by migration `20261002_0012`.
- Singaporean-pattern plates can create a successful simulated deduction only when an active synthetic vehicle has matching `singaporean` registration origin and the separately persisted foreign-charge setting is available. The dynamic toll and foreign charge are stored separately; the final amount is debited once.

### Simulator Toll Plaza

- Special local-ALPR-only toll location.
- Accepts laptop webcam and uploaded still images.
- Generated network traffic must never be sent to Simulator Toll Plaza.
- Capacity is 10 active crossings.
- Accepted crossings contribute to live congestion for a rolling 60-second window.
- Congestion is derived from active crossings and capped at 100%.
- Average speed remains unavailable rather than fabricated.
- Accepted crossings can create detection records, simulated transactions, traffic state, and dynamic pricing.
- Normal generated network traffic remains separate.

### Traffic and Dynamic Pricing

- Location-aware `toll_locations`.
- Per-location `base_toll`.
- Per-location traffic profile and capacity.
- Malaysia-time simulated demand profiles.
- Percentage-first congestion calculation.
- Four congestion bands: Normal, Moderate, Peak Hour, Severe.
- Rule-based dynamic pricing.
- Dynamic price calculation is based on the location base toll and congestion multiplier.
- Configurable minimum toll, maximum multiplier, minimum price-change interval, and hysteresis.
- Persisted traffic and price history.
- Network-wide and selected-location telemetry.
- Prediction remains isolated from live Overview state.

### Payment and Persistence

- V3 G/H verified on 2026-10-06: fresh and populated-V2-upgraded databases converge at `20261002_0013`; Simulator webcam/upload history retains ownership and links. Full backend verification passed (125 tests: 73 unit, 52 dedicated PostgreSQL integration). Flat-rate-only scope is documented in `docs/FLAT_RATE_SCOPE.md`; section I network replacement remains pending. Migration test details are in `docs/V3_DATABASE_MIGRATIONS.md`. The disposable test fixture rejects development database targets and clears test rows before full legacy downgrades.

- PostgreSQL with SQLAlchemy and Alembic.
- Synthetic users, accounts, vehicles, detections, traffic, prices, and transactions.
- Simulated wallet ledger.
- Simulated top-ups and reversals/refunds.
- Per-location revenue/transaction summaries.
- Payment notifications.
- Idempotent simulated toll processing.
- No real banking or eWallet integration.

### Dashboard / Presentation

The administrator dashboard has exactly three top-level pages:

1. `Overview`
2. `Dynamic Pricing Management`
3. `Prediction`

Do not restore separate top-level pages for Plate Recognition, AI Intelligence, Simulator, Local Webcam, Traffic Analytics, or other retired routes unless the user explicitly requests them.

Current presentation features include:

- Interactive simulated toll network map.
- All Locations and selected-location context.
- Recent simulated detections and transactions.
- Congestion-paced demo feed for normal simulated tolls.
- Simulator Toll Plaza webcam/upload flow.
- Simulator Toll visual feedback.
- Pricing explanation / `Why this price?`.
- Prediction `Current -> Future`.
- Prediction horizon up to 12 hours.
- Compact Model Performance modal.
- Local one-command demo startup.
- Alerts / operational events.
- Historical analysis and CSV export.
- Demo Mode and reset/seed tooling.

## 4. Proposal Alignment Requirements and Status

These are V3 requirements. Origin classification and its synthetic fixture evaluation are complete. Synthetic Singaporean records and the separate foreign-charge payment path are also implemented; network and UI alignment remain tracked separately.

### 4.1 Malaysian vs Singaporean plate-origin classification (implemented in A–C)

The V3 origin stage is implemented for a conservative subset of Malaysian and Singaporean patterns. `docs/PLATE_ORIGIN.md` defines supported shapes and limitations. The origin evaluation is limited to its labelled synthetic text fixture.

Required output states:

- `malaysian`
- `singaporean`
- `unknown` / `unsupported`

Rules:

- YOLO remains a one-class plate detector. Do not retrain YOLO merely to classify countries.
- Country/origin classification happens after OCR text normalization.
- Malaysian and Singaporean validation rules must be separate and auditable.
- Ambiguous or unsupported results must fail safely.
- Do not claim that pattern classification legally verifies nationality, ownership, VEP status, or registration status.
- Do not query JPJ, LTA, VEP, or government owner databases.

### 4.2 Synthetic Singaporean vehicles/accounts

The proposal requires supported Singaporean plate inputs and synthetic Singaporean vehicle/account records.

V3 must add:

- Synthetic Singaporean test/demo plates.
- Synthetic vehicles/accounts that can be matched by the normal payment workflow.
- Seed data that is fictional and clearly prototype-only.
- Tests covering both Malaysian and Singaporean records.

Do not use real owner data.

### 4.3 Simulated foreign-vehicle charge

Singaporean vehicles must receive a separately itemized, configurable simulated foreign-vehicle charge.

Rules:

- The congestion-based toll and foreign-vehicle charge are separate concepts.
- Formula:
  `final_simulated_total = dynamic_toll_amount + foreign_vehicle_charge`
- Do not fold the foreign charge into the congestion multiplier.
- Persist the foreign charge separately from the dynamic toll amount.
- Dashboard/history should be able to show:
  - base toll
  - congestion multiplier/band
  - dynamic toll amount
  - foreign-vehicle charge
  - final simulated total
- Malaysian vehicles receive no foreign-vehicle charge.
- Unknown/unsupported origin does not proceed as a successful simulated deduction.
- Keep the charge configurable. Do not hard-code a real-world legal rule into the core pricing algorithm.
- If RM20 is used as seeded demo configuration, label it clearly as a **simulated foreign-vehicle charge inspired by the proposal**, not as a real toll-plaza fee.

### 4.4 Flat-rate toll-system scope

PlatePlus V3 is limited to flat-rate toll systems.

Required normal simulated toll systems:

- LDP
- AKLEH
- NPE
- Grand Saga

The existing repository currently uses Penchala/LDP, DUKE, KESAS, and NPE for normal generated locations. V3 must align the normal network with the proposal.

Rules:

- Normal simulated network = LDP, AKLEH, NPE, Grand Saga.
- `Simulator Toll Plaza` remains a separate special local-ALPR demo location and does not count as one of the four normal simulated toll systems.
- Each normal location has a configured base toll, traffic profile, road capacity, location metadata, and independent history.
- Do not implement entry/exit tracking.
- Do not implement distance-based toll calculation.
- Do not implement journey-length pricing.
- Dynamic pricing adjusts the configured flat base toll:
  `dynamic_toll = base_toll * congestion_multiplier` subject to existing safeguards.
- Treat all displayed operational rates as simulated configuration unless a source is intentionally documented.

### 4.5 Proposal-visible plate origin and foreign charge

The proposal requires the admin experience to expose plate origin and foreign-charge effects. This does not require adding a new top-level page.

Prefer integration into the existing three-page UI:

- Overview recent detections: plate + origin where useful.
- Overview recent transactions: toll amount, foreign charge, final amount where applicable.
- Selected-location or transaction detail: clear breakdown.
- Model/decision evidence: show origin classification result and reason.
- Dynamic Pricing Management remains responsible only for congestion pricing, not country classification.
- Prediction remains traffic/toll prediction only and must not fabricate future plate origins.

## 5. Data Model Guidance for V3

Before changing schema, inspect existing entities and migrations.

Preferred additions are minimal, explicit, and auditable.

Possible fields / concepts:

### Vehicle

- `registration_origin` or equivalent:
  - `malaysian`
  - `singaporean`

### DetectionRecord

Persist the classifier outcome so the decision is auditable:

- `plate_origin`
- optional `origin_rule` / `origin_reason`
- optional `origin_confidence` only if there is a defensible value; do not invent a probability for deterministic rules.

### TollTransaction

Persist charge components separately:

- `dynamic_toll_amount`
- `foreign_vehicle_charge`
- `amount` remains the final simulated total, if compatible with current semantics.

If changing `amount` semantics would break existing code, introduce explicit component fields and migrate carefully rather than silently changing behavior.

### Configuration

Use an explicit configuration source for the foreign-vehicle charge. It may live in database settings or another existing configuration model. Prefer an auditable/configurable value over a magic constant in transaction code.

## 6. Migration Rules

- Never rewrite already-applied historical migrations merely to make the current schema look cleaner.
- Add a new Alembic migration for V3 schema/network changes.
- Preserve existing records where possible.
- If renaming/replacing normal simulated locations, write a deterministic migration strategy.
- Do not accidentally reassign Simulator Toll Plaza history.
- Existing normal-location history may be migrated only when the mapping is semantically defensible; otherwise keep historical records and seed the new V3 locations separately.
- Migration downgrade behavior should be explicit.
- Update seed logic so a clean database and an upgraded database converge to the same intended V3 demo state.

## 7. ALPR Origin-Classification Rules

Implement country/origin classification as a separate function/service with focused tests.

Desired pipeline:

`image -> YOLO -> crop -> PaddleOCR -> normalization -> confidence gate -> origin classification -> vehicle lookup -> simulated pricing/payment`

Classification behavior:

- If a normalized plate clearly matches a supported Malaysian pattern: `malaysian`.
- If it clearly matches a supported Singaporean pattern: `singaporean`.
- If it matches both or neither: `unknown` / `unsupported`.
- Unknown/ambiguous classifications fail safely before successful deduction.
- Keep the raw OCR string, normalized value, and classification result available for audit/evaluation.
- Do not silently mutate a plate to force it into a country pattern.
- Existing constrained OCR confusion correction may be reused only when its result remains auditable and does not create cross-country ambiguity.

## 8. Dynamic Pricing Rules

Dynamic pricing remains rule-based and congestion-driven.

- Keep Normal / Moderate / Peak Hour / Severe.
- Keep location-specific `base_toll`.
- Keep minimum toll / maximum multiplier / hysteresis / minimum-change safeguards.
- Do not introduce ML pricing without explicit user approval.
- Do not make plate origin alter the congestion multiplier.
- Foreign charge is added after the dynamic toll decision.
- `Why this price?` must explain congestion pricing separately from foreign charge.

Example explanation:

`Base toll RM2.00 -> Moderate 1.5x -> Dynamic toll RM3.00 -> Singaporean foreign charge RM20.00 -> Final simulated total RM23.00`

Only use actual configured values in UI.

## 9. Traffic and Location Rules

Normal network generation must independently simulate only:

- LDP
- AKLEH
- NPE
- Grand Saga

Simulator Toll Plaza remains excluded from normal generation.

When locations are changed:

- Update database seed/migrations.
- Update location tests.
- Update map route definitions and labels.
- Update frontend fixtures.
- Update simulator/prediction fixtures.
- Update traffic profiles.
- Update docs.
- Update any hard-coded strings in errors, tests, or screenshots.
- Search the repository for `PENCHALA`, `DUKE`, `KESAS`, old route labels, and old location IDs.

Do not leave proposal/repository naming mismatches.

## 10. Simulator Toll Plaza Rules

Keep both current local input methods:

- laptop webcam
- uploaded JPG/JPEG/PNG/WebP still image

Do not remove either unless explicitly requested.

Both inputs:

- use local YOLO/PaddleOCR
- use the same confidence and origin-classification rules
- use the same duplicate protection
- use the same vehicle lookup/payment path
- use the same 60-second congestion window
- use the same pricing path
- persist metadata only
- do not persist raw image bytes by default

If a Singaporean image is accepted at Simulator Toll Plaza, it must follow the same foreign-charge logic as a Singaporean recognition elsewhere.

## 11. Prediction Rules

- Prediction is browser-local/sandboxed unless current code says otherwise.
- It may read canonical live current telemetry.
- It must not mutate Overview traffic, prices, detections, transactions, or wallets.
- Keep the time-based scenario only.
- Keep location, start time, duration, and playback speed controls.
- Keep up to 12-hour duration.
- Keep Malaysia-time rollover correct.
- Exclude Simulator Toll Plaza from time-profile prediction because its congestion is local-ALPR-derived.
- After V3 network alignment, Prediction location options must be LDP, AKLEH, NPE, and Grand Saga.

## 12. Evaluation and Evidence Rules

Current verified evidence must not be overstated.

Preserve:

- YOLO detector: user-reported 93.1% held-out test accuracy.
- PaddleOCR held-out exact-match: 37/44 = 84.1%.
- Development OCR exact-match: 125/146 = 85.6%.
- Angled development set: 30/31 = 96.8%.
- Low-light development set: 14/16 = 87.5%.
- Glare/overexposure development set: 4/7 = 57.1%.
- Positive detector review: 0 false negatives on 146 reviewed positive detector-evaluation images, not a general 100% detector-accuracy claim.
- False-positive rate remains unavailable without human-labelled negative images.

V3 adds a new evaluation requirement:

- Test Malaysian vs Singaporean origin classification with explicitly labelled synthetic or human-verified examples.
- Report origin-classification accuracy/confusion counts separately from OCR exact-match accuracy.
- Do not use the preserved 44-crop OCR held-out set for tuning.
- Do not fabricate Singaporean evaluation metrics before a labelled set exists.

As of 2026-10-02, a separate 32-case synthetic text fixture and reproducible evaluator provide the V3 origin confusion matrix: MY 9 correct/3 unknown, SG 8 correct/4 unknown, unsupported 8 unknown, and zero MY-to-SG or SG-to-MY classifications. All seven overlapping and eight unsupported cases were safely rejected. The 25/32 (78.1%) exact-origin figure is fixture-only and must never be presented as field accuracy, OCR accuracy, registration verification, or general Singaporean recognition accuracy. See `ml/evaluation/origin/README.md` and `docs/TESTING_EVALUATION.md`.

## 13. Dashboard Rules

Keep the current restrained dark presentation design.

- Exactly three top-level pages unless explicitly changed.
- Overview is the live operations surface.
- Dynamic Pricing Management edits congestion-pricing policy.
- Prediction explains now-vs-future time-profile behavior.
- Model Performance remains a modal/popover, not a new route.
- Local camera/upload stays tied to Simulator Toll Plaza.
- Avoid restoring UI bloat.
- Plate-origin and foreign-charge information should appear contextually, not through a new sidebar page.
- Respect keyboard navigation, visible focus, and reduced-motion behavior.

## 14. Testing Expectations

After each V3 vertical slice, add or update focused tests.

Minimum V3 coverage:

### Origin classification

- Valid Malaysian examples.
- Valid Singaporean examples.
- Ambiguous examples.
- Unsupported examples.
- OCR confusion cases that could cross country patterns.
- Unknown origin fails safely.

### Payment

- Malaysian accepted transaction has zero foreign charge.
- Singaporean accepted transaction adds configured foreign charge once.
- Insufficient balance checks use final simulated total.
- Idempotent replay does not charge twice.
- Failure transaction component amounts are consistent.
- Wallet ledger records final debit correctly.
- Reversal/refund uses the actual debited total.

### Location alignment

- Seeded normal network codes/names are LDP, AKLEH, NPE, GRAND_SAGA.
- Simulator remains separate.
- Normal scheduler excludes Simulator.
- No generated normal location retains DUKE/KESAS/Penchala as active V3 network context.
- Per-location isolation remains intact.

### Frontend

- Location selectors show the V3 network.
- Map labels/routes match the V3 network.
- Origin appears correctly for detections where required.
- Singaporean transaction shows separate foreign charge and final total.
- Malaysian transaction does not show a non-zero foreign charge.
- Prediction uses only the four normal V3 toll systems.
- Existing three-page navigation remains intact.

### Regression

Run the existing backend, PostgreSQL integration, ML, frontend, and build suites relevant to the changed area.

## 15. Local Commands

Do not install dependencies or start environment-changing services without approval unless the user explicitly asks.

Existing documented commands include:

Backend unit tests:

`cd backend && .\.venv\Scripts\python.exe -m pytest tests\unit -q`

ML tests:

`cd ml && ..\backend\.venv\Scripts\python.exe -m pytest tests -q`

Frontend tests/build:

`cd frontend && npm test && npm run build`

PostgreSQL integration tests require the dedicated test database and `RUN_POSTGRES_TESTS=1`.

Local capstone launcher:

`start_plateplus_demo.bat`

Do not point destructive integration fixtures at the development database.

## 16. Definition of Done for Proposal Alignment

Proposal-alignment work is not done until:

- Malaysian/Singaporean origin classification exists.
- Unknown/ambiguous origin fails safely.
- Synthetic Singaporean records exist.
- Foreign-vehicle charge is separately configurable and persisted.
- Final transaction total includes the separate foreign charge only for Singaporean vehicles.
- Dashboard/history can explain the charge breakdown.
- Normal simulated network is LDP, AKLEH, NPE, Grand Saga.
- Flat-rate scope is reflected in code, tests, and docs.
- Simulator Toll Plaza remains separate and local-ALPR-only.
- Existing pricing, prediction, demo, and three-page UI behavior has not regressed.
- Relevant automated tests pass.
- Documentation and `.harnessV3` status are updated truthfully.
