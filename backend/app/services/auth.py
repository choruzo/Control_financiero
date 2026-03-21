from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import bcrypt as _bcrypt
from fastapi import HTTPException, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.refresh_token import RefreshToken
from app.models.user import User

# Precomputed hash used to normalize timing when a user is not found,
# preventing email enumeration via response-time analysis.
_DUMMY_HASH: str = _bcrypt.hashpw(b"__dummy__", _bcrypt.gensalt(rounds=12)).decode("utf-8")


# ── Password helpers ──────────────────────────────────────────────────────────

def get_password_hash(password: str) -> str:
    return _bcrypt.hashpw(password.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return _bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ── JWT helpers ───────────────────────────────────────────────────────────────

def _create_token(data: dict, expires_delta: timedelta) -> str:
    payload = {**data, "exp": datetime.now(UTC) + expires_delta}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: UUID, email: str) -> str:
    return _create_token(
        {"sub": str(user_id), "email": email, "type": "access"},
        timedelta(minutes=settings.jwt_access_token_expire_minutes),
    )


def create_refresh_token(user_id: UUID) -> tuple[str, UUID, datetime]:
    jti = uuid4()
    expires_at = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_token_expire_days)
    token = _create_token(
        {"sub": str(user_id), "type": "refresh", "jti": str(jti)},
        timedelta(days=settings.jwt_refresh_token_expire_days),
    )
    return token, jti, expires_at


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


# ── User CRUD ─────────────────────────────────────────────────────────────────

async def create_user(db: AsyncSession, email: str, password: str) -> User:
    email = email.lower().strip()
    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    user = User(email=email, hashed_password=get_password_hash(password))
    db.add(user)
    await db.flush()
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:
    email = email.lower().strip()
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    # Always run bcrypt comparison to neutralise timing-based user enumeration.
    hash_to_check = user.hashed_password if user else _DUMMY_HASH
    if not verify_password(password, hash_to_check) or user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return user


# ── Token issuance & rotation ─────────────────────────────────────────────────

async def issue_tokens(db: AsyncSession, user: User) -> dict:
    access_token = create_access_token(user.id, user.email)
    refresh_jwt, jti, expires_at = create_refresh_token(user.id)

    db_refresh = RefreshToken(user_id=user.id, jti=jti, expires_at=expires_at)
    db.add(db_refresh)
    await db.flush()

    return {"access_token": access_token, "refresh_token": refresh_jwt, "token_type": "bearer"}


async def rotate_refresh_token(db: AsyncSession, refresh_jwt: str) -> dict:
    payload = decode_token(refresh_jwt)

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    jti = UUID(payload["jti"])
    user_id = UUID(payload["sub"])

    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.jti == jti,
            RefreshToken.user_id == user_id,
            RefreshToken.revoked.is_(False),
        )
    )
    db_token = result.scalar_one_or_none()
    if db_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Revoke the consumed refresh token before issuing new pair.
    db_token.revoked = True
    await db.flush()

    return await issue_tokens(db, user)
