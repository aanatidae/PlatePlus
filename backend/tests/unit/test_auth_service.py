from uuid import uuid4

import pytest

from app.core.settings import Settings
from app.services.auth.service import (
    InvalidAccessTokenError,
    create_access_token,
    hash_password,
    verify_access_token,
    verify_password,
)


def test_password_hash_cannot_be_used_as_the_original_password() -> None:
    password = "local-demo-password"
    password_hash = hash_password(password)

    assert password_hash != password
    assert verify_password(password, password_hash)
    assert not verify_password("wrong-password", password_hash)


def test_signed_access_token_round_trip() -> None:
    settings = Settings(auth_token_secret="test-secret", auth_access_token_minutes=60)
    admin_id = uuid4()

    token, _ = create_access_token(admin_id, "admin@example.test", settings)

    assert verify_access_token(token, settings) == admin_id


def test_tampered_access_token_is_rejected() -> None:
    settings = Settings(auth_token_secret="test-secret", auth_access_token_minutes=60)
    token, _ = create_access_token(uuid4(), "admin@example.test", settings)

    with pytest.raises(InvalidAccessTokenError):
        verify_access_token(f"{token}tampered", settings)
