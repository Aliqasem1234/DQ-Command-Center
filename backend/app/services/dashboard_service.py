import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func, cast, Date
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.role import Role
from app.models.department import Department
from app.models.audit_log import AuditLog
from app.models.login_attempt import LoginAttempt
from app.schemas.dashboard import (
    DashboardStats, DashboardResponse, RegistrationDataPoint,
    LoginDataPoint, RecentActivityItem,
)

logger = logging.getLogger(__name__)


async def get_dashboard_data(db: AsyncSession) -> DashboardResponse:
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    total_users_result = await db.execute(select(func.count(User.id)))
    total_users = total_users_result.scalar() or 0

    active_users_result = await db.execute(
        select(func.count(User.id)).where(User.is_active == True)
    )
    active_users = active_users_result.scalar() or 0

    roles_count_result = await db.execute(select(func.count(Role.id)))
    roles_count = roles_count_result.scalar() or 0

    depts_count_result = await db.execute(
        select(func.count(Department.id)).where(Department.is_active == True)
    )
    departments_count = depts_count_result.scalar() or 0

    audit_today_result = await db.execute(
        select(func.count(AuditLog.id)).where(AuditLog.created_at >= today_start)
    )
    audit_events_today = audit_today_result.scalar() or 0

    registration_chart = []
    for i in range(6, -1, -1):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        count_result = await db.execute(
            select(func.count(User.id)).where(
                User.created_at >= day_start,
                User.created_at < day_end,
            )
        )
        count = count_result.scalar() or 0
        registration_chart.append(
            RegistrationDataPoint(date=day_start.strftime("%Y-%m-%d"), count=count)
        )

    login_chart = []
    for i in range(6, -1, -1):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        count_result = await db.execute(
            select(func.count(LoginAttempt.id)).where(
                LoginAttempt.attempted_at >= day_start,
                LoginAttempt.attempted_at < day_end,
                LoginAttempt.was_successful == True,
            )
        )
        count = count_result.scalar() or 0
        login_chart.append(
            LoginDataPoint(date=day_start.strftime("%Y-%m-%d"), count=count)
        )

    recent_result = await db.execute(
        select(AuditLog).options(
            selectinload(AuditLog.user),
        ).order_by(AuditLog.created_at.desc()).limit(10)
    )
    recent_logs = recent_result.unique().scalars().all()

    recent_activity = []
    for log in recent_logs:
        recent_activity.append(RecentActivityItem(
            id=str(log.id),
            user_name=log.user.full_name if log.user else None,
            user_email=log.user.email if log.user else None,
            action=log.action,
            entity_type=log.entity_type,
            created_at=log.created_at,
        ))

    stats = DashboardStats(
        total_users=total_users,
        active_users=active_users,
        roles_count=roles_count,
        departments_count=departments_count,
        audit_events_today=audit_events_today,
    )

    return DashboardResponse(
        stats=stats,
        registration_chart=registration_chart,
        login_chart=login_chart,
        recent_activity=recent_activity,
    )
