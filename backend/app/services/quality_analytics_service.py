"""
Quality Analytics Service - Calculates all quality metrics and health scores

Provides:
- Overall health score (0-100)
- Quality by dimension
- Trend analysis
- Issue analytics
- Rule effectiveness
- SLA compliance
"""

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID
from sqlalchemy import select, func, desc, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.data_quality_rule import DataQualityRule, DataQualityResult, DataQualityDimension, RuleStatus
from app.models.data_hierarchy import (
    Dataset, DatasetVersion, QualityIssue, RuleEffectiveness,
    QualityCheckRun, IssueSeverity, IssueStatus
)
from app.core.dataset_access import accessible_dataset_ids, visible_rules_clause

logger = logging.getLogger(__name__)


class QualityAnalyticsService:
    """Service for quality analytics and health calculations"""

    # ------------------------------------------------------------------
    # Every function takes an optional `user`. When given, only data the
    # user may access is aggregated (app.core.dataset_access), so nobody
    # ever sees global numbers presented as their own.
    # ------------------------------------------------------------------

    @staticmethod
    def _dataset_conditions(column, user, dataset_id):
        conditions = []
        if user is not None:
            conditions.append(column.in_(accessible_dataset_ids(user)))
        if dataset_id:
            conditions.append(column == dataset_id)
        return conditions

    @staticmethod
    def _status_for(score: float | None) -> str:
        if score is None:
            return "no_data"
        if score >= 95:
            return "excellent"
        if score >= 85:
            return "good"
        if score >= 70:
            return "fair"
        if score >= 50:
            return "poor"
        return "critical"

    @staticmethod
    async def calculate_overall_health_score(
        db: AsyncSession,
        domain_id: UUID = None,
        dataset_id: UUID = None,
        days: int = 30,
        user=None,
    ) -> dict:
        """Overall health = the average quality score of the datasets in
        scope, each taken from its most recently created scanned version.

        A dataset's quality score is the share of its cells not affected by
        any failing check (quality_discovery_service.compute_quality_score),
        so this is the same number users see on each dataset, averaged.
        Datasets that have never been scanned have no score and are left
        out; with none scanned the health is unknown (None), not "100%".
        (Previously: a pass rate of check *runs* divided by a severity
        weight, which scored a fully passing critical rule 50 and reported
        100% "excellent" when there was no data at all.)
        """
        conditions = QualityAnalyticsService._dataset_conditions(DatasetVersion.dataset_id, user, dataset_id)
        latest = (
            select(
                DatasetVersion.dataset_id,
                DatasetVersion.quality_score,
                func.row_number().over(
                    partition_by=DatasetVersion.dataset_id,
                    order_by=(DatasetVersion.version_number.desc()),
                ).label("rn"),
            )
            .where(DatasetVersion.quality_score.is_not(None), *conditions)
            .subquery()
        )
        rows = (await db.execute(select(latest.c.quality_score).where(latest.c.rn == 1))).scalars().all()
        if not rows:
            return {
                "health_score": None,
                "status": "no_data",
                "scanned_datasets": 0,
                "calculation_basis": "No scanned datasets",
            }
        score = sum(rows) / len(rows)
        return {
            "health_score": round(score, 1),
            "status": QualityAnalyticsService._status_for(score),
            "scanned_datasets": len(rows),
            "calculation_basis": "Average quality score of the latest scanned version of each dataset",
        }

    @staticmethod
    async def quality_by_dimension(
        db: AsyncSession,
        dataset_id: UUID = None,
        days: int = 30,
        user=None,
    ) -> dict:
        """Per dimension: the average share of records that passed each
        active check, using every check's most recent result in the window.

        Uses records_passed / records_checked (what fraction of the data is
        fine), not whether the run as a whole passed - automatic checks only
        exist while they find a problem, so a run-level pass rate would be 0
        for every one of them.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        rule_conditions = [DataQualityRule.status == RuleStatus.ACTIVE]
        if user is not None:
            rule_conditions.append(visible_rules_clause(user))
        if dataset_id:
            rule_conditions.append(DataQualityRule.dataset_id == dataset_id)

        latest = (
            select(
                DataQualityResult.rule_id,
                DataQualityResult.records_checked,
                DataQualityResult.records_passed,
                func.row_number().over(
                    partition_by=DataQualityResult.rule_id,
                    order_by=DataQualityResult.execution_timestamp.desc(),
                ).label("rn"),
            )
            .where(DataQualityResult.execution_timestamp >= cutoff)
            .subquery()
        )
        rows = (
            await db.execute(
                select(DataQualityRule.dimension, latest.c.records_checked, latest.c.records_passed)
                .select_from(DataQualityRule)
                .outerjoin(latest, and_(latest.c.rule_id == DataQualityRule.id, latest.c.rn == 1))
                .where(*rule_conditions)
            )
        ).all()

        per_dimension: dict = {}
        for dimension, checked, passed in rows:
            entry = per_dimension.setdefault(dimension, {"rates": [], "rule_count": 0})
            entry["rule_count"] += 1
            if checked:
                entry["rates"].append((passed or 0) / checked * 100)

        results = {}
        for dimension in DataQualityDimension:
            entry = per_dimension.get(dimension)
            if entry is None:
                results[dimension.value] = {"score": None, "status": "no_rules", "rule_count": 0}
                continue
            score = sum(entry["rates"]) / len(entry["rates"]) if entry["rates"] else None
            results[dimension.value] = {
                "score": round(score, 1) if score is not None else None,
                "status": QualityAnalyticsService._status_for(score) if score is not None else "no_data",
                "rule_count": entry["rule_count"],
            }
        return results

    @staticmethod
    async def quality_trends(
        db: AsyncSession,
        dataset_id: UUID = None,
        days: int = 30,
        user=None,
    ) -> dict:
        """Daily average dataset quality score of the scans run in the
        window, and whether it went up or down. Only scans that recorded a
        quality score count (runs from before scores were recorded only
        have a check pass rate, a different measure that must not be mixed
        into the same line)."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        conditions = QualityAnalyticsService._dataset_conditions(QualityCheckRun.dataset_id, user, dataset_id)
        runs = (
            await db.execute(
                select(QualityCheckRun.check_timestamp, QualityCheckRun.quality_score)
                .where(
                    QualityCheckRun.check_timestamp >= cutoff,
                    QualityCheckRun.quality_score.is_not(None),
                    *conditions,
                )
                .order_by(QualityCheckRun.check_timestamp)
            )
        ).all()

        by_day: dict[str, list[float]] = {}
        for timestamp, score in runs:
            by_day.setdefault(timestamp.date().isoformat(), []).append(score)
        daily = [
            {"date": day, "pass_rate": round(sum(scores) / len(scores), 1), "total_runs": len(scores)}
            for day, scores in sorted(by_day.items())
        ]

        trend = "stable"
        if len(daily) >= 2:
            half = len(daily) // 2
            first = sum(d["pass_rate"] for d in daily[:half]) / half
            second = sum(d["pass_rate"] for d in daily[half:]) / (len(daily) - half)
            if second > first + 2:
                trend = "improving"
            elif second < first - 2:
                trend = "degrading"
        elif not daily:
            trend = "unknown"

        return {"trend": trend, "period_days": days, "total_check_runs": len(runs), "daily_data": daily}

    @staticmethod
    async def issue_analytics(
        db: AsyncSession,
        dataset_id: UUID = None,
        user=None,
    ) -> dict:
        """Counts of open and in-progress issues in scope, by severity."""
        conditions = QualityAnalyticsService._dataset_conditions(QualityIssue.dataset_id, user, dataset_id)
        rows = (
            await db.execute(
                select(QualityIssue.status, QualityIssue.severity, func.count())
                .where(QualityIssue.status.in_([IssueStatus.OPEN, IssueStatus.IN_PROGRESS]), *conditions)
                .group_by(QualityIssue.status, QualityIssue.severity)
            )
        ).all()
        severity_counts = {s.value: 0 for s in (IssueSeverity.CRITICAL, IssueSeverity.HIGH, IssueSeverity.MEDIUM, IssueSeverity.LOW)}
        open_count = in_progress = 0
        for status_, severity, count in rows:
            if status_ == IssueStatus.OPEN:
                open_count += count
                severity_counts[severity.value] = severity_counts.get(severity.value, 0) + count
            else:
                in_progress += count
        return {
            "open_issues": open_count,
            "in_progress_issues": in_progress,
            "by_severity": severity_counts,
            "critical_count": severity_counts[IssueSeverity.CRITICAL.value],
            "high_count": severity_counts[IssueSeverity.HIGH.value],
        }

    @staticmethod
    async def rule_effectiveness_summary(
        db: AsyncSession,
        dataset_id: UUID = None,
        limit: int = 10,
    ) -> list:
        """Get rules ranked by effectiveness"""
        try:
            query = select(RuleEffectiveness).where(
                RuleEffectiveness.last_30_days_pass_rate.isnot(None)
            ).order_by(
                RuleEffectiveness.last_30_days_pass_rate.asc()  # Lowest pass rates first
            ).limit(limit)

            result = await db.execute(query)
            effectiveness = result.scalars().all()

            summary = []
            for eff in effectiveness:
                summary.append({
                    "rule_id": str(eff.rule_id),
                    "pass_rate": round(eff.last_30_days_pass_rate, 1) if eff.last_30_days_pass_rate else None,
                    "trend": eff.trend.value if eff.trend else None,
                    "last_calculated": eff.last_calculated.isoformat() if eff.last_calculated else None,
                })

            return summary

        except Exception as e:
            logger.error(f"Error getting rule effectiveness: {str(e)}")
            return []

    @staticmethod
    async def top_problematic_datasets(
        db: AsyncSession,
        limit: int = 5,
    ) -> list:
        """Get datasets with most quality issues"""
        try:
            # Get open critical issues grouped by dataset
            query = select(
                QualityIssue.dataset_id,
                func.count(QualityIssue.id).label("issue_count"),
            ).where(
                QualityIssue.status == IssueStatus.OPEN,
                QualityIssue.severity == IssueSeverity.CRITICAL,
            ).group_by(
                QualityIssue.dataset_id
            ).order_by(
                desc(func.count(QualityIssue.id))
            ).limit(limit)

            result = await db.execute(query)
            rows = result.all()

            problematic = []
            for row in rows:
                dataset_id, issue_count = row
                dataset_query = select(Dataset).where(Dataset.id == dataset_id)
                dataset_result = await db.execute(dataset_query)
                dataset = dataset_result.scalar_one_or_none()

                if dataset:
                    problematic.append({
                        "dataset_id": str(dataset.id),
                        "dataset_name": dataset.name,
                        "critical_issue_count": issue_count,
                    })

            return problematic

        except Exception as e:
            logger.error(f"Error getting problematic datasets: {str(e)}")
            return []
