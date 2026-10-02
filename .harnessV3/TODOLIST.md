# PlatePlus V3 TODO List

Legend:

- `[x]` verified implemented in current repository baseline
- `[ ]` still required / not verified implemented
- `[~]` partially implemented; V3 alignment still needed

## A. Repository / Harness

- [x] Existing repository is `aanatidae/PlatePlus`.
- [x] Stable branch is `main`.
- [x] `.harnessV2` exists as historical improvement documentation.
- [x] Create `.harnessV3` guidance for current proposal alignment.
- [x] Create a V3 feature branch only after explicit user approval. (Renamed to `feature/sgimplementation` by user request.)
- [x] Record baseline test results before V3 code changes. (46 backend unit and 18 ML tests passed.)
- [x] Search all active code/tests/docs for stale V2 toll names before implementation. (Old normal-network names remain in location, traffic, map, Prediction, tests, and historical migrations for later V3 network alignment.)
- [x] Keep `.harness` and `.harnessV2` unchanged unless explicitly requested.

## B. Current ALPR Baseline

- [x] YOLO11 one-class plate detection exists.
- [x] PaddleOCR pipeline exists.
- [x] Plate cropping exists.
- [x] Uppercase/alphanumeric normalization exists.
- [x] Malaysian-style plausibility validation exists.
- [x] Controlled OCR-confusion correction exists.
- [x] Detector/OCR confidence gates exist.
- [x] Low-confidence recognition fails safely.
- [x] Unknown vehicle handling exists.
- [x] Duplicate/idempotency protection exists.
- [x] Local laptop webcam flow exists.
- [x] Local uploaded still-image flow exists.
- [x] Uploaded images are ephemeral by default.
- [x] Webcam frames/crops are ephemeral by default.
- [x] Add explicit Malaysian/Singaporean/unknown origin classification.
- [x] Ensure origin classification occurs after OCR normalization and confidence gates, not in YOLO.
- [x] Ensure ambiguous results never default to Malaysian or Singaporean.
- [x] Persist origin classification result for audit. (New `20261002_0012` migration verified by dedicated PostgreSQL integration tests.)
- [x] Add origin classification reason/rule where useful.
- [x] Add origin classification to decision/evidence output.

## C. Malaysian / Singaporean Plate Support

- [x] Malaysian-style plate workflow is supported.
- [x] Define supported Malaysian origin-classification patterns separately from generic plausibility logic.
- [x] Define supported Singaporean prefix-number-suffix patterns.
- [x] Add Singaporean normalization/validation fixtures.
- [x] Add Malaysian-vs-Singaporean ambiguity tests.
- [x] Add unsupported/unknown tests.
- [x] Add OCR-confusion tests that could change country classification.
- [x] Add explicit fail-safe behavior for ambiguous classification. (User confirmed reject on overlap.)
- [x] Do not query JPJ, LTA, VEP, or owner databases.
- [x] Do not claim pattern matching legally verifies vehicle nationality/ownership.

Sections A–C completed on 2026-10-02. Post-change verification: 89 backend tests (including 37 dedicated PostgreSQL integration), 34 ML tests, 43 frontend tests, and a frontend production build passed. The classifier is intentionally conservative: overlapping car-style `S` plates return `unknown`. Singaporean simulated deduction remains disabled until the separate V3 foreign-charge work in sections E–G and M is complete.

## D. Origin Classification Evaluation

- [x] Preserved OCR held-out set remains 44 crops.
- [x] PaddleOCR held-out exact-match result is documented as 37/44 (84.1%).
- [x] Development OCR result is documented as 125/146 (85.6%).
- [x] Positive development detector set has documented 0 false negatives on reviewed positive images.
- [x] False-positive rate is not claimed without labelled negatives.
- [x] Build a separate labelled origin-classification test fixture/set. (32 explicitly labelled synthetic text scenarios; no images or issued-registration claim.)
- [x] Measure MY -> MY correct classifications. (9/12; three safe unknown abstentions.)
- [x] Measure SG -> SG correct classifications. (8/12; four safe unknown abstentions.)
- [x] Measure MY -> SG confusions. (0/12.)
- [x] Measure SG -> MY confusions. (0/12.)
- [x] Measure unknown/ambiguous rejection correctness. (8/8 unsupported and 7/7 overlapping cases rejected with the expected reason.)
- [x] Keep origin-classification metrics separate from OCR exact-match metrics.
- [x] Do not tune using the preserved 44-crop held-out OCR set. (The evaluator reads only `ml/evaluation/origin/labels.csv`; manifest hash remains `b723d69850778f9a65d1a3db1bd386272aea80f7`.)
- [x] Do not invent Singaporean accuracy metrics before labelled data exists. (Report only the explicitly labelled synthetic-fixture result; no real-world or OCR accuracy claim.)

