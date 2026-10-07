# Testing and Evaluation

This prototype is a simulated-only ALPR and dynamic-toll system. The figures below describe the evaluated local prototype; they do not establish performance for production tolling, enforcement, or real-world vehicle identification.

## Automated coverage

Run each Python suite from its own project directory because both projects contain a `tests` package.

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests\unit -q

cd ..\ml
..\backend\.venv\Scripts\python.exe -m pytest tests -q

cd ..\frontend
npm test
npm run build
```

The backend unit suite covers account deduction, insufficient-balance rejection, low-confidence charge eligibility, traffic simulation, schemas, authentication, and webcam processing. The ML suite covers plate normalization, crop extraction, OCR behavior, confidence gates, webcam-session cooldowns, and safe failure cases. PostgreSQL integration tests and the authenticated still-image-to-payment system test remain opt-in because they reset the dedicated temporary test database; run the commands in `SETUP.md` after starting `postgres_test`.

The frontend Vitest contract suite checks protected route availability, user-visible loading/error/simulation messaging, primary accessibility labels, and the CSS tablet/mobile/reduced-motion rules. It is complemented by visual verification of the deployed login screen; dashboard content still requires an administrator session and an available API.

Historical verification on 2026-09-04: backend unit tests **24 passed**, ML tests **17 passed**, frontend UI-contract tests **4 passed**, and `npm run build` completed successfully. The Docker CLI was unavailable then, so PostgreSQL integration tests were not rerun in that session.

G/H verification on 2026-10-06: **125 backend tests passed** (73 unit, 52 PostgreSQL
integration), using only the dedicated `capstone_alpr_test` database after approved
Docker/test-service startup. New migration scenarios cover fresh/V2-upgraded schema
and seed convergence, repeated seeding, populated V3 downgrade/re-upgrade, and preserved
Simulator history for both webcam and image-upload sources. Four new flat-rate pricing
cases verify location base × congestion multiplier without journey/entry/exit/distance
inputs; existing floor, cap, interval, hysteresis, payment, and foreign-charge regressions
also passed. Ruff passed for the migration test/shared fixture. This verification did
not run physical webcam inference, retrain models, or change the development database.
See [migration verification](V3_DATABASE_MIGRATIONS.md) and [flat-rate scope](FLAT_RATE_SCOPE.md).

## Recorded metrics

| Measure | Result | Prototype target |
| --- | ---: | ---: |
| YOLO car-plate detector test accuracy (reported after 150-epoch training) | 93.1% | At least 90% precision / 85% recall |
| PaddleOCR exact-match accuracy on preserved held-out crops | 37/44 (84.1%) | At least 80% |
| EasyOCR exact-match baseline on the same held-out crops | 15/44 (34.1%) | Comparison baseline only |
| Live still-image demonstration | YOLO 92.3%, OCR 99.88%, registered match, RM2.00 simulated payment, idempotent replay | End-to-end simulated flow |
| Toll calculation and pricing selection tests | Passing | 100% correctness |

## V3 plate-origin pattern evaluation

The V3 classifier was evaluated separately on [32 labelled synthetic text cases](../ml/evaluation/origin/README.md). This is a deterministic policy check on normalized plate text; it does not run YOLO or PaddleOCR and does not reuse the protected 44-crop OCR held-out set. The fixture labels describe simulated Malaysian, Singaporean, and unsupported scenarios rather than verified issued registrations.

| Reference origin | Classified Malaysian | Classified Singaporean | Rejected as unknown |
| --- | ---: | ---: | ---: |
| Malaysian | 9 | 0 | 3 |
| Singaporean | 0 | 8 | 4 |
| Unknown/unsupported | 0 | 0 | 8 |

Exact origin labels were **25/32 (78.1%)** on this deliberately selected synthetic fixture. MY-to-SG and SG-to-MY confusions were **0** each. The classifier correctly rejected **7/7 overlapping** and **8/8 unsupported** examples. Seven known-origin inputs were rejected because their text shapes overlap. The fixture is small and enriched with overlap cases, so the percentage is not a field-accuracy estimate. No Singaporean image/OCR evaluation or human-verified origin set exists yet. See `ml/evaluation/origin/results.json` for per-case decisions.

The origin result is independent of PaddleOCR's **37/44 held-out exact-match** and **125/146 development exact-match** results; none of these numbers should be combined into a single accuracy claim.

## Development-set robustness evaluation

The separate development protocol processed 150 manually reviewed, non-held-out
images (138 training and 12 validation images). Of those, 146 are reviewed
single-target, OCR-scorable positives with human-verifiable text; four are
explicitly non-scorable challenging scenes (one damaged/partially obstructed
plate and two multi-plate wall-rack scenes). They are excluded from OCR and
detector positive/negative rates. The preserved 44-crop held-out set was not
read or modified.

| Development OCR measure | Result | Interpretation |
| --- | ---: | --- |
| Overall exact match | 125/146 (85.6%) | Development-only; do not present as final unbiased accuracy. |
| Clear | 93/111 (83.8%) | Large but condition labels may overlap. |
| Angled | 30/31 (96.8%) | Development-only. |
| Low light | 14/16 (87.5%) | Development-only. |
| Small or distant | 12/15 (80.0%) | Development-only. |
| Glare/overexposure | 4/7 (57.1%) | Small sample; priority area for further review. |
| Partial obstruction | 1/1 (100.0%) | Insufficient sample size for a conclusion. |

Detector output found a plate in all 146 positive detector-evaluation images
(146 true positives, 0 false negatives). There were no human-labelled negative
images, so the measured false-positive rate is unavailable; the displayed
precision/recall/F1 values of 1.0 are positive-only development results, not a
general detector-performance claim.

## Limitations and known failure cases

- All traffic, owners, accounts, pricing, and payments are synthetic; the system must not be connected to payment networks, government data, or enforcement workflows.
- The local model artifact is Git-ignored and must be supplied separately after a fresh clone. Local inference also depends on installed YOLO/PaddleOCR assets.
- OCR evaluation has only 44 preserved held-out crops. It is useful as a prototype benchmark, not as a broad generalization claim; further tuning needs a separate labeled development set.
- Plate plausibility validation rejects common malformed OCR strings before simulated charging. Controlled character correction is limited to a single unambiguous Malaysian-format candidate; ambiguous OCR is retained without substitution and fails safely.
- Condition-specific recognition accuracy, false-positive rate, and false-negative rate are not yet reported because they require independently human-labelled development/evaluation samples. The repository provides an isolated development-set manifest and condition-breakdown workflow; do not infer these values from live operational records.
- The source dataset mixes polygon and box-style labels, and has no original test split. The project reserves a deterministic subset from the supplied validation data.
- Low detection/OCR confidence, no usable normalized plate, unknown/disabled vehicles, missing toll prices, unavailable primary accounts, insufficient balances, duplicate idempotency keys, invalid images, missing weights, and inference errors all fail safely without a successful charge.
- Browser webcam permission and physical-camera inference have intentionally not been re-verified in this work. That explicit hardware test remains deferred.
- The deployed dashboard is administrator-only and excludes local webcam/image inference. Its external API and database availability are platform-dependent; the free Render deployment does not run the continuous scheduler.
- Frontend UI checks include rendered deployed login verification and automated source contracts for responsive rules; a full authenticated browser end-to-end suite remains a future enhancement.


## V3 normal network verification - 2026-10-07

Section I aligns the normal network to LDP/AKLEH/NPE/Grand Saga. Verification passed:
127 backend tests (73 unit, 54 dedicated PostgreSQL integration), 35 ML tests, 60
frontend tests, production build, new migration/test Ruff checks, and diff checks.
The existing frontend chunk-size warning remains. Migration tests preserve original
normal-highway detection ownership, retain Simulator links, compare fresh/upgraded
schema and idempotent seed, verify downgrade/re-upgrade and safe populated rollback
refusal. API/scheduler tests exclude retired history from live aggregates and keep
generated traffic off Simulator. Daily profile tests verify distinct Malaysia-time
congestion, useful pricing bands, deterministic variation and congestion-related
speed. Frontend tests verify V3 map routes/markers, Prediction options and date
rollover, and unchanged three-page navigation. The local demo database reached
`20261007_0014` without changing migration-time counts (1 traffic record, 40 prices,
673 detections, 673 transactions); repeated seed succeeded. Browser preview was
unavailable because the frontend service was not running. Physical webcam
verification was not run. No new model-accuracy claim is made.


## V3 Simulator, pricing, and navigation - 2026-10-07

J/L/N verification passed: 143 backend tests (74 unit, 69 dedicated PostgreSQL),
35 ML tests, 80 frontend tests, and production build. The existing bundle-size
warning remains. New endpoint tests exercise real local sessions, PostgreSQL,
origin/payment, and telemetry services with controlled inference output; no camera
hardware, model download, training, or physical inference is performed.

Both sources verify Malaysian and Singaporean success, Singaporean insufficient
funds, unknown-origin rejection, origin-independent expiry at exactly 60 seconds,
read-only history retention, and shared cooldown/idempotency without extra records.
The rolling window excludes future timestamps and reports a fresh derived state
separately from its last historical crossing. Four V3 bases are checked with floor,
cap, minimum interval, and hysteresis. Simulator band/multiplier agrees when held.

Frontend behavioral tests verify stored decimal-string components, separate foreign
charge and final/attempted totals, compact zero-foreign-charge rows, origin labels,
upload rendering and preview clearing, modal close/focus, three-page navigation
and retired-route redirects. Pricing history loads only when expanded, uses
Malaysia-date/location filters, does not retain old-scope data, and never writes.
Daily congestion/toll history has a table alternative to its chart. Origin evidence
is explicitly synthetic-text-only and separate from OCR; the positive detector
review denominator is corrected to 146 scorable images. After final small telemetry
and audit-empty-state changes, 14 Simulator/window tests and two history tests passed.
See [behavior and verification](V3_SIMULATOR_PRICING_NAVIGATION.md).
