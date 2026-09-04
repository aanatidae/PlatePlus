# High-Level Implementation Roadmap

## Current Baseline

Resolve the workspace root as the directory containing `.harness`; it is normally `D:/Capstone Project` on the user's PC and `C:/Capstone Project` on the user's laptop. Repository-relative paths are authoritative across both machines.

The repository is initialized and tracks `origin/main`. It contains the Malaysian car-plate dataset, a trained local YOLO car-plate model (Git-ignored), ML/OCR processing, FastAPI webcam endpoints, a React/TypeScript webcam UI, unit tests, and setup documentation.

Project Foundation, dataset preparation, the car-plate-only YOLO detector, PaddleOCR baseline, local webcam implementation, the backend/PostgreSQL persistence foundation, backend administrator login, protected dashboard login UI, simulated toll payment, and configurable traffic simulation/dynamic pricing are complete. The physical browser-webcam permission/inference verification is intentionally deferred and must not be run without explicit user approval. Dashboard expansion and end-to-end integration remain pending.

Testing and evaluation coverage is complete for the current prototype: focused plate-normalization, toll-payment, traffic, webcam, database/API, still-image end-to-end, and dashboard UI-contract tests are recorded in `docs/TESTING_EVALUATION.md`. The deployed login UI has also been visually checked. The physical browser-webcam verification remains intentionally deferred.

The administrator frontend uses a dark command-centre visual system: a responsive operations sidebar, top location/sync/status bar, dark teal operational surfaces, high-contrast traffic states, live telemetry KPIs, compact technical labels, a toll-flow visualization, and responsive data layouts. The Overview is exclusively backed by the read-only Malaysia-time live telemetry service and persisted ALPR/payment activity. Plate Recognition, Dynamic Toll Management, AI Intelligence, Simulator, and local-webcam routes remain protected. On the production dashboard, Plate Recognition clearly explains that raw-image ALPR remains local-only rather than presenting an unavailable upload control. AI Intelligence exposes its recognition gates, traffic-model mode/cadence, four-band pricing policy, Malaysia-time clock, and useful telemetry-recovery states instead of generic `N/A` values. The Simulator copies live values only as a baseline and calculates local sandbox state/history without writing live traffic, prices, or transactions.

## Phase 1: Repository And Project Foundation

- Source control, project layout, environment conventions, dependency manifests, and initial setup documentation are complete.
- Continue documenting launch, test, migration, and seed commands as the remaining implementation is introduced.
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

- The FastAPI persistence foundation, Docker-based development/test PostgreSQL configuration, separate users/accounts, UUID models, Alembic migration, synthetic seed data, and validated persistence routes are implemented.
- Development and test PostgreSQL containers are healthy; the migration, synthetic seed data, and PostgreSQL integration tests have been verified locally.
- Extend the existing persistence APIs with traffic simulation, dynamic pricing, dashboard statistics, and remaining integration workflows.

## Phase 5: Simulated Toll Payment

- Implemented automatic simulated payment for confidence-eligible webcam recognitions.
- Uses the latest stored toll price whose effective time is not in the future, an active registered vehicle, and its designated primary synthetic account.
- Safely records successful, failed, low-confidence, insufficient-balance, unknown-vehicle, and idempotent replay outcomes without duplicate deductions.

## Phase 6: Traffic Simulation And Dynamic Pricing

- The backend simulation is complete: persisted scheduler settings, editable four-band rules, a Malaysia-time profile, real-time simulated-clock support, deterministic seeded runs for tests, manual runs, audit history, PostgreSQL/API integration coverage, and a separate scheduler process are implemented. A predictor protocol keeps the simulation open to a future ML-based traffic model.
- Support normal, moderate, peak-hour, and severe congestion scenarios.
- Support deterministic simulation when a test seed is supplied.
- Calculate congestion percentage and category from simulated inputs.
- Store historical simulated traffic records.
- Implement configurable rule-based dynamic toll pricing.
- Keep the architecture open for future ML-based congestion prediction.

## Phase 7: Admin Dashboard

- Build a responsive administrator-only web dashboard.
- The dashboard login uses the seeded demo admin account and redirects unauthenticated or expired sessions to `/login`.
- The administrator overview now has read-only real-time telemetry from a Malaysia-time traffic generator, including current congestion, vehicle flow, live toll/base/multiplier, ALPR activity, payment count, recognition confidence, and operational status. The local sandbox at `/simulator` is independent and never writes to live records; the former standalone Traffic Analytics route has been removed from the frontend.
- Responsive browser verification passed at desktop, tablet, and mobile viewport sizes for the overview and traffic-administration pages.
- Prepare the final dashboard for Vercel deployment. Document its API configuration and preserve the local-only webcam/inference boundary unless a separately approved architecture changes it.
- The Vercel SPA configuration, explicit free-tier Render Blueprint, CORS configuration, production webcam feature flag, and deployment runbook are deployed and verified. The Blueprint explicitly selects the free web plan and omits the paid continuous scheduler; administrators use the existing manual simulation action in `/traffic`. Its API startup command normalizes Render's PostgreSQL URL, applies migrations, and idempotently seeds the synthetic demo data, so it does not require paid Render shell/one-off-job access. Render-style PostgreSQL URLs are normalized for both the application and Alembic. The remote API excludes the local webcam router so it does not require local ALPR/OCR code or model files. The Vercel production dashboard at `https://capstone-alpr-dashboard.vercel.app` has verified direct dashboard and traffic routes; Render CORS is configured for that origin.
- Display current congestion, congestion category, current toll price, vehicles detected today, transaction counts, simulated revenue, average recognition confidence, recent detections, and recent transactions.
- Add traffic congestion and toll price charts.
- Add filtering for date/time, congestion category, license plate, transaction status, registered/unknown status, and toll price where useful.
- Clearly label financial and traffic data as simulated.

## Phase 8: Integration

- Webcam-frame ingestion is already connected through YOLO detection, plate cropping, PaddleOCR, normalization, confidence gates, preview overlays, and per-session cooldown handling.
- Still-image upload is connected to the local recognition pipeline and runs YOLO detection, PaddleOCR, confidence gates, vehicle lookup, simulated payment, persistence, and dashboard refresh without retaining source image bytes. It is administrator-authenticated and remains unavailable from the remote production API along with local webcam inference.
- The PostgreSQL automated upload-to-payment end-to-end test passes. Live still-image inference was verified locally with the existing YOLO artifact and PaddleOCR cache: detection, OCR, vehicle matching, a simulated RM2.00 payment, persistence, and idempotent replay all succeeded without downloading additional assets.
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
- Prepare and document the Vercel deployment path for the final administrator dashboard.
- Document setup from a clean machine.
- Document PostgreSQL configuration and seed credentials.
- Document how to transfer the local model artifact, enable this laptop's webcam, run local inference, and use dashboard workflows.
- Document privacy, security, ethical limitations, and simulated-only scope.
- Capture screenshots or demo evidence if needed for final submission.
