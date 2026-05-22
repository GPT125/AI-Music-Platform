from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Cookie, Depends, HTTPException, Response, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.db import get_db
from backend.app.models import User


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
COOKIE_NAME = "santoor_session"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_token(user: User) -> str:
    settings = get_settings()
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": user.id,
        "email": user.email,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=7)).timestamp()),
    }
    return jwt.encode(payload, settings.effective_jwt_secret, algorithm="HS256")


def set_auth_cookie(response: Response, user: User) -> None:
    response.set_cookie(
        COOKIE_NAME,
        create_token(user),
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
    )


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME)


def current_user(
    db: Session = Depends(get_db),
    token: Optional[str] = Cookie(default=None, alias=COOKIE_NAME),
) -> User:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        payload = jwt.decode(token, get_settings().effective_jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    user = db.get(User, payload.get("sub"))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    return user


def seed_initial_admin(db: Session) -> None:
    settings = get_settings()
    if not settings.initial_admin_email or not settings.initial_admin_password:
        return
    existing = db.query(User).filter(User.email == settings.initial_admin_email.lower()).first()
    if existing:
        return
    db.add(
        User(
            email=settings.initial_admin_email.lower(),
            password_hash=hash_password(settings.initial_admin_password),
            is_admin=True,
        )
    )
    db.commit()

