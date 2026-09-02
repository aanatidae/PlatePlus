# Backend

FastAPI backend package for the simulated ALPR dynamic toll prototype.

The backend includes PostgreSQL SQLAlchemy models, Alembic migrations, idempotent synthetic demo seeding, administrator login, protected persistence routes under `/api/data`, local webcam routes, simulated toll payment, and administrator-controlled traffic simulation with dynamic pricing.

From this directory, after creating the root `.env` and starting PostgreSQL:

```powershell
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload
```

The seed creates three synthetic users, three separate MYR accounts, three Malaysian-style demo vehicles, an initial simulated traffic/price record, and a password-hashed demo admin. Use `POST /api/auth/login` with the `DEMO_ADMIN_EMAIL` and `DEMO_ADMIN_PASSWORD` values from your local `.env`, then send the returned bearer token as `Authorization: Bearer <token>` to `/api/data/*` routes. Do not use the example password in a shared demo; set a unique `AUTH_TOKEN_SECRET` and demo password locally first.

To verify database APIs against the temporary PostgreSQL test service:

```powershell
$env:RUN_POSTGRES_TESTS="1"
pytest tests/integration/test_database_api.py
pytest tests/integration/test_toll_payment.py tests/integration/test_traffic_api.py
```

## Simulated Traffic And Dynamic Pricing

All traffic and prices are synthetic. After authenticating as an administrator, use `/api/traffic/settings` to configure the run interval, rule-based Malaysia-time profile or a fixed scenario, and real or advancing simulated time. Use `/api/traffic/pricing-rules` to edit the four contiguous congestion bands, and `POST /api/traffic/simulate` to record a manual run.

Run the scheduler as a separate local process only when scheduled simulations are wanted:

```powershell
python -m app.traffic_scheduler
```

The implementation exposes a `TrafficScenarioPredictor` protocol so a future simulated prediction model can replace the time profile without changing persistence or pricing behavior.
