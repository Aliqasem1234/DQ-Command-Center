import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.data_hierarchy import Dataset, DatasetVersion, DatasetType, DatasetVersionStatus
from app.services import file_storage_service
from app.services.profiling_service import profile_dataset_version
from app.services.dataframe_io import read_dataframe, write_dataframe
from app.services.data_cleaning_service import apply_operations, diff_sample, CleaningOperationError
from app.utils.audit_logger import create_audit_log

logger = logging.getLogger(__name__)


class DatasetProcessingError(Exception):
    """Raised when an uploaded file's content can't be read/profiled at all
    (e.g. a corrupt or unparseable CSV). Distinct from a plain ValueError so
    the route can tell it apart from a genuine conflict like a duplicate
    dataset name."""
    pass


async def create_dataset_from_upload(
    db: AsyncSession,
    domain_id: UUID,
    name: str,
    description: str | None,
    file: UploadFile,
    current_user_id: UUID,
) -> DatasetVersion:
    """Create a brand-new Dataset and its first (original) DatasetVersion
    from an uploaded file, then profile it immediately."""
    now = datetime.now(timezone.utc)

    existing = await db.execute(
        select(Dataset).where(Dataset.domain_id == domain_id, Dataset.name == name)
    )
    if existing.scalar_one_or_none():
        raise ValueError(f"A dataset named '{name}' already exists in this domain.")

    dataset = Dataset(
        name=name,
        description=description,
        domain_id=domain_id,
        dataset_type=DatasetType.FILE,
        data_owner_id=current_user_id,
        status="active",
        created_at=now,
        updated_at=now,
    )
    db.add(dataset)
    await db.flush()

    try:
        version = await _store_new_version(db, dataset, file, current_user_id, source_version=None)
    except Exception:
        await db.rollback()
        raise

    await create_audit_log(
        db=db, user_id=current_user_id, action="CREATE", entity_type="Dataset",
        entity_id=str(dataset.id), entity_name=dataset.name,
        new_values={"name": dataset.name, "domain_id": str(domain_id)},
    )
    await db.commit()

    try:
        await profile_dataset_version(db, version)
    except Exception as e:
        # The file couldn't be read at all (e.g. corrupt/unparseable CSV).
        # A failed upload should leave no trace: remove the dataset, its
        # version, and the stored file rather than leaving a permanently
        # broken, empty dataset behind for the user to find later.
        file_storage_service.delete_file(version.file_path)
        await db.delete(version)
        await db.delete(dataset)
        await db.commit()
        raise DatasetProcessingError(str(e)) from e

    return version


async def add_version_from_upload(
    db: AsyncSession,
    dataset: Dataset,
    file: UploadFile,
    current_user_id: UUID,
) -> DatasetVersion:
    """Upload a fresh raw file as a new version of an existing dataset
    (e.g. a refreshed export), independent of any cleaning chain."""
    version = await _store_new_version(db, dataset, file, current_user_id, source_version=None)

    await create_audit_log(
        db=db, user_id=current_user_id, action="CREATE", entity_type="DatasetVersion",
        entity_id=str(version.id), entity_name=f"{dataset.name} v{version.version_number}",
        new_values={"original_filename": version.original_filename},
    )
    await db.commit()

    try:
        await profile_dataset_version(db, version)
    except Exception as e:
        file_storage_service.delete_file(version.file_path)
        await db.delete(version)
        await db.commit()
        raise DatasetProcessingError(str(e)) from e

    return version


