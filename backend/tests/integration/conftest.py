"""PostgreSQL test-database fixtures (opt in with RUN_POSTGRES_TESTS=1)."""

import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.core.settings import Settings
from app.db.session import get_db
from app.models import Admin
from app.services.auth.service import hash_password


def _empty_then_downgrade(engine, config):
    # Old network downgrades delete seeded locations. Empty disposable test data
    # first so RESTRICT foreign keys do not block full test-schema cleanup.
    tables = [name for name in inspect(engine).get_table_names() if name != "alembic_version"]
    if tables:
        quote = engine.dialect.identifier_preparer.quote
        with engine.begin() as connection:
            connection.execute(text("TRUNCATE " + ", ".join(quote(name) for name in tables) + " CASCADE"))
    command.downgrade(config, "base")


@pytest.fixture(scope="session")
def test_engine():
    if os.getenv("RUN_POSTGRES_TESTS") != "1":
        pytest.skip("Set RUN_POSTGRES_TESTS=1 after starting postgres_test.")

    settings = Settings()
    test_url = settings.test_database_url
    # These fixtures drop the schema. Never permit a development database target.
    target = make_url(test_url)
    development = make_url(settings.sqlalchemy_database_url)
    if target.database != "capstone_alpr_test" or (
        target.host, target.port, target.database
    ) == (development.host, development.port, development.database):
        pytest.fail("Migration fixtures require a separate capstone_alpr_test database.")
    previous_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = test_url
    config = Config("alembic.ini")
    engine = create_engine(test_url, pool_pre_ping=True)
    _empty_then_downgrade(engine, config)
    command.upgrade(config, "head")
    yield engine
    _empty_then_downgrade(engine, config)
    engine.dispose()
    if previous_url is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = previous_url


@pytest.fixture()
def reset_schema(test_engine):
    def reset(target="head"):
        config = Config("alembic.ini")
        _empty_then_downgrade(test_engine, config)
        command.upgrade(config, target)
    return reset


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
    from app.api.live import router as live_router
    from app.api.locations import router as locations_router
    from app.api.operations import router as operations_router
    from app.api.traffic import router as traffic_router

    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(database_router)
    app.include_router(locations_router)
    app.include_router(operations_router)
    app.include_router(live_router)
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
