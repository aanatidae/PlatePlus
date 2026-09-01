# Backend

FastAPI backend package for the simulated ALPR dynamic toll prototype.

The backend includes PostgreSQL SQLAlchemy models, an Alembic migration, idempotent synthetic demo seeding, administrator login, protected persistence routes under `/api/data`, and local webcam routes. Simulated toll business logic remains a follow-up phase.

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
```
