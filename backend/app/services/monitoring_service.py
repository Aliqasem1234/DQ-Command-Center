"""
Data Quality Monitoring Service

Provides comprehensive monitoring, alerting, and trend analysis for data quality rules.
"""

import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func, and_, true, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.data_quality_rule import DataQualityResult, DataQualityRule, DataQualityDimension
from app.core.dataset_access import visible_rules_clause


def _rule_scope(user):
    return visible_rules_clause(user) if user is not None else true()


def _result_scope(user):
    return DataQualityResult.rule_id.in_(select(DataQualityRule.id).where(_rule_scope(user)))

logger = logging.getLogger(__name__)


class MonitoringService:
    """Service for monitoring data quality metrics and trends"""

    @staticmethod
    async def get_pass_rate_trend(
        db: AsyncSession,
        days: int = 30,
        dimension: str = None,
        user=None,
    ) -> list[dict]:
        """Get pass rate trend over time"""
        try:
            start_date = datetime.now(timezone.utc) - timedelta(days=days)

            query = select(
                func.date(DataQualityResult.execution_timestamp).label("date"),
                func.count(DataQualityResult.id).label("total_results"),
                func.sum(
                    case((DataQualityResult.status == "passed", 1), else_=0)
                ).label("passed_results"),
            ).where(DataQualityResult.execution_timestamp >= start_date, _result_scope(user))

            if dimension:
                try:
                    dim = DataQualityDimension(dimension.lower())
                    query = query.where(
                        DataQualityResult.rule_id.in_(
                            select(DataQualityRule.id).where(DataQualityRule.dimension == dim)
                        )
                    )
                except ValueError:
                    pass

            query = query.group_by(func.date(DataQualityResult.execution_timestamp)).order_by(
                func.date(DataQualityResult.execution_timestamp)
            )

            result = await db.execute(query)
            rows = result.all()

            return [
                {
                    "date": str(row[0]),
                    "total_results": row[1] or 0,
                    "passed_results": row[2] or 0,
                    "pass_rate": (
                        (row[2] / row[1] * 100) if row[1] and row[1] > 0 else 0
                    ),
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"Error calculating pass rate trend: {str(e)}")
            return []

    @staticmethod
    async def get_dimension_trends(
        db: AsyncSession,
        days: int = 30,
        user=None,
    ) -> list[dict]:
        """Get pass rate trends by dimension"""
        try:
            trends = []

            for dimension in DataQualityDimension:
                trend = await MonitoringService.get_pass_rate_trend(
                    db, days=days, dimension=dimension.value, user=user
                )
                if trend:
                    trends.append(
                        {
                            "dimension": dimension.value,
                            "trend": trend,
                            "current_pass_rate": trend[-1]["pass_rate"] if trend else 0,
                            "average_pass_rate": (
                                sum(t["pass_rate"] for t in trend) / len(trend)
                                if trend
                                else 0
                            ),
                        }
                    )

            return trends

        except Exception as e:
            logger.error(f"Error calculating dimension trends: {str(e)}")
            return []

    @staticmethod
    async def get_rule_performance(
        db: AsyncSession,
        rule_id: str = None,
        limit: int = 10,
        user=None,
    ) -> list[dict]:
        """Get performance metrics for rules (pass rate, failure trends)"""
        try:
            query = select(
                DataQualityRule.id,
                DataQualityRule.name,
                DataQualityRule.dimension,
                DataQualityRule.severity,
                func.count(DataQualityResult.id).label("total_executions"),
                func.sum(
                    case((DataQualityResult.status == "passed", 1), else_=0)
                ).label("passed_executions"),
                func.sum(
                    case((DataQualityResult.status == "failed", 1), else_=0)
                ).label("failed_executions"),
                func.avg(DataQualityResult.execution_duration_ms).label("avg_duration"),
                func.max(DataQualityResult.execution_timestamp).label("last_execution"),
            ).join(DataQualityResult, DataQualityRule.id == DataQualityResult.rule_id).where(_rule_scope(user))

            if rule_id:
                query = query.where(DataQualityRule.id == rule_id)

            query = query.group_by(
                DataQualityRule.id,
                DataQualityRule.name,
                DataQualityRule.dimension,
                DataQualityRule.severity,
            ).order_by(
                func.sum(
                    case((DataQualityResult.status == "failed", 1), else_=0)
                ).desc()
            ).limit(limit)

            result = await db.execute(query)
            rows = result.all()

            return [
                {
                    "rule_id": str(row[0]),
                    "rule_name": row[1],
                    "dimension": row[2].value if row[2] else None,
                    "severity": row[3].value if row[3] else None,
                    "total_executions": row[4] or 0,
                    "passed_executions": row[5] or 0,
                    "failed_executions": row[6] or 0,
                    "pass_rate": (
                        (row[5] / row[4] * 100) if row[4] and row[4] > 0 else 0
                    ),
                    "avg_duration_ms": float(row[7]) if row[7] else 0,
                    "last_execution": str(row[8]) if row[8] else None,
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"Error calculating rule performance: {str(e)}")
            return []

    @staticmethod
    async def get_failing_rules(
        db: AsyncSession,
        limit: int = 10,
        user=None,
    ) -> list[dict]:
        """Get top failing rules (most recent failures)"""
        try:
            # Get most recent failed results
            failed_subquery = (
                select(
                    DataQualityResult.rule_id,
                    func.max(DataQualityResult.execution_timestamp).label(
                        "last_failure"
                    ),
                )
                .where(DataQualityResult.status == "failed")
                .group_by(DataQualityResult.rule_id)
                .subquery()
            )

            query = select(
                DataQualityRule.id,
                DataQualityRule.name,
                DataQualityRule.severity,
                failed_subquery.c.last_failure,
                func.count(DataQualityResult.id).label("consecutive_failures"),
            ).join(
                failed_subquery, DataQualityRule.id == failed_subquery.c.rule_id
            ).join(
                DataQualityResult, DataQualityRule.id == DataQualityResult.rule_id
            ).where(
                and_(
                    DataQualityResult.status == "failed",
                    DataQualityResult.execution_timestamp >= failed_subquery.c.last_failure - timedelta(days=1),
                    _rule_scope(user),
                )
            ).group_by(
                DataQualityRule.id,
                DataQualityRule.name,
                DataQualityRule.severity,
                failed_subquery.c.last_failure,
            ).order_by(
                failed_subquery.c.last_failure.desc()
            ).limit(limit)

            result = await db.execute(query)
            rows = result.all()

            return [
                {
                    "rule_id": str(row[0]),
                    "rule_name": row[1],
                    "severity": row[2].value if row[2] else None,
                    "last_failure": str(row[3]) if row[3] else None,
                    "consecutive_failures": row[4] or 0,
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"Error getting failing rules: {str(e)}")
            return []

    @staticmethod
    async def get_health_score(db: AsyncSession, user=None) -> dict:
        """Calculate overall data quality health score (0-100)"""
        try:
            # Get results from last 7 days
            seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)

            total_result = await db.execute(
                select(func.count(DataQualityResult.id)).where(_result_scope(user)).where(
                    DataQualityResult.execution_timestamp >= seven_days_ago
                )
            )
            total = total_result.scalar() or 0

            passed_result = await db.execute(
                select(func.count(DataQualityResult.id)).where(_result_scope(user)).where(
                    and_(
                        DataQualityResult.status == "passed",
                        DataQualityResult.execution_timestamp >= seven_days_ago,
                    )
                )
            )
            passed = passed_result.scalar() or 0

            # Calculate pass rate
            pass_rate = (passed / total * 100) if total > 0 else 0

            # Calculate trend (compare to previous 7 days)
            fourteen_days_ago = datetime.now(timezone.utc) - timedelta(days=14)
            prev_total_result = await db.execute(
                select(func.count(DataQualityResult.id)).where(_result_scope(user)).where(
                    and_(
                        DataQualityResult.execution_timestamp >= fourteen_days_ago,
                        DataQualityResult.execution_timestamp < seven_days_ago,
                    )
                )
            )
            prev_total = prev_total_result.scalar() or 0

            prev_passed_result = await db.execute(
                select(func.count(DataQualityResult.id)).where(_result_scope(user)).where(
                    and_(
                        DataQualityResult.status == "passed",
                        DataQualityResult.execution_timestamp >= fourteen_days_ago,
                        DataQualityResult.execution_timestamp < seven_days_ago,
                    )
                )
            )
            prev_passed = prev_passed_result.scalar() or 0

            prev_pass_rate = (prev_passed / prev_total * 100) if prev_total > 0 else 0

            trend = pass_rate - prev_pass_rate

            return {
                "health_score": round(pass_rate, 2),
                "trend": round(trend, 2),
                "status": (
                    "healthy" if pass_rate >= 90 else
                    "warning" if pass_rate >= 70 else
                    "critical"
                ),
                "results_evaluated": total,
                "results_passed": passed,
            }

        except Exception as e:
            logger.error(f"Error calculating health score: {str(e)}")
            return {
                "health_score": 0,
                "trend": 0,
                "status": "unknown",
                "results_evaluated": 0,
                "results_passed": 0,
            }
