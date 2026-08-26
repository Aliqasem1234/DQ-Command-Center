from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.database import get_db
from app.dependencies import get_current_user_from_token
from app.models.user import User
from app.core.rbac import require_permission
from app.core.permissions import ROLES_MANAGE
from app.schemas.role import (
    RoleCreate, RoleUpdate, RoleResponse, RoleListResponse, RolePermissionsUpdate,
)
from app.services import role_service

router = APIRouter(prefix="/roles")


@router.get(
    "/all",
    response_model=list,
    summary="List all roles (simple)",
)
async def list_all_roles(
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
):
    return await role_service.list_roles_simple(db)


@router.get(
    "",
    response_model=RoleListResponse,
    summary="List roles",
)
async def list_roles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_permission(ROLES_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    return await role_service.list_roles(db, page=page, page_size=page_size)


@router.get(
    "/{role_id}",
    response_model=RoleResponse,
    summary="Get role details",
)
async def get_role(
    role_id: UUID,
    current_user: User = Depends(require_permission(ROLES_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    role = await role_service.get_role(db, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found")
    return role


@router.post(
    "",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new role",
)
async def create_role(
    request: Request,
    body: RoleCreate,
    current_user: User = Depends(require_permission(ROLES_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await role_service.create_role(
            db, body,
            actor_user_id=current_user.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put(
    "/{role_id}",
    response_model=RoleResponse,
    summary="Update a role",
)
async def update_role(
    request: Request,
    role_id: UUID,
    body: RoleUpdate,
    current_user: User = Depends(require_permission(ROLES_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    try:
        role = await role_service.update_role(
            db, role_id, body,
            actor_user_id=current_user.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        if role is None:
            raise HTTPException(status_code=404, detail="Role not found")
        return role
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete(
    "/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a role",
)
async def delete_role(
    request: Request,
    role_id: UUID,
    current_user: User = Depends(require_permission(ROLES_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    try:
        success = await role_service.delete_role(
            db, role_id,
            actor_user_id=current_user.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        if not success:
            raise HTTPException(status_code=404, detail="Role not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put(
    "/{role_id}/permissions",
    response_model=RoleResponse,
    summary="Update role permissions",
)
async def update_role_permissions(
    request: Request,
    role_id: UUID,
    body: RolePermissionsUpdate,
    current_user: User = Depends(require_permission(ROLES_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    role = await role_service.update_role_permissions(
        db, role_id, body,
        actor_user_id=current_user.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found")
    return role
