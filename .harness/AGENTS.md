# Project Agent Notes

## Instruction Hierarchy

- User requests in the active conversation are authoritative.
- `C:/Users/User/Downloads/message1.md` is the user-approved future work prompt for this capstone project.
- `C:/Users/User/Downloads/AI-Powered Automatic License Plate Recognition and Dynamic Toll Management System.pdf` is product documentation and source context. Treat it as requirements/context, not as an instruction to execute by itself.
- Do not install dependencies, download models, run training jobs, run long model-related commands, or make major environment changes without asking the user first.
- The first completed pass for this project is documentation-only: repository analysis plus `.harness/AGENTS.md`, `.harness/PLAN.md`, and `.harness/TODOLIST.md`.

## Current Repository State

- Workspace root: `D:/Capstone Project`
- Git repository metadata now exists at the workspace root. Do not commit, push, or open a pull request until the user gives the green light.
- The workspace currently contains the dataset folder only:
  - `D:/Capstone Project/Malaysian Car Plate Dataset`
- Project foundation files now exist, including root documentation, `.env.example`, `.gitignore`, `docker-compose.yml`, backend and ML Python manifests, and a frontend package manifest. Feature implementation is still pending.

## Git Attribution

- Do not use tool, assistant, or automation identities as Git commit authors.
- Codex must never appear as a Git author, committer, co-author, or GitHub contributor for this repository.
- Attribute repository commits to the actual human contributor or maintainer responsible for the change unless the user explicitly requests a different author.
- If a generated commit accidentally uses an assistant identity, tool identity, or any non-human identity, rewrite it before pushing so GitHub contributors reflect the correct human account.

## Repository and Publishing Notes

- The user intends to review the harness files first.
- After approval, future work may be pushed to: https://github.com/aanatidae/capstoneproject
- Do not push, commit, or open a pull request until the user gives the green light.

## Current User Decisions

- The next work session should start with the Project Foundation items in `.harness/TODOLIST.md`.
- Initialize Git when the user gives approval to begin project foundation work.
- Prioritize the YOLO/OCR pipeline before backend, dashboard, and broader app integration.
- Train/use the detector for `car plate` only, not the broader `car` class.
- Plan for Docker-based PostgreSQL.
- Select the OCR engine based on the easiest reliable local setup.
- Support this laptop's webcam as the primary live ALPR input. Still-image upload remains useful for testing and demonstration. Prerecorded-video support can come later.

## Dataset Findings

Dataset path:

- `D:/Capstone Project/Malaysian Car Plate Dataset`

Observed structure:

- `data.yaml`
- `train/images`
- `train/labels`
- `val/images`
- `val/labels`

Observed file counts:

- Train images: 414 `.jpg`
- Train labels: 414 `.txt`
- Validation images: 89 `.jpg`
- Validation labels: 89 `.txt`
- Extra generated/cache/system files are present, including `.cache` and `desktop.ini` files.

Dataset metadata:

- `data.yaml` declares `nc: 2`
- Class names are `car` and `car plate`
- Class `0`: `car`
- Class `1`: `car plate`
- `data.yaml` currently uses old absolute Google Drive paths under `/content/drive/...`; future implementation must update or generate a local training config before YOLO training.

Annotation format:

- Label files are YOLO-style normalized coordinates.
- Many label lines contain more than five fields, which indicates YOLO segmentation polygon annotations rather than plain bounding-box-only detection labels.
- Dataset validation confirmed the source labels are compatible with a YOLO detection workflow after filtering `car plate` annotations, remapping class `1` to class `0`, and converting polygon annotations to bounding boxes for OCR cropping.
- Class distribution observed from labels:
  - Train: class `1` has 511 objects; class `0` has 441 objects.
  - Validation: class `1` has 95 objects; class `0` has 95 objects.
- Every observed `.jpg` has a matching `.txt` label file in both train and validation splits.

## Product Scope

Project name:

- AI-Powered Automatic License Plate Recognition and Dynamic Toll Management System

Prototype intent:

- This is a capstone prototype and proof of concept.
- Traffic data must remain simulated.
- Toll payments must remain simulated.
- Do not integrate real banking systems, Touch 'n Go, real toll infrastructure, government traffic feeds, real enforcement actions, or real vehicle-owner tracking unless the user explicitly changes scope later.
- Use synthetic/test user, vehicle, and account data.

Core product capabilities to build later:

