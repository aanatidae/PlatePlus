"""Runtime settings for the local prototype."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration loaded from the repository's local `.env` file."""

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    app_name: str = "AI-Powered ALPR Dynamic Toll Prototype"
    app_env: str = "development"
    database_url: str = (
        "postgresql+psycopg://capstone_user:capstone_password@localhost:5432/capstone_alpr"
    )
    test_database_url: str = (
        "postgresql+psycopg://capstone_user:capstone_password@localhost:5433/capstone_alpr_test"
    )
    demo_admin_email: str = "admin@example.test"
    demo_admin_password: str = "change-me"
    auth_token_secret: str = "local-development-secret-change-before-sharing"
    auth_access_token_minutes: int = 60
    cors_allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    enable_local_webcam: bool = True
    yolo_model_path: Path = Path("../models/trained/car_plate_yolo_best.pt")
    detection_confidence_threshold: float = 0.50
    ocr_confidence_threshold: float = 0.70
    webcam_frame_interval_ms: int = 750
    webcam_duplicate_cooldown_seconds: float = 20.0
    webcam_max_frame_bytes: int = 5_000_000
    paddleocr_model_storage: Path = Path("../models/paddleocr")

    @property
    def sqlalchemy_database_url(self) -> str:
        """Accept Render's standard PostgreSQL URL while retaining the psycopg driver."""
        if self.database_url.startswith("postgres://"):
            return self.database_url.replace("postgres://", "postgresql+psycopg://", 1)
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return self.database_url

    @property
    def allowed_cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]
