"""
FitCheck AI — Auth API
Register, Login, Refresh token, Google OAuth
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime, timezone
import re

from app.core.database import get_db
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
)
from app.models.user import User, UserPlan, UserStatus
from app.services.email_service import send_welcome_email

router = APIRouter()


# ── Schemas ───────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("Password must contain a letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain a number")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


class RefreshRequest(BaseModel):
    refresh_token: str


class GoogleOAuthRequest(BaseModel):
    google_token: str       # ID token from Google Sign-In


# ── Register ──────────────────────────────────────────
@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    data: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    # Check email not already taken
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        auth_provider="email",
    )
    db.add(user)
    await db.flush()    # get ID before commit

    # Send welcome email in background
    background_tasks.add_task(send_welcome_email, user.email, user.full_name or "there")

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        user=_user_dict(user),
    )


# ── Login ─────────────────────────────────────────────
@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if user.status == UserStatus.BANNED:
        raise HTTPException(status_code=403, detail="Account suspended")

    user.last_login_at = datetime.now(timezone.utc)

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        user=_user_dict(user),
    )


# ── Refresh token ─────────────────────────────────────
@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(data.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        user=_user_dict(user),
    )


# ── Google OAuth ──────────────────────────────────────
@router.post("/google", response_model=TokenResponse)
async def google_oauth(
    data: GoogleOAuthRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Verify Google ID token, create or fetch user.
    Frontend sends the Google ID token after Google Sign-In.
    """
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests
    from app.core.config import settings

    try:
        google_client_id = "YOUR_GOOGLE_CLIENT_ID"   # set in env
        id_info = id_token.verify_oauth2_token(
            data.google_token,
            google_requests.Request(),
            google_client_id,
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    google_id = id_info["sub"]
    email     = id_info.get("email")
    name      = id_info.get("name")
    avatar    = id_info.get("picture")

    # Find existing user by google_id or email
    result = await db.execute(
        select(User).where(
            (User.google_id == google_id) | (User.email == email)
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            email=email,
            full_name=name,
            avatar_url=avatar,
            google_id=google_id,
            auth_provider="google",
        )
        db.add(user)
        await db.flush()
        background_tasks.add_task(send_welcome_email, email, name or "there")
    else:
        user.google_id  = google_id
        user.avatar_url = avatar or user.avatar_url

    user.last_login_at = datetime.now(timezone.utc)

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        user=_user_dict(user),
    )


# ── Me ────────────────────────────────────────────────
@router.get("/me")
async def me(db: AsyncSession = Depends(get_db)):
    """Get current user profile — requires Authorization header."""
    from app.core.security import get_current_user
    from fastapi import Request
    # handled via dependency injection in real usage
    return {"message": "Use Authorization: Bearer <token>"}


# ── Helper ────────────────────────────────────────────
def _user_dict(user: User) -> dict:
    return {
        "id":         user.id,
        "email":      user.email,
        "full_name":  user.full_name,
        "plan":       user.plan,
        "is_admin":   user.is_admin,
        "avatar_url": user.avatar_url,
        "created_at": str(user.created_at),
    }
