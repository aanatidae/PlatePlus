"""FastAPI entry point for the local ALPR prototype."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.dashboard import router as dashboard_router
from app.api.database import router as database_router
from app.api.live import router as live_router
from app.api.intelligence import router as intelligence_router
from app.api.locations import router as locations_router
from app.api.operations import router as operations_router
from app.api.traffic import router as traffic_router
from app.core.settings import Settings
from app.db.session import SessionLocal
from app.services.operations import record_failure, record_recovery

settings = Settings()
app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def capture_operational_failures(request: Request, call_next):
    """Record only operational 5xx failures; never retain headers, tokens, or bodies."""
    operation = f"{request.method} {request.url.path}"
    try:
        response = await call_next(request)
    except Exception as error:
        with SessionLocal() as database:
            record_failure("database" if "sql" in type(error).__name__.lower() else "backend_api", operation, error, database=database)
        raise
    if response.status_code >= 500:
        with SessionLocal() as database:
            record_failure("backend_api", operation, f"HTTP {response.status_code}", database=database)
    else:
        with SessionLocal() as database:
            record_recovery(database, "backend_api", operation)
            database.commit()
    return response
if settings.enable_local_webcam:
    from app.api.webcam import router as webcam_router

    app.include_router(webcam_router)
app.include_router(auth_router)
app.include_router(database_router)
app.include_router(dashboard_router)
app.include_router(live_router)
app.include_router(intelligence_router)
app.include_router(locations_router)
app.include_router(operations_router)
app.include_router(traffic_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
