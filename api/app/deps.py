import uuid

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.security import decode_token
from app.sessions import ACCESS_COOKIE, CSRF_HEADER

bearer = HTTPBearer(auto_error=False)

SAFE_METHODS = ("GET", "HEAD", "OPTIONS")


def require_csrf_header(request: Request) -> None:
    """Запросы с cookie, меняющие данные, должны нести заголовок, который чужой сайт без CORS отправить не может."""
    if request.method not in SAFE_METHODS and not request.headers.get(CSRF_HEADER):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF check failed")


def get_current_user(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if creds is not None:
        token = creds.credentials
    else:
        token = request.cookies.get(ACCESS_COOKIE)
        if token is None:
            raise unauthorized
        require_csrf_header(request)
    try:
        payload = decode_token(token)
        user_id = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise unauthorized
    user = db.get(User, user_id)
    if user is None:
        raise unauthorized
    return user
