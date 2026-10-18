"""
Dataset file ingestion, profiling, automatic quality discovery, cleaning,
and export - the "bring your own data" pipeline. Mounted at
/api/v1/dataset-files to avoid clashing with the existing
/api/v1/datasets endpoints in data_hierarchy_routes.py, which manage the
Dataset entity itself (metadata, not file content).
"""
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_user_from_token
from app.core.rbac import require_permission
from app.models.user import User
from app.models.data_hierarchy import DatasetVersion
from app.schemas.dataset_upload import (
    DatasetVersionResponse, ProfileSummaryResponse, ScanResultResponse,
    CleaningRequest, CleaningPreviewResponse, QualityComparisonResponse, VersionQualitySummary,
)
from app.services import dataset_upload_service, file_storage_service
from app.services.file_storage_service import UploadValidationError
from app.core.dataset_access import get_accessible_dataset, get_visible_domain
from app.services.dataset_upload_service import DatasetProcessingError
from app.services.profiling_service import profile_dataset_version
from app.services.quality_discovery_service import scan_dataset_version
from app.services.data_cleaning_service import CleaningOperationError
from app.services.dataframe_io import read_dataframe

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dataset-files", tags=["Dataset Files"])


def _version_to_response(version: DatasetVersion) -> dict:
    return {
        **{k: v for k, v in version.__dict__.items() if not k.startswith("_")},
        "created_by_name": version.created_by.full_name if version.created_by else None,
    }


async def _get_version_with_creator(db: AsyncSession, dataset_id: UUID, version_id: UUID) -> DatasetVersion:
    result = await db.execute(
        select(DatasetVersion)
        .options(selectinload(DatasetVersion.created_by))
        .where(DatasetVersion.dataset_id == dataset_id, DatasetVersion.id == version_id)
    )
    version = result.scalar_one_or_none()
    if version is None:
        raise HTTPException(status_code=404, detail="Dataset version not found")
    return version


@router.post("/upload", response_model=DatasetVersionResponse, status_code=201, summary="Upload a file to create a new dataset")
async def upload_new_dataset(
    domain_id: str | None = Form(None),
    name: str = Form(...),
    description: str | None = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("datasets:manage")),
):
    # A dataset is never required to have a domain, so an empty string (a
    # blank form field, rather than an omitted one) is treated the same as
    # not providing one at all.
    parsed_domain_id: UUID | None = None
    if domain_id:
        try:
            parsed_domain_id = UUID(domain_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid domain_id")

    if parsed_domain_id is not None:
        await get_visible_domain(db, parsed_domain_id, current_user)
    try:
        version = await dataset_upload_service.create_dataset_from_upload(
            db, parsed_domain_id, name, description, file, current_user.id
        )
    except UploadValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatasetProcessingError as e:
        raise HTTPException(status_code=422, detail=f"Could not process file: {e}")
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    version = await _get_version_with_creator(db, version.dataset_id, version.id)
    return _version_to_response(version)


@router.post("/{dataset_id}/versions/upload", response_model=DatasetVersionResponse, status_code=201, summary="Upload a fresh file as a new version of an existing dataset")
async def upload_new_version(
    dataset_id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("datasets:manage")),
):
    dataset = await get_accessible_dataset(db, dataset_id, current_user)
    try:
        version = await dataset_upload_service.add_version_from_upload(db, dataset, file, current_user.id)
    except UploadValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatasetProcessingError as e:
        raise HTTPException(status_code=422, detail=f"Could not process file: {e}")
    version = await _get_version_with_creator(db, dataset_id, version.id)
    return _version_to_response(version)


@router.get("/{dataset_id}/versions", response_model=list[DatasetVersionResponse], summary="List all versions of a dataset")
async def list_versions(
    dataset_id: UUID,
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("datasets:view")),
):
    await get_accessible_dataset(db, dataset_id, current_user)
    result = await db.execute(
        select(DatasetVersion)
        .options(selectinload(DatasetVersion.created_by))
        .where(DatasetVersion.dataset_id == dataset_id)
        .order_by(DatasetVersion.version_number.desc())
    )
    return [_version_to_response(v) for v in result.scalars().all()]


@router.get("/{dataset_id}/versions/{version_id}", response_model=DatasetVersionResponse, summary="Get a specific dataset version")
async def get_version(
    dataset_id: UUID,
    version_id: UUID,
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("datasets:view")),
):
    await get_accessible_dataset(db, dataset_id, current_user)
    version = await _get_version_with_creator(db, dataset_id, version_id)
    return _version_to_response(version)


