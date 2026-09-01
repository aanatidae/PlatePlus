# AI-Powered Automatic License Plate Recognition and Dynamic Toll Management System

Capstone prototype for Malaysian automatic license plate recognition (ALPR), OCR-based plate matching, simulated toll transactions, simulated traffic conditions, and configurable dynamic toll pricing.

The computer-vision baseline is complete: a one-class YOLO detector identifies Malaysian car plates and PaddleOCR recognizes plate text from detected crops. The next implementation stage is the FastAPI backend with Docker-based PostgreSQL, followed by the simulated toll, traffic-pricing, and administrator dashboard features.

## Scope

- Traffic data is simulated.
- Toll payments and account balances are simulated.
- No real banking, toll infrastructure, traffic-feed, enforcement, or vehicle-owner integrations are in scope.
- The first recognition prototype targets still images only.
- The detector should focus on the `car plate` class.

## Planned Stack

- Backend/API: FastAPI
- Database: Docker-based PostgreSQL
- ML/computer vision: Python, YOLO, OpenCV
- OCR: PaddleOCR (CPU, PaddlePaddle 3.2.x)
- Frontend: React with TypeScript

## Repository Layout

```text
backend/   FastAPI application, services, database models, and backend tests
frontend/  React/TypeScript dashboard application
ml/        Dataset configs, ALPR pipeline code, OCR code, and ML tests
scripts/   Local setup, validation, seed, and utility scripts
docs/      Architecture, setup, and demo documentation
infra/     Docker and local infrastructure configuration
.harness/  Agent notes, roadmap, and implementation checklist
```

## Setup Status

The repository includes ML dataset preparation, plate processing, YOLO crop extraction, PaddleOCR recognition, PostgreSQL models/migrations, synthetic demo seeding, validated persistence APIs, and tests. The trained model is a local, Git-ignored artifact at `models/trained/car_plate_yolo_best.pt`; it is not included in a fresh clone. Do not install dependencies, download models, start training, or start Docker services without explicit approval.

## Current ML Baseline

- Detector: one-class `car plate` YOLO model, trained for 150 epochs; user-reported held-out test accuracy: 93.1%.
- OCR: PaddleOCR reached 37 exact matches out of 44 held-out crops (84.1%) using uppercase-alphanumeric normalization.
- Confidence gates remain required before any downstream simulated charge; low-confidence or unknown results must fail safely.
- The still-image pipeline is the current target. Video-frame processing is deferred.

## Initial Commands

Copy environment defaults before running future services:

```bash
cp .env.example .env
```

Start PostgreSQL after Docker is available:

```bash
docker compose up -d postgres postgres_test
```

Backend setup command planned for future implementation:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
uvicorn app.main:app --reload
```

Frontend setup command planned for future implementation:

```bash
cd frontend
npm install
npm run dev
```

## Current Limitations

- No runnable app exists yet.
- The PostgreSQL persistence foundation is implemented; admin authentication, simulated toll business logic, traffic simulation, and the frontend dashboard remain pending.
- The trained YOLO weights are intentionally ignored by Git and must be supplied locally before inference can run on a fresh clone.
- PaddleOCR has been selected and evaluated, but dependencies/models must still be installed locally with user approval when integration begins.
- The initial Alembic migration creates the complete UUID-based prototype schema.
