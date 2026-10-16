from uuid import UUID
import logging
from typing import Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.audit import AuditLogResponse, AuditLogListResponse

logger = logging.getLogger(__name__)


async def list_audit_logs(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    user_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> AuditLogListResponse:
    query = select(AuditLog).options(
        selectinload(AuditLog.user),
    )
    count_query = select(func.count(AuditLog.id))

    if action:
        query = query.where(AuditLog.action == action)
        count_query = count_query.where(AuditLog.action == action)

    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
        count_query = count_query.where(AuditLog.entity_type == entity_type)

    if user_id:
        # The column is a UUID; comparing it with a raw string only works on
        # some drivers. An unparseable id simply matches nothing.
        try:
            user_uuid = user_id if isinstance(user_id, UUID) else UUID(str(user_id))
        except ValueError:
            user_uuid = None
        query = query.where(AuditLog.user_id == user_uuid)
        count_query = count_query.where(AuditLog.user_id == user_uuid)

    if date_from:
        try:
            dt_from = datetime.fromisoformat(date_from)
            query = query.where(AuditLog.created_at >= dt_from)
            count_query = count_query.where(AuditLog.created_at >= dt_from)
        except ValueError:
            pass

    if date_to:
        try:
            dt_to = datetime.fromisoformat(date_to)
            query = query.where(AuditLog.created_at <= dt_to)
            count_query = count_query.where(AuditLog.created_at <= dt_to)
        except ValueError:
            pass

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    sort_column = getattr(AuditLog, sort_by, AuditLog.created_at)
    if sort_order == "desc":
        sort_column = sort_column.desc()
    query = query.order_by(sort_column)

    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    logs = result.unique().scalars().all()

    items = [_audit_log_to_response(log) for log in logs]
    return AuditLogListResponse(items=items, total=total, page=page, page_size=page_size)


async def get_audit_log(db: AsyncSession, log_id: str) -> Optional[AuditLogResponse]:
    result = await db.execute(
        select(AuditLog).options(
            selectinload(AuditLog.user),
        ).where(AuditLog.id == log_id)
    )
    log = result.scalar_one_or_none()
    if log is None:
        return None
    return _audit_log_to_response(log)


def _audit_log_to_response(log: AuditLog) -> AuditLogResponse:
    return AuditLogResponse(
        id=str(log.id),
        user_id=str(log.user_id) if log.user_id else None,
        user_email=log.user.email if log.user else None,
        user_name=log.user.full_name if log.user else None,
        action=log.action,
        entity_type=log.entity_type,
        entity_id=log.entity_id,
        entity_name=log.entity_name,
        old_values=log.old_values,
        new_values=log.new_values,
        ip_address=log.ip_address,
        user_agent=log.user_agent,
        created_at=log.created_at,
    )
