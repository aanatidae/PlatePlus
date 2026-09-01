"""Administrator login and bearer-token endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.settings import Settings
from app.db.session import get_db
from app.models import Admin
from app.schemas.auth import AccessTokenResponse, AdminLoginRequest, AuthenticatedAdmin
from app.services.auth.service import (
    InvalidAccessTokenError,
    create_access_token,
    verify_access_token,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["authentication"])
_bearer_scheme = HTTPBearer(auto_error=False)
DatabaseSession = Annotated[Session, Depends(get_db)]
BearerCredentials = Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)]


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Administrator authentication is required.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_admin(
    database: DatabaseSession, credentials: BearerCredentials
) -> Admin:
    if credentials is None:
        raise _unauthorized()
    try:
        admin_id = verify_access_token(credentials.credentials, Settings())
    except InvalidAccessTokenError as error:
        raise _unauthorized() from error
    admin = database.get(Admin, admin_id)
    if admin is None or not admin.is_active:
        raise _unauthorized()
    return admin


@router.post("/login", response_model=AccessTokenResponse)
def login(payload: AdminLoginRequest, database: DatabaseSession) -> AccessTokenResponse:
    admin = database.scalar(select(Admin).where(func.lower(Admin.email) == payload.email))
    if admin is None or not admin.is_active or not admin.password_hash:
        raise _unauthorized()
    if not verify_password(payload.password, admin.password_hash):
        raise _unauthorized()
    token, expires_at = create_access_token(admin.id, admin.email, Settings())
    return AccessTokenResponse(
        access_token=token,
        expires_at=expires_at,
        admin=AuthenticatedAdmin.model_validate(admin),
    )


@router.get("/me", response_model=AuthenticatedAdmin)
def current_admin(admin: Annotated[Admin, Depends(require_admin)]) -> AuthenticatedAdmin:
    return AuthenticatedAdmin.model_validate(admin)
