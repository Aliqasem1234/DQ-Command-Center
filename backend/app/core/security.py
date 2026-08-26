import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.token import RefreshToken
from app.models.user import User

pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__time_cost=3,
    argon2__memory_cost=65536,
    argon2__parallelism=4,
    argon2__hash_len=32,
)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: UUID) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "type": "access",
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: UUID, token_id: UUID) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(user_id),
        "jti": str(token_id),
        "exp": expire,
        "type": "refresh",
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def generate_token_string() -> str:
    return secrets.token_urlsafe(48)


async def get_current_user(db: AsyncSession, token: str) -> Optional[User]:
    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        return None

    user_id = payload.get("sub")
    if user_id is None:
        return None

    try:
        result = await db.execute(select(User).where(User.id == UUID(user_id)))
        return result.scalar_one_or_none()
    except (ValueError, Exception):
        return None


async def create_tokens(db: AsyncSession, user: User) -> Tuple[str, str, RefreshToken]:
    refresh_token_str = generate_token_string()
    token_id = UUID(bytes=secrets.token_bytes(16))

    access_token = create_access_token(user.id)
    refresh_token_str_jwt = create_refresh_token(user.id, token_id)

    token_hash = hash_token(refresh_token_str_jwt)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    db_token = RefreshToken(
        id=token_id,
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
        created_at=datetime.now(timezone.utc),
    )
    db.add(db_token)
    await db.flush()

    return access_token, refresh_token_str_jwt, db_token


async def rotate_refresh_token(db: AsyncSession, old_token: str) -> Optional[Tuple[str, str, RefreshToken]]:
    payload = decode_token(old_token)
    if payload is None or payload.get("type") != "refresh":
        return None

    token_id = payload.get("jti")
    user_id = payload.get("sub")
    if token_id is None or user_id is None:
        return None

    try:
        token_uuid = UUID(token_id)
        user_uuid = UUID(user_id)
    except ValueError:
        return None

    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.id == token_uuid,
            RefreshToken.is_revoked == False,
        )
    )
    db_token = result.scalar_one_or_none()
    if db_token is None:
        return None

    token_hash = hash_token(old_token)
    if db_token.token_hash != token_hash:
        return None

    expires_at = db_token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return None

    db_token.is_revoked = True
    await db.flush()

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()
    if user is None:
        return None

    return await create_tokens(db, user)


async def revoke_refresh_token(db: AsyncSession, token: str) -> bool:
    payload = decode_token(token)
    if payload is None or payload.get("type") != "refresh":
        return False

    token_id = payload.get("jti")
    if token_id is None:
        return False

    try:
        token_uuid = UUID(token_id)
    except ValueError:
        return False

    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.id == token_uuid,
            RefreshToken.is_revoked == False,
        )
    )
    db_token = result.scalar_one_or_none()
    if db_token is None:
        return False

    token_hash = hash_token(token)
    if db_token.token_hash != token_hash:
        return False

    db_token.is_revoked = True
    await db.flush()
    return True
