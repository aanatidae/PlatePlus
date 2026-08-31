# Implementation Checklist

Status legend:

- `[x]` Complete
- `[~]` In progress
- `[ ]` Pending
- `[!]` Blocked or needs user decision

## Documentation And Analysis

- [x] Read and distinguish `message1.md` from the product PDF.
- [x] Confirm first work session scope is documentation-only.
- [x] Analyze workspace root contents.
- [x] Confirm the workspace is not currently a Git repository.
- [x] Confirm no application code, package manifests, tests, launch scripts, or migrations exist yet.
- [x] Inspect `Malaysian Car Plate Dataset` structure.
- [x] Inspect dataset metadata and label format.
- [x] Record launch/test command status.
- [x] Create `.harness/AGENTS.md`.
- [x] Create `.harness/PLAN.md`.
- [x] Create `.harness/TODOLIST.md`.

## Project Foundation

- [ ] Ask user whether to initialize Git.
- [ ] Create source layout for backend, frontend, ML, scripts, tests, and docs.
- [ ] Add root project README.
- [ ] Add environment variable template.
- [ ] Add dependency manifests after selecting exact tooling.
- [ ] Document setup commands after manifests exist.

## Dataset And YOLO

- [ ] Clean or ignore generated files such as `desktop.ini` and label cache files.
- [ ] Fix or generate a local YOLO `data.yaml`.
- [ ] Verify whether labels should be trained as YOLO detection boxes or segmentation polygons.
- [ ] Decide whether to train both `car` and `car plate` classes or only `car plate`.
- [ ] Create or reserve an independent test split.
- [ ] Add dataset validation script.
- [ ] Add training configuration.
- [ ] Ask user before installing ML dependencies or downloading base weights.
- [ ] Train YOLO model from the Malaysian dataset.
- [ ] Evaluate detection precision, recall, and F1 score.
- [ ] Export trained model for inference.

## OCR And Plate Processing

- [ ] Select OCR engine.
- [ ] Ask user before installing OCR dependencies.
- [ ] Implement plate crop extraction from YOLO detections.
- [ ] Implement OCR recognizer service.
- [ ] Implement Malaysian plate text normalization.
- [ ] Define detection and OCR confidence thresholds.
- [ ] Prevent low-confidence recognition from successful automatic charging.
- [ ] Create OCR ground truth strategy, likely from filenames plus manual correction.
- [ ] Evaluate OCR recognition accuracy.

## Backend And Database

- [ ] Scaffold FastAPI backend.
- [ ] Configure PostgreSQL for normal development and demo use.
- [ ] Configure separate PostgreSQL test database for integration tests.
- [ ] Add database migration tooling.
- [ ] Create admin model/table.
- [ ] Create users/accounts model/table.
- [ ] Create vehicles model/table.
- [ ] Create toll transactions model/table.
- [ ] Create traffic records model/table.
- [ ] Create toll prices model/table.
- [ ] Create detection records model/table.
- [ ] Add seed script for synthetic data and one demo admin account.
- [ ] Add API validation and meaningful error responses.

## Basic Admin Authentication

- [ ] Implement seeded admin login.
- [ ] Hash seeded admin password securely.
- [ ] Protect admin dashboard routes.
- [ ] Protect privileged API routes.
- [ ] Document demo credentials in the appropriate local-only setup place.

## Simulated Toll Payment

- [ ] Implement registered vehicle lookup by normalized plate.
- [ ] Implement simulated account retrieval.
- [ ] Implement toll price retrieval.
- [ ] Implement sufficient-balance check.
- [ ] Implement simulated balance deduction.
- [ ] Record successful transactions.
- [ ] Record failed transactions.
- [ ] Record unknown vehicle detections.
- [ ] Record recognition-failed detections.
- [ ] Add duplicate processing protection.

## Traffic Simulation And Pricing

- [ ] Implement traffic scenarios: normal, moderate, peak hour, severe congestion.
- [ ] Support simulated time.
- [ ] Add randomized variation.
- [ ] Support deterministic seeded simulation for tests.
- [ ] Calculate congestion percentage.
- [ ] Classify congestion level.
- [ ] Implement configurable dynamic pricing rules.
- [ ] Store traffic records.
- [ ] Store toll price records.
- [ ] Leave extension point for future ML-based traffic prediction.

## Admin Dashboard

- [ ] Scaffold React/TypeScript frontend.
- [ ] Build admin login view.
- [ ] Build current metrics view.
- [ ] Build congestion chart.
- [ ] Build toll price chart.
- [ ] Build recent detections table.
- [ ] Build recent transactions table.
- [ ] Build historical traffic view.
- [ ] Add filters for date/time, congestion category, plate, transaction status, registered/unknown status, and toll price where useful.
- [ ] Clearly label traffic and financial values as simulated.
- [ ] Verify responsive layout.

## Integration

- [ ] Connect image upload to YOLO inference.
- [ ] Connect YOLO detection to plate crop extraction.
- [ ] Connect crop extraction to OCR.
- [ ] Connect OCR to vehicle lookup.
- [ ] Connect vehicle lookup to simulated payment.
- [ ] Connect payment and detection outcomes to persistence.
- [ ] Connect traffic simulation to dynamic pricing.
- [ ] Connect backend APIs to dashboard.
- [ ] Verify complete end-to-end demo flow.

## Testing And Evaluation

- [ ] Add unit tests for plate normalization.
- [ ] Add unit tests for congestion calculation.
- [ ] Add unit tests for dynamic pricing.
- [ ] Add unit tests for account balance deduction.
- [ ] Add unit tests for insufficient balance handling.
- [ ] Add unit tests for low-confidence handling.
- [ ] Add unit tests for deterministic traffic simulation.
- [ ] Add PostgreSQL integration tests for database/API workflows.
- [ ] Add end-to-end system test for the main toll event.
- [ ] Add UI tests for dashboard readability and responsive behavior.
- [ ] Record ML detection metrics.
- [ ] Record OCR accuracy metrics.
- [ ] Record known limitations and failure cases.

## Documentation And Demo

- [ ] Document all launch commands.
- [ ] Document all test commands.
- [ ] Document PostgreSQL setup.
- [ ] Document seed/admin setup.
- [ ] Document YOLO training and inference commands.
- [ ] Document OCR evaluation workflow.
- [ ] Document simulated-only scope and exclusions.
- [ ] Prepare final capstone demo flow.