Section D completed on 2026-10-02. The synthetic-fixture exact-origin count is 25/32 (78.1%), with seven deliberate known-origin abstentions. The confusion matrix and per-case results are in `ml/evaluation/origin/results.json`; limitations are documented beside the fixture and in `docs/TESTING_EVALUATION.md`. The ML suite passes (35 tests), and the evaluator passes Ruff checks.

## E. Synthetic Singaporean Records

- [x] Synthetic users/accounts/vehicles exist.
- [x] Multiple synthetic account balances exist.
- [x] Wallet ledger exists.
- [x] Top-up/reversal/refund support exists.
- [x] Add fictional Singaporean-style synthetic vehicles.
- [x] Add synthetic accounts for Singaporean demo vehicles.
- [x] Add at least one successful Singaporean transaction scenario.
- [x] Add at least one insufficient-balance Singaporean scenario if useful.
- [x] Mark vehicle registration origin explicitly in data.
- [x] Ensure seed remains idempotent.
- [x] Ensure no real owner information is used.

## F. Foreign-Vehicle Charge

- [x] Add configurable simulated foreign-vehicle charge setting.
- [x] Do not embed the foreign charge inside congestion multipliers.
- [x] Persist dynamic toll component separately.
- [x] Persist foreign charge component separately.
- [x] Preserve/finalize `amount` semantics as final simulated total.
- [x] Malaysian accepted transaction -> foreign charge `0.00`.
- [x] Singaporean accepted transaction -> configured foreign charge.
- [x] Final total = dynamic toll + foreign charge.
- [x] Balance sufficiency check uses final total.
- [x] Wallet debit uses final total.
- [x] Payment notification uses final total.
- [x] Idempotent replay does not charge foreign amount twice.
- [x] Refund/reversal reverses the final debited total.
- [x] Failure records preserve consistent component values.
- [x] Unknown/unsupported origin cannot create successful deduction.
- [x] Keep all foreign charging clearly simulated.
- [x] If RM20 is seeded, label it as a configurable simulated demo value, not a real toll-plaza fee.

Sections E–F completed on 2026-10-02. Migration `20261002_0013` adds explicit vehicle origin, transaction components, and a separate persisted charge setting seeded at a clearly simulated RM20.00. Three fictional Singaporean vehicles/accounts are seeded idempotently, including a low-balance case. The payment, ledger, notification, replay, refund, API, and Simulator upload paths have PostgreSQL integration coverage; the full backend suite passed (96 tests). See `docs/FOREIGN_VEHICLE_CHARGE.md`.

## G. Database / Migration

- [x] PostgreSQL + SQLAlchemy + Alembic exist.
- [x] Location ownership exists for traffic/prices/detections/transactions.
- [x] `toll_locations.base_toll` exists.
- [x] `simulation_profile` exists.
- [x] Add a new V3 Alembic migration; do not rewrite old migrations. (`20261002_0013` follows origin migration `0012`.)
- [x] Add vehicle registration-origin field or equivalent.
- [x] Add detection plate-origin field or equivalent. (Completed in `0012`.)
- [x] Add transaction dynamic-toll component field.
- [x] Add transaction foreign-charge component field.
- [x] Add/configure foreign-charge setting source.
- [x] Backfill existing records safely. (Historical `amount` becomes dynamic toll; foreign charge stays zero.)
- [x] Verify downgrade behavior. (Verified against the dedicated test database.)
- [ ] Verify clean database and upgraded database converge to valid V3 state.
- [ ] Verify existing Simulator Toll Plaza records remain attached correctly.

## H. Flat-Rate Toll Scope

