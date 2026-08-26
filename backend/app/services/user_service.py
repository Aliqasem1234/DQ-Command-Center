import logging
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.role import Role, UserRole
from app.models.department import Department
from app.core.security import hash_password
from app.utils.audit_logger import create_audit_log
from app.schemas.user import (
    UserCreate, UserUpdate, UserResponse, UserListResponse, UserAssignRole,
)

logger = logging.getLogger(__name__)


async def list_users(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    role: Optional[str] = None,
    department_id: Optional[str] = None,
    is_active: Optional[bool] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> UserListResponse:
    query = select(User).options(
        selectinload(User.roles).selectinload(UserRole.role),
        selectinload(User.department_rel),
    )
    count_query = select(func.count(User.id))

    if search:
        search_filter = or_(
            User.email.ilike(f"%{search}%"),
            User.username.ilike(f"%{search}%"),
            User.full_name.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    if department_id:
        query = query.where(User.department_id == UUID(department_id))
        count_query = count_query.where(User.department_id == UUID(department_id))

    if is_active is not None:
        query = query.where(User.is_active == is_active)
        count_query = count_query.where(User.is_active == is_active)

    if role:
        query = query.join(UserRole).join(Role).where(Role.name == role)
        count_query = count_query.join(UserRole).join(Role).where(Role.name == role)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    sort_column = getattr(User, sort_by, User.created_at)
    if sort_order == "desc":
        sort_column = sort_column.desc()
    query = query.order_by(sort_column)

    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    users = result.unique().scalars().all()

    items = [_user_to_response(u) for u in users]
    return UserListResponse(items=items, total=total, page=page, page_size=page_size)


async def get_user(db: AsyncSession, user_id: UUID) -> Optional[UserResponse]:
    result = await db.execute(
        select(User).options(
            selectinload(User.roles).selectinload(UserRole.role),
            selectinload(User.department_rel),
        ).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        return None
    return _user_to_response(user)


async def admin_create_user(
    db: AsyncSession,
    data: UserCreate,
    actor_user_id: Optional[UUID] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> UserResponse:
    now = datetime.now(timezone.utc)

    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise ValueError("Email already registered")

    existing = await db.execute(select(User).where(User.username == data.username))
    if existing.scalar_one_or_none():
        raise ValueError("Username already taken")

    department_id = None
    if data.department_id:
        dept_result = await db.execute(select(Department).where(Department.id == UUID(data.department_id)))
        dept = dept_result.scalar_one_or_none()
        if dept:
            department_id = dept.id

    user = User(
        email=data.email,
        username=data.username,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        department=data.department,
        department_id=department_id,
        is_active=True,
        is_verified=True,
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    await db.flush()

    if data.roles:
        roles_result = await db.execute(
            select(Role).where(Role.name.in_(data.roles))
        )
        roles = roles_result.scalars().all()
        for role in roles:
            ur = UserRole(user_id=user.id, role_id=role.id)
            db.add(ur)
        await db.flush()

    await create_audit_log(
        db, actor_user_id, "CREATE", "user", str(user.id), entity_name=data.email,
        new_values={"email": data.email, "username": data.username, "full_name": data.full_name},
        ip_address=ip_address, user_agent=user_agent,
    )
    await db.commit()

    return await get_user(db, user.id)


async def admin_update_user(
    db: AsyncSession,
    user_id: UUID,
    data: UserUpdate,
    actor_user_id: Optional[UUID] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Optional[UserResponse]:
    result = await db.execute(
        select(User).options(
            selectinload(User.roles).selectinload(UserRole.role),
            selectinload(User.department_rel),
        ).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        return None

    old_values = {
        "email": user.email, "full_name": user.full_name,
        "is_active": user.is_active, "department_id": str(user.department_id) if user.department_id else None,
    }

    if data.email is not None and data.email != user.email:
        existing = await db.execute(
            select(User).where(User.email == data.email, User.id != user_id)
        )
        if existing.scalar_one_or_none():
            raise ValueError("Email already in use")
        user.email = data.email
    if data.username is not None and data.username != user.username:
        existing = await db.execute(
            select(User).where(User.username == data.username, User.id != user_id)
        )
        if existing.scalar_one_or_none():
            raise ValueError("Username already taken")
        user.username = data.username
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.department is not None:
        user.department = data.department
    if data.department_id is not None:
        try:
            user.department_id = UUID(data.department_id) if data.department_id else None
        except ValueError:
            user.department_id = None
    if data.is_active is not None:
        user.is_active = data.is_active
    user.updated_at = datetime.now(timezone.utc)

    await db.flush()
    await create_audit_log(
        db, actor_user_id, "UPDATE", "user", str(user.id), entity_name=user.email,
        old_values=old_values,
        new_values={"email": user.email, "full_name": user.full_name, "is_active": user.is_active},
        ip_address=ip_address, user_agent=user_agent,
    )
    await db.commit()

    return _user_to_response(user)


async def admin_delete_user(
    db: AsyncSession,
    user_id: UUID,
    actor_user_id: Optional[UUID] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> bool:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        return False

    user.is_active = False
    user.updated_at = datetime.now(timezone.utc)

    await create_audit_log(
        db, actor_user_id, "DEACTIVATE", "user", str(user.id), entity_name=user.email,
        old_values={"is_active": True},
        new_values={"is_active": False},
        ip_address=ip_address, user_agent=user_agent,
    )
    await db.commit()
    return True


async def assign_user_roles(
    db: AsyncSession,
    user_id: UUID,
    data: UserAssignRole,
    actor_user_id: Optional[UUID] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Optional[UserResponse]:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        return None

    existing_roles = await db.execute(
        select(UserRole)
        .options(selectinload(UserRole.role))
        .where(UserRole.user_id == user_id)
    )
    existing_role_rows = existing_roles.scalars().all()
    existing_role_names = [ur.role.name for ur in existing_role_rows if ur.role]
    for ur in existing_role_rows:
        await db.delete(ur)

    if data.roles:
        roles_result = await db.execute(
            select(Role).where(Role.name.in_(data.roles))
        )
        roles = roles_result.scalars().all()
        for role in roles:
            ur = UserRole(user_id=user.id, role_id=role.id)
            db.add(ur)

    await db.flush()
    await create_audit_log(
        db, actor_user_id, "UPDATE_ROLES", "user", str(user.id), entity_name=user.email,
        old_values={"roles": existing_role_names},
        new_values={"roles": data.roles},
        ip_address=ip_address, user_agent=user_agent,
    )
    await db.commit()

    return await get_user(db, user.id)


def _user_to_response(user: User) -> UserResponse:
    role_names = []
    role_ids = []
    for ur in user.roles:
        if ur.role:
            role_names.append(ur.role.name)
            role_ids.append(str(ur.role.id))

    dept_name = None
    if user.department_rel:
        dept_name = user.department_rel.name

    return UserResponse(
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
        updated_at=user.updated_at,
        roles=role_names,
        role_ids=role_ids,
    )
