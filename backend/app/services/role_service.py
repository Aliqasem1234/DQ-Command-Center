import logging
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.role import Role, UserRole, Permission, RolePermission
from app.utils.audit_logger import create_audit_log
from app.schemas.role import (
    RoleCreate, RoleUpdate, RoleResponse, RoleListResponse,
    PermissionResponse, RolePermissionsUpdate,
)

logger = logging.getLogger(__name__)


async def list_roles(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
) -> RoleListResponse:
    result = await db.execute(
        select(Role).options(
            selectinload(Role.role_permissions).selectinload(RolePermission.permission),
        ).order_by(Role.name)
    )
    roles = result.unique().scalars().all()

    items = []
    for role in roles:
        user_count_result = await db.execute(
            select(func.count(UserRole.id)).where(UserRole.role_id == role.id)
        )
        user_count = user_count_result.scalar() or 0
        items.append(_role_to_response(role, user_count))

    return RoleListResponse(
        items=items, total=len(items), page=page, page_size=page_size
    )


async def get_role(db: AsyncSession, role_id: UUID) -> Optional[RoleResponse]:
    result = await db.execute(
        select(Role).options(
            selectinload(Role.role_permissions).selectinload(RolePermission.permission),
        ).where(Role.id == role_id)
    )
    role = result.scalar_one_or_none()
    if role is None:
        return None

    user_count_result = await db.execute(
        select(func.count(UserRole.id)).where(UserRole.role_id == role.id)
    )
    user_count = user_count_result.scalar() or 0
    return _role_to_response(role, user_count)


async def create_role(
    db: AsyncSession,
    data: RoleCreate,
    actor_user_id: Optional[UUID] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> RoleResponse:
    now = datetime.now(timezone.utc)

    existing = await db.execute(select(Role).where(Role.name == data.name))
    if existing.scalar_one_or_none():
        raise ValueError("Role with this name already exists")

    role = Role(
        name=data.name,
        description=data.description,
        is_system=False,
        created_at=now,
        updated_at=now,
    )
    db.add(role)
    await db.flush()

    if data.permission_ids:
        perms_result = await db.execute(
            select(Permission).where(Permission.id.in_([UUID(pid) for pid in data.permission_ids]))
        )
        for perm in perms_result.scalars().all():
            rp = RolePermission(role_id=role.id, permission_id=perm.id)
            db.add(rp)
        await db.flush()

    await create_audit_log(
        db, actor_user_id, "CREATE", "role", str(role.id), entity_name=data.name,
        new_values={"name": data.name, "permissions": data.permission_ids},
        ip_address=ip_address, user_agent=user_agent,
    )
    await db.commit()

    return await get_role(db, role.id)


async def update_role(
    db: AsyncSession,
    role_id: UUID,
    data: RoleUpdate,
    actor_user_id: Optional[UUID] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Optional[RoleResponse]:
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if role is None:
        return None

    if role.is_system:
        raise ValueError("Cannot modify system roles")

    old_values = {"name": role.name, "description": role.description}

    if data.name is not None and data.name != role.name:
        existing = await db.execute(
            select(Role).where(Role.name == data.name, Role.id != role_id)
        )
        if existing.scalar_one_or_none():
            raise ValueError("Role name already exists")
        role.name = data.name
    if data.description is not None:
        role.description = data.description
    role.updated_at = datetime.now(timezone.utc)

    await db.flush()
    await create_audit_log(
        db, actor_user_id, "UPDATE", "role", str(role.id), entity_name=role.name,
        old_values=old_values, new_values={"name": role.name, "description": role.description},
        ip_address=ip_address, user_agent=user_agent,
    )
    await db.commit()

    return await get_role(db, role.id)


async def delete_role(
    db: AsyncSession,
    role_id: UUID,
    actor_user_id: Optional[UUID] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> bool:
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if role is None:
        return False

    if role.is_system:
        raise ValueError("Cannot delete system roles")

    await create_audit_log(
        db, actor_user_id, "DELETE", "role", str(role.id), entity_name=role.name,
        old_values={"name": role.name},
        ip_address=ip_address, user_agent=user_agent,
    )

    await db.delete(role)
    await db.commit()
    return True


async def update_role_permissions(
    db: AsyncSession,
    role_id: UUID,
    data: RolePermissionsUpdate,
    actor_user_id: Optional[UUID] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Optional[RoleResponse]:
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if role is None:
        return None

    existing_rps = await db.execute(
        select(RolePermission).where(RolePermission.role_id == role_id)
    )
    for rp in existing_rps.scalars().all():
        await db.delete(rp)
    # Flush the deletes first: the unit of work would otherwise emit the
    # INSERTs before them and trip the unique (owner, link) constraint
    # whenever an existing link is kept.
    await db.flush()

    if data.permission_ids:
        perms_result = await db.execute(
            select(Permission).where(Permission.id.in_([UUID(pid) for pid in data.permission_ids]))
        )
        for perm in perms_result.scalars().all():
            rp = RolePermission(role_id=role.id, permission_id=perm.id)
            db.add(rp)

    await db.flush()
    await create_audit_log(
        db, actor_user_id, "UPDATE_PERMISSIONS", "role", str(role.id), entity_name=role.name,
        new_values={"permission_ids": data.permission_ids},
        ip_address=ip_address, user_agent=user_agent,
    )
    await db.commit()

    return await get_role(db, role.id)


async def list_permissions(db: AsyncSession) -> List[PermissionResponse]:
    result = await db.execute(
        select(Permission).order_by(Permission.module, Permission.name)
    )
    permissions = result.scalars().all()
    return [
        PermissionResponse(
            id=str(p.id), name=p.name, code=p.code,
            module=p.module, description=p.description,
        )
        for p in permissions
    ]


async def list_roles_simple(db: AsyncSession) -> List[dict]:
    result = await db.execute(select(Role).order_by(Role.name))
    roles = result.scalars().all()
    return [{"id": str(r.id), "name": r.name} for r in roles]


def _role_to_response(role: Role, user_count: int = 0) -> RoleResponse:
    permissions = []
    for rp in role.role_permissions:
        if rp.permission:
            permissions.append(PermissionResponse(
                id=str(rp.permission.id),
                name=rp.permission.name,
                code=rp.permission.code,
                module=rp.permission.module,
                description=rp.permission.description,
            ))

    return RoleResponse(
        id=str(role.id),
        name=role.name,
        description=role.description,
        is_system=role.is_system,
        created_at=role.created_at,
        updated_at=role.updated_at,
        user_count=user_count,
        permissions=permissions,
    )