- [x] Current pricing already starts from per-location `base_toll`.
- [x] Current dynamic pricing already applies congestion-relative multipliers.
- [x] Current system does not require route-distance calculation.
- [ ] Make flat-rate-only scope explicit in current repository docs.
- [ ] Ensure no entry/exit-based charge calculation is introduced.
- [ ] Ensure no journey-distance calculation is introduced.
- [ ] Keep `dynamic toll = flat base toll × congestion multiplier`, subject to safeguards.
- [ ] Treat base toll values as prototype configuration unless explicitly sourced.

## I. Normal Simulated Toll Network

Current repository normal generated locations are still based on Penchala/LDP, DUKE, KESAS, and NPE.

Required V3 normal generated network:

- LDP
- AKLEH
- NPE
- Grand Saga

Tasks:

- [ ] Replace/align normal location `PENCHALA` with LDP network naming/model as required.
- [ ] Replace DUKE with AKLEH.
- [ ] Keep/update NPE.
- [ ] Replace KESAS with Grand Saga.
- [ ] Choose stable V3 location codes: `LDP`, `AKLEH`, `NPE`, `GRAND_SAGA`.
- [ ] Add/update display names.
- [ ] Add/update route labels.
- [ ] Add/update prototype map coordinates.
- [ ] Add/update road capacities.
- [ ] Add/update base toll configuration.
- [ ] Add/update independent traffic profiles.
- [ ] Add/update peak hours.
- [ ] Add/update speed profiles.
- [ ] Add/update variation parameters.
- [ ] Add migration/seed behavior for V3 locations.
- [ ] Decide safe handling of historical old-location records.
- [ ] Update backend location tests.
- [ ] Update scheduler/network simulation tests.
- [ ] Update frontend location fixtures.
- [ ] Update map route definitions.
- [ ] Update map marker tests.
- [ ] Update Prediction fixtures.
- [ ] Remove stale active references to DUKE/KESAS/Penchala from current V3 docs/UI/tests.

## J. Simulator Toll Plaza

- [x] Simulator Toll Plaza exists.
- [x] It is a separate special local-ALPR location.
- [x] Capacity is 10 active crossings.
- [x] Active congestion window is 60 seconds.
- [x] Webcam detections can affect Simulator congestion.
- [x] Uploaded images can affect Simulator congestion.
- [x] Generated network traffic excludes Simulator Toll Plaza.
- [x] Average speed is not fabricated.
- [x] Detection/payment history persists.
- [x] Raw images remain ephemeral.
- [x] Route Simulator Toll recognition through the new origin classifier.
- [x] Malaysian Simulator recognition follows normal toll charge.
- [x] Singaporean Simulator recognition receives separate simulated foreign charge.
- [x] Unknown origin fails safely.
- [ ] Verify 60-second congestion expiry is independent of charge nationality/origin.
- [ ] Regression-test webcam and uploaded-image paths after V3 changes.

## K. Traffic Simulation

- [x] Malaysia-time traffic simulation exists.
- [x] Percentage-first location traffic profiles exist.
- [x] Normal/Moderate/Peak Hour/Severe bands exist.
- [x] Per-location road capacity exists.
- [x] Per-location baseline demand exists.
- [x] Per-location peak behavior exists.
- [x] Per-location average-speed profile exists.
- [x] Deterministic testable variation exists.
- [x] Persisted traffic history exists.
- [x] Network generation excludes Simulator Toll Plaza.
- [ ] Retune/verify profiles for LDP, AKLEH, NPE, Grand Saga.
- [ ] Verify four V3 normal locations can show different congestion at the same Malaysia time.
- [ ] Verify new profiles still traverse useful pricing bands for demos.
- [ ] Verify no old V2 location is still generated after V3 migration.

## L. Dynamic Pricing

- [x] Four editable congestion bands exist.
- [x] Per-location base toll exists.
- [x] Minimum toll exists.
- [x] Maximum multiplier exists.
- [x] Minimum change interval exists.
- [x] Hysteresis exists.
- [x] Pricing explanation exists.
- [x] Pricing preview exists.
- [x] Pricing audit history exists.
- [x] Pricing remains rule-based, not ML.
- [x] Ensure foreign charge is applied only after the pricing decision.
- [ ] Ensure `Why this price?` explains congestion toll separately from foreign charge.
- [ ] Verify V3 location base tolls work with existing safeguards.
- [x] Verify foreign charge never changes congestion band/multiplier. (Payment adds it after reading the stored price.)

## M. Simulated Payment

