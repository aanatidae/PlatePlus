"""PostgreSQL test-database fixtures (opt in with RUN_POSTGRES_TESTS=1)."""

import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.settings import Settings
from app.db.session import get_db
from app.models import Admin
from app.services.auth.service import hash_password


@pytest.fixture(scope="session")
def test_engine():
    if os.getenv("RUN_POSTGRES_TESTS") != "1":
        pytest.skip("Set RUN_POSTGRES_TESTS=1 after starting postgres_test.")

    test_url = Settings().test_database_url
    previous_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = test_url
    config = Config("alembic.ini")
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    engine = create_engine(test_url, pool_pre_ping=True)
    yield engine
    engine.dispose()
    command.downgrade(config, "base")
    if previous_url is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = previous_url


@pytest.fixture()
def database(test_engine):
    connection = test_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection, expire_on_commit=False)()
    yield session
    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


@pytest.fixture()
def database_app(database):
    from fastapi import FastAPI

    from app.api.auth import router as auth_router
    from app.api.database import router as database_router
    from app.api.traffic import router as traffic_router

    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(database_router)
    app.include_router(traffic_router)

    def override_database():
        yield database

    app.dependency_overrides[get_db] = override_database
    return app


@pytest.fixture()
def admin_auth_headers(database, database_app) -> dict[str, str]:
    from fastapi.testclient import TestClient

    database.add(
        Admin(
            email="admin@example.test",
            display_name="Test Administrator",
            password_hash=hash_password("test-password"),
        )
    )
    database.flush()
    response = TestClient(database_app).post(
        "/api/auth/login", json={"email": "admin@example.test", "password": "test-password"}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
