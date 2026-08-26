"""
Enhanced dashboard service with data quality metrics integration
"""

import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.models.data_quality_rule import DataQualityRule, DataQualityResult
from app.services.data_quality_service import DataQualityService
from app.services.monitoring_service import MonitoringService

logger = logging.getLogger(__name__)


class EnhancedDashboardService:
    """Service for enhanced dashboard with DQ metrics"""

    @staticmethod
    async def get_dq_dashboard_section(db: AsyncSession) -> dict:
        """Get data quality section for dashboard"""
        try:
            # Get overall metrics
            metrics = await DataQualityService.calculate_metrics(db)

            # Get health score
            health = await MonitoringService.get_health_score(db)

            # Get failing rules
            failing_rules = await MonitoringService.get_failing_rules(db, limit=5)

            # Get pass rate trend (last 7 days)
            trend = await MonitoringService.get_pass_rate_trend(db, days=7)

            return {
                "health_score": health["health_score"],
                "health_status": health["status"],
                "health_trend": health["trend"],
                "total_rules": metrics.total_rules,
                "active_rules": metrics.active_rules,
                "overall_pass_rate": metrics.overall_pass_rate,
                "results_evaluated": health["results_evaluated"],
                "results_passed": health["results_passed"],
                "dimension_summary": [
                    {
                        "dimension": dim.dimension.value,
                        "total_rules": dim.total_rules,
                        "active_rules": dim.active_rules,
                        "passed_results": dim.passed_results,
                        "failed_results": dim.failed_results,
                    }
                    for dim in metrics.dimension_stats
                ],
                "failing_rules": [
                    {
                        "rule_id": rule["rule_id"],
                        "rule_name": rule["rule_name"],
                        "severity": rule["severity"],
                        "consecutive_failures": rule["consecutive_failures"],
                    }
                    for rule in failing_rules[:5]
                ],
                "pass_rate_trend": [
                    {
                        "date": t["date"],
                        "pass_rate": t["pass_rate"],
                    }
                    for t in trend
                ],
            }

        except Exception as e:
            logger.error(f"Error getting DQ dashboard section: {str(e)}")
            return {
                "health_score": 0,
                "health_status": "unknown",
                "health_trend": 0,
                "total_rules": 0,
                "active_rules": 0,
                "overall_pass_rate": 0,
                "results_evaluated": 0,
                "results_passed": 0,
                "dimension_summary": [],
                "failing_rules": [],
                "pass_rate_trend": [],
            }

    @staticmethod
    async def get_governance_dashboard_section(db: AsyncSession) -> dict:
        """Get governance section for dashboard"""
        try:
            from app.models.data_governance import DataAsset, GovernancePolicy

            # Get asset statistics
            assets_result = await db.execute(select(func.count(DataAsset.id)))
            total_assets = assets_result.scalar() or 0

            classified_result = await db.execute(
                select(func.count(DataAsset.id)).where(DataAsset.classification.isnot(None))
            )
            classified_assets = classified_result.scalar() or 0

            # Get policy statistics
            policies_result = await db.execute(select(func.count(GovernancePolicy.id)))
            total_policies = policies_result.scalar() or 0

            return {
                "total_data_assets": total_assets,
                "classified_assets": classified_assets,
                "classification_coverage": (classified_assets / total_assets * 100) if total_assets > 0 else 0,
                "total_governance_policies": total_policies,
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting governance dashboard section: {str(e)}")
            return {
                "total_data_assets": 0,
                "classified_assets": 0,
                "classification_coverage": 0,
                "total_governance_policies": 0,
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

    @staticmethod
    async def get_full_dashboard(db: AsyncSession) -> dict:
        """Get complete enhanced dashboard"""
        try:
            dq_section = await EnhancedDashboardService.get_dq_dashboard_section(db)
            governance_section = await EnhancedDashboardService.get_governance_dashboard_section(db)

            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data_quality": dq_section,
                "governance": governance_section,
            }

        except Exception as e:
            logger.error(f"Error getting full dashboard: {str(e)}")
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data_quality": {},
                "governance": {},
            }
