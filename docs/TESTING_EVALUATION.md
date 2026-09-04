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

## Limitations and known failure cases

- All traffic, owners, accounts, pricing, and payments are synthetic; the system must not be connected to payment networks, government data, or enforcement workflows.
- The local model artifact is Git-ignored and must be supplied separately after a fresh clone. Local inference also depends on installed YOLO/PaddleOCR assets.
- OCR evaluation has only 44 preserved held-out crops. It is useful as a prototype benchmark, not as a broad generalization claim; further tuning needs a separate labeled development set.
- The source dataset mixes polygon and box-style labels, and has no original test split. The project reserves a deterministic subset from the supplied validation data.
- Low detection/OCR confidence, no usable normalized plate, unknown/disabled vehicles, missing toll prices, unavailable primary accounts, insufficient balances, duplicate idempotency keys, invalid images, missing weights, and inference errors all fail safely without a successful charge.
- Browser webcam permission and physical-camera inference have intentionally not been re-verified in this work. That explicit hardware test remains deferred.
- The deployed dashboard is administrator-only and excludes local webcam/image inference. Its external API and database availability are platform-dependent; the free Render deployment does not run the continuous scheduler.
- Frontend UI checks include rendered deployed login verification and automated source contracts for responsive rules; a full authenticated browser end-to-end suite remains a future enhancement.