async def _store_new_version(
    db: AsyncSession,
    dataset: Dataset,
    file: UploadFile,
    current_user_id: UUID,
    source_version: DatasetVersion | None,
) -> DatasetVersion:
    max_version_result = await db.execute(
        select(func.max(DatasetVersion.version_number)).where(DatasetVersion.dataset_id == dataset.id)
    )
    max_version = max_version_result.scalar() or 0

    relative_path, file_format, size_bytes = await file_storage_service.save_upload(dataset.id, file)

    version = DatasetVersion(
        dataset_id=dataset.id,
        version_number=max_version + 1,
        file_path=relative_path,
        original_filename=file_storage_service.safe_display_filename(file.filename),
        file_format=file_format,
        file_size_bytes=size_bytes,
        is_original=(max_version == 0),
        source_version_id=source_version.id if source_version else None,
        status=DatasetVersionStatus.UPLOADED,
        created_by_id=current_user_id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(version)
    await db.flush()
    return version


async def get_dataset_or_404(db: AsyncSession, dataset_id: UUID) -> Dataset | None:
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    return result.scalar_one_or_none()


async def get_version_or_404(db: AsyncSession, dataset_id: UUID, version_id: UUID) -> DatasetVersion | None:
    result = await db.execute(
        select(DatasetVersion).where(DatasetVersion.dataset_id == dataset_id, DatasetVersion.id == version_id)
    )
    return result.scalar_one_or_none()


async def list_versions(db: AsyncSession, dataset_id: UUID) -> list[DatasetVersion]:
    result = await db.execute(
        select(DatasetVersion)
        .where(DatasetVersion.dataset_id == dataset_id)
        .order_by(DatasetVersion.version_number.desc())
    )
    return list(result.scalars().all())


async def get_latest_version(db: AsyncSession, dataset_id: UUID) -> DatasetVersion | None:
    result = await db.execute(
        select(DatasetVersion)
        .where(DatasetVersion.dataset_id == dataset_id)
        .order_by(DatasetVersion.version_number.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


def preview_cleaning(version: DatasetVersion, operations: list[dict]) -> dict:
    """Dry-run: apply operations to a copy of the version's real data and
    return a diff summary + sample changed rows. Nothing is written."""
    original = read_dataframe(version.file_path, version.file_format)
    result_df, summary = apply_operations(original, operations)
    samples = diff_sample(original, result_df, limit=20)
    return {**summary, "sample_changes": samples}


async def apply_cleaning(
    db: AsyncSession,
    dataset: Dataset,
    source_version: DatasetVersion,
    operations: list[dict],
    current_user_id: UUID,
) -> DatasetVersion:
    """Apply cleaning operations to source_version's data and persist the
    result as a brand-new DatasetVersion. The source file/version are
    never modified."""
    original = read_dataframe(source_version.file_path, source_version.file_format)
    result_df, summary = apply_operations(original, operations)

    max_version_result = await db.execute(
        select(func.max(DatasetVersion.version_number)).where(DatasetVersion.dataset_id == dataset.id)
    )
    max_version = max_version_result.scalar() or 0
    new_version_number = max_version + 1

    relative_path = f"{dataset.id}/cleaned_v{new_version_number}.{source_version.file_format}"
    write_dataframe(result_df, relative_path, source_version.file_format)
    abs_path = file_storage_service.resolve_path(relative_path)
    size_bytes = abs_path.stat().st_size

    now = datetime.now(timezone.utc)
    new_version = DatasetVersion(
        dataset_id=dataset.id,
        version_number=new_version_number,
        file_path=relative_path,
        original_filename=f"{dataset.name}_cleaned_v{new_version_number}.{source_version.file_format}",
        file_format=source_version.file_format,
        file_size_bytes=size_bytes,
        row_count=len(result_df),
        column_count=len(result_df.columns),
        is_original=False,
        source_version_id=source_version.id,
        cleaning_operations=operations,
        rows_changed=summary["rows_changed"],
        values_changed=summary["values_changed"],
        status=DatasetVersionStatus.UPLOADED,
        created_by_id=current_user_id,
        created_at=now,
    )
    db.add(new_version)
    await db.flush()

    await create_audit_log(
        db=db, user_id=current_user_id, action="CLEAN", entity_type="DatasetVersion",
        entity_id=str(new_version.id), entity_name=f"{dataset.name} v{new_version_number}",
        old_values={"source_version": source_version.version_number},
        new_values={"operations": operations, "rows_changed": summary["rows_changed"], "values_changed": summary["values_changed"]},
    )
    await db.commit()

    await profile_dataset_version(db, new_version)
    return new_version
