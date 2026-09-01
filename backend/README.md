# Backend

FastAPI backend package for the simulated ALPR dynamic toll prototype.

The backend includes PostgreSQL SQLAlchemy models, an Alembic migration, idempotent synthetic demo seeding, validated persistence routes under `/api/data`, and the local webcam routes. Authentication and simulated toll business logic are separate follow-up phases.

From this directory, after creating the root `.env` and starting PostgreSQL:

```powershell
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload
```

The seed creates three synthetic users, three separate MYR accounts, three Malaysian-style demo vehicles, an initial simulated traffic/price record, and a demo admin identity without a password hash. Password setup belongs to the authentication phase.

To verify database APIs against the temporary PostgreSQL test service:

```powershell
$env:RUN_POSTGRES_TESTS="1"
pytest tests/integration/test_database_api.py
```
