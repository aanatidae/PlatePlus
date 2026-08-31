# Setup Notes

These notes document the project foundation only. Commands that install dependencies, download models, or run training should be executed only after user approval.

## Environment

1. Copy `.env.example` to `.env`.
2. Change demo secrets before sharing the application beyond a local capstone demo.

## PostgreSQL

The project is planned around Docker-based PostgreSQL.

```bash
docker compose up -d postgres postgres_test
```

The normal development database listens on port `5432`. The test database listens on port `5433` and uses temporary storage.

## Backend

The backend manifest is in `backend/pyproject.toml`. Planned setup:

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