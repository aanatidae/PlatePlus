# AI-Powered Automatic License Plate Recognition and Dynamic Toll Management System

Capstone prototype for Malaysian automatic license plate recognition (ALPR), OCR-based plate matching, simulated toll transactions, simulated traffic conditions, and configurable dynamic toll pricing.

This repository is currently in project foundation stage. The local dataset is present, but training, OCR integration, backend APIs, database migrations, and frontend dashboard implementation are still pending.

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
- OCR: selected later based on the easiest reliable local setup
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

Dependency manifests and Docker Compose configuration have been added as foundation files. Do not install dependencies, download models, or start training without explicit approval.

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
- No dependencies have been installed.
- No YOLO model has been trained or downloaded.
- No OCR engine has been selected or installed.
- No database migrations exist yet.