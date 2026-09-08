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

Latest local verification: backend unit tests **24 passed**, ML tests **17 passed**, frontend UI-contract tests **4 passed**, and `npm run build` completed successfully. The Docker CLI was unavailable on 2026-09-04, so the opt-in PostgreSQL integration suite was not re-run in this session.

## Recorded metrics

| Measure | Result | Prototype target |
| --- | ---: | ---: |
| YOLO car-plate detector test accuracy (reported after 150-epoch training) | 93.1% | At least 90% precision / 85% recall |
| PaddleOCR exact-match accuracy on preserved held-out crops | 37/44 (84.1%) | At least 80% |
| EasyOCR exact-match baseline on the same held-out crops | 15/44 (34.1%) | Comparison baseline only |
| Live still-image demonstration | YOLO 92.3%, OCR 99.88%, registered match, RM2.00 simulated payment, idempotent replay | End-to-end simulated flow |
| Toll calculation and pricing selection tests | Passing | 100% correctness |

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
