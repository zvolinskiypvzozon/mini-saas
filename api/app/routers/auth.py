from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_csrf_header
from app.models import Organization, User
from app.ratelimit import login_limiter
from app.schemas import LoginIn, RegisterIn, TokenOut, UserOut
from app.security import hash_password, verify_password
from app.sessions import (
    REFRESH_COOKIE,
    clear_auth_cookies,
    find_refresh_token,
    issue_tokens,
    revoke_family,
    set_auth_cookies,
)

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/auth/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    email = data.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    org = Organization(name=data.organization_name)
    user = User(
        organization=org,
        email=email,
        password_hash=hash_password(data.password),
        role="owner",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/auth/login", response_model=TokenOut)
def login(data: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    email = data.email.lower()
    client_ip = request.client.host if request.client else "unknown"
    limit_key = f"{client_ip}:{email}"

    retry_after = login_limiter.retry_after(limit_key)
    if retry_after:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts, try again later",
            headers={"Retry-After": str(retry_after)},
        )

    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(data.password, user.password_hash):
        login_limiter.failure(limit_key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    login_limiter.reset(limit_key)
    access, refresh = issue_tokens(db, user)
    db.commit()
    set_auth_cookies(response, access, refresh)
    return TokenOut(access_token=access)


def _session_expired(detail: str) -> JSONResponse:
    response = JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": detail})
    clear_auth_cookies(response)
    return response


@router.post(
    "/auth/refresh",
    response_model=TokenOut,
    dependencies=[Depends(require_csrf_header)],
)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(REFRESH_COOKIE)
    stored = find_refresh_token(db, token) if token else None
    if stored is None:
        return _session_expired("Not authenticated")

    if stored.revoked_at is not None:
        # уже использованный refresh пришёл снова — его украли; гасим всю цепочку этого входа
        revoke_family(db, stored.family_id)
        db.commit()
        return _session_expired("Refresh token reuse detected")

    if stored.expires_at <= datetime.now(timezone.utc):
        return _session_expired("Session expired")

    stored.revoked_at = datetime.now(timezone.utc)
    access, new_refresh = issue_tokens(db, stored.user, family_id=stored.family_id)
    db.commit()
    set_auth_cookies(response, access, new_refresh)
    return TokenOut(access_token=access)


@router.post(
    "/auth/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf_header)],
)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(REFRESH_COOKIE)
    stored = find_refresh_token(db, token) if token else None
    if stored is not None:
        revoke_family(db, stored.family_id)
        db.commit()
    clear_auth_cookies(response)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