- [x] Synthetic account lookup exists.
- [x] Successful payment exists.
- [x] Insufficient-balance handling exists.
- [x] Unknown-vehicle handling exists.
- [x] Idempotency exists.
- [x] Wallet ledger exists.
- [x] Top-up exists.
- [x] Refund/reversal exists.
- [x] Per-location revenue exists.
- [x] Simulated payment notifications exist.
- [x] Extend payment outcome/schema for charge breakdown.
- [x] Use origin-aware charge calculation.
- [x] Add combined-total balance test.
- [x] Add combined-total ledger test.
- [x] Add combined-total refund test.
- [x] Add foreign-charge idempotency test.

## N. Dashboard Navigation / Structure

- [x] Overview is a top-level page.
- [x] Dynamic Pricing Management is a top-level page.
- [x] Prediction is a top-level page.
- [x] Retired pages are not required as top-level navigation.
- [x] Model Performance is a compact modal.
- [x] Simulator Toll camera/upload is accessed from Overview.
- [ ] Do not reintroduce removed pages merely because older proposal wording mentions separate views.
- [ ] Satisfy proposal information requirements inside the current three-page design.

## O. Overview V3 Alignment

- [x] Network map exists.
- [x] All Locations view exists.
- [x] Selected-location metrics exist.
- [x] Recent detections exist.
- [x] Recent transactions exist.
- [x] Normal simulated live feed exists.
- [x] Simulator Toll presentation feedback exists.
- [x] Alerts/operational events exist.
- [ ] Map normal locations to LDP/AKLEH/NPE/Grand Saga.
- [ ] Show plate origin in recent detections where appropriate.
- [ ] Show foreign charge separately in Singaporean transactions.
- [ ] Show final simulated total.
- [ ] Keep Malaysian transaction rows compact when foreign charge is zero.
- [ ] Keep Simulator Toll local input buttons.
- [ ] Verify new charge fields do not break live feed rendering.

## P. Dynamic Pricing Management V3 Alignment

- [x] Congestion pricing controls exist.
- [x] Rule preview exists.
- [x] Pricing explanation exists.
- [x] History exists.
- [ ] Keep foreign charge concept visually separate from congestion bands.
- [ ] If admin-configurable foreign charge is surfaced here, place it in a distinct clearly labelled section.
- [ ] Never imply plate origin changes the congestion multiplier.
- [ ] Update location selector to LDP/AKLEH/NPE/Grand Saga.

## Q. Prediction

- [x] Prediction page exists.
- [x] Time-based traffic prediction exists.
- [x] Current-vs-future summary exists.
- [x] Location selector exists.
- [x] Start time exists.
- [x] Duration exists.
- [x] Playback speed exists.
- [x] Duration supports up to 12 hours.
- [x] Chart tooltip is themed.
- [x] Prediction remains isolated from live state.
- [x] Simulator Toll Plaza is excluded.
- [ ] Update Prediction normal-location options to LDP/AKLEH/NPE/Grand Saga.
- [ ] Verify midnight/date rollover after V3 location changes.
- [ ] Do not add foreign-vehicle charging to traffic prediction.

## R. Model Performance / Evaluation UI

- [x] Model Performance modal exists.
- [x] Modal has close behavior in current baseline.
- [x] Verified held-out/development evidence exists.
- [x] Known limitations are shown.
- [ ] Add origin-classification evidence only after V3 labelled evaluation exists.
- [ ] Clearly distinguish OCR accuracy from origin-classification accuracy.
- [ ] Keep unsupported metrics marked unavailable.
- [ ] Do not restore AI Intelligence page.

## S. Alerts / Operational Events

- [x] Severe congestion alerts exist.
- [x] Camera state alerts exist.
- [x] Repeated low-confidence alerts exist.
- [x] Repeated failed-payment alerts exist.
- [x] Backend/API/database operational events exist.
- [x] Acknowledgement/history exist.
- [ ] Decide whether repeated origin-classification failures warrant an informational/warning event.
- [ ] Do not create noisy per-detection alerts without evidence they improve the demo.

## T. Testing — Backend

