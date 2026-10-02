# PlatePlus V3 Implementation Plan

## Purpose

V3 aligns the current working PlatePlus repository with the latest capstone proposal and presentation feedback without rebuilding already-complete functionality.

The repository already contains a mature multi-location ALPR, simulated-payment, dynamic-pricing, Prediction, demo, and presentation stack. The V3 workstreams are:

1. Malaysian vs Singaporean plate-origin classification.
2. Synthetic Singaporean vehicles/accounts.
3. Separately itemized simulated foreign-vehicle charge.
4. Flat-rate-only product boundary.
5. Replace the normal generated network with LDP, AKLEH, NPE, and Grand Saga.
6. Surface origin/foreign-charge information through the existing three-page UI.
7. Add proposal-alignment tests and documentation.

As of 2026-10-02, the repository baseline and plate-origin slice (TODO sections A–C) are complete on `feature/sgimplementation`. Detection metadata now stores a conservative origin decision and reason. Overlapping patterns are rejected. Singaporean deduction is deliberately blocked until its separate foreign-charge configuration and transaction components are implemented. Baseline tests passed before changes; post-change verification passed with 89 backend tests (including 37 PostgreSQL integration), 34 ML tests, 43 frontend tests, and a frontend production build.

Origin evaluation (TODO section D) now has a separate, reproducible 32-case synthetic text fixture. It reports MY/SG/unknown confusion counts, cross-country errors, and safe rejection of overlapping or unsupported patterns. The 25/32 exact-origin result is a selected-fixture result only; OCR held-out and development results remain separate and untouched. No real-world origin accuracy is claimed.

## V3 Target Architecture

Recognition path:

`Camera / uploaded image -> YOLO11 -> crop -> PaddleOCR -> normalization -> confidence gate -> origin classification -> synthetic vehicle/account lookup -> simulated toll transaction`

Pricing path:

`location flat base toll -> congestion percentage -> pricing band/multiplier -> safeguarded dynamic toll`

Final charge path:

`dynamic toll + foreign-vehicle charge (Singaporean only) = final simulated total`

Traffic path:

`Malaysia-time profile -> per-location demand -> congestion -> pricing`

Normal generated network:

- LDP
- AKLEH
- NPE
- Grand Saga

Special local-ALPR location:

- Simulator Toll Plaza

Simulator Toll Plaza is not part of normal generated network traffic.

---

## Phase 0 — Baseline Verification and V3 Branch

### Goal

Create a safe baseline before schema/domain changes.

### Tasks

- Confirm current `main` SHA.
- Create a V3 feature branch only with user approval.
- Run fast existing unit/frontend suites where environment is already available.
- Record currently failing tests before changes.
- Search repository for old location identifiers:
  - `PENCHALA`
  - `DUKE`
  - `KESAS`
  - old route labels
- Search repository for all current transaction amount assumptions.
- Search repository for all Malaysian-only plate validation assumptions.
- Confirm current migration head.
- Confirm current seed behavior.

### Exit criteria

- Known baseline documented.
- No accidental `main` changes.
- V3 gaps are mapped to concrete files.

---

## Phase 1 — V3 Domain Model and Migration

### Goal

Add the minimum schema needed for plate origin and separated foreign charges, and align the normal network.

### Proposed schema changes

Add an Alembic migration after current head.

Preferred additions:

- `vehicles.registration_origin`
- `detection_records.plate_origin`
- optional `detection_records.origin_rule` / reason
- `toll_transactions.dynamic_toll_amount`
- `toll_transactions.foreign_vehicle_charge`
- retain `toll_transactions.amount` as final total if compatible

Add a configurable foreign-vehicle charge setting using the most appropriate existing settings/configuration model.

### Network migration

Align the normal generated network to:

- `LDP`
- `AKLEH`
- `NPE`
- `GRAND_SAGA`

Keep `SIMULATOR` unchanged.

Do not rewrite old migrations. Add a new migration.

Decide carefully whether existing Penchala/DUKE/KESAS historical records should:

- be mapped to new demo locations when semantically defensible, or
- remain historical while new V3 locations are seeded.

Prefer data safety over pretending old history belongs to a new toll system.

### Exit criteria

- Clean migration upgrade.
- Clean database seed converges to V3 state.
- Existing Simulator records remain attached to Simulator.
- Component fields have explicit defaults/backfill behavior.
- Downgrade path is defined.

---

## Phase 2 — Plate-Origin Classification

### Goal

Classify accepted OCR results as Malaysian, Singaporean, or unknown/unsupported.

### Implementation

Create a dedicated origin-classification module/service.

Keep YOLO one-class.

