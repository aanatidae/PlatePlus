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
    yolo_model_path: Path = Path("../models/trained/car_plate_yolo_best.pt")
    detection_confidence_threshold: float = 0.50
    ocr_confidence_threshold: float = 0.70
    webcam_frame_interval_ms: int = 750
    webcam_duplicate_cooldown_seconds: float = 20.0
    webcam_max_frame_bytes: int = 5_000_000
    paddleocr_model_storage: Path = Path("../models/paddleocr")
