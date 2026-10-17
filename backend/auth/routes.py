"""Auth API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from auth.google_oauth import (
    GoogleOAuthError,
    consume_oauth_state,
    create_google_auth_url,
    exchange_code_for_user,
)
from auth.security import (
    AuthValidationError,
    create_access_token,
    decode_access_token,
    hash_password,
    validate_password,
    validate_username,
    verify_password,
)
from auth.store import (
    AuthError,
    UserRecord,
    create_local_user,
    create_or_get_google_user,
    get_user_by_id,
    get_user_by_username,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
_bearer = HTTPBearer(auto_error=False)


class RegisterBody(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=128)


class LoginBody(BaseModel):
    username: str
    password: str


class GoogleCallbackBody(BaseModel):
    code: str
    state: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


def _token_response(user: UserRecord) -> AuthResponse:
    token = create_access_token(user.id, user.username)
    return AuthResponse(access_token=token, user=user.to_public())


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> UserRecord:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Not authenticated.")
    try:
        payload = decode_access_token(credentials.credentials)
    except AuthValidationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    user = get_user_by_id(str(payload.get("sub", "")))
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")
    return user


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> UserRecord | None:
    if credentials is None:
        return None
    try:
        return get_current_user(credentials)
    except HTTPException:
        return None


@router.post("/register", response_model=AuthResponse)
def register(body: RegisterBody) -> AuthResponse:
    try:
        username = validate_username(body.username)
        validate_password(body.password)
        user = create_local_user(username, hash_password(body.password))
        return _token_response(user)
    except AuthValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AuthError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/login", response_model=AuthResponse)
def login(body: LoginBody) -> AuthResponse:
    try:
        username = validate_username(body.username)
    except AuthValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    user = get_user_by_username(username)
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    return _token_response(user)


@router.get("/google/url")
def google_auth_url() -> dict[str, str]:
    try:
        url, state = create_google_auth_url()
        return {"url": url, "state": state}
    except GoogleOAuthError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/google/callback", response_model=AuthResponse)
def google_callback(body: GoogleCallbackBody) -> AuthResponse:
    if not consume_oauth_state(body.state):
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state.")
    try:
        profile = exchange_code_for_user(body.code)
        suggested = (profile.get("email") or profile.get("name") or "user").split("@")[0]
        user = create_or_get_google_user(
            google_sub=profile["sub"],
            email=profile.get("email"),
            suggested_username=suggested,
        )
        return _token_response(user)
    except GoogleOAuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AuthError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/me")
def me(user: UserRecord = Depends(get_current_user)) -> dict:
    return user.to_public()
