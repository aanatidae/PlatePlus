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
- [x] Verify clean database and upgraded database converge to valid V3 state. (Fresh head+seed versus populated V2 `0011` upgraded to `0013`+seed; schema, fleet/wallets, locations/profiles, charge setting, ledger count, and repeated seed compared.)
- [x] Verify existing Simulator Toll Plaza records remain attached correctly. (Both `webcam_alpr` and `uploaded_image`: original IDs, location, traffic/price/detection/transaction/vehicle links, timestamp, source, amount and origin/component backfills preserved.)

Section G completed on 2026-10-06 after user-approved Docker Desktop/test-container startup. Both dedicated migration scenarios passed, including populated V3-to-V2 downgrade/re-upgrade. The full backend suite passed: 125 tests (73 unit, 52 PostgreSQL integration). Fixture target guard rejects development databases; full disposable-schema reset clears test rows before older network downgrades to avoid RESTRICT foreign-key failures. Historical migrations and development data remain unchanged. Ruff for the migration test/shared fixture and `git diff --check` passed. See `docs/V3_DATABASE_MIGRATIONS.md`.

## H. Flat-Rate Toll Scope

- [x] Current pricing already starts from per-location `base_toll`.
- [x] Current dynamic pricing already applies congestion-relative multipliers.
- [x] Current system does not require route-distance calculation.
- [x] Make flat-rate-only scope explicit in current repository docs. (README, architecture, and `docs/FLAT_RATE_SCOPE.md`.)
- [x] Ensure no entry/exit-based charge calculation is introduced. (Pricing/payment input paths reviewed; each crossing uses one location's stored price.)
- [x] Ensure no journey-distance calculation is introduced. (No distance/journey inputs in pricing/payment; map metadata is not a pricing input.)
- [x] Keep `dynamic toll = flat base toll × congestion multiplier`, subject to safeguards. (Four new location-relative formula cases plus existing floor/cap/interval/hysteresis tests passed.)
- [x] Treat base toll values as prototype configuration unless explicitly sourced. (Explicitly documented for seeded and example rates.)

Section H completed on 2026-10-06. All 73 backend unit tests passed. Flat-rate documentation distinguishes the current normal network from the pending section I target; no network migration, entry/exit tracking, distance charging, physical webcam test, or dependency installation was introduced.

## I. Normal Simulated Toll Network

Current normal generated locations are LDP, AKLEH, NPE, and Grand Saga. DUKE/KESAS are retired historical entries; Simulator Toll Plaza remains separate.

Required V3 normal generated network:

- LDP
- AKLEH
- NPE
- Grand Saga

Tasks:

- [x] Replace/align normal location `PENCHALA` with LDP network naming/model as required.
- [x] Replace DUKE with AKLEH.
- [x] Keep/update NPE.
- [x] Replace KESAS with Grand Saga.
- [x] Choose stable V3 location codes: `LDP`, `AKLEH`, `NPE`, `GRAND_SAGA`.
- [x] Add/update display names.
- [x] Add/update route labels.
- [x] Add/update prototype map coordinates.
- [x] Add/update road capacities.
- [x] Add/update base toll configuration.
- [x] Add/update independent traffic profiles.
- [x] Add/update peak hours.
- [x] Add/update speed profiles.
- [x] Add/update variation parameters.
- [x] Add migration/seed behavior for V3 locations.
- [x] Decide safe handling of historical old-location records.
- [x] Update backend location tests.
- [x] Update scheduler/network simulation tests.
- [x] Update frontend location fixtures.
- [x] Update map route definitions.
- [x] Update map marker tests.
- [x] Update Prediction fixtures.
- [x] Remove stale active references to DUKE/KESAS/Penchala from current V3 docs/UI/tests.

Section I completed on 2026-10-07. Migration `20261007_0014` retains the existing LDP/Penchala ID and configuration, retires DUKE/KESAS without transferring history, and creates independent AKLEH/Grand Saga IDs with prototype metadata, rates, capacities, and traffic profiles. Current location lists, network aggregates, alerts evaluation, demo generation/reset, pricing propagation, map routes/markers, and Prediction exclude retired locations. Historical metadata/data APIs remain queryable by original IDs. Populated new-highway rollback is safely refused by RESTRICT foreign keys. Fresh/upgraded seed convergence, downgrade/re-upgrade, history retention, four-road scheduling, independent daily pricing-band/speed profiles, map and Prediction regressions passed. Verification: 127 backend tests (73 unit, 54 dedicated PostgreSQL integration), 35 ML tests, 60 frontend tests, production build, new-file Ruff, and diff checks passed. Existing build-size warning remains. Local demo database upgraded to `0014`; pre/post migration counts remained 1 traffic record, 40 prices, 673 detections, and 673 transactions; repeated seed succeeded. The browser preview was unavailable because the frontend was not running; no physical webcam check, dependency installation, commit, push, or deployment was performed. See `docs/MULTI_LOCATION.md` and `docs/V3_DATABASE_MIGRATIONS.md`.

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
- [x] Verify 60-second congestion expiry is independent of charge nationality/origin.
- [x] Regression-test webcam and uploaded-image paths after V3 changes.

Section J completed on 2026-10-07. The active window is now (now - 60 seconds, now], excluding future records and expiring exactly at 60 seconds. Malaysian/Singaporean accepted crossings, including insufficient-balance outcomes, expire identically for webcam and upload; unknown origin never creates an active crossing or debit. Derived telemetry stays fresh while last_crossing_at retains history. Shared source/session cooldown suppresses duplicates without failure-record noise, and idempotent replay skips extra traffic/price creation. PostgreSQL endpoint regressions use the real session/API/payment/telemetry path with controlled inference output; raw input retention remains off. Physical webcam verification was not requested or performed. Verification for J/L/N: 143 backend tests (74 unit, 69 dedicated PostgreSQL), 35 ML tests, 80 frontend tests and production build passed; existing bundle-size warning remains. Final targeted Simulator/window (14) and pricing-history (2) regressions passed after small follow-ups. No dependency/model installation, physical camera test, commit, push, or deployment. See `docs/V3_SIMULATOR_PRICING_NAVIGATION.md`.

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
- [x] Retune/verify profiles for LDP, AKLEH, NPE, Grand Saga. (Section I, 2026-10-07.)
- [x] Verify four V3 normal locations can show different congestion at the same Malaysia time. (Section I, 2026-10-07.)
- [x] Verify new profiles still traverse useful pricing bands for demos. (Section I, 2026-10-07.)
- [x] Verify no old V2 location is still generated after V3 migration. (Section I, 2026-10-07.)

## L. Dynamic Pricing

- [x] Four editable congestion bands exist.
- [x] Verify hundredth-based band editing and persistence (2026-10-06): 0–30, 30.01–60, 60.01–80, 80.01–100; decimal multipliers; readable validation errors; browser save/reload and PostgreSQL round-trip passed. Existing cap, interval and hysteresis regressions pass.
- [x] Verify immediate policy propagation (2026-10-06): save atomically appends per-location current TollPrice records using existing congestion; policy context bypasses traffic interval/hysteresis holds but preserves price limits. Normal feed and future payments use new prices; historical records remain unchanged. Simulator reads actual rolling crossings without creating traffic. Browser Overview/live-feed smoke test and PostgreSQL regressions passed; 119 backend tests and 59 frontend tests passed, production build passed.
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
- [x] Ensure `Why this price?` explains congestion toll separately from foreign charge.
- [x] Verify V3 location base tolls work with existing safeguards.
- [x] Verify foreign charge never changes congestion band/multiplier. (Payment adds it after reading the stored price.)

Section L completed on 2026-10-07. Why this price? explicitly describes the congestion toll independently of the separately configured transaction-only foreign charge. Stored component breakdowns show final or attempted totals without recalculation. Tests exercise each actual V3 location base with floor/cap/interval/hysteresis. Simulator reports its held/applied band consistently with its multiplier. The existing Pricing page now exposes expandable read-only recorded congestion/toll history and network policy audit, with Malaysia-date/category/location scope, bounded records, a chart/table alternative, and empty/error states. Verification for J/L/N: 143 backend tests (74 unit, 69 dedicated PostgreSQL), 35 ML tests, 80 frontend tests and production build passed; existing bundle-size warning remains. Final targeted Simulator/window (14) and pricing-history (2) regressions passed after small follow-ups. No dependency/model installation, physical camera test, commit, push, or deployment. See `docs/V3_SIMULATOR_PRICING_NAVIGATION.md`.

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
- [x] Do not reintroduce removed pages merely because older proposal wording mentions separate views.
- [x] Satisfy proposal information requirements inside the current three-page design.

Section N completed on 2026-10-07. Exactly Overview, Dynamic Pricing Management and Prediction remain in navigation; behavioral tests confirm navigation, retired-route redirects and modal close/focus. Proposal information is contextual: Overview detections show origin patterns/reasons, transaction and camera/upload results show separate stored foreign charge and total, Pricing contains read-only historical congestion/tolls and policy audit, and Model Performance separates OCR from synthetic-text origin evidence and active thresholds. Corrected positive detector review to 146 scorable images. No retired page or new sidebar destination was introduced. Verification for J/L/N: 143 backend tests (74 unit, 69 dedicated PostgreSQL), 35 ML tests, 80 frontend tests and production build passed; existing bundle-size warning remains. Final targeted Simulator/window (14) and pricing-history (2) regressions passed after small follow-ups. No dependency/model installation, physical camera test, commit, push, or deployment. See `docs/V3_SIMULATOR_PRICING_NAVIGATION.md`.

## O. Overview V3 Alignment

- [x] Network map exists.
- [x] All Locations view exists.
- [x] Selected-location metrics exist.
- [x] Recent detections exist.
- [x] Recent transactions exist.
- [x] Normal simulated live feed exists.
- [x] Simulator Toll presentation feedback exists.
- [x] Alerts/operational events exist.
- [x] Map normal locations to LDP/AKLEH/NPE/Grand Saga. (Section I, 2026-10-07.)
- [x] Show plate origin in recent detections where appropriate. (J/L/N, 2026-10-07.)
- [x] Show foreign charge separately in Singaporean transactions. (J/L/N, 2026-10-07.)
- [x] Show final simulated total. (J/L/N, 2026-10-07.)
- [x] Keep Malaysian transaction rows compact when foreign charge is zero. (J/L/N, 2026-10-07.)
- [x] Keep Simulator Toll local input buttons. (J/L/N, 2026-10-07.)
- [x] Verify new charge fields do not break live feed rendering. (J/L/N, 2026-10-07.)

## P. Dynamic Pricing Management V3 Alignment

- [x] Congestion pricing controls exist.
- [x] Rule preview exists.
- [x] Pricing explanation exists.
- [x] History exists.
- [x] Keep foreign charge concept visually separate from congestion bands. (J/L/N, 2026-10-07.)
- [x] If admin-configurable foreign charge is surfaced here, place it in a distinct clearly labelled section. (Dedicated expandable setting section, authenticated existing API; frontend verification passed on 2026-10-07.)
- [x] Never imply plate origin changes the congestion multiplier. (J/L/N, 2026-10-07.)
- [x] Update location selector to LDP/AKLEH/NPE/Grand Saga. (Section I, 2026-10-07.)

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
- [x] Update Prediction normal-location options to LDP/AKLEH/NPE/Grand Saga. (Section I, 2026-10-07.)
- [x] Verify midnight/date rollover after V3 location changes. (Section I, 2026-10-07.)
- [x] Do not add foreign-vehicle charging to traffic prediction. (All four V3 frame sequences are identical with/without origin/foreign-charge fields; Malaysia-time default and midnight/year rollover verified on 2026-10-07.)

## R. Model Performance / Evaluation UI

- [x] Model Performance modal exists.
- [x] Modal has close behavior in current baseline.
- [x] Verified held-out/development evidence exists.
- [x] Known limitations are shown.
- [x] Add origin-classification evidence only after V3 labelled evaluation exists. (J/L/N, 2026-10-07.)
- [x] Clearly distinguish OCR accuracy from origin-classification accuracy. (J/L/N, 2026-10-07.)
- [x] Keep unsupported metrics marked unavailable. (J/L/N, 2026-10-07.)
- [x] Do not restore AI Intelligence page. (J/L/N, 2026-10-07.)

## S. Alerts / Operational Events

- [x] Severe congestion alerts exist.
- [x] Camera state alerts exist.
- [x] Repeated low-confidence alerts exist.
- [x] Repeated failed-payment alerts exist.
- [x] Backend/API/database operational events exist.
- [x] Acknowledgement/history exist.
- [~] Decide whether repeated origin-classification failures warrant an informational/warning event. (Implemented decision: reuse the existing per-location rejected-recognition rollup with an origin-rejection count, no separate per-detection alert; PostgreSQL verification pending test-service startup approval.)
- [~] Do not create noisy per-detection alerts without evidence they improve the demo. (Stable location/type incident, bounded lifecycle events, and recovered-incident UI filtering implemented; PostgreSQL verification pending.)

P/Q/S work in progress on 2026-10-07: separate foreign-charge configuration, fee-independent Prediction with correct Malaysia default time, and coalesced origin-aware operational rollups are implemented. Frontend 89 tests, backend unit 74 tests, ML 35 tests, build, relevant Ruff and diff checks pass. PostgreSQL containers are stopped; the user has been asked for permission to start only `postgres_test` under AGENTS.md service-start rules. Do not claim integration completion before it runs. See `docs/V3_PRICING_PREDICTION_ALERTS.md`.

## T. Testing — Backend

- [x] Existing backend unit tests exist.
- [x] Existing PostgreSQL integration coverage exists.
- [x] Unit-test origin classifier.
- [x] Unit-test per-country charge behavior.
- [x] Unit-test V3 flat-rate location validation.
- [x] Integration-test plate-origin persistence.
- [x] Integration-test foreign-charge persistence.
- [x] Integration-test location-aware Singaporean transaction.
- [x] Integration-test upgraded V3 migration.
- [x] Re-run existing location/network aggregation tests. (J/L/N, 2026-10-07.)
- [x] Re-run existing Simulator Toll tests. (J/L/N, 2026-10-07.)
- [x] Re-run existing wallet/reversal tests. (J/L/N, 2026-10-07.)

## U. Testing — ML

- [x] ML test suite exists.
- [x] Malaysian normalization tests exist.
- [x] Add Singaporean registration fixtures.
- [x] Add origin-classification tests.
- [x] Add ambiguity tests.
- [x] Add cross-country OCR-confusion tests.
- [x] Preserve held-out OCR set unchanged.

## V. Testing — Frontend

- [x] Frontend Vitest suite exists.
- [x] Production build command exists.
- [x] Location/map tests exist.
- [x] Prediction tests exist.
- [x] Update expected normal toll network.
- [x] Test origin display in detection. (J/L/N, 2026-10-07.)
- [x] Test Singaporean charge breakdown. (J/L/N, 2026-10-07.)
- [x] Test Malaysian no-foreign-charge case. (J/L/N, 2026-10-07.)
- [x] Test V3 Prediction selector options.
- [x] Test V3 map labels/routes.
- [x] Confirm three-page navigation remains unchanged. (J/L/N, 2026-10-07.)
- [x] Run `npm test`. (J/L/N, 2026-10-07.)
- [x] Run `npm run build`. (J/L/N, 2026-10-07.)

Sections T/U/V completed on 2026-10-07. Reviewed existing coverage and added backend country-payment unit tests, four-location Singaporean payment/API isolation regressions, ML normalization and protected-held-out-manifest regressions, and rendered V3 Prediction selector coverage with exact map labels. Verification: 160 backend tests (82 unit, 78 dedicated PostgreSQL integration), 40 ML tests, 90 frontend tests in 16 files, production build, changed-test Ruff and diff checks passed. Existing bundle-size warning remains. User approved starting only postgres_test; development data was not targeted. This full run also verifies previously pending P/Q/S integration cases. No physical webcam test, dependencies/models, commit, push or deployment. See `docs/V3_TESTING_COMPLETION.md`.

## W. Accessibility / UX Regression

- [x] Visible focus work exists.
- [x] Keyboard navigation work exists.
- [x] Reduced-motion behavior exists.
- [x] Accessible alternative toll selection exists.
- [x] Verify new origin labels are not colour-only. (J/L/N, 2026-10-07.)
- [x] Verify charge breakdown is screen-reader readable. (J/L/N, 2026-10-07.)
- [x] Verify map/location changes remain usable at presentation resolutions.
- [x] Verify upload/camera result status remains readable.

## X. Documentation

- [x] README describes the V3 network, three-page structure, origin/charge surfaces, and linked history/evidence documentation. (I/J/L/N, 2026-10-07.)
- [x] Setup documentation exists.
- [x] Testing/evaluation documentation exists.
- [x] Demo documentation exists.
- [x] Update README to state MY + SG origin-classification scope.
- [x] Update README to state flat-rate-only scope.
- [x] Update README normal network to LDP/AKLEH/NPE/Grand Saga. (Section I, 2026-10-07.)
- [x] Update setup/seed docs for Singaporean synthetic records and foreign charge.
- [x] Update database/schema docs.
- [x] Update API docs if response models gain origin/charge fields.
- [x] Update testing/evaluation docs for origin classification.
- [x] Update architecture diagram/documentation.
- [x] Update demo flow to include one Malaysian and one Singaporean example. (J/L/N, 2026-10-07.)
- [x] Keep explicit simulation/no-real-payment boundaries.
- [x] Update `.harnessV3` status after implementation. (J/L/N, 2026-10-07.)

Sections W/X completed on 2026-10-07. Browser regressions at 1280x720, 1366x768, 1920x1080, 1024x768, 390x844 and 960x540 verify contained/non-overlapping map markers, keyboard-only location selection, readable uploaded-image results and keyboard-scrollable camera charge totals using a synthetic canvas stream and intercepted API responses. Fixed compact marker clipping/overlap, wrapped upload messages, added full shared recognition messages and bounded/focusable camera results. No physical webcam permission/inference or database writes. Updated README, setup/seed examples, architecture diagram, schema/API references, evaluation and demo guidance; preserved simulation and metric boundaries. Frontend 94 tests, production build, script syntax, relative-documentation links and diff checks passed; existing bundle-size warning remains. Local screenshots/results are ignored evidence in .plateplus-demo/qa-w. User approved frontend startup; final section Y remains separate. See `docs/V3_ACCESSIBILITY_DOCUMENTATION.md`.

## Y. Final Capstone Demo Verification

- [x] One-command local startup succeeds.
- [x] Database migration reaches V3 head. (`20261007_0014`.)
- [x] Seed succeeds idempotently. (Repeat seed preserved all counts and wallet balances.)
- [x] Login succeeds. (Actual local administrator browser sign-in.)
- [x] All Locations shows LDP/AKLEH/NPE/Grand Saga + separate Simulator Toll Plaza.
- [x] Normal live feed uses only normal generated locations.
- [ ] Webcam still works. **Physical camera explicitly deferred by the user on 2026-10-07: “Leave physical webcam verification pending.”** Real local session/frame API inference with a fictional PNG passed; this does not verify hardware capture.
- [x] Image upload still works. (Actual YOLO/PaddleOCR API and real browser file chooser/upload.)
- [x] Malaysian plate is classified correctly. (Fictional optical fixture VAA1234.)
- [x] Malaysian plate receives no foreign charge. (Successful RM2.00; zero foreign charge.)
- [x] Singaporean plate is classified correctly. (Fictional optical fixtures GBC6427R, YN4821R, XD7316E.)
- [x] Singaporean plate receives separate simulated foreign charge. (RM2.00 + RM20.00 = RM22.00, stored ledger and actual UI.)
- [x] Unknown/ambiguous origin fails safely. (SBA1234A: unknown, no successful deduction; unsupported cases covered by ML/backend regressions.)
- [x] Simulator congestion updates and expires after 60 seconds. (Four accepted crossings / 40%; zero after 63 real seconds, preserved last-crossing history.)
- [x] Dynamic pricing still responds to congestion. (Actual saved four-location decisions and AKLEH browser preview; existing safeguard regressions passed.)
- [x] `Why this price?` remains accurate. (Actual configured values; foreign charge kept separate.)
- [x] Prediction remains isolated. (12-hour browser run across midnight completed at frame 145; all database counts and wallets unchanged.)
- [x] Model Performance modal opens/closes. (Verified evidence; Escape close.)
- [x] No real bank/eWallet/government integration exists. (Runtime code/dependency review; synthetic records and local inference only.)
- [x] Final screenshots captured after V3 UI is stable. (Ignored `.plateplus-demo/qa-y/` evidence.)

Section Y verification completed on 2026-10-07 **except the user-deferred physical webcam item**. Actual optical outcomes, ledger/replay protection, shared input cooldown and real-time Simulator expiry passed. Real browser checks verify upload charge breakdowns, pricing, Model Performance and a complete 12-hour midnight-rollover forecast; database snapshots prove Prediction isolation. Fixed compact top-bar overflow between desktop/mobile breakpoints and verified 843px, 1366x768 and 390x844 layouts. Backend 160, ML 40, frontend 94 tests and production build passed; new script Ruff/syntax checks passed. No settings/history reset, dependencies/models, training, commit, push or deployment. Feed remains paused and local API/frontend/PostgreSQL remain available. Cold inference warm-up and existing stale persisted LDP traffic/scheduler state are documented honestly. See `docs/V3_FINAL_DEMO_VERIFICATION.md` and `scripts/verify_v3_local_demo.py`.

## Z. Highest-Priority Next Tasks

1. [x] Add V3 schema migration for origin and charge components.
2. [x] Implement Malaysian/Singaporean/unknown origin classifier.
3. [x] Add Singaporean synthetic seed records.
4. [x] Implement separately itemized foreign-vehicle charge.
5. [x] Align normal network to LDP/AKLEH/NPE/Grand Saga.
6. [x] Update Overview transaction/detection display. (J/L/N, 2026-10-07.)
7. [x] Update Prediction/map/location fixtures. (Section I, 2026-10-07.)
8. [x] Add V3 unit/integration/frontend tests. (T/U/V verified 2026-10-07.)
9. [x] Update repository documentation. (W/X verified 2026-10-07.)
10. [x] Run final localhost capstone verification. (2026-10-07: all authorized non-hardware checks completed; physical webcam remains explicitly deferred in Y.)
