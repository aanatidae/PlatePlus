# Implementation Checklist

Resolve the workspace root as the directory containing `.harness`; it is normally `D:/Capstone Project` on the user's PC and `C:/Capstone Project` on the user's laptop. Use repository-relative paths in implementation and documentation wherever practical.

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

- [x] Ask user whether to initialize Git.
- [x] Create source layout for backend, frontend, ML, scripts, tests, and docs.
- [x] Add root project README.
- [x] Add environment variable template.
- [x] Add dependency manifests after selecting exact tooling.
- [x] Document setup commands after manifests exist.

## Dataset And YOLO

- [x] Clean or ignore generated files such as `desktop.ini` and label cache files.
- [x] Fix or generate a local YOLO `data.yaml`.
- [x] Verify whether labels should be trained as YOLO detection boxes or segmentation polygons.
- [x] Decide whether to train both `car` and `car plate` classes or only `car plate`.
- [x] Create or reserve an independent test split.
- [x] Add dataset validation script.
- [x] Add training configuration.
- [x] Ask user before installing ML dependencies or downloading base weights.
- [x] Train YOLO model from the Malaysian dataset.
- [x] Evaluate detection precision, recall, and F1 score.
- [x] Export trained model for inference.

## OCR And Plate Processing

- [x] Decide OCR engine selection criteria.
- [x] Select OCR engine.
- [x] Ask user before installing OCR dependencies.
- [x] Implement plate crop extraction from YOLO detections.
- [x] Implement OCR recognizer service.
- [x] Implement Malaysian plate text normalization.
- [x] Define detection and OCR confidence thresholds.
- [x] Prevent low-confidence recognition from successful automatic charging.
- [x] Create OCR ground truth strategy, likely from filenames plus manual correction.
- [x] Evaluate OCR recognition accuracy.

## Local Webcam Real-Time ALPR

- [x] Decide and document the webcam capture approach for this laptop: browser Camera API preview with sampled local FastAPI frame processing.
- [x] Implement webcam permission, start, stop, and camera-unavailable handling.
- [x] Implement configurable frame sampling/rate limiting and bounded frame processing.
- [x] Connect sampled webcam frames to YOLO detection, crop extraction, PaddleOCR, normalization, and confidence gates.
- [x] Display a live preview with detection boxes, recognized plate, confidence, and simulated-only status.
- [x] Keep raw frames and crops ephemeral by default.
- [x] Implement per-session duplicate recognition/charge cooldown protection; database transaction idempotency remains a later toll-payment responsibility.
- [x] Handle missing model artifact and inference failures without recording a successful charge.
- [x] Add webcam lifecycle, frame-processing, duplicate-protection, and failure-state tests (17 ML tests and 6 backend webcam tests passing).
- [x] Document model transfer and webcam setup for this laptop.
- [!] Final physical browser-webcam permission/inference verification is deferred by user instruction; do not run it without explicit approval.

## Backend And Database

- [x] Scaffold FastAPI backend.
- [x] Decide PostgreSQL deployment approach.
- [x] Configure Docker-based PostgreSQL for normal development and demo use.
- [x] Configure separate PostgreSQL test database for integration tests.
- [x] Add database migration tooling.
- [x] Create admin model/table.
- [x] Create separate users and accounts models/tables using UUID identifiers.
- [x] Create vehicles model/table.
- [x] Create toll transactions model/table with an idempotency key.
- [x] Create traffic records model/table.
- [x] Create toll prices model/table.
- [x] Create detection records model/table.
- [x] Add idempotent seed script for synthetic data and one demo admin account; password setup remains part of authentication.
- [x] Add validated persistence APIs with meaningful 404, 409, and 422 responses.

## Basic Admin Authentication

- [x] Implement seeded admin login.
- [x] Hash seeded admin password securely.
- [ ] Protect admin dashboard routes.
- [x] Protect privileged API routes.
- [x] Document demo credentials in the appropriate local-only setup place.

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

- [x] Scaffold React/TypeScript frontend.
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
- [x] Connect webcam frame ingestion to YOLO inference.
- [x] Connect YOLO detection to plate crop extraction.
- [x] Connect crop extraction to OCR.
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
- [x] Record ML detection metrics.
- [x] Record OCR accuracy metrics.
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
