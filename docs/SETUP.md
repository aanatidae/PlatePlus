# Local Setup and Operations

These are the current local commands for the prototype. Installing dependencies, downloading OCR assets, training models, starting Docker, and granting browser-camera permission can change the local environment; do those actions only with approval.

## Environment

1. Copy `.env.example` to `.env`.
2. Set non-default `DEMO_ADMIN_PASSWORD` and `AUTH_TOKEN_SECRET` values before any shared demonstration.
3. Keep `ENABLE_LOCAL_WEBCAM=true` only on a local operator machine. The deployed dashboard uses `false`.

## PostgreSQL

The project uses Docker-based PostgreSQL for development and a separate temporary PostgreSQL service for integration tests.

```bash
docker compose up -d postgres postgres_test
```

The normal development database listens on port `5432`. The test database listens on port `5433` and uses temporary storage.

After installing backend dependencies, apply the schema and seed synthetic demo data:

```powershell
cd backend
alembic upgrade head
python -m app.db.seed
```

The seed is idempotent. It creates only synthetic users, separate MYR accounts, Malaysian-style vehicle records, one initial traffic/price decision, and a password-hashed demo administrator. Use the `DEMO_ADMIN_EMAIL` and `DEMO_ADMIN_PASSWORD` values from your untracked `.env` to sign in to the dashboard or `POST /api/auth/login`.

Run PostgreSQL API integration tests against only the temporary test database:

```powershell
cd backend
$env:RUN_POSTGRES_TESTS="1"
pytest tests/integration/test_database_api.py tests/integration/test_toll_payment.py tests/integration/test_traffic_api.py
```

Do not point `RUN_POSTGRES_TESTS` at the development database: the integration fixture migrates and resets the dedicated temporary test database.

## Simulated Traffic And Pricing

The traffic scheduler and its prices are synthetic-only. Administrators can configure its schedule, selected scenario mode, and an advancing simulated Malaysia-time clock through `/api/traffic/settings`. The four contiguous pricing bands are editable through `/api/traffic/pricing-rules`; every configuration change and manual run is written to the audit log.

To generate scheduled records, run this alongside the API after applying migrations:

```powershell
cd backend
python -m app.traffic_scheduler
```

## Launch the local application

The backend manifest is in `backend/pyproject.toml`:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
uvicorn app.main:app --reload
```

## Frontend

The frontend manifest is in `frontend/package.json`:

```bash
cd frontend
npm install
npm run dev
```

## ML Pipeline

YOLO and PaddleOCR dependencies are intentionally separated because their first use can download assets. Transfer the trained model to `models/trained/car_plate_yolo_best.pt` without adding it to Git. See [COLAB_TRAINING.md](COLAB_TRAINING.md) for training and [OCR_PLATE_PROCESSING.md](OCR_PLATE_PROCESSING.md) for OCR evaluation.

## Local Webcam ALPR

The webcam runs in the browser on the same laptop as the frontend. Camera permission is requested only after selecting **Start camera**; selecting **Stop camera** stops all camera tracks and ends the local backend session. The frontend samples still JPEG frames rather than sending every video frame. Raw frames and crops are not stored by default.

Before starting local inference, place the Git-ignored trained model at:

```text
models/trained/car_plate_yolo_best.pt
```

Install the backend, ML, YOLO, and PaddleOCR dependencies only after approval:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
pip install -e "../ml[paddleocr,yolo]"
uvicorn app.main:app --reload
```

The health check is available at `http://127.0.0.1:8000/health`. Keep this terminal open while using the local dashboard.

In a second terminal, install and start the frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL (normally `http://127.0.0.1:5173`) and sign in with the seed values from `.env`.

## Test commands

Run each Python suite from its own project directory because both `backend` and `ml` define a `tests` package.

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests\unit -q

cd ..\ml
..\backend\.venv\Scripts\python.exe -m pytest tests -q

cd ..\frontend
npm test
npm run build
```

Open the local frontend shown by Vite, then choose **Start camera** and grant browser camera access. The first PaddleOCR use may download OCR models locally. No Docker service is needed for this webcam-only flow.
