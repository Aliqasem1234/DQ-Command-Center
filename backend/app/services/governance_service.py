import logging
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.data_hierarchy import DataGovernance, GovernancePolicy
from app.schemas.data_governance import (
    GovernanceAssignmentCreate,
    GovernanceAssignmentUpdate,
    GovernancePolicyCreate,
    GovernancePolicyUpdate,
)
from app.utils.audit_logger import create_audit_log

logger = logging.getLogger(__name__)


class GovernanceService:
    """Service for managing data governance role assignments and policies"""

    # Governance Assignment Methods (owner / steward / curator / analyst)
    @staticmethod
    async def create_assignment(
        db: AsyncSession,
        data: GovernanceAssignmentCreate,
        current_user_id: UUID,
    ) -> DataGovernance:
        try:
            assignment = DataGovernance(
                domain_id=data.domain_id,
                dataset_id=data.dataset_id,
                element_id=data.element_id,
                role=data.role,
                user_id=data.user_id,
                department_id=data.department_id,
                responsibility_description=data.responsibility_description,
                start_date=data.start_date,
                end_date=data.end_date,
                is_active=data.is_active,
                assigned_date=datetime.now(timezone.utc),
            )
            db.add(assignment)
            await db.flush()

            await create_audit_log(
                db=db,
                user_id=current_user_id,
                action="CREATE",
                entity_type="DataGovernance",
                entity_id=str(assignment.id),
                entity_name=f"{data.role.value} assignment",
                new_values={"role": data.role.value, "user_id": str(data.user_id)},
            )

            await db.commit()
            return await GovernanceService.get_assignment(db, assignment.id)

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating governance assignment: {str(e)}")
            raise

    @staticmethod
    async def get_assignment(db: AsyncSession, assignment_id: UUID) -> DataGovernance:
        result = await db.execute(
            select(DataGovernance)
            .options(
                selectinload(DataGovernance.user),
                selectinload(DataGovernance.domain),
                selectinload(DataGovernance.dataset),
                selectinload(DataGovernance.element),
            )
            .where(DataGovernance.id == assignment_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_assignments(
        db: AsyncSession,
        domain_id: UUID = None,
        dataset_id: UUID = None,
        element_id: UUID = None,
        role: str = None,
        is_active: bool = None,
        page: int = 1,
        page_size: int = 10,
        scope=None,
    ) -> tuple[list[DataGovernance], int]:
        query = select(DataGovernance).options(
            selectinload(DataGovernance.user),
            selectinload(DataGovernance.domain),
            selectinload(DataGovernance.dataset),
            selectinload(DataGovernance.element),
        )
        if scope is not None:
            query = query.where(scope)

        if domain_id:
            query = query.where(DataGovernance.domain_id == domain_id)
        if dataset_id:
            query = query.where(DataGovernance.dataset_id == dataset_id)
        if element_id:
            query = query.where(DataGovernance.element_id == element_id)
        if role:
            query = query.where(DataGovernance.role == role)
        if is_active is not None:
            query = query.where(DataGovernance.is_active == is_active)

        count_result = await db.execute(
            select(func.count()).select_from(query.with_only_columns(DataGovernance.id).subquery())
        )
        total = count_result.scalar() or 0

        query = query.order_by(desc(DataGovernance.assigned_date))
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        assignments = result.scalars().all()

        return assignments, total

    @staticmethod
    async def update_assignment(
        db: AsyncSession,
        assignment_id: UUID,
        data: GovernanceAssignmentUpdate,
        current_user_id: UUID,
    ) -> DataGovernance:
        try:
            assignment = await GovernanceService.get_assignment(db, assignment_id)
            if not assignment:
                return None

            update_data = data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(assignment, field, value)

            await db.flush()

            await create_audit_log(
                db=db,
                user_id=current_user_id,
                action="UPDATE",
                entity_type="DataGovernance",
                entity_id=str(assignment.id),
                entity_name=f"{assignment.role.value} assignment",
            )

            await db.commit()
            return await GovernanceService.get_assignment(db, assignment_id)

        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating governance assignment: {str(e)}")
            raise

    @staticmethod
    async def revoke_assignment(
        db: AsyncSession,
        assignment_id: UUID,
        current_user_id: UUID,
    ) -> bool:
        try:
            assignment = await GovernanceService.get_assignment(db, assignment_id)
            if not assignment:
                return False

            await create_audit_log(
                db=db,
                user_id=current_user_id,
                action="DELETE",
                entity_type="DataGovernance",
                entity_id=str(assignment.id),
                entity_name=f"{assignment.role.value} assignment",
            )

            await db.delete(assignment)
            await db.commit()
            return True

        except Exception as e:
            await db.rollback()
            logger.error(f"Error revoking governance assignment: {str(e)}")
            raise

    # Governance Policy Methods
    @staticmethod
    async def create_policy(
        db: AsyncSession,
        data: GovernancePolicyCreate,
        current_user_id: UUID,
    ) -> GovernancePolicy:
        try:
            now = datetime.now(timezone.utc)

            policy = GovernancePolicy(
                name=data.name,
                description=data.description,
                domain_id=data.domain_id,
                dataset_id=data.dataset_id,
                policy_type=data.policy_type,
                policy_definition=data.policy_definition,
                status=data.status,
                effective_date=data.effective_date,
                expiration_date=data.expiration_date,
                created_by_id=current_user_id,
                created_at=now,
                updated_at=now,
            )

            db.add(policy)
            await db.flush()

            await create_audit_log(
                db=db,
                user_id=current_user_id,
                action="CREATE",
                entity_type="GovernancePolicy",
                entity_id=str(policy.id),
                entity_name=policy.name,
            )

            await db.commit()
            return policy

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating governance policy: {str(e)}")
            raise

    @staticmethod
    async def get_policy(db: AsyncSession, policy_id: UUID) -> GovernancePolicy:
        result = await db.execute(
            select(GovernancePolicy)
            .options(selectinload(GovernancePolicy.created_by))
            .where(GovernancePolicy.id == policy_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_policies(
        db: AsyncSession,
        domain_id: UUID = None,
        dataset_id: UUID = None,
        policy_type: str = None,
        page: int = 1,
        page_size: int = 10,
        scope=None,
    ) -> tuple[list[GovernancePolicy], int]:
        query = select(GovernancePolicy).options(selectinload(GovernancePolicy.created_by))
        if scope is not None:
            query = query.where(scope)

        if domain_id:
            query = query.where(GovernancePolicy.domain_id == domain_id)
        if dataset_id:
            query = query.where(GovernancePolicy.dataset_id == dataset_id)
        if policy_type:
            query = query.where(GovernancePolicy.policy_type == policy_type)

        count_result = await db.execute(
            select(func.count()).select_from(query.with_only_columns(GovernancePolicy.id).subquery())
        )
        total = count_result.scalar() or 0

        query = query.order_by(desc(GovernancePolicy.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        policies = result.scalars().all()

        return policies, total

    @staticmethod
    async def update_policy(
        db: AsyncSession,
        policy_id: UUID,
        data: GovernancePolicyUpdate,
        current_user_id: UUID,
    ) -> GovernancePolicy:
        try:
            policy = await GovernanceService.get_policy(db, policy_id)
            if not policy:
                return None

            update_data = data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(policy, field, value)

            policy.updated_at = datetime.now(timezone.utc)
            await db.flush()

            await create_audit_log(
                db=db,
                user_id=current_user_id,
                action="UPDATE",
                entity_type="GovernancePolicy",
                entity_id=str(policy.id),
                entity_name=policy.name,
            )

            await db.commit()
            return await GovernanceService.get_policy(db, policy_id)

        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating governance policy: {str(e)}")
            raise

    @staticmethod
    async def delete_policy(
        db: AsyncSession,
        policy_id: UUID,
        current_user_id: UUID,
    ) -> bool:
        try:
            policy = await GovernanceService.get_policy(db, policy_id)
            if not policy:
                return False

            await create_audit_log(
                db=db,
                user_id=current_user_id,
                action="DELETE",
                entity_type="GovernancePolicy",
                entity_id=str(policy.id),
                entity_name=policy.name,
            )

            await db.delete(policy)
            await db.commit()
            return True

        except Exception as e:
            await db.rollback()
            logger.error(f"Error deleting governance policy: {str(e)}")
            raise
