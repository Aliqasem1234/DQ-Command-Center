import logging
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.metadata import Metadata, MetadataTag
from app.utils.audit_logger import log_audit_action

logger = logging.getLogger(__name__)


class MetadataService:
    """Service for managing metadata"""

    @staticmethod
    async def create_or_update_metadata(
        db: AsyncSession,
        data_asset_id: UUID,
        metadata_data: dict,
        current_user_id: UUID,
    ) -> Metadata:
        """Create or update metadata for a data asset"""
        try:
            result = await db.execute(
                select(Metadata).where(Metadata.data_asset_id == data_asset_id)
            )
            metadata = result.scalar_one_or_none()

            if not metadata:
                metadata = Metadata(data_asset_id=data_asset_id, **metadata_data)
                db.add(metadata)
            else:
                for key, value in metadata_data.items():
                    if value is not None:
                        setattr(metadata, key, value)
                metadata.updated_at = datetime.now(timezone.utc)

            await db.flush()
            await db.commit()
            return metadata

        except Exception as e:
            await db.rollback()
            logger.error(f"Error managing metadata: {str(e)}")
            raise

    @staticmethod
    async def add_metadata_tag(
        db: AsyncSession,
        metadata_id: UUID,
        tag: str,
        category: str = None,
    ) -> MetadataTag:
        """Add a tag to metadata"""
        try:
            metadata_tag = MetadataTag(
                metadata_id=metadata_id,
                tag=tag,
                category=category,
            )
            db.add(metadata_tag)
            await db.commit()
            return metadata_tag

        except Exception as e:
            await db.rollback()
            logger.error(f"Error adding metadata tag: {str(e)}")
            raise

    @staticmethod
    async def get_metadata_by_asset(db: AsyncSession, data_asset_id: UUID) -> Metadata:
        """Get metadata for a data asset"""
        result = await db.execute(
            select(Metadata).where(Metadata.data_asset_id == data_asset_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_metadata_tags(db: AsyncSession, metadata_id: UUID) -> list[MetadataTag]:
        """Get all tags for a metadata entry"""
        result = await db.execute(
            select(MetadataTag).where(MetadataTag.metadata_id == metadata_id)
        )
        return result.scalars().all()

    @staticmethod
    async def search_metadata(
        db: AsyncSession,
        search_term: str = None,
        tag: str = None,
        data_type: str = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[Metadata], int]:
        """Search metadata with filtering"""
        query = select(Metadata)

        if search_term:
            query = query.where(
                Metadata.display_name.ilike(f"%{search_term}%") |
                Metadata.description.ilike(f"%{search_term}%") |
                Metadata.business_definition.ilike(f"%{search_term}%")
            )

        if data_type:
            query = query.where(Metadata.data_type == data_type)

        count_result = await db.execute(
            select(func.count(Metadata.id)).select_from(query.statement.subquery())
        )
        total = count_result.scalar() or 0

        query = query.order_by(desc(Metadata.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        metadata = result.scalars().all()

        return metadata, total

    @staticmethod
    async def get_metadata_statistics(db: AsyncSession) -> dict:
        """Get statistics about all metadata"""
        try:
            total_result = await db.execute(select(func.count(Metadata.id)))
            total = total_result.scalar() or 0

            profiled_result = await db.execute(
                select(func.count(Metadata.id)).where(Metadata.last_profiled.isnot(None))
            )
            profiled = profiled_result.scalar() or 0

            avg_completeness_result = await db.execute(
                select(func.avg(Metadata.completeness_score))
            )
            avg_completeness = avg_completeness_result.scalar() or 0

            avg_validity_result = await db.execute(
                select(func.avg(Metadata.validity_score))
            )
            avg_validity = avg_validity_result.scalar() or 0

            avg_uniqueness_result = await db.execute(
                select(func.avg(Metadata.uniqueness_score))
            )
            avg_uniqueness = avg_uniqueness_result.scalar() or 0

            return {
                "total_metadata": total,
                "profiled_count": profiled,
                "profile_coverage": (profiled / total * 100) if total > 0 else 0,
                "avg_completeness_score": float(avg_completeness),
                "avg_validity_score": float(avg_validity),
                "avg_uniqueness_score": float(avg_uniqueness),
            }

        except Exception as e:
            logger.error(f"Error getting metadata statistics: {str(e)}")
            return {}
