import os
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Response
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import RefreshToken, User
from app.security import (
    ACCESS_TTL_MIN,
    REFRESH_TTL_DAYS,
    create_access_token,
    hash_token,
    new_refresh_token,
)

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
ACCESS_COOKIE_PATH = "/api"
REFRESH_COOKIE_PATH = "/api/auth"
CSRF_HEADER = "X-Requested-With"
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "false").lower() == "true"


def issue_tokens(db: Session, user: User, family_id: uuid.UUID | None = None) -> tuple[str, str]:
    """Новая пара: короткий access JWT и длинный refresh. В БД хранится только хеш refresh."""
    refresh = new_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            family_id=family_id or uuid.uuid4(),
            token_hash=hash_token(refresh),
            expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_TTL_DAYS),
        )
    )
    return create_access_token(str(user.id), str(user.organization_id)), refresh


def find_refresh_token(db: Session, token: str) -> RefreshToken | None:
    return db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(token)))


def revoke_family(db: Session, family_id: uuid.UUID) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(timezone.utc))
    )


def _cookie_options(path: str) -> dict:
    return {"path": path, "httponly": True, "secure": COOKIE_SECURE, "samesite": "strict"}


def set_auth_cookies(response: Response, access: str, refresh: str) -> None:
    response.set_cookie(
        ACCESS_COOKIE, access, max_age=ACCESS_TTL_MIN * 60, **_cookie_options(ACCESS_COOKIE_PATH)
    )
    response.set_cookie(
        REFRESH_COOKIE,
        refresh,
        max_age=REFRESH_TTL_DAYS * 24 * 3600,
        **_cookie_options(REFRESH_COOKIE_PATH),
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, **_cookie_options(ACCESS_COOKIE_PATH))
    response.delete_cookie(REFRESH_COOKIE, **_cookie_options(REFRESH_COOKIE_PATH))
