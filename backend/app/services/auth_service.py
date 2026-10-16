import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from uuid import UUID

import secrets
from sqlalchemy import select, func, delete, inspect, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.role import UserRole, Role, RolePermission
from app.core.seed_secure import SYSTEM_PERMISSIONS

ALL_PERMISSION_CODES = [p["code"] for p in SYSTEM_PERMISSIONS]
from app.core.security import (
    hash_password,
    verify_password,
    hash_token,
    generate_token_string,
    create_tokens,
    rotate_refresh_token,
    revoke_refresh_token,
)
from app.models.login_attempt import LoginAttempt
from app.models.token import PasswordResetToken, EmailVerificationToken, RefreshToken
from app.models.user import User
from app.schemas.auth import UserResponse
from app.services.email_service import email_service

logger = logging.getLogger(__name__)


DEFAULT_ROLE_NAME = "User"


def normalize_email(email: str) -> str:
    # Emails are compared case-insensitively so "Anna@x.se" and "anna@x.se"
    # can't become two accounts, and login works regardless of casing.
    return email.strip().lower()


async def _username_taken(db: AsyncSession, username: str) -> bool:
    result = await db.execute(select(User.id).where(User.username == username))
    return result.first() is not None


async def generate_unique_username(db: AsyncSession, email: str) -> str:
    base = re.sub(r"[^a-z0-9._-]", "", email.split("@")[0].lower())[:40]
    if len(base) < 3:
        base = f"{base}user"
    candidate = base
    while await _username_taken(db, candidate):
        candidate = f"{base}-{secrets.token_hex(3)}"
    return candidate


async def assign_default_role(db: AsyncSession, user: User) -> None:
    """Give a user the least-privileged system role if they have no role yet.

    New accounts previously got no role at all until email verification,
    which never happens without SMTP - so a freshly registered user could
    log in but every page answered 403.
    """
    from app.models.role import Role

    existing = await db.execute(select(UserRole.id).where(UserRole.user_id == user.id))
    if existing.first() is not None:
        return
    role = (await db.execute(select(Role).where(Role.name == DEFAULT_ROLE_NAME))).scalar_one_or_none()
    if role is None:
        logger.error(f"Default role '{DEFAULT_ROLE_NAME}' missing; user {user.id} has no role")
        return
    db.add(UserRole(user_id=user.id, role_id=role.id))
    await db.flush()


