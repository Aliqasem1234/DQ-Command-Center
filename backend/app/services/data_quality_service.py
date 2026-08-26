import logging
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy import select, desc, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.data_quality_rule import (
    DataQualityRule,
    DataQualityResult,
    DataQualityDimension,
    RuleStatus,
)
from app.schemas.data_quality_rule import (
    DataQualityRuleCreate,
    DataQualityRuleUpdate,
    DataQualityResultCreate,
    DimensionStats,
    DataQualityMetrics,
)
from app.utils.audit_logger import log_audit_action

logger = logging.getLogger(__name__)


class DataQualityService:
    """Service for managing data quality rules and results"""

    @staticmethod
    async def create_rule(
        db: AsyncSession,
        data: DataQualityRuleCreate,
        current_user_id: UUID,
    ) -> DataQualityRule:
        """Create a new data quality rule with audit logging"""
        try:
            now = datetime.now(timezone.utc)

            rule = DataQualityRule(
                name=data.name,
                description=data.description,
                data_source=data.data_source,
                target_field=data.target_field,
                dimension=data.dimension,
                rule_type=data.rule_type,
                severity=data.severity,
                status=data.status,
                rule_definition=data.rule_definition,
                owner_id=data.owner_id,
                created_by_id=current_user_id,
                is_active=data.is_active,
                created_at=now,
                updated_at=now,
            )

            db.add(rule)
            await db.flush()

            # Log audit
            await log_audit_action(
                db=db,
                user_id=current_user_id,
                action="CREATE",
                entity_type="DataQualityRule",
                entity_id=str(rule.id),
                entity_name=rule.name,
                new_values={
                    "name": rule.name,
                    "dimension": rule.dimension.value,
                    "rule_type": rule.rule_type,
                    "severity": rule.severity.value,
                },
            )

            await db.commit()
            return await DataQualityService.get_rule(db, rule.id)

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating data quality rule: {str(e)}")
            raise

    @staticmethod
    async def update_rule(
        db: AsyncSession,
        rule_id: UUID,
        data: DataQualityRuleUpdate,
        current_user_id: UUID,
    ) -> DataQualityRule:
        """Update an existing data quality rule with audit logging"""
        try:
            result = await db.execute(
                select(DataQualityRule)
                .options(selectinload(DataQualityRule.owner), selectinload(DataQualityRule.created_by))
                .where(DataQualityRule.id == rule_id)
            )
            rule = result.scalar_one_or_none()

            if not rule:
                return None

            # Track old values for audit
            old_values = {
                "name": rule.name,
                "dimension": rule.dimension.value,
                "severity": rule.severity.value,
                "status": rule.status.value,
                "is_active": rule.is_active,
            }

            # Update fields
            update_data = data.dict(exclude_unset=True)
            for field, value in update_data.items():
                if value is not None:
                    setattr(rule, field, value)

            rule.updated_at = datetime.now(timezone.utc)
            db.add(rule)
            await db.flush()

            # Log audit
            new_values = {
                "name": rule.name,
                "dimension": rule.dimension.value,
                "severity": rule.severity.value,
                "status": rule.status.value,
                "is_active": rule.is_active,
            }

            await log_audit_action(
                db=db,
                user_id=current_user_id,
                action="UPDATE",
                entity_type="DataQualityRule",
                entity_id=str(rule.id),
                entity_name=rule.name,
                old_values=old_values,
                new_values=new_values,
            )

            await db.commit()
            return rule

        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating data quality rule: {str(e)}")
            raise

    @staticmethod
    async def delete_rule(
        db: AsyncSession,
        rule_id: UUID,
        current_user_id: UUID,
    ) -> bool:
        """Delete a data quality rule with audit logging"""
        try:
            result = await db.execute(
                select(DataQualityRule).where(DataQualityRule.id == rule_id)
            )
            rule = result.scalar_one_or_none()

            if not rule:
                return False

            rule_name = rule.name

            # Log audit before deletion
            await log_audit_action(
                db=db,
                user_id=current_user_id,
                action="DELETE",
                entity_type="DataQualityRule",
                entity_id=str(rule.id),
                entity_name=rule_name,
                old_values={
                    "name": rule.name,
                    "dimension": rule.dimension.value,
                    "rule_type": rule.rule_type,
                },
            )

            await db.delete(rule)
            await db.commit()
            return True

        except Exception as e:
            await db.rollback()
            logger.error(f"Error deleting data quality rule: {str(e)}")
            raise

    @staticmethod
    async def get_rule(db: AsyncSession, rule_id: UUID) -> DataQualityRule:
        """Get a data quality rule by ID"""
        result = await db.execute(
            select(DataQualityRule)
            .options(selectinload(DataQualityRule.owner), selectinload(DataQualityRule.created_by))
            .where(DataQualityRule.id == rule_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_rules(
        db: AsyncSession,
        dimension: str = None,
        status: str = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[DataQualityRule], int]:
        """List data quality rules with filtering"""
        query = select(DataQualityRule).options(
            selectinload(DataQualityRule.owner), selectinload(DataQualityRule.created_by)
        )

        if dimension:
            try:
                dim_enum = DataQualityDimension(dimension)
                query = query.where(DataQualityRule.dimension == dim_enum)
            except ValueError:
                pass

        if status:
            try:
                status_enum = RuleStatus(status)
                query = query.where(DataQualityRule.status == status_enum)
            except ValueError:
                pass

        # Get total count
        count_result = await db.execute(
            select(func.count()).select_from(query.with_only_columns(DataQualityRule.id).subquery())
        )
        total = count_result.scalar() or 0

        # Apply pagination and ordering
        query = query.order_by(desc(DataQualityRule.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        rules = result.scalars().all()

        return rules, total

    @staticmethod
    async def record_result(
        db: AsyncSession,
        data: DataQualityResultCreate,
    ) -> DataQualityResult:
        """Record a data quality result"""
        try:
            result = DataQualityResult(
                rule_id=data.rule_id,
                execution_timestamp=data.execution_timestamp,
                status=data.status,
                records_checked=data.records_checked,
                records_passed=data.records_passed,
                records_failed=data.records_failed,
                execution_duration_ms=data.execution_duration_ms,
                error_details=data.error_details,
                created_at=datetime.now(timezone.utc),
            )

            db.add(result)
            await db.commit()
            return result

        except Exception as e:
            await db.rollback()
            logger.error(f"Error recording data quality result: {str(e)}")
            raise

    @staticmethod
    async def get_rule_results(
        db: AsyncSession,
        rule_id: UUID,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[DataQualityResult], int]:
        """Get results for a specific rule"""
        query = select(DataQualityResult).where(
            DataQualityResult.rule_id == rule_id
        )

        # Get total count
        count_result = await db.execute(
            select(func.count(DataQualityResult.id)).where(
                DataQualityResult.rule_id == rule_id
            )
        )
        total = count_result.scalar() or 0

        # Apply pagination and ordering
        query = query.order_by(desc(DataQualityResult.execution_timestamp))
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        results = result.scalars().all()

        return results, total

    @staticmethod
    async def calculate_metrics(db: AsyncSession) -> DataQualityMetrics:
        """Calculate overall data quality metrics"""
        try:
            now = datetime.now(timezone.utc)

            # Count rules by status
            total_rules_result = await db.execute(
                select(func.count(DataQualityRule.id))
            )
            total_rules = total_rules_result.scalar() or 0

            active_rules_result = await db.execute(
                select(func.count(DataQualityRule.id)).where(
                    DataQualityRule.status == RuleStatus.ACTIVE
                )
            )
            active_rules = active_rules_result.scalar() or 0

            draft_rules_result = await db.execute(
                select(func.count(DataQualityRule.id)).where(
                    DataQualityRule.status == RuleStatus.DRAFT
                )
            )
            draft_rules = draft_rules_result.scalar() or 0

            # Count results
            total_results_result = await db.execute(
                select(func.count(DataQualityResult.id))
            )
            total_results = total_results_result.scalar() or 0

            passed_result = await db.execute(
                select(func.count(DataQualityResult.id)).where(
                    DataQualityResult.status == "passed"
                )
            )
            results_passed = passed_result.scalar() or 0

            failed_result = await db.execute(
                select(func.count(DataQualityResult.id)).where(
                    DataQualityResult.status == "failed"
                )
            )
            results_failed = failed_result.scalar() or 0

            error_result = await db.execute(
                select(func.count(DataQualityResult.id)).where(
                    DataQualityResult.status == "error"
                )
            )
            results_with_errors = error_result.scalar() or 0

            # Calculate pass rate
            overall_pass_rate = 0.0
            if total_results > 0:
                overall_pass_rate = (results_passed / total_results) * 100

            # Calculate stats per dimension
            dimension_stats = []
            for dimension in DataQualityDimension:
                rules_result = await db.execute(
                    select(func.count(DataQualityRule.id)).where(
                        DataQualityRule.dimension == dimension
                    )
                )
                total_dim_rules = rules_result.scalar() or 0

                active_dim_result = await db.execute(
                    select(func.count(DataQualityRule.id)).where(
                        and_(
                            DataQualityRule.dimension == dimension,
                            DataQualityRule.status == RuleStatus.ACTIVE,
                        )
                    )
                )
                active_dim_rules = active_dim_result.scalar() or 0

                # Get passed results for this dimension
                passed_dim_result = await db.execute(
                    select(func.count(DataQualityResult.id)).where(
                        and_(
                            DataQualityResult.status == "passed",
                            DataQualityResult.rule_id.in_(
                                select(DataQualityRule.id).where(
                                    DataQualityRule.dimension == dimension
                                )
                            ),
                        )
                    )
                )
                passed_dim = passed_dim_result.scalar() or 0

                # Get failed results for this dimension
                failed_dim_result = await db.execute(
                    select(func.count(DataQualityResult.id)).where(
                        and_(
                            DataQualityResult.status == "failed",
                            DataQualityResult.rule_id.in_(
                                select(DataQualityRule.id).where(
                                    DataQualityRule.dimension == dimension
                                )
                            ),
                        )
                    )
                )
                failed_dim = failed_dim_result.scalar() or 0

                # Get last execution for this dimension
                last_execution_result = await db.execute(
                    select(func.max(DataQualityResult.execution_timestamp)).where(
                        DataQualityResult.rule_id.in_(
                            select(DataQualityRule.id).where(
                                DataQualityRule.dimension == dimension
                            )
                        )
                    )
                )
                last_execution = last_execution_result.scalar()

                dimension_stats.append(
                    DimensionStats(
                        dimension=dimension,
                        total_rules=total_dim_rules,
                        active_rules=active_dim_rules,
                        passed_results=passed_dim,
                        failed_results=failed_dim,
                        last_execution=last_execution,
                    )
                )

            return DataQualityMetrics(
                total_rules=total_rules,
                active_rules=active_rules,
                draft_rules=draft_rules,
                total_results=total_results,
                results_passed=results_passed,
                results_failed=results_failed,
                results_with_errors=results_with_errors,
                overall_pass_rate=overall_pass_rate,
                dimension_stats=dimension_stats,
                last_updated=now,
            )

        except Exception as e:
            logger.error(f"Error calculating metrics: {str(e)}")
            raise
