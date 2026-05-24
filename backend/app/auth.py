from datetime import datetime, timedelta, timezone
import secrets
import uuid
from typing import Optional
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import Cookie, Depends, HTTPException, Response, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.db import get_db
from backend.app.models import User


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
COOKIE_NAME = "santoor_session"
GOOGLE_STATE_COOKIE = "santoor_google_state"


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
    settings = get_settings()
    response.set_cookie(
        COOKIE_NAME,
        create_token(user),
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
    )


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME)


def create_google_auth_url(state: str) -> str:
    settings = get_settings()
    if not settings.effective_google_client_id:
        raise HTTPException(status_code=503, detail="Google auth is not configured")
    query = urlencode(
        {
            "client_id": settings.effective_google_client_id,
            "redirect_uri": settings.effective_google_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "prompt": "select_account",
        }
    )
    return f"https://accounts.google.com/o/oauth2/v2/auth?{query}"


def create_google_state() -> str:
    return secrets.token_urlsafe(32)


async def exchange_google_code(code: str) -> dict:
    settings = get_settings()
    if not settings.effective_google_client_id or not settings.effective_google_client_secret:
        raise HTTPException(status_code=503, detail="Google auth is not configured")
    async with httpx.AsyncClient(timeout=12) as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.effective_google_client_id,
                "client_secret": settings.effective_google_client_secret,
                "redirect_uri": settings.effective_google_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
    if response.status_code >= 400:
        raise HTTPException(status_code=401, detail="Google sign-in failed")
    token_payload = response.json()
    token = token_payload.get("id_token")
    if not token:
        raise HTTPException(status_code=401, detail="Google did not return an identity token")
    try:
        return id_token.verify_oauth2_token(token, google_requests.Request(), settings.effective_google_client_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Google identity token could not be verified")


def verify_google_credential(credential: str) -> dict:
    settings = get_settings()
    if not settings.effective_google_client_id:
        raise HTTPException(status_code=503, detail="Google auth is not configured")
    try:
        return id_token.verify_oauth2_token(credential, google_requests.Request(), settings.effective_google_client_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Google identity token could not be verified")


def upsert_google_user(db: Session, profile: dict) -> User:
    email = str(profile.get("email", "")).lower()
    google_sub = str(profile.get("sub", ""))
    if not email or not google_sub:
        raise HTTPException(status_code=401, detail="Google profile is missing email identity")
    user = db.query(User).filter(User.google_sub == google_sub).first()
    if not user:
        user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, password_hash="", is_admin=False)
        db.add(user)
    user.auth_provider = "google"
    user.google_sub = google_sub
    user.name = str(profile.get("name", ""))[:255]
    user.avatar_url = str(profile.get("picture", ""))
    db.commit()
    db.refresh(user)
    return user


def create_guest_user(db: Session) -> User:
    guest_id = uuid.uuid4().hex
    user = User(
        email=f"guest-{guest_id}@guest.santoorai.app",
        password_hash="",
        is_admin=False,
        auth_provider="guest",
        google_sub="",
        name="Guest",
        avatar_url="",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


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