async def register_user(
    db: AsyncSession,
    email: str,
    password: str,
    full_name: str,
    username: Optional[str] = None,
) -> Tuple[User, str]:
    now = datetime.now(timezone.utc)
    email = normalize_email(email)

    result = await db.execute(select(User).where(func.lower(User.email) == email))
    if result.scalar_one_or_none():
        raise ValueError("Email already registered")

    if username:
        if await _username_taken(db, username):
            raise ValueError("Username already taken")
    else:
        username = await generate_unique_username(db, email)

    user = User(
        email=email,
        username=username,
        password_hash=hash_password(password),
        full_name=full_name,
        is_active=True,
        is_verified=False,
        is_super_admin=False,
        failed_login_attempts=0,
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    await db.flush()
    await assign_default_role(db, user)

    # Generate email verification token
    token_str = generate_token_string()
    token_hash_val = hash_token(token_str)
    verify_token = EmailVerificationToken(
        user_id=user.id,
        token_hash=token_hash_val,
        expires_at=now + timedelta(hours=24),
        created_at=now,
    )
    db.add(verify_token)
    await db.flush()

    await db.commit()

    # Send verification email in background
    await email_service.send_verification_email(email, token_str)

    return user, token_str


async def login_user(
    db: AsyncSession,
    email: str,
    password: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Tuple[User, str, str]:
    now = datetime.now(timezone.utc)
    email = normalize_email(email)

    result = await db.execute(
        select(User)
        .options(
            selectinload(User.roles)
            .selectinload(UserRole.role)
            .selectinload(Role.role_permissions)
            .selectinload(RolePermission.permission)
        )
        .where(func.lower(User.email) == email)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise ValueError("Invalid email or password")

    if not user.is_active:
        raise ValueError("Account is deactivated")

    if user.is_locked:
        raise ValueError("Account is locked. Try again later.")

    login_attempt = LoginAttempt(
        user_id=user.id,
        ip_address=ip_address,
        user_agent=user_agent,
        was_successful=False,
        attempted_at=now,
    )

    if not verify_password(password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.LOCKOUT_THRESHOLD:
            user.locked_until = now + timedelta(minutes=settings.LOCKOUT_DURATION_MINUTES)
            logger.warning(f"Account locked for {user.email} due to {user.failed_login_attempts} failed attempts")
        db.add(login_attempt)
        await db.flush()
        await db.commit()
        raise ValueError("Invalid email or password")

    # Successful login
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = now

    login_attempt.was_successful = True
    db.add(login_attempt)

    access_token, refresh_token, _ = await create_tokens(db, user)
    await db.flush()
    await db.commit()

    return user, access_token, refresh_token


async def refresh_user_tokens(db: AsyncSession, refresh_token: str) -> Tuple[str, str]:
    result = await rotate_refresh_token(db, refresh_token)
    if result is None:
        raise ValueError("Invalid or expired refresh token")
    access_token, new_refresh_token, _ = result
    await db.commit()
    return access_token, new_refresh_token


async def logout_user(db: AsyncSession, refresh_token: str) -> bool:
    success = await revoke_refresh_token(db, refresh_token)
    if success:
        await db.commit()
    return success


async def forgot_password(db: AsyncSession, email: str) -> Optional[str]:
    now = datetime.now(timezone.utc)
    email = normalize_email(email)

    result = await db.execute(select(User).where(func.lower(User.email) == email))
    user = result.scalar_one_or_none()

    if user is None:
        return None  # Don't reveal if email exists

    # Revoke old reset tokens
    await db.execute(
        delete(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.is_used == False,
        )
    )

    token_str = generate_token_string()
    token_hash_val = hash_token(token_str)
    reset_token = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash_val,
        expires_at=now + timedelta(hours=1),
        created_at=now,
    )
    db.add(reset_token)
    await db.flush()
    await db.commit()

    await email_service.send_password_reset_email(email, token_str)
    return token_str


async def reset_password(db: AsyncSession, token: str, new_password: str) -> bool:
    now = datetime.now(timezone.utc)
    token_hash_val = hash_token(token)

    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash_val,
            PasswordResetToken.is_used == False,
            PasswordResetToken.expires_at > now,
        )
    )
    reset_token = result.scalar_one_or_none()
    if reset_token is None:
        raise ValueError("Invalid or expired reset token")

    result = await db.execute(select(User).where(User.id == reset_token.user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise ValueError("User not found")

    user.password_hash = hash_password(new_password)
    user.failed_login_attempts = 0
    user.locked_until = None
    reset_token.is_used = True

    # A reset is how someone recovers a compromised account, so every
    # existing session must end: revoke all refresh tokens. (This previously
    # deleted the reset tokens instead, leaving old sessions valid for days.)
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.is_revoked == False)  # noqa: E712
        .values(is_revoked=True)
    )
    await db.execute(
        delete(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
        )
    )

    await db.flush()
    await db.commit()
    return True


async def verify_email(db: AsyncSession, token: str) -> bool:
    now = datetime.now(timezone.utc)
    token_hash_val = hash_token(token)

    result = await db.execute(
        select(EmailVerificationToken).where(
            EmailVerificationToken.token_hash == token_hash_val,
            EmailVerificationToken.is_used == False,
            EmailVerificationToken.expires_at > now,
        )
    )
    verify_token = result.scalar_one_or_none()
    if verify_token is None:
        raise ValueError("Invalid or expired verification token")

    result = await db.execute(select(User).where(User.id == verify_token.user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise ValueError("User not found")

    user.is_verified = True
    verify_token.is_used = True

    await db.flush()
    await db.commit()
    return True


async def update_profile(
    db: AsyncSession,
    user: User,
    full_name: str,
) -> User:
    user.full_name = full_name
    user.updated_at = datetime.now(timezone.utc)

    await db.flush()
    await db.commit()
    return user


async def change_password(
    db: AsyncSession,
    user: User,
    current_password: str,
    new_password: str,
) -> bool:
    if not verify_password(current_password, user.password_hash):
        raise ValueError("Current password is incorrect")

    user.password_hash = hash_password(new_password)

    await db.flush()
    await db.commit()
    return True


def get_permission_codes(user: User) -> list[str]:
    """Effective permission codes, mirroring app.core.rbac.require_permission.

    Only reads relationships that are already loaded (login and
    get_current_user eager-load them), so it never triggers lazy IO.
    """
    if user.is_super_admin:
        return sorted(ALL_PERMISSION_CODES)
    loaded = inspect(user).unloaded
    if "roles" in loaded:
        return []
    codes = set()
    for ur in user.roles:
        role = ur.role
        if role is None or "role_permissions" in inspect(role).unloaded:
            continue
        for rp in role.role_permissions:
            if rp.permission is not None:
                codes.add(rp.permission.code)
    return sorted(codes)


def user_to_response(user: User) -> UserResponse:
    dept_name = None
    if hasattr(user, 'department_rel') and user.department_rel:
        dept_name = user.department_rel.name

    roles = []
    if user.roles:
        roles = [ur.role.name for ur in user.roles if ur.role]

    return UserResponse(
        permissions=get_permission_codes(user),
        id=str(user.id),
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        department=user.department,
        department_id=str(user.department_id) if user.department_id else None,
        department_name=dept_name,
        is_active=user.is_active,
        is_verified=user.is_verified,
        is_super_admin=user.is_super_admin,
        created_at=user.created_at,
        roles=roles,
    )
