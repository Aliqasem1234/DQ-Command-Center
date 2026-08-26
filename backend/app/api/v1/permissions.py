from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database import get_db
from app.dependencies import get_current_user_from_token
from app.models.user import User
from app.core.rbac import require_permission
from app.core.permissions import ROLES_MANAGE
from app.schemas.role import PermissionResponse
from app.services import role_service

router = APIRouter(prefix="/permissions")


@router.get(
    "",
    response_model=List[PermissionResponse],
    summary="List all permissions",
)
async def list_permissions(
    current_user: User = Depends(require_permission(ROLES_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    return await role_service.list_permissions(db)
