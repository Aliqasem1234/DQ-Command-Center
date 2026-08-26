"""
Data Quality Results Reporting Service

Provides detailed analysis and reporting on rule execution results.
"""

import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.models.data_quality_rule import DataQualityResult, DataQualityRule

logger = logging.getLogger(__name__)


class ResultsReportingService:
    """Service for analyzing and reporting on data quality results"""

    @staticmethod
    async def get_result_statistics(
        db: AsyncSession,
        rule_id: UUID = None,
        days: int = 30,
    ) -> dict:
        """Get statistics for results"""
        try:
            start_date = datetime.now(timezone.utc) - timedelta(days=days)

            query = select(DataQualityResult).where(
                DataQualityResult.execution_timestamp >= start_date
            )

            if rule_id:
                query = query.where(DataQualityResult.rule_id == rule_id)

            result = await db.execute(query)
            results = result.scalars().all()

            if not results:
                return {
                    "total_results": 0,
                    "passed": 0,
                    "failed": 0,
                    "errors": 0,
                    "pass_rate": 0,
                    "error_rate": 0,
                    "avg_duration_ms": 0,
                    "min_duration_ms": 0,
                    "max_duration_ms": 0,
                }

            passed = sum(1 for r in results if r.status == "passed")
            failed = sum(1 for r in results if r.status == "failed")
            errors = sum(1 for r in results if r.status == "error")
            total = len(results)

            durations = [r.execution_duration_ms for r in results if r.execution_duration_ms]

            return {
                "total_results": total,
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "pass_rate": (passed / total * 100) if total > 0 else 0,
                "failure_rate": (failed / total * 100) if total > 0 else 0,
                "error_rate": (errors / total * 100) if total > 0 else 0,
                "avg_duration_ms": sum(durations) / len(durations) if durations else 0,
                "min_duration_ms": min(durations) if durations else 0,
                "max_duration_ms": max(durations) if durations else 0,
            }

        except Exception as e:
            logger.error(f"Error calculating result statistics: {str(e)}")
            return {}

    @staticmethod
    async def get_error_summary(
        db: AsyncSession,
        rule_id: UUID = None,
        limit: int = 10,
    ) -> list[dict]:
        """Get summary of errors and error patterns"""
        try:
            query = select(DataQualityResult).where(
                DataQualityResult.status == "error"
            ).order_by(
                desc(DataQualityResult.execution_timestamp)
            )

            if rule_id:
                query = query.where(DataQualityResult.rule_id == rule_id)

            query = query.limit(limit)

            result = await db.execute(query)
            errors = result.scalars().all()

            return [
                {
                    "result_id": str(e.id),
                    "rule_id": str(e.rule_id),
                    "execution_timestamp": e.execution_timestamp.isoformat(),
                    "error_details": e.error_details,
                    "error_stack": e.error_stack,
                }
                for e in errors
            ]

        except Exception as e:
            logger.error(f"Error getting error summary: {str(e)}")
            return []

    @staticmethod
    async def get_result_timeline(
        db: AsyncSession,
        rule_id: UUID = None,
        limit: int = 20,
    ) -> list[dict]:
        """Get timeline of recent results"""
        try:
            query = select(
                DataQualityResult.id,
                DataQualityResult.rule_id,
                DataQualityResult.status,
                DataQualityResult.execution_timestamp,
                DataQualityResult.records_checked,
                DataQualityResult.records_passed,
                DataQualityResult.records_failed,
                DataQualityResult.execution_duration_ms,
                DataQualityRule.name,
            ).join(DataQualityRule).order_by(
                desc(DataQualityResult.execution_timestamp)
            )

            if rule_id:
                query = query.where(DataQualityResult.rule_id == rule_id)

            query = query.limit(limit)

            result = await db.execute(query)
            rows = result.all()

            return [
                {
                    "result_id": str(row[0]),
                    "rule_id": str(row[1]),
                    "rule_name": row[8],
                    "status": row[2],
                    "timestamp": row[3].isoformat(),
                    "records_checked": row[4],
                    "records_passed": row[5],
                    "records_failed": row[6],
                    "duration_ms": row[7],
                    "pass_rate": (
                        (row[5] / row[4] * 100) if row[4] and row[4] > 0 else None
                    ),
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"Error getting result timeline: {str(e)}")
            return []

    @staticmethod
    async def get_failure_analysis(
        db: AsyncSession,
        rule_id: UUID,
        days: int = 30,
    ) -> dict:
        """Analyze failure patterns for a rule"""
        try:
            start_date = datetime.now(timezone.utc) - timedelta(days=days)

            # Get all results for this rule
            query = select(DataQualityResult).where(
                and_(
                    DataQualityResult.rule_id == rule_id,
                    DataQualityResult.execution_timestamp >= start_date,
                )
            ).order_by(DataQualityResult.execution_timestamp)

            result = await db.execute(query)
            results = result.scalars().all()

            if not results:
                return {
                    "total_executions": 0,
                    "total_failures": 0,
                    "consecutive_failures": 0,
                    "failure_trend": [],
                }

            failures = [r for r in results if r.status == "failed"]
            total_failures = len(failures)

            # Calculate consecutive failures (from most recent)
            consecutive = 0
            for r in reversed(results):
                if r.status == "failed":
                    consecutive += 1
                else:
                    break

            # Get failure trend by day
            failure_by_day = {}
            for r in results:
                day = r.execution_timestamp.date()
                if day not in failure_by_day:
                    failure_by_day[day] = {"total": 0, "failures": 0}
                failure_by_day[day]["total"] += 1
                if r.status == "failed":
                    failure_by_day[day]["failures"] += 1

            trend = [
                {
                    "date": str(day),
                    "total": counts["total"],
                    "failures": counts["failures"],
                    "failure_rate": (counts["failures"] / counts["total"] * 100)
                    if counts["total"] > 0
                    else 0,
                }
                for day, counts in sorted(failure_by_day.items())
            ]

            return {
                "total_executions": len(results),
                "total_failures": total_failures,
                "failure_rate": (total_failures / len(results) * 100)
                if len(results) > 0
                else 0,
                "consecutive_failures": consecutive,
                "failure_trend": trend,
            }

        except Exception as e:
            logger.error(f"Error analyzing failures: {str(e)}")
            return {}

    @staticmethod
    async def get_quality_report(
        db: AsyncSession,
        days: int = 30,
    ) -> dict:
        """Generate comprehensive quality report"""
        try:
            start_date = datetime.now(timezone.utc) - timedelta(days=days)

            # Count rules by status
            query = select(
                DataQualityRule.status,
                func.count(DataQualityRule.id),
            ).group_by(DataQualityRule.status)

            result = await db.execute(query)
            rules_by_status = {row[0].value: row[1] for row in result.all()}

            # Get results metrics
            results_query = select(DataQualityResult).where(
                DataQualityResult.execution_timestamp >= start_date
            )
            results_result = await db.execute(results_query)
            all_results = results_result.scalars().all()

            passed = sum(1 for r in all_results if r.status == "passed")
            failed = sum(1 for r in all_results if r.status == "failed")
            errors = sum(1 for r in all_results if r.status == "error")
            total = len(all_results)

            return {
                "reporting_period_days": days,
                "report_timestamp": datetime.now(timezone.utc).isoformat(),
                "rules": {
                    "total": sum(rules_by_status.values()),
                    "by_status": rules_by_status,
                },
                "results": {
                    "total_executions": total,
                    "passed": passed,
                    "failed": failed,
                    "errors": errors,
                    "pass_rate": (passed / total * 100) if total > 0 else 0,
                    "failure_rate": (failed / total * 100) if total > 0 else 0,
                    "error_rate": (errors / total * 100) if total > 0 else 0,
                },
            }

        except Exception as e:
            logger.error(f"Error generating quality report: {str(e)}")
            return {}