Pipeline order:

1. Detect plate.
2. Crop.
3. PaddleOCR.
4. Normalize.
5. Apply confidence gates.
6. Apply controlled OCR correction where already allowed.
7. Classify origin.
8. Reject ambiguous/unsupported origin.
9. Vehicle lookup.
10. Simulated payment.

### Malaysian rules

Reuse/improve current Malaysian validation.

### Singaporean rules

Implement explicit supported Singaporean registration patterns based on the proposal's prefix-number-suffix requirement.

Do not overgeneralize.

### Unknown/ambiguous behavior

- Never silently default to Malaysian.
- Never silently default to Singaporean.
- Do not process successful payment if origin is unresolved.
- Persist enough evidence for audit/error analysis.

### Evaluation

Create a separate origin-classification fixture/evaluation set.

Track:

- Malaysian correct.
- Singaporean correct.
- Unknown correct.
- MY -> SG confusion.
- SG -> MY confusion.
- rejected ambiguous cases.

Do not mix origin-classification accuracy with OCR exact-match accuracy.

### Exit criteria

- Deterministic origin classifier exists.
- Unit tests cover both countries and unknown cases.
- Existing Malaysian valid cases still work.
- Ambiguous cases fail safely.

---

## Phase 3 — Synthetic Singaporean Vehicles and Foreign Charge

### Goal

Complete the proposal's payment behavior.

### Seed data

Add fictional Singaporean-style demo plates and synthetic accounts.

Requirements:

- No real owner data.
- Sufficient balances for success examples.
- At least one low/insufficient-balance scenario if useful for testing.
- Clear synthetic naming.

### Transaction calculation

For Malaysian vehicles:

`final total = dynamic toll`

For Singaporean vehicles:

`final total = dynamic toll + configured foreign charge`

Persist:

- dynamic toll component
- foreign-charge component
- final amount

### Balance and ledger

- Balance sufficiency must check the final amount.
- Debit ledger must use the final amount.
- Notifications must state the final simulated charge.
- Reversal/refund must reverse the actual final debit.
- Idempotency must prevent duplicate foreign charge.

### Failure behavior

- Unknown origin: fail before successful payment.
- Unknown vehicle: no successful deduction.
- Missing price: no successful deduction.
- Insufficient balance: do not partially charge.
- Duplicate event: return prior outcome, no second charge.

### Exit criteria

- Malaysian and Singaporean transaction tests pass.
- Charge components reconcile exactly to final amount.
- No real payment integration introduced.

---

## Phase 4 — Flat-Rate Network Alignment

### Goal

Make the implemented demo match the proposal's flat-rate scope.

### Backend

Seed/configure normal locations:

- LDP
- AKLEH
- NPE
- Grand Saga

For each location:

- unique code
- display name
- route/highway label
- prototype coordinates/map placement
- base toll
- road capacity
- simulation profile
- status

Do not claim prototype-configured base tolls are official real-world rates unless explicitly sourced/documented.

### Traffic

Retune profiles only as needed to retain:

- independent daily curves
- Normal/Moderate/Peak/Severe transitions
- Malaysia-time behavior
- deterministic tests

### Frontend

Update:

- network route definitions
- marker labels
- toll selector options
- Prediction fixtures
- pricing fixtures
- map tests
- any screenshots/copy

Remove active V3 references to:

- DUKE
- KESAS
- Penchala as a separate normal toll entry

`Simulator Toll Plaza` remains separate.

### Exit criteria

- Normal generated network has exactly the four proposal systems.
- Scheduler does not generate Simulator traffic.
- Map and API use consistent names.
- Prediction uses the four normal V3 locations only.
- Existing All Locations aggregation still works.

---

## Phase 5 — Dashboard Proposal Alignment

### Goal

Expose the new origin and charge behavior without reintroducing removed pages.

### Overview

Recent detections should be able to show:

- plate
- origin
- location
- time
- status

Recent transactions should be able to show:

- plate
- location
- dynamic toll
- foreign charge when non-zero
- final amount
- status
- time

For normal Malaysian transactions, avoid cluttering every row with `RM0.00 foreign charge` unless useful.

### Simulator Toll Plaza

After webcam/upload recognition:

- show accepted plate
- show classified origin
- show payment result
- if Singaporean, show foreign charge in the result/transaction feedback
- congestion behavior remains based on accepted crossing state, not charge amount

### Pricing explanation

Keep `Why this price?` focused on congestion-based dynamic toll.

Where a transaction is shown, add a separate charge breakdown:

`Dynamic toll -> foreign charge -> final total`

Do not imply foreign charge affects congestion pricing.

### Dynamic Pricing Management