- [x] Existing backend unit tests exist.
- [x] Existing PostgreSQL integration coverage exists.
- [ ] Unit-test origin classifier.
- [ ] Unit-test per-country charge behavior.
- [ ] Unit-test V3 flat-rate location validation.
- [ ] Integration-test plate-origin persistence.
- [ ] Integration-test foreign-charge persistence.
- [ ] Integration-test location-aware Singaporean transaction.
- [ ] Integration-test upgraded V3 migration.
- [ ] Re-run existing location/network aggregation tests.
- [ ] Re-run existing Simulator Toll tests.
- [ ] Re-run existing wallet/reversal tests.

## U. Testing — ML

- [x] ML test suite exists.
- [x] Malaysian normalization tests exist.
- [ ] Add Singaporean registration fixtures.
- [ ] Add origin-classification tests.
- [ ] Add ambiguity tests.
- [ ] Add cross-country OCR-confusion tests.
- [ ] Preserve held-out OCR set unchanged.

## V. Testing — Frontend

- [x] Frontend Vitest suite exists.
- [x] Production build command exists.
- [x] Location/map tests exist.
- [x] Prediction tests exist.
- [ ] Update expected normal toll network.
- [ ] Test origin display in detection.
- [ ] Test Singaporean charge breakdown.
- [ ] Test Malaysian no-foreign-charge case.
- [ ] Test V3 Prediction selector options.
- [ ] Test V3 map labels/routes.
- [ ] Confirm three-page navigation remains unchanged.
- [ ] Run `npm test`.
- [ ] Run `npm run build`.

## W. Accessibility / UX Regression

- [x] Visible focus work exists.
- [x] Keyboard navigation work exists.
- [x] Reduced-motion behavior exists.
- [x] Accessible alternative toll selection exists.
- [ ] Verify new origin labels are not colour-only.
- [ ] Verify charge breakdown is screen-reader readable.
- [ ] Verify map/location changes remain usable at presentation resolutions.
- [ ] Verify upload/camera result status remains readable.

## X. Documentation

- [~] README describes an older current-state network/page set and needs V3 alignment.
- [x] Setup documentation exists.
- [x] Testing/evaluation documentation exists.
- [x] Demo documentation exists.
- [ ] Update README to state MY + SG origin-classification scope.
- [ ] Update README to state flat-rate-only scope.
- [ ] Update README normal network to LDP/AKLEH/NPE/Grand Saga.
- [ ] Update setup/seed docs for Singaporean synthetic records and foreign charge.
- [ ] Update database/schema docs.
- [ ] Update API docs if response models gain origin/charge fields.
- [ ] Update testing/evaluation docs for origin classification.
- [ ] Update architecture diagram/documentation.
- [ ] Update demo flow to include one Malaysian and one Singaporean example.
- [ ] Keep explicit simulation/no-real-payment boundaries.
- [ ] Update `.harnessV3` status after implementation.

## Y. Final Capstone Demo Verification

- [ ] One-command local startup succeeds.
- [ ] Database migration reaches V3 head.
- [ ] Seed succeeds idempotently.
- [ ] Login succeeds.
- [ ] All Locations shows LDP/AKLEH/NPE/Grand Saga + separate Simulator Toll Plaza.
- [ ] Normal live feed uses only normal generated locations.
- [ ] Webcam still works.
- [ ] Image upload still works.
- [ ] Malaysian plate is classified correctly.
- [ ] Malaysian plate receives no foreign charge.
- [ ] Singaporean plate is classified correctly.
- [ ] Singaporean plate receives separate simulated foreign charge.
- [ ] Unknown/ambiguous origin fails safely.
- [ ] Simulator congestion updates and expires after 60 seconds.
- [ ] Dynamic pricing still responds to congestion.
- [ ] `Why this price?` remains accurate.
- [ ] Prediction remains isolated.
- [ ] Model Performance modal opens/closes.
- [ ] No real bank/eWallet/government integration exists.
- [ ] Final screenshots captured after V3 UI is stable.

## Z. Highest-Priority Next Tasks

1. [x] Add V3 schema migration for origin and charge components.
2. [x] Implement Malaysian/Singaporean/unknown origin classifier.
3. [x] Add Singaporean synthetic seed records.
4. [x] Implement separately itemized foreign-vehicle charge.
5. [ ] Align normal network to LDP/AKLEH/NPE/Grand Saga.
6. [ ] Update Overview transaction/detection display.
7. [ ] Update Prediction/map/location fixtures.
8. [ ] Add V3 unit/integration/frontend tests.
9. [ ] Update repository documentation.
10. [ ] Run final localhost capstone verification.