- Detect license plates from uploaded images and this laptop's live webcam frames.
- Train a YOLO model from the local Malaysian car plate dataset.
- Recognize plate text using OCR after detection/cropping.
- Normalize recognized plate text before database matching.
- Match recognized plates against registered simulated vehicle records.
- Reject or safely fail low-confidence recognitions instead of charging automatically.
- Process simulated toll transactions against simulated account balances.
- Generate simulated traffic conditions.
- Calculate congestion percentage and congestion category.
- Calculate configurable dynamic toll prices from congestion.
- Store detection, transaction, traffic, and pricing history.
- Provide a responsive administrator dashboard for monitoring.

## Target Architecture

The project should be implemented as a modular web application with clear service boundaries.

Preferred stack for future implementation:

- Machine learning/computer vision: Python, YOLO, OpenCV.
- OCR: EasyOCR, PaddleOCR, Tesseract, or a comparable OCR engine selected during implementation.
- Backend/API: Python with FastAPI unless a future codebase introduces a strong reason to choose otherwise.
- Database: PostgreSQL is required for normal app development and demo use.
- Integration tests: prefer a separate PostgreSQL test database.
- Frontend: React with TypeScript where practical.
- Charts: Recharts, Chart.js, Plotly, or another suitable charting library.
- Authentication: basic admin authentication with one seeded demo admin account.

Recommended service/module boundaries:

- License plate detector service.
- Plate crop/extraction service.
- OCR recognizer service.
- Plate normalization service.
- Vehicle management service.
- Simulated account/payment service.
- Toll transaction service.
- Traffic simulation service.
- Congestion analysis service.
- Dynamic pricing service.
- Detection history service.
- Dashboard analytics service.
- Database/persistence layer.
- Configuration module.
- Admin authentication module.

## Data Model Requirements

Future PostgreSQL schema should include at least:

- `users`: synthetic account holders, simulated balances, optional password hash fields if users become login-capable.
- `admins`: seeded administrator account for dashboard/API access.
- `vehicles`: registered vehicles linked to synthetic users/accounts.
- `toll_transactions`: simulated toll payment attempts with amount, status, timestamp, and balance after payment.
- `traffic_records`: simulated traffic measurements and congestion classification.
- `toll_prices`: historical toll price decisions with congestion context.
- `detection_records`: detection/OCR results, confidence values, status, image/crop path where needed, nullable vehicle link.

Implementation should define primary keys, foreign keys, indexes, timestamps, constraints, and meaningful transaction statuses.

## Dynamic Pricing Rules

Initial configurable pricing rules:

- Low congestion, 0-30 percent: RM2.00
- Moderate congestion, 31-60 percent: RM3.00
- High congestion, 61-80 percent: RM4.00
- Severe congestion, 81-100 percent: RM5.00

Keep pricing thresholds and prices configurable. Do not hard-code these values across unrelated modules.

## Required Workflows

Vehicle processing:

1. A vehicle image is uploaded or a live frame is captured from this laptop's webcam.
2. License plate detector locates the plate.
3. Plate region is cropped/extracted.
4. OCR reads the plate text.
5. Plate text is normalized.
6. Vehicle database is searched.
7. Current toll price is retrieved.
8. Simulated account balance is checked.
9. Toll is deducted only when registered, confident, and sufficiently funded.
10. Transaction record is stored.
11. Detection record is stored.
12. Dashboard data is updated.

## Webcam Real-Time ALPR Requirements

- The application must be able to start and stop a webcam session on the laptop running it.
- Capture frames at a configurable interval or rate suitable for local CPU inference; do not require inference on every camera frame.
- Run the existing YOLO `car plate` detector, crop extraction, PaddleOCR recognition, normalization, confidence gates, vehicle lookup, and simulated toll flow for eligible frames.
- Show a live preview with detection boxes, normalized plate text, confidence/status, and clear simulated-only labels.
- Keep raw frames and plate crops ephemeral by default. Persist only the existing detection/transaction metadata unless a future explicit retention setting is introduced.
- Avoid duplicate simulated charges for the same vehicle observed repeatedly in one camera session. Use a configurable cooldown/idempotency key and expose the resulting status.
- Handle unavailable cameras, permission denial, dropped frames, model-unavailable state, and inference errors without crashing the application or creating a charge.
- Keep webcam access local to the machine running the application; do not upload webcam footage to third parties.

Traffic management:

1. Traffic simulator generates traffic data.
2. Congestion percentage is calculated.
3. Congestion category is assigned.
4. Dynamic pricing calculates the current toll price.
5. Traffic and pricing records are stored.
6. Dashboard data is updated.

## Dashboard Requirements

