"""Password hashing and signed bearer-token support for local administrators."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from app.core.settings import Settings

_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_KEY_LENGTH = 32


class InvalidAccessTokenError(ValueError):
    """Raised when a bearer token is malformed, tampered with, or expired."""


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_SCRYPT_KEY_LENGTH,
    )
    return "$".join(
        (
            "scrypt",
            str(_SCRYPT_N),
            str(_SCRYPT_R),
            str(_SCRYPT_P),
            _encode(salt),
            _encode(digest),
        )
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, n, r, p, encoded_salt, encoded_digest = password_hash.split("$")
        if algorithm != "scrypt":
            return False
        expected_digest = _decode(encoded_digest)
        actual_digest = hashlib.scrypt(
            password.encode("utf-8"),
            salt=_decode(encoded_salt),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected_digest),
        )
        return hmac.compare_digest(actual_digest, expected_digest)
    except (TypeError, ValueError):
        return False


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def create_access_token(admin_id: UUID, email: str, settings: Settings) -> tuple[str, datetime]:
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=settings.auth_access_token_minutes)
    payload = {
        "sub": str(admin_id),
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    encoded_payload = _encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(
        settings.auth_token_secret.encode("utf-8"), encoded_payload.encode("ascii"), hashlib.sha256
    ).digest()
    return f"{encoded_payload}.{_encode(signature)}", expires_at


def verify_access_token(token: str, settings: Settings) -> UUID:
    try:
        encoded_payload, encoded_signature = token.split(".", maxsplit=1)
        expected_signature = hmac.new(
            settings.auth_token_secret.encode("utf-8"),
            encoded_payload.encode("ascii"),
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(_decode(encoded_signature), expected_signature):
            raise InvalidAccessTokenError("Invalid token signature.")
        payload: dict[str, Any] = json.loads(_decode(encoded_payload))
        if int(payload["exp"]) <= int(datetime.now(UTC).timestamp()):
            raise InvalidAccessTokenError("Token has expired.")
        return UUID(str(payload["sub"]))
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        if isinstance(error, InvalidAccessTokenError):
            raise
        raise InvalidAccessTokenError("Invalid access token.") from error
