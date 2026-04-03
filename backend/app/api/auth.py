import secrets
import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from jose import jwt, JWTError
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import bcrypt

from app.config import settings
from app.db.session import get_db
from app.db.models import User
from app.api.deps import get_current_user
from app.api.rate_limit import rate_limit_login, rate_limit_register
from app.constants import BCRYPT_ROUNDS, MIN_SUBMIT_SECONDS
from app.services.email import send_verification_email, send_password_reset_email

router = APIRouter()

PASSWORD_RESET_EXPIRE_HOURS = 1


# --------------- Request / Response models ---------------

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    company: str = ""
    tz_offset: float = 0


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    company: str = ""
    tz_offset: float = 0


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    is_email_verified: bool
    digest_enabled: bool
    digest_frequency: str

    model_config = {"from_attributes": True}


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class MessageResponse(BaseModel):
    detail: str


class DigestPreferencesRequest(BaseModel):
    enabled: bool
    frequency: str = "daily"


class DigestPreferencesResponse(BaseModel):
    digest_enabled: bool
    digest_frequency: str


# --------------- Helpers ---------------

def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode()


def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def _create_token(user_id: str, token_type: str = "access") -> str:
    if token_type == "access":
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    payload = {"sub": user_id, "type": token_type, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        "refresh_token", token,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=settings.refresh_token_expire_days * 86400,
    )


def _check_bot_signals(body: RegisterRequest | LoginRequest) -> None:
    if body.company:
        raise HTTPException(status_code=422, detail="Invalid submission")
    if body.tz_offset > 0:
        elapsed = time.time() - body.tz_offset
        if elapsed < MIN_SUBMIT_SECONDS:
            raise HTTPException(status_code=422, detail="Invalid submission")


# --------------- Auth endpoints ---------------

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    _rl=Depends(rate_limit_register),
):
    _check_bot_signals(body)

    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    verification_token = secrets.token_urlsafe(48)

    user = User(
        email=body.email,
        password_hash=_hash_password(body.password),
        is_email_verified=False,
        email_verification_token=verification_token,
    )
    db.add(user)
    await db.flush()

    send_verification_email(body.email, verification_token)

    access_token = _create_token(str(user.id), "access")
    refresh_token = _create_token(str(user.id), "refresh")
    _set_refresh_cookie(response, refresh_token)
    return TokenResponse(access_token=access_token)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    _rl=Depends(rate_limit_login),
):
    _check_bot_signals(body)

    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if user is None or not _verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_email_verified:
        raise HTTPException(status_code=403, detail="Email not verified")

    access_token = _create_token(str(user.id), "access")
    refresh_token = _create_token(str(user.id), "refresh")
    _set_refresh_cookie(response, refresh_token)
    return TokenResponse(access_token=access_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: Request, db: AsyncSession = Depends(get_db)):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = payload["sub"]
    except (JWTError, KeyError):
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return TokenResponse(access_token=_create_token(str(user.id), "access"))


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("refresh_token")
    return {"detail": "Logged out"}


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    return UserResponse(
        id=str(user.id),
        email=user.email,
        is_email_verified=user.is_email_verified,
        digest_enabled=user.digest_enabled,
        digest_frequency=user.digest_frequency,
    )


# --------------- Digest preferences ---------------

@router.get("/digest-preferences", response_model=DigestPreferencesResponse)
async def get_digest_preferences(user: User = Depends(get_current_user)):
    return DigestPreferencesResponse(
        digest_enabled=user.digest_enabled,
        digest_frequency=user.digest_frequency,
    )


@router.patch("/digest-preferences", response_model=DigestPreferencesResponse)
async def update_digest_preferences(
    body: DigestPreferencesRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.frequency not in ("daily", "weekly"):
        raise HTTPException(status_code=400, detail="Frequency must be 'daily' or 'weekly'")
    
    user.digest_enabled = body.enabled
    user.digest_frequency = body.frequency
    await db.flush()
    
    return DigestPreferencesResponse(
        digest_enabled=user.digest_enabled,
        digest_frequency=user.digest_frequency,
    )


# --------------- Email verification ---------------

@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(body: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(User.email_verification_token == body.token)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired verification link")

    user.is_email_verified = True
    user.email_verification_token = None
    await db.flush()
    return MessageResponse(detail="Email verified successfully")


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(body: ResendVerificationRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user and not user.is_email_verified:
        token = secrets.token_urlsafe(48)
        user.email_verification_token = token
        await db.flush()
        send_verification_email(user.email, token)

    # Always return success to prevent email enumeration
    return MessageResponse(detail="If that email is registered and unverified, a verification link has been sent.")


# --------------- Password reset ---------------

@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(body: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user:
        token = secrets.token_urlsafe(48)
        user.password_reset_token = token
        user.password_reset_expires = datetime.now(timezone.utc) + timedelta(hours=PASSWORD_RESET_EXPIRE_HOURS)
        await db.flush()
        send_password_reset_email(user.email, token)

    # Always return success to prevent email enumeration
    return MessageResponse(detail="If that email is registered, a password reset link has been sent.")


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    result = await db.execute(
        select(User).where(User.password_reset_token == body.token)
    )
    user = result.scalar_one_or_none()

    if not user or not user.password_reset_expires:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")

    if datetime.now(timezone.utc) > user.password_reset_expires:
        user.password_reset_token = None
        user.password_reset_expires = None
        await db.flush()
        raise HTTPException(status_code=400, detail="Reset link has expired. Please request a new one.")

    user.password_hash = _hash_password(body.password)
    user.password_reset_token = None
    user.password_reset_expires = None
    await db.flush()
    return MessageResponse(detail="Password has been reset successfully. You can now sign in.")
