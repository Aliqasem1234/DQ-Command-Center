from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.dependencies import get_current_user_from_token
from app.models.user import User
from app.core.rbac import require_permission
from app.core.permissions import AUDIT_VIEW
from app.schemas.audit import AuditLogResponse, AuditLogListResponse
from app.services import audit_service

router = APIRouter(prefix="/audit")


@router.get(
    "/logs",
    response_model=AuditLogListResponse,
    summary="List audit logs",
)
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    action: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    current_user: User = Depends(require_permission(AUDIT_VIEW)),
    db: AsyncSession = Depends(get_db),
):
    return await audit_service.list_audit_logs(
        db, page=page, page_size=page_size,
        action=action, entity_type=entity_type,
        user_id=user_id,
        date_from=date_from, date_to=date_to,
        sort_by=sort_by, sort_order=sort_order,
    )


@router.get(
    "/logs/{log_id}",
    response_model=AuditLogResponse,
    summary="Get audit log detail",
)
async def get_audit_log(
    log_id: str,
    current_user: User = Depends(require_permission(AUDIT_VIEW)),
    db: AsyncSession = Depends(get_db),
):
    log = await audit_service.get_audit_log(db, log_id)
    if log is None:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return log