@router.get("/{dataset_id}/versions/{version_id}/rows", summary="Preview raw rows from a version's file")
async def preview_rows(
    dataset_id: UUID,
    version_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("datasets:view")),
):
    await get_accessible_dataset(db, dataset_id, current_user)
    version = await dataset_upload_service.get_version_or_404(db, dataset_id, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Dataset version not found")
    df = read_dataframe(version.file_path, version.file_format)
    total = len(df)
    start = (page - 1) * page_size
    page_df = df.iloc[start:start + page_size]
    return {
        "columns": list(df.columns),
        "rows": page_df.fillna("").to_dict("records"),
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/{dataset_id}/versions/{version_id}/profile", response_model=ProfileSummaryResponse, summary="(Re-)profile a version")
async def reprofile_version(
    dataset_id: UUID,
    version_id: UUID,
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("datasets:manage")),
):
    await get_accessible_dataset(db, dataset_id, current_user)
    version = await dataset_upload_service.get_version_or_404(db, dataset_id, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Dataset version not found")
    try:
        return await profile_dataset_version(db, version)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not profile file: {e}")


@router.post("/{dataset_id}/versions/{version_id}/scan", response_model=ScanResultResponse, summary="Run automatic data quality discovery on a version")
async def scan_version(
    dataset_id: UUID,
    version_id: UUID,
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("datasets:manage")),
):
    await get_accessible_dataset(db, dataset_id, current_user)
    version = await dataset_upload_service.get_version_or_404(db, dataset_id, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Dataset version not found")
    try:
        return await scan_dataset_version(db, version, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not scan file: {e}")


@router.post("/{dataset_id}/versions/{version_id}/clean/preview", response_model=CleaningPreviewResponse, summary="Dry-run cleaning operations without saving")
async def preview_cleaning(
    dataset_id: UUID,
    version_id: UUID,
    body: CleaningRequest,
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("datasets:manage")),
):
    await get_accessible_dataset(db, dataset_id, current_user)
    version = await dataset_upload_service.get_version_or_404(db, dataset_id, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Dataset version not found")
    try:
        operations = [op.model_dump(exclude_none=True) for op in body.operations]
        return await dataset_upload_service.preview_cleaning(db, version, operations)
    except CleaningOperationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{dataset_id}/versions/{version_id}/clean", response_model=DatasetVersionResponse, status_code=201, summary="Apply cleaning operations, creating a new version")
async def apply_cleaning(
    dataset_id: UUID,
    version_id: UUID,
    body: CleaningRequest,
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("datasets:manage")),
):
    dataset = await get_accessible_dataset(db, dataset_id, current_user)
    version = await dataset_upload_service.get_version_or_404(db, dataset_id, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Dataset version not found")
    try:
        operations = [op.model_dump(exclude_none=True) for op in body.operations]
        new_version = await dataset_upload_service.apply_cleaning(db, dataset, version, operations, current_user.id)
    except CleaningOperationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    new_version = await _get_version_with_creator(db, dataset_id, new_version.id)
    return _version_to_response(new_version)


@router.post("/{dataset_id}/versions/{version_id}/restore", response_model=DatasetVersionResponse, status_code=201, summary="Restore an earlier version as a new version")
async def restore_version(
    dataset_id: UUID,
    version_id: UUID,
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("datasets:manage")),
):
    dataset = await get_accessible_dataset(db, dataset_id, current_user)
    version = await dataset_upload_service.get_version_or_404(db, dataset_id, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Dataset version not found")
    new_version = await dataset_upload_service.restore_version(db, dataset, version, current_user.id)
    new_version = await _get_version_with_creator(db, dataset_id, new_version.id)
    return _version_to_response(new_version)


@router.get("/{dataset_id}/versions/{version_id}/download", summary="Download a version's file")
async def download_version(
    dataset_id: UUID,
    version_id: UUID,
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("datasets:view")),
):
    await get_accessible_dataset(db, dataset_id, current_user)
    version = await dataset_upload_service.get_version_or_404(db, dataset_id, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Dataset version not found")
    path = file_storage_service.resolve_path(version.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File no longer exists on disk")
    filename = version.original_filename or f"version-{version.version_number}.{version.file_format}"
    media_type = "text/csv" if version.file_format == "csv" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return FileResponse(path=str(path), filename=filename, media_type=media_type)


@router.get("/{dataset_id}/quality-comparison", response_model=QualityComparisonResponse, summary="Compare quality score across all versions of a dataset")
async def quality_comparison(
    dataset_id: UUID,
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("datasets:view")),
):
    await get_accessible_dataset(db, dataset_id, current_user)
    versions = await dataset_upload_service.list_versions(db, dataset_id)
    return QualityComparisonResponse(
        dataset_id=dataset_id,
        versions=[
            VersionQualitySummary(
                version_id=v.id,
                version_number=v.version_number,
                is_original=v.is_original,
                quality_score=v.quality_score,
                row_count=v.row_count,
                created_at=v.created_at,
            )
            for v in sorted(versions, key=lambda v: v.version_number)
        ],
    )
