# High-Level Implementation Roadmap

## Current Baseline

The workspace currently contains the selected dataset only. There is no existing backend, frontend, database schema, test suite, launch script, or Git repository metadata at the workspace root.

The project now has a completed ML/OCR baseline, a local webcam implementation, and initial FastAPI/React application surfaces. Database-backed business workflows and the broader administrator dashboard remain pending.

## Phase 1: Repository And Project Foundation

- Establish source control when the user gives approval to begin project foundation work.
- Create a clear project structure for backend, frontend, ML, scripts, tests, and documentation.
- Add environment configuration conventions.
- Document setup, launch, test, migration, and seed commands as they are introduced.
- Keep all real toll/payment/traffic integrations out of scope.

## Phase 2: Dataset Preparation And YOLO Training

- Validate the `Malaysian Car Plate Dataset` annotations.
- Decide whether the YOLO task is detection or segmentation based on annotation compatibility and product needs.
- Focus the detector on the `car plate` class only for the first prototype.
- Generate a local YOLO data configuration with workspace-relative paths.
- Create or reserve a true test split because the current dataset has only train and validation splits.
- Train a YOLO model from the Malaysian dataset after user approval for dependencies/downloads/training.
- Evaluate detection precision, recall, and F1 score.
- Export the trained model for application inference.

## Phase 3: License Plate Recognition Pipeline And Local Webcam

- The local webcam implementation uses a browser preview and a FastAPI endpoint for sampled JPEG frames; prerecorded-video support remains deferred.
- The live path includes start/stop lifecycle control, configurable sampling, bounded frame upload, YOLO detection, crop extraction, PaddleOCR, normalization, confidence gates, preview overlay, and simulated-only status.
- Frames and crops remain ephemeral by default. Camera permission/device errors, unavailable model weights, frame-size limits, and inference errors fail safely without a charge-eligible result.
- A per-session cooldown prevents repeated accepted plate recognitions. Database-level transaction idempotency remains part of the later simulated toll-payment phase.
- Complete the final physical browser-camera test once the retained permission prompt is accepted; all code-level and automated checks have passed.

## Phase 4: Backend And PostgreSQL

- Build a FastAPI backend unless future constraints justify another backend.
- Set up Docker-based PostgreSQL as the required normal development and demo database.
- Prefer a separate PostgreSQL test database for integration tests.
- Create database models and migrations for admins, users/accounts, vehicles, transactions, traffic records, toll prices, and detection records.
- Seed synthetic users, registered vehicles, balances, and one demo admin account.
- Expose API boundaries for vehicle lookup, detection processing, payment simulation, traffic simulation, dynamic pricing, dashboard statistics, and historical records.

## Phase 5: Simulated Toll Payment

- Retrieve the current toll price.
- Match recognized plates to registered simulated vehicles.
- Retrieve associated synthetic accounts.
- Check account balance.
- Deduct the simulated toll only when recognition confidence, registration status, and balance checks pass.
- Store successful, failed, low-confidence, insufficient-balance, and unknown-vehicle outcomes clearly.
- Add safeguards against accidental duplicate event processing.

## Phase 6: Traffic Simulation And Dynamic Pricing

- Implement a first-class traffic simulation module.
- Support normal, moderate, peak-hour, and severe congestion scenarios.
- Support deterministic simulation when a test seed is supplied.
- Calculate congestion percentage and category from simulated inputs.
- Store historical simulated traffic records.
- Implement configurable rule-based dynamic toll pricing.
- Keep the architecture open for future ML-based congestion prediction.

## Phase 7: Admin Dashboard

- Build a responsive administrator-only web dashboard.
- Add login using the seeded demo admin account.
- Display current congestion, congestion category, current toll price, vehicles detected today, transaction counts, simulated revenue, average recognition confidence, recent detections, and recent transactions.
- Add traffic congestion and toll price charts.
- Add filtering for date/time, congestion category, license plate, transaction status, registered/unknown status, and toll price where useful.
- Clearly label financial and traffic data as simulated.

## Phase 8: Integration

- Connect still-image upload and webcam-frame ingestion to detection, OCR, vehicle lookup, simulated payment, detection records, and dashboard updates.
- Connect traffic simulation to congestion calculation, dynamic pricing, pricing records, and dashboard updates.
- Ensure service boundaries allow detector, OCR engine, traffic simulator, pricing algorithm, backend, database, and frontend to be replaced independently.

## Phase 9: Testing And Evaluation

- Add focused unit tests for business logic and data normalization.
- Add integration tests using a PostgreSQL test database.
- Add end-to-end system tests for the main demo flow.
- Add webcam lifecycle and frame-processing tests, including duplicate-charge prevention and failure states.
- Add UI tests for dashboard usability and responsiveness.
- Evaluate ML detection metrics on held-out images.
- Evaluate OCR accuracy using curated ground truth.
- Record limitations, metrics, and known failure cases for the capstone report/demo.

## Phase 10: Demo Hardening And Documentation

- Prepare a reliable local demo path.
- Document setup from a clean machine.
- Document PostgreSQL configuration and seed credentials.
- Document how to transfer the local model artifact, enable this laptop's webcam, run local inference, and use dashboard workflows.
- Document privacy, security, ethical limitations, and simulated-only scope.
- Capture screenshots or demo evidence if needed for final submission.
