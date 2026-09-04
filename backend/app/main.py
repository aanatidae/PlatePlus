"""FastAPI entry point for the local ALPR prototype."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.dashboard import router as dashboard_router
from app.api.database import router as database_router
from app.api.live import router as live_router
from app.api.locations import router as locations_router
from app.api.traffic import router as traffic_router
from app.core.settings import Settings

settings = Settings()
app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
if settings.enable_local_webcam:
    from app.api.webcam import router as webcam_router

    app.include_router(webcam_router)
app.include_router(auth_router)
app.include_router(database_router)
app.include_router(dashboard_router)
app.include_router(live_router)
app.include_router(locations_router)
app.include_router(traffic_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
