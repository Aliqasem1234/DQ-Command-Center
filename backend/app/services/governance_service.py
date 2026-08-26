import logging
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.data_governance import DataAsset, GovernancePolicy, DataStewardship
from app.schemas.data_governance import (
    DataAssetCreate,
    DataAssetUpdate,
    GovernancePolicyCreate,
    GovernancePolicyUpdate,
    DataStewardshipCreate,
    DataStewardshipUpdate,
)
from app.utils.audit_logger import log_audit_action

logger = logging.getLogger(__name__)


class GovernanceService:
    """Service for managing data governance"""

    # Data Asset Methods
    @staticmethod
    async def create_data_asset(
        db: AsyncSession,
        data: DataAssetCreate,
        current_user_id: UUID,
    ) -> DataAsset:
        """Create a new data asset"""
        try:
            now = datetime.now(timezone.utc)

            asset = DataAsset(
                name=data.name,
                description=data.description,
                business_definition=data.business_definition,
                asset_type=data.asset_type,
                data_source=data.data_source,
                database_name=data.database_name,
                table_or_collection=data.table_or_collection,
                classification=data.classification,
                status=data.status,
                data_owner_id=data.data_owner_id,
                data_steward_id=data.data_steward_id,
                retention_days=data.retention_days,
                is_active=data.is_active,
                created_at=now,
                updated_at=now,
            )

            db.add(asset)
            await db.flush()

            await log_audit_action(
                db=db,
                user_id=current_user_id,
                action="CREATE",
                entity_type="DataAsset",
                entity_id=str(asset.id),
                entity_name=asset.name,
                new_values={"name": asset.name, "asset_type": asset.asset_type},
            )

            await db.commit()
            return asset

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating data asset: {str(e)}")
            raise

    @staticmethod
    async def get_data_asset(db: AsyncSession, asset_id: UUID) -> DataAsset:
        """Get a data asset by ID"""
        result = await db.execute(
            select(DataAsset).where(DataAsset.id == asset_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_data_assets(
        db: AsyncSession,
        asset_type: str = None,
        classification: str = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[DataAsset], int]:
        """List data assets with filtering"""
        query = select(DataAsset)

        if asset_type:
            query = query.where(DataAsset.asset_type == asset_type)

        if classification:
            query = query.where(DataAsset.classification == classification)

        count_result = await db.execute(
            select(func.count(DataAsset.id)).select_from(query.statement.subquery())
        )
        total = count_result.scalar() or 0

        query = query.order_by(desc(DataAsset.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        assets = result.scalars().all()

        return assets, total

    @staticmethod
    async def update_data_asset(
        db: AsyncSession,
        asset_id: UUID,
        data: DataAssetUpdate,
        current_user_id: UUID,
    ) -> DataAsset:
        """Update a data asset"""
        try:
            result = await db.execute(
                select(DataAsset).where(DataAsset.id == asset_id)
            )
            asset = result.scalar_one_or_none()

            if not asset:
                return None

            old_values = {"name": asset.name, "classification": asset.classification.value}

            update_data = data.dict(exclude_unset=True)
            for field, value in update_data.items():
                if value is not None:
                    setattr(asset, field, value)

            asset.updated_at = datetime.now(timezone.utc)
            db.add(asset)
            await db.flush()

            await log_audit_action(
                db=db,
                user_id=current_user_id,
                action="UPDATE",
                entity_type="DataAsset",
                entity_id=str(asset.id),
                entity_name=asset.name,
                old_values=old_values,
                new_values={"name": asset.name, "classification": asset.classification.value},
            )

            await db.commit()
            return asset

        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating data asset: {str(e)}")
            raise

    @staticmethod
    async def delete_data_asset(
        db: AsyncSession,
        asset_id: UUID,
        current_user_id: UUID,
    ) -> bool:
        """Delete a data asset"""
        try:
            result = await db.execute(
                select(DataAsset).where(DataAsset.id == asset_id)
            )
            asset = result.scalar_one_or_none()

            if not asset:
                return False

            asset_name = asset.name

            await log_audit_action(
                db=db,
                user_id=current_user_id,
                action="DELETE",
                entity_type="DataAsset",
                entity_id=str(asset.id),
                entity_name=asset_name,
            )

            await db.delete(asset)
            await db.commit()
            return True

        except Exception as e:
            await db.rollback()
            logger.error(f"Error deleting data asset: {str(e)}")
            raise

    # Governance Policy Methods
    @staticmethod
    async def create_governance_policy(
        db: AsyncSession,
        data: GovernancePolicyCreate,
        current_user_id: UUID,
    ) -> GovernancePolicy:
        """Create a governance policy"""
        try:
            now = datetime.now(timezone.utc)

            policy = GovernancePolicy(
                name=data.name,
                description=data.description,
                data_asset_id=data.data_asset_id,
                department_id=data.department_id,
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

            await log_audit_action(
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
    async def list_governance_policies(
        db: AsyncSession,
        policy_type: str = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[GovernancePolicy], int]:
        """List governance policies"""
        query = select(GovernancePolicy)

        if policy_type:
            query = query.where(GovernancePolicy.policy_type == policy_type)

        count_result = await db.execute(
            select(func.count(GovernancePolicy.id)).select_from(query.statement.subquery())
        )
        total = count_result.scalar() or 0

        query = query.order_by(desc(GovernancePolicy.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        policies = result.scalars().all()

        return policies, total

    # Data Stewardship Methods
    @staticmethod
    async def create_data_stewardship(
        db: AsyncSession,
        data: DataStewardshipCreate,
        current_user_id: UUID,
    ) -> DataStewardship:
        """Create a data stewardship relationship"""
        try:
            stewardship = DataStewardship(
                data_asset_id=data.data_asset_id,
                user_id=data.user_id,
                department_id=data.department_id,
                responsibility_type=data.responsibility_type,
                description=data.description,
                start_date=data.start_date,
                end_date=data.end_date,
                is_active=data.is_active,
            )

            db.add(stewardship)
            await db.flush()

            await log_audit_action(
                db=db,
                user_id=current_user_id,
                action="CREATE",
                entity_type="DataStewardship",
                entity_id=str(stewardship.id),
                entity_name=data.responsibility_type,
            )

            await db.commit()
            return stewardship

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating data stewardship: {str(e)}")
            raise

    @staticmethod
    async def list_data_stewardships(
        db: AsyncSession,
        data_asset_id: UUID = None,
        responsibility_type: str = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[DataStewardship], int]:
        """List data stewardships"""
        query = select(DataStewardship)

        if data_asset_id:
            query = query.where(DataStewardship.data_asset_id == data_asset_id)

        if responsibility_type:
            query = query.where(DataStewardship.responsibility_type == responsibility_type)

        count_result = await db.execute(
            select(func.count(DataStewardship.id)).select_from(query.statement.subquery())
        )
        total = count_result.scalar() or 0

        query = query.order_by(desc(DataStewardship.assigned_date))
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        stewardships = result.scalars().all()

        return stewardships, total
