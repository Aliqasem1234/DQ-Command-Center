from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional

from app.database import get_db
from app.dependencies import get_current_user_from_token
from app.models.user import User
from app.core.rbac import require_permission
from app.core.permissions import USERS_MANAGE
from app.schemas.user import (
    UserCreate, UserUpdate, UserResponse, UserListResponse, UserAssignRole,
)
from app.services import user_service

router = APIRouter(prefix="/users")


async def _ensure_can_manage(db, actor, target_id=None, requested_roles=None):
    try:
        await user_service.ensure_can_manage(db, actor, target_id=target_id, requested_roles=requested_roles)
    except user_service.PrivilegeEscalationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get(
    "",
    response_model=UserListResponse,
    summary="List users (admin)",
)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    department_id: Optional[UUID] = Query(None),
    is_active: Optional[bool] = Query(None),
    sort_by: str = Query("created_at", pattern="^(created_at|updated_at|email|username|full_name|last_login_at)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: User = Depends(require_permission(USERS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    return await user_service.list_users(
        db, page=page, page_size=page_size,
        search=search, role=role,
        department_id=str(department_id) if department_id else None, is_active=is_active,
        sort_by=sort_by, sort_order=sort_order,
    )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user details",
)
async def get_user(
    user_id: UUID,
    current_user: User = Depends(require_permission(USERS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    user = await user_service.get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user (admin)",
)
async def create_user(
    request: Request,
    body: UserCreate,
    current_user: User = Depends(require_permission(USERS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    await _ensure_can_manage(db, current_user, requested_roles=body.roles)
    try:
        return await user_service.admin_create_user(
            db, body,
            actor_user_id=current_user.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update a user",
)
async def update_user(
    request: Request,
    user_id: UUID,
    body: UserUpdate,
    current_user: User = Depends(require_permission(USERS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    await _ensure_can_manage(db, current_user, target_id=user_id)
    try:
        user = await user_service.admin_update_user(
            db, user_id, body,
            actor_user_id=current_user.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate a user",
)
async def delete_user(
    request: Request,
    user_id: UUID,
    current_user: User = Depends(require_permission(USERS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
    await _ensure_can_manage(db, current_user, target_id=user_id)
    success = await user_service.admin_delete_user(
        db, user_id,
        actor_user_id=current_user.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    if not success:
        raise HTTPException(status_code=404, detail="User not found")


@router.put(
    "/{user_id}/roles",
    response_model=UserResponse,
    summary="Assign roles to a user",
)
async def assign_user_roles(
    request: Request,
    user_id: UUID,
    body: UserAssignRole,
    current_user: User = Depends(require_permission(USERS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    await _ensure_can_manage(db, current_user, target_id=user_id, requested_roles=body.roles)
    user = await user_service.assign_user_roles(
        db, user_id, body,
        actor_user_id=current_user.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user
