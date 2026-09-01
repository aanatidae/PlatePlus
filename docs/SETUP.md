# Setup Notes

These notes document the project foundation only. Commands that install dependencies, download models, or run training should be executed only after user approval.

## Environment

1. Copy `.env.example` to `.env`.
2. Change demo secrets before sharing the application beyond a local capstone demo.

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

The seed is idempotent. It creates only synthetic users, separate MYR accounts, Malaysian-style vehicle records, one initial traffic/price decision, and a demo administrator identity. Authentication and the administrator password hash are intentionally configured in the later authentication phase.

Run PostgreSQL API integration tests against only the temporary test database:

```powershell
cd backend
$env:RUN_POSTGRES_TESTS="1"
pytest tests/integration/test_database_api.py
```

## Backend

The backend manifest is in `backend/pyproject.toml`:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
uvicorn app.main:app --reload
```

## Frontend

The frontend manifest is in `frontend/package.json`. Planned setup:

```bash
cd frontend
npm install
npm run dev
```

## ML Pipeline

The ML manifest is in `ml/pyproject.toml`. YOLO and OCR dependencies are intentionally separated because model downloads and OCR engine choice require explicit approval.

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

In a second terminal, install and start the frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open the local frontend shown by Vite, then choose **Start camera** and grant browser camera access. The first PaddleOCR use may download OCR models locally. No Docker service is needed for this webcam-only flow.
