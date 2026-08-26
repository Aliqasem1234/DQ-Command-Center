from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional

from app.database import get_db
from app.dependencies import get_current_user_from_token
from app.models.user import User
from app.core.rbac import require_permission
from app.core.permissions import DEPARTMENTS_MANAGE
from app.schemas.department import (
    DepartmentCreate, DepartmentUpdate, DepartmentResponse, DepartmentListResponse,
)
from app.services import department_service

router = APIRouter(prefix="/departments")


@router.get(
    "",
    response_model=DepartmentListResponse,
    summary="List departments",
)
async def list_departments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    sort_by: str = Query("name"),
    sort_order: str = Query("asc"),
    current_user: User = Depends(require_permission(DEPARTMENTS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    return await department_service.list_departments(
        db, page=page, page_size=page_size,
        search=search, sort_by=sort_by, sort_order=sort_order,
    )


@router.get(
    "/all",
    response_model=list,
    summary="List all active departments (simple)",
)
async def list_all_departments(
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
):
    return await department_service.list_all_departments_simple(db)


@router.get(
    "/{department_id}",
    response_model=DepartmentResponse,
    summary="Get department details",
)
async def get_department(
    department_id: UUID,
    current_user: User = Depends(require_permission(DEPARTMENTS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    dept = await department_service.get_department(db, department_id)
    if dept is None:
        raise HTTPException(status_code=404, detail="Department not found")
    return dept


@router.post(
    "",
    response_model=DepartmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new department",
)
async def create_department(
    request: Request,
    body: DepartmentCreate,
    current_user: User = Depends(require_permission(DEPARTMENTS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await department_service.create_department(
            db, body,
            actor_user_id=current_user.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put(
    "/{department_id}",
    response_model=DepartmentResponse,
    summary="Update a department",
)
async def update_department(
    request: Request,
    department_id: UUID,
    body: DepartmentUpdate,
    current_user: User = Depends(require_permission(DEPARTMENTS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    try:
        dept = await department_service.update_department(
            db, department_id, body,
            actor_user_id=current_user.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        if dept is None:
            raise HTTPException(status_code=404, detail="Department not found")
        return dept
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete(
    "/{department_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a department",
)
async def delete_department(
    request: Request,
    department_id: UUID,
    current_user: User = Depends(require_permission(DEPARTMENTS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    success = await department_service.delete_department(
        db, department_id,
        actor_user_id=current_user.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    if not success:
        raise HTTPException(status_code=404, detail="Department not found")
