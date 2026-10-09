# Local Setup and Operations

These are the current local commands for the prototype. Installing dependencies, downloading OCR assets, training models, starting Docker, and granting browser-camera permission can change the local environment; do those actions only with approval.

## Environment

Optional upload-only Gemini fallback is off by default. Follow [backend-only
activation and disclosure](GEMINI_FALLBACK.md): install the declared SDK only with
approval, apply migration `20261009_0015`, keep the key in backend environment/private
ignored root `.env`, then restart the API. Webcam frames do not call Gemini.

1. Copy `.env.example` to `.env`.
2. Set non-default `DEMO_ADMIN_PASSWORD` and `AUTH_TOKEN_SECRET` values before any shared demonstration.
3. Keep `ENABLE_LOCAL_WEBCAM=true` only on a local operator machine. The deployed dashboard uses `false`.

### Windows local OCR prerequisite

Install or repair the [Microsoft x64 Visual C++ v14 Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist)
with approval before local PaddleOCR use. Paddle's `mkldnn.dll` requires the Microsoft
OpenMP runtime `VCOMP140.DLL`. If it is missing, image uploads and webcam inference
can report that local OCR is unavailable despite the Python packages being installed.
Restart the API after runtime installation and follow the installer's reboot guidance.
Verify from your normal launcher, without relying on another application's DLL paths.
See [the diagnosed upload failure and repair](V3_UPLOAD_RUNTIME_FIX.md).

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

Migrate to `20261007_0014` for the LDP/AKLEH/NPE/Grand Saga normal network and separate Simulator Toll Plaza. Retired highway history is retained; see [network migration](MULTI_LOCATION.md).

The seed is idempotent. It creates synthetic users, separate MYR accounts, 96 Malaysian-style presentation vehicles, three fictional Singaporean-pattern vehicles with varied balances, one initial traffic/price decision, and a password-hashed demo administrator. Migration `20261002_0013` seeds a configurable RM20.00 **simulated** foreign-vehicle charge; see [charge behavior and API](FOREIGN_VEHICLE_CHARGE.md). Use the `DEMO_ADMIN_EMAIL` and `DEMO_ADMIN_PASSWORD` values from your untracked `.env` to sign in to the dashboard or `POST /api/auth/login`.

Run PostgreSQL API integration tests against only the temporary test database:

```powershell
cd backend
$env:RUN_POSTGRES_TESTS="1"
.\.venv\Scripts\python.exe -m pytest tests -q
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

## One-command capstone presentation startup

From the project root, run `start_plateplus_demo.bat`. It reuses the existing Docker Compose PostgreSQL service, applies the current migration, runs the idempotent synthetic seed, starts FastAPI and Vite only when their ports are unused, and opens `http://localhost:5173`. It never installs Python or npm dependencies. Backend and frontend logs are written to `.plateplus-demo/logs/`.

1. Run `start_plateplus_demo.bat`.
2. Wait for `PlatePlus demo is ready.` and sign in.
3. Select **Simulator Toll Plaza** on Overview and choose **Open Camera**.
4. The launcher attempts to start the normal-location presentation feed using the seeded local administrator; use **Start Live Feed** on Overview if it reports a credential/API warning. Simulator Toll Plaza is intentionally excluded.

Use `stop_plateplus_demo.bat` to stop only backend/frontend processes that this launcher recorded. It does not stop PostgreSQL or unrelated Python/Node processes.

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

Only when explicitly demonstrating physical inference, select Simulator Toll Plaza,
open its camera PiP, choose **Start camera** and grant browser permission. The
integrated camera/upload workflow requires the local API, PostgreSQL, model weights
and cached OCR assets. Do not allow first-use asset downloads without approval.

## V3 synthetic seed and foreign charge

The following fictional examples are created by `app.db.seed`:

| Plate | Registration origin | Initial wallet | Seeded RM20 charge scenario |
| --- | --- | ---: | --- |
| GBC6427R | singaporean | RM75.00 | Sufficient for typical demo toll + charge |
| YN4821R | singaporean | RM8.00 | Insufficient for the seeded charge |
| XD7316E | singaporean | RM45.00 | Sufficient for typical demo toll + charge |

These are initial balances, not promised current balances after demo payments.
Repeated seed preserves existing wallet balances and does not reset history or
overwrite an edited foreign-charge setting. The normal generated feed continues
to use the 96 Malaysian-style synthetic vehicles; it does not generate Simulator
crossings. No real registration or owner is asserted by these examples.

On Dynamic Pricing Management, expand **Simulated foreign-vehicle charge** to edit
the separately persisted setting. Authenticated `GET`/`PUT
`/api/data/foreign-vehicle-charge` provide the same configuration. The RM20.00
default is a simulated proposal example, not an official fee. Changing it affects
future transactions, not stored charges, congestion bands or Prediction.
See [API contracts](API.md), [schema](DATABASE_SCHEMA.md) and
[origin rules](PLATE_ORIGIN.md).