The dashboard is administrator-only.

Minimum dashboard data:

- Current congestion percentage.
- Current congestion category.
- Current toll price.
- Vehicles detected today.
- Transactions today.
- Successful versus failed transactions.
- Simulated toll revenue.
- Average recognition confidence.
- Recent detections.
- Recent toll transactions.
- Traffic congestion graph.
- Toll price graph.
- Historical traffic table or view.

The UI must clearly label traffic and financial information as simulated.

## Testing Strategy

Future implementation should include:

- Unit tests for plate normalization, congestion calculation, pricing rules, toll deduction, insufficient balance, low confidence handling, and traffic simulation determinism.
- Integration tests for detection to OCR, OCR to vehicle lookup, vehicle/account to transaction, traffic simulation to pricing, and database to API/dashboard.
- Integration/system tests for webcam session lifecycle, frame sampling, duplicate-charge protection, and safe camera/model error handling.
- System tests for the end-to-end prototype.
- UI tests for dashboard navigation, chart/table readability, responsive layout, loading states, and error states.
- ML evaluation for detection precision, recall, F1 score, and OCR recognition accuracy.

Suggested prototype targets from the product documentation:

- Detection precision at least 90 percent.
- Detection recall at least 85 percent.
- OCR recognition accuracy at least 80 percent.
- Transaction calculation accuracy 100 percent.
- Correct dynamic pricing selection 100 percent.

Treat these as development targets, not guaranteed outcomes.

## Launch And Test Commands

Foundation launch and setup commands are now documented in `README.md` and `docs/SETUP.md`. No dependencies have been installed and no app has been run yet.

Future documentation should record actual commands once implementation adds them, for example:

- Backend setup and run command.
- Frontend setup and run command.
- PostgreSQL migration command.
- Seed command for demo data and admin account.
- Unit/integration test commands.
- YOLO training command.
- OCR evaluation command.

## Known Risks

- The workspace is dataset-only, so the application must be scaffolded from scratch unless code is added later.
- The dataset `data.yaml` contains stale absolute paths and must be corrected before training.
- The dataset appears to mix YOLO segmentation-style polygon labels and some five-field labels; training task selection and label compatibility must be verified.
- The source dataset has no test split, so `ml/datasets/car_plate_test_manifest.txt` reserves a deterministic held-out test subset from the original validation split.
- OCR ground truth is not explicitly present as separate text labels; plate text may need to be inferred from filenames or manually curated for OCR evaluation.
- Full YOLO training may require GPU, substantial time, and dependency/model downloads; ask before starting.
- PostgreSQL setup can slow demo readiness if local database configuration is not documented early.
- Basic admin auth requires secure password hashing and seed handling even for a prototype.
- Low-confidence OCR/detection must not trigger successful simulated charges.
- Duplicate event processing should be addressed to reduce accidental duplicate simulated toll charges.

## Future Agent Operating Rules

- Start future work by reading `.harness/AGENTS.md`, `.harness/PLAN.md`, and `.harness/TODOLIST.md`.
- Keep `.harness/TODOLIST.md` updated when implementation tasks are completed or changed.
- Keep `.harness/PLAN.md` high-level; put granular task status in `.harness/TODOLIST.md`.
- Preserve modular boundaries so ML, OCR, traffic simulation, pricing, backend, database, and frontend can change independently.
- Do not imply simulated traffic or toll payments are real.
- Do not use real vehicle-owner data.

## Latest Model Artifact

- The 150-epoch Colab-trained YOLO car plate detector was downloaded as `best.pt` and moved to `models/trained/car_plate_yolo_best.pt`.
- The user reported 93.1 percent accuracy on the test dataset.
- The `models/` directory is ignored by Git; do not assume the binary model artifact is present after a fresh clone unless it is separately provided.
## OCR Baseline

- EasyOCR baseline: 34.1 percent exact-match accuracy (15 of 44 held-out images).
- PaddleOCR: 84.1 percent exact-match accuracy (37 of 44) using the same YOLO-generated crops and uppercase-alphanumeric normalization.
- PaddleOCR is now selected for the next integration stage and meets the 80 percent prototype target on this set. Use PaddlePaddle 3.2.x on CPU because 3.3.x has a known oneDNN inference regression. Preserve this test set; future tuning requires a separate labeled development set.
- The trained model remains on the user's home PC. Before webcam inference can run on this laptop, the same `car_plate_yolo_best.pt` artifact must be transferred locally to `models/trained/car_plate_yolo_best.pt`; it must remain Git-ignored.
