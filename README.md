# PlatePlus

Capstone prototype for automatic license plate recognition (ALPR) with supported Malaysian and Singaporean plate patterns, OCR-based plate matching, simulated toll transactions, simulated traffic conditions, and configurable dynamic toll pricing.

The computer-vision baseline is complete: a one-class YOLO detector trained on Malaysian car-plate images identifies plates, PaddleOCR reads detected crops, and a conservative pattern stage classifies supported Malaysian or Singaporean results. The FastAPI/PostgreSQL foundation, simulated toll workflow, configurable traffic-pricing backend, and administrator dashboard are complete.

The normal simulated network contains LDP, AKLEH, NPE, and Grand Saga, plus a separate Simulator Toll Plaza for local webcam/image ALPR. The administrator dashboard has three pages: Overview, Dynamic Pricing Management, and Prediction. Overview opens in All Locations with selectable schematic markers and persisted location context. Prediction offers only normal locations and remains isolated from live data. Historical highway records retain their original ownership; retired locations are excluded from the current network. See [multi-location monitoring](docs/MULTI_LOCATION.md) for configuration, migration, and API behavior. Origin labels and stored charge components appear in Overview and local camera/upload results. Dynamic Pricing includes expandable read-only history and policy audit; Model Performance remains a modal with separately labelled OCR and synthetic origin-fixture evidence. See [V3 presentation behavior](docs/V3_SIMULATOR_PRICING_NAVIGATION.md).

## Scope

- Traffic data is simulated.
- Toll payments and account balances are simulated.
- Toll charging is flat-rate-only: each crossing uses its location's configured flat base toll multiplied by the congestion multiplier, subject to the pricing safeguards. No entry/exit tracking, journey length, or distance-based charging is supported. Base tolls are prototype configuration, not official rates. See [flat-rate scope](docs/FLAT_RATE_SCOPE.md).
- Unambiguous Malaysian and Singaporean plate patterns can match fictional demo vehicles; Singaporean simulated payments add a separately configured foreign-vehicle charge.
- No real banking, toll infrastructure, traffic-feed, enforcement, or vehicle-owner integrations are in scope.
- Recognition supports local browser-webcam frames and one-time still-image uploads. Both local inference paths remain unavailable from the cloud dashboard by design.
- The detector should focus on the `car plate` class.

## Stack

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
.harnessV2/ Current personal-improvement roadmap and milestone status
```

## Setup Status

The repository includes ML dataset preparation, plate processing, YOLO crop extraction, PaddleOCR recognition, PostgreSQL models/migrations, synthetic demo seeding, administrator authentication, simulated toll handling, a configurable traffic simulator and pricing engine, and tests. The trained model is a local, Git-ignored artifact at `models/trained/car_plate_yolo_best.pt`; it is not included in a fresh clone. Do not install dependencies, download models, start training, or start Docker services without explicit approval.

## Current ML Baseline

- Detector: one-class `car plate` YOLO model, trained for 150 epochs; user-reported held-out test accuracy: 93.1%.
- OCR: PaddleOCR reached 37 exact matches out of 44 held-out crops (84.1%) using uppercase-alphanumeric normalization.
- Confidence gates remain required before any downstream simulated charge; low-confidence or unknown results must fail safely.
- Still-image and browser-frame processing are available locally; prerecorded-video processing remains deferred.

## Documentation

- [Local setup, database, launch, and test commands](docs/SETUP.md)
- [Capstone demo flow](docs/DEMO.md)
- [Testing, metrics, limitations, and failure cases](docs/TESTING_EVALUATION.md)
- [OCR workflow](docs/OCR_PLATE_PROCESSING.md)
- [Plate-origin rules and simulated foreign-vehicle charge](docs/FOREIGN_VEHICLE_CHARGE.md)
- [YOLO training workflow](docs/COLAB_TRAINING.md)
- [Vercel and Render deployment](docs/DEPLOYMENT.md)

## Initial Commands

Copy environment defaults before running future services:

```bash
cp .env.example .env
```

Start PostgreSQL after Docker is available:

```bash
docker compose up -d postgres postgres_test
```

Backend setup command:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
uvicorn app.main:app --reload
```

Frontend setup command:

```bash
cd frontend
npm install
npm run dev
```

## Current Limitations

- The administrator dashboard is administrator-only, and all of its traffic, pricing, financial, and vehicle data remain simulated.
- The traffic scheduler is a separate local process; it is not part of the Vercel dashboard deployment boundary.
- The trained YOLO weights are intentionally ignored by Git and must be supplied locally before inference can run on a fresh clone.
- PaddleOCR has been selected and evaluated, but dependencies/models must still be installed locally with user approval when integration begins.
- The initial Alembic migration creates the complete UUID-based prototype schema.
