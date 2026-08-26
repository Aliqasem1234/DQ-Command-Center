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

from app.models.data_quality_rule import DataQualityResult, DataQualityDimension, RuleStatus
from app.models.data_hierarchy import (
    Dataset, DataQualityRule, QualityIssue, RuleEffectiveness,
    QualityCheckRun, IssueSeverity, IssueStatus
)

logger = logging.getLogger(__name__)


class QualityAnalyticsService:
    """Service for quality analytics and health calculations"""

    @staticmethod
    async def calculate_overall_health_score(
        db: AsyncSession,
        domain_id: UUID = None,
        dataset_id: UUID = None,
        days: int = 30,
    ) -> dict:
        """
        Calculate overall data quality health score (0-100)
        
        Factors:
        - Quality rule pass rates (weighted)
        - Severity of failing rules
        - Open issues
        - SLA compliance
        """
        try:
            now = datetime.now(timezone.utc)
            cutoff_date = now - timedelta(days=days)

            # Get relevant rules
            query = select(DataQualityRule).where(
                DataQualityRule.status == RuleStatus.ACTIVE
            )
            
            if dataset_id:
                query = query.where(DataQualityRule.dataset_id == dataset_id)
            
            rule_result = await db.execute(query)
            active_rules = rule_result.scalars().all()

            if not active_rules:
                # No rules = perfect health (no quality issues detected)
                return {
                    "health_score": 100.0,
                    "status": "excellent",
                    "message": "No quality rules configured",
                    "calculation_basis": "No rules",
                }

            # Calculate pass rate for each rule
            total_score = 0.0
            rule_scores = {}

            for rule in active_rules:
                # Get recent results
                results_query = select(DataQualityResult).where(
                    and_(
                        DataQualityResult.rule_id == rule.id,
                        DataQualityResult.execution_timestamp >= cutoff_date,
                    )
                ).order_by(desc(DataQualityResult.execution_timestamp)).limit(10)

                results_result = await db.execute(results_query)
                results = results_result.scalars().all()

                if not results:
                    # No recent results = neutral (50%)
                    rule_score = 50.0
                else:
                    # Calculate pass rate from results
                    passed = sum(1 for r in results if r.status == "passed")
                    pass_rate = (passed / len(results)) * 100 if results else 0
                    
                    # Apply severity weight
                    severity_weight = {
                        "low": 0.5,
                        "medium": 1.0,
                        "high": 1.5,
                        "critical": 2.0,
                    }.get(rule.severity.value, 1.0)
                    
                    # Score = pass_rate adjusted by severity
                    rule_score = pass_rate / (severity_weight if severity_weight > 0 else 1)

                total_score += rule_score
                rule_scores[str(rule.id)] = {
                    "rule_name": rule.name,
                    "pass_rate": pass_rate if results else None,
                    "recent_results": len(results),
                }

            # Average score
            health_score = total_score / len(active_rules) if active_rules else 100.0
            health_score = min(100.0, max(0.0, health_score))  # Clamp to 0-100

            # Determine status
            if health_score >= 95:
                status = "excellent"
            elif health_score >= 85:
                status = "good"
            elif health_score >= 70:
                status = "fair"
            elif health_score >= 50:
                status = "poor"
            else:
                status = "critical"

            return {
                "health_score": round(health_score, 1),
                "status": status,
                "active_rules": len(active_rules),
                "calculation_basis": f"Last {days} days",
                "rule_scores": rule_scores,
            }

        except Exception as e:
            logger.error(f"Error calculating health score: {str(e)}")
            return {
                "health_score": None,
                "status": "unknown",
                "error": str(e),
            }

    @staticmethod
    async def quality_by_dimension(
        db: AsyncSession,
        dataset_id: UUID = None,
        days: int = 30,
    ) -> dict:
        """Calculate quality metrics by dimension (accuracy, completeness, etc.)"""
        try:
            now = datetime.now(timezone.utc)
            cutoff_date = now - timedelta(days=days)

            results = {}

            # Get all dimensions
            for dimension in DataQualityDimension:
                # Get rules for this dimension
                query = select(DataQualityRule).where(
                    and_(
                        DataQualityRule.dimension == dimension,
                        DataQualityRule.status == RuleStatus.ACTIVE,
                    )
                )
                
                if dataset_id:
                    query = query.where(DataQualityRule.dataset_id == dataset_id)

                rule_result = await db.execute(query)
                rules = rule_result.scalars().all()

                if not rules:
                    results[dimension.value] = {
                        "score": None,
                        "status": "no_rules",
                        "rule_count": 0,
                    }
                    continue

                # Calculate average pass rate for rules in this dimension
                total_pass_rate = 0.0
                rule_count = 0

                for rule in rules:
                    res_query = select(DataQualityResult).where(
                        and_(
                            DataQualityResult.rule_id == rule.id,
                            DataQualityResult.execution_timestamp >= cutoff_date,
                        )
                    ).order_by(desc(DataQualityResult.execution_timestamp)).limit(5)

                    res_result = await db.execute(res_query)
                    dim_results = res_result.scalars().all()

                    if dim_results:
                        passed = sum(1 for r in dim_results if r.status == "passed")
                        pass_rate = (passed / len(dim_results)) * 100
                        total_pass_rate += pass_rate
                        rule_count += 1

                score = (total_pass_rate / rule_count) if rule_count > 0 else None

                if score is not None:
                    if score >= 95:
                        status = "excellent"
                    elif score >= 85:
                        status = "good"
                    elif score >= 70:
                        status = "fair"
                    else:
                        status = "poor"
                else:
                    status = "no_data"

                results[dimension.value] = {
                    "score": round(score, 1) if score is not None else None,
                    "status": status,
                    "rule_count": len(rules),
                }

            return results

        except Exception as e:
            logger.error(f"Error calculating dimension scores: {str(e)}")
            return {}

    @staticmethod
    async def quality_trends(
        db: AsyncSession,
        dataset_id: UUID = None,
        days: int = 30,
    ) -> dict:
        """Calculate quality trends over time"""
        try:
            now = datetime.now(timezone.utc)
            cutoff_date = now - timedelta(days=days)

            # Get check runs for this period
            query = select(QualityCheckRun).where(
                QualityCheckRun.check_timestamp >= cutoff_date
            )
            
            if dataset_id:
                query = query.where(QualityCheckRun.dataset_id == dataset_id)

            query = query.order_by(QualityCheckRun.check_timestamp)
            result = await db.execute(query)
            check_runs = result.scalars().all()

            # Group by day
            daily_stats = {}
            for check_run in check_runs:
                date_key = check_run.check_timestamp.date().isoformat()
                
                if date_key not in daily_stats:
                    daily_stats[date_key] = {
                        "total_runs": 0,
                        "total_passed": 0,
                        "total_failed": 0,
                        "pass_rate": 0.0,
                    }

                daily_stats[date_key]["total_runs"] += 1
                if check_run.overall_pass_rate:
                    daily_stats[date_key]["total_passed"] += check_run.overall_pass_rate / 100
                    daily_stats[date_key]["total_failed"] += (100 - check_run.overall_pass_rate) / 100

            # Calculate daily averages
            daily_trends = []
            for date_key in sorted(daily_stats.keys()):
                stats = daily_stats[date_key]
                if stats["total_runs"] > 0:
                    pass_rate = (stats["total_passed"] / stats["total_runs"]) * 100
                else:
                    pass_rate = 0.0

                daily_trends.append({
                    "date": date_key,
                    "pass_rate": round(pass_rate, 1),
                    "total_runs": stats["total_runs"],
                })

            # Determine trend direction
            trend = "stable"
            if len(daily_trends) >= 2:
                first_half = sum(t["pass_rate"] for t in daily_trends[:len(daily_trends)//2]) / (len(daily_trends)//2 + 1)
                second_half = sum(t["pass_rate"] for t in daily_trends[len(daily_trends)//2:]) / (len(daily_trends) - len(daily_trends)//2 + 1)
                
                if second_half > first_half + 2:
                    trend = "improving"
                elif second_half < first_half - 2:
                    trend = "degrading"

            return {
                "trend": trend,
                "period_days": days,
                "total_check_runs": len(check_runs),
                "daily_data": daily_trends,
            }

        except Exception as e:
            logger.error(f"Error calculating trends: {str(e)}")
            return {
                "trend": "unknown",
                "error": str(e),
            }

    @staticmethod
    async def issue_analytics(
        db: AsyncSession,
        dataset_id: UUID = None,
    ) -> dict:
        """Analyze quality issues"""
        try:
            # Get issues by status
            query = select(QualityIssue).where(QualityIssue.status == IssueStatus.OPEN)
            if dataset_id:
                query = query.where(QualityIssue.dataset_id == dataset_id)

            result = await db.execute(query)
            open_issues = result.scalars().all()

            # Count by severity
            severity_counts = {
                IssueSeverity.CRITICAL.value: 0,
                IssueSeverity.HIGH.value: 0,
                IssueSeverity.MEDIUM.value: 0,
                IssueSeverity.LOW.value: 0,
            }

            for issue in open_issues:
                severity_counts[issue.severity.value] += 1

            # Get in-progress issues
            in_progress_query = select(QualityIssue).where(
                QualityIssue.status == IssueStatus.IN_PROGRESS
            )
            if dataset_id:
                in_progress_query = in_progress_query.where(QualityIssue.dataset_id == dataset_id)

            in_progress_result = await db.execute(in_progress_query)
            in_progress_issues = in_progress_result.scalars().all()

            return {
                "open_issues": len(open_issues),
                "in_progress_issues": len(in_progress_issues),
                "by_severity": severity_counts,
                "critical_count": severity_counts[IssueSeverity.CRITICAL.value],
                "high_count": severity_counts[IssueSeverity.HIGH.value],
            }

        except Exception as e:
            logger.error(f"Error analyzing issues: {str(e)}")
            return {"error": str(e)}

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