- Keep rule editing focused on congestion.
- Do not add origin rules here unless explicitly requested.
- If the foreign-charge configuration needs an admin control, place it in a compact clearly separate configuration section or existing appropriate settings surface, not inside congestion bands.

### Prediction

- Keep origin/foreign charge out of traffic prediction.
- Prediction continues to forecast congestion and toll only.
- Use LDP/AKLEH/NPE/Grand Saga.

### Exit criteria

- No new sidebar page required.
- Origin/charge visible where operationally relevant.
- Existing three-page layout preserved.
- Simulator feedback remains presentation-friendly.

---

## Phase 6 — Proposal-Alignment Test Matrix

### Backend unit tests

Add:

- Malaysian origin classification.
- Singaporean origin classification.
- ambiguous/unknown classification.
- cross-country OCR confusion cases.
- Malaysian transaction has zero foreign charge.
- Singaporean transaction adds configured charge.
- final balance uses combined total.
- insufficient balance uses combined total.
- idempotency does not duplicate foreign charge.
- refund/reversal uses combined total.
- detection origin persistence.
- transaction component persistence.

### PostgreSQL integration tests

Add/extend:

- V3 migration.
- V3 location seed.
- Singaporean synthetic vehicle/account persistence.
- location-aware detection/transaction persistence.
- foreign-charge fields through APIs.
- cross-location isolation.
- migration from existing database state.

### ML tests

Add:

- origin classification helper tests.
- normalization compatibility.
- ambiguity handling.
- separate classification fixtures.

Do not retrain YOLO solely for this feature.

### Frontend tests

Add:

- four V3 normal locations.
- Simulator remains separate.
- origin display.
- Singaporean charge breakdown.
- Malaysian transaction without added charge.
- Prediction selector V3 options.
- map route/marker updates.
- no retired page/navigation regression.

### Exit criteria

- Relevant existing tests pass.
- New V3 tests pass.
- Frontend production build passes.

---

## Phase 7 — Documentation and Evaluation Alignment

### Update repository documentation

Update:

- `README.md`
- `docs/SETUP.md`
- `docs/TESTING_EVALUATION.md`
- `docs/MULTI_LOCATION.md`
- architecture documentation
- demo instructions
- API/database notes where applicable

### Required wording

Make clear:

- all payment and traffic are simulated
- PlatePlus is flat-rate-only
- normal V3 demo network is LDP/AKLEH/NPE/Grand Saga
- Simulator Toll Plaza is separate
- origin classification is pattern-based, not legal verification
- foreign charge is simulated and separately itemized
- no JPJ/LTA/VEP/owner-data integration
- no real banking/eWallet
- no distance/entry-exit charging

### Evaluation documentation

Add origin-classification evaluation only when labelled examples exist.

Do not fabricate metrics.

### Exit criteria

- Code, UI, tests, README, docs, and `.harnessV3` agree.
- No stale current-state claim says the normal network is Penchala/DUKE/KESAS/NPE.
- No stale current-state claim says PlatePlus is Malaysian-only.

---

## Phase 8 — Final Capstone Verification

### Local startup

Use existing one-command launcher where possible.

Verify:

1. PostgreSQL starts/is healthy.
2. migrations reach head.
3. seed succeeds idempotently.
4. FastAPI starts.
5. Vite starts.
6. admin can sign in.
7. normal live demo feed works for LDP/AKLEH/NPE/Grand Saga.
8. Simulator Toll Plaza webcam still works.
9. Simulator Toll Plaza image upload still works.
10. Malaysian plate produces normal simulated toll.
11. Singaporean plate produces normal simulated toll + separate foreign charge.
12. unknown origin fails safely.
13. congestion/dynamic pricing still works.
14. Prediction stays isolated.
15. Model Performance modal still works.
16. no real external data/payment dependency exists.

### Final evidence

Capture presentation screenshots only after the V3 UI is stable.

Recommended evidence:

- All Locations map with V3 toll systems.
- selected normal toll.
- Simulator Toll Plaza.
- Malaysian detection/transaction.
- Singaporean detection/transaction charge breakdown.
- `Why this price?`.
- Dynamic Pricing Management.
- Prediction now-vs-future.
- Model Performance modal.

---

## Recommended Implementation Order

1. Baseline verification.
2. New V3 migration/schema.
3. Origin classifier.
4. Singaporean seed data.
5. Foreign-charge transaction logic.
6. V3 network locations.
7. Frontend surfacing.
8. Unit/integration/frontend regression tests.
9. Docs.
10. Local presentation verification.

Do not start with cosmetic frontend changes before the backend data contract is defined.
