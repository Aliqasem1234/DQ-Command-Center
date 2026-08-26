"""
Audit log analytics service for compliance and monitoring
"""

import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.user import User

logger = logging.getLogger(__name__)


class AuditAnalyticsService:
    """Service for analyzing audit logs"""

    @staticmethod
    async def get_activity_summary(
        db: AsyncSession,
        days: int = 30,
        user_id: str = None,
    ) -> dict:
        """Get summary of audit activity"""
        try:
            start_date = datetime.now(timezone.utc) - timedelta(days=days)

            query = select(AuditLog).where(AuditLog.created_at >= start_date)

            if user_id:
                query = query.where(AuditLog.user_id == user_id)

            result = await db.execute(query)
            logs = result.scalars().all()

            if not logs:
                return {
                    "total_actions": 0,
                    "actions_by_type": {},
                    "actions_by_entity": {},
                    "top_users": [],
                }

            # Count by action type
            actions_by_type = {}
            for log in logs:
                actions_by_type[log.action] = actions_by_type.get(log.action, 0) + 1

            # Count by entity type
            actions_by_entity = {}
            for log in logs:
                actions_by_entity[log.entity_type] = actions_by_entity.get(log.entity_type, 0) + 1

            # Get top users
            user_counts = {}
            for log in logs:
                if log.user_id:
                    user_counts[str(log.user_id)] = user_counts.get(str(log.user_id), 0) + 1

            top_users = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:5]

            return {
                "total_actions": len(logs),
                "actions_by_type": actions_by_type,
                "actions_by_entity": actions_by_entity,
                "top_users": [{"user_id": uid, "action_count": count} for uid, count in top_users],
            }

        except Exception as e:
            logger.error(f"Error getting activity summary: {str(e)}")
            return {}

    @staticmethod
    async def get_user_activity(
        db: AsyncSession,
        user_id: str,
        limit: int = 20,
    ) -> list[dict]:
        """Get activity log for a specific user"""
        try:
            query = (
                select(AuditLog)
                .where(AuditLog.user_id == user_id)
                .order_by(AuditLog.created_at.desc())
                .limit(limit)
            )

            result = await db.execute(query)
            logs = result.scalars().all()

            return [
                {
                    "action": log.action,
                    "entity_type": log.entity_type,
                    "entity_id": log.entity_id,
                    "created_at": log.created_at.isoformat(),
                    "ip_address": log.ip_address,
                    "user_agent": log.user_agent,
                }
                for log in logs
            ]

        except Exception as e:
            logger.error(f"Error getting user activity: {str(e)}")
            return []

    @staticmethod
    async def get_entity_history(
        db: AsyncSession,
        entity_type: str,
        entity_id: str,
    ) -> list[dict]:
        """Get change history for a specific entity"""
        try:
            query = (
                select(AuditLog)
                .where(
                    and_(
                        AuditLog.entity_type == entity_type,
                        AuditLog.entity_id == entity_id,
                    )
                )
                .order_by(AuditLog.created_at.desc())
            )

            result = await db.execute(query)
            logs = result.scalars().all()

            return [
                {
                    "action": log.action,
                    "performed_at": log.created_at.isoformat(),
                    "performed_by": log.user_id,
                    "old_values": log.old_values,
                    "new_values": log.new_values,
                }
                for log in logs
            ]

        except Exception as e:
            logger.error(f"Error getting entity history: {str(e)}")
            return []

    @staticmethod
    async def get_compliance_report(
        db: AsyncSession,
        days: int = 30,
    ) -> dict:
        """Get compliance report from audit logs"""
        try:
            start_date = datetime.now(timezone.utc) - timedelta(days=days)

            # Count all actions
            total_result = await db.execute(
                select(func.count(AuditLog.id)).where(AuditLog.created_at >= start_date)
            )
            total_actions = total_result.scalar() or 0

            # Count deletes (for compliance tracking)
            deletes_result = await db.execute(
                select(func.count(AuditLog.id)).where(
                    and_(
                        AuditLog.action == "DELETE",
                        AuditLog.created_at >= start_date,
                    )
                )
            )
            deletes = deletes_result.scalar() or 0

            # Count creates
            creates_result = await db.execute(
                select(func.count(AuditLog.id)).where(
                    and_(
                        AuditLog.action == "CREATE",
                        AuditLog.created_at >= start_date,
                    )
                )
            )
            creates = creates_result.scalar() or 0

            # Count updates
            updates_result = await db.execute(
                select(func.count(AuditLog.id)).where(
                    and_(
                        AuditLog.action == "UPDATE",
                        AuditLog.created_at >= start_date,
                    )
                )
            )
            updates = updates_result.scalar() or 0

            # Count actions by unique users
            users_result = await db.execute(
                select(func.count(func.distinct(AuditLog.user_id))).where(
                    AuditLog.created_at >= start_date
                )
            )
            unique_users = users_result.scalar() or 0

            return {
                "reporting_period_days": days,
                "total_audit_actions": total_actions,
                "creates": creates,
                "updates": updates,
                "deletes": deletes,
                "unique_users": unique_users,
                "report_timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Error generating compliance report: {str(e)}")
            return {}
