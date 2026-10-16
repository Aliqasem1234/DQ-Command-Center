"""
Reorganized Data Hierarchy API Routes

New hierarchical structure:
/api/v1/domains
  ├── List, Create, Get domains
  ├── /{id}/datasets - Datasets in domain
  └── /{id}/governance - Governance for domain

/api/v1/datasets
  ├── List, Create, Get datasets
  ├── /{id}/elements - Elements in dataset
  ├── /{id}/quality-rules - Quality rules
  ├── /{id}/quality-results - Quality results
  ├── /{id}/issues - Quality issues
  ├── /{id}/lineage - Lineage relationships
  └── /{id}/governance - Governance assignments

/api/v1/elements
  ├── List, Get elements
  ├── /{id}/metadata - Metadata details
  └── /{id}/quality-rules - Quality rules

/api/v1/quality-rules
  ├── List, Create, Get rules
  ├── /{id}/results - Rule results
  └── /{id}/effectiveness - Rule effectiveness

/api/v1/quality-issues
  ├── List, Create, Get issues
  └── /{id}/[status|assign|resolve]

/api/v1/dashboard
  ├── /health - Health score
  ├── /dimensions - Quality by dimension
  ├── /trends - Quality trends
  ├── /top-issues - Critical issues
  └── /summary - Overall summary
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional

from app.database import get_db
from app.schemas.data_hierarchy import (
    DataDomainResponse, DataDomainCreate, DataDomainUpdate,
    DatasetResponse, DatasetCreate, DatasetDomainUpdate,
    DataElementResponse, DataElementCreate,
    HealthScoreResponse, DashboardHealthResponse,
    SearchResultsResponse, QualityIssueSummaryResponse,
)
from app.services.data_hierarchy_service import DataHierarchyService
from app.services.quality_analytics_service import QualityAnalyticsService
from app.dependencies import get_current_user_from_token
from app.core.rbac import require_permission
from app.core.dataset_access import (
    get_accessible_dataset, accessible_datasets_clause, get_visible_domain, has_global_dataset_access,
    can_delete_dataset, visible_rules_clause,
)
import logging
from sqlalchemy import select, delete as sa_delete
from app.models.data_hierarchy import Dataset, DatasetVersion
from app.services import file_storage_service
from app.utils.audit_logger import log_audit_action

logger = logging.getLogger(__name__)
from app.models.user import User

router = APIRouter(tags=["data-hierarchy"])


# ===== DOMAIN ENDPOINTS =====

@router.get("/domains", response_model=list[DataDomainResponse])
async def list_domains(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
    _: None = Depends(require_permission("datasets:view")),
) -> list:
    """List the caller's data domains"""
    domains, _ = await DataHierarchyService.list_domains(db, page, page_size, current_user)
    return domains


@router.post("/domains", response_model=DataDomainResponse, status_code=201)
async def create_domain(
    request: DataDomainCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
    _: None = Depends(require_permission("datasets:manage")),
) -> DataDomainResponse:
    """Create a new data domain owned by the caller"""
    try:
        domain = await DataHierarchyService.create_domain(
            db=db,
            name=request.name,
            description=request.description,
            business_owner_id=request.business_owner_id,
            domain_steward_id=request.domain_steward_id,
            current_user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return domain


@router.get("/domains/{domain_id}", response_model=DataDomainResponse)
async def get_domain(
    domain_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
    _: None = Depends(require_permission("datasets:view")),
) -> DataDomainResponse:
    """Get one of the caller's domains"""
    return await get_visible_domain(db, domain_id, current_user)


@router.put("/domains/{domain_id}", response_model=DataDomainResponse)
async def update_domain(
    domain_id: UUID,
    request: DataDomainUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
    _: None = Depends(require_permission("datasets:manage")),
) -> DataDomainResponse:
    """Update one of the caller's domains"""
    domain = await get_visible_domain(db, domain_id, current_user)
    
    # Update fields
    if request.name:
        domain.name = request.name
    if request.description:
        domain.description = request.description
    if request.business_owner_id:
        domain.business_owner_id = request.business_owner_id
    if request.domain_steward_id:
        domain.domain_steward_id = request.domain_steward_id
    
    db.add(domain)
    await db.commit()
    return domain


# ===== DATASET ENDPOINTS =====

@router.get("/datasets", response_model=list[DatasetResponse])
async def list_datasets(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
    _: None = Depends(require_permission("datasets:view")),
) -> list:
    """List all datasets across all domains (filtered by ownership for non-admin users)"""
    datasets, _ = await DataHierarchyService.list_all_datasets(db, page, page_size, current_user)
    return datasets


@router.get("/domains/{domain_id}/datasets", response_model=list[DatasetResponse])
async def list_domain_datasets(
    domain_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
    _: None = Depends(require_permission("datasets:view")),
) -> list:
    """List datasets in one of the caller's domains"""
    await get_visible_domain(db, domain_id, current_user)
    datasets, _ = await DataHierarchyService.list_datasets_in_domain(
        db, domain_id, page, page_size, current_user
    )
    return datasets


@router.post("/datasets", response_model=DatasetResponse, status_code=201)
async def create_dataset(
    request: DatasetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
    _: None = Depends(require_permission("datasets:manage")),
) -> DatasetResponse:
    """Create a new dataset owned by the caller"""
    if request.domain_id is not None:
        await get_visible_domain(db, request.domain_id, current_user)
    # Ownership comes from the caller, never from the request body - otherwise
    # anyone could create datasets "owned" by another user.
    if not has_global_dataset_access(current_user):
        request.data_owner_id = current_user.id
    elif request.data_owner_id is None:
        request.data_owner_id = current_user.id
    dataset = await DataHierarchyService.create_dataset(
        db=db,
        name=request.name,
        domain_id=request.domain_id,
        dataset_type=request.dataset_type,
        description=request.description,
        business_definition=request.business_definition,
        data_source_system=request.data_source_system,
        database_name=request.database_name,
        table_name=request.table_name,
        classification=request.classification,
        data_owner_id=request.data_owner_id,
        data_steward_id=request.data_steward_id,
        current_user_id=current_user.id,
    )
    return dataset


@router.get("/datasets/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(
    dataset_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
    _: None = Depends(require_permission("datasets:view")),
) -> DatasetResponse:
    """Get a specific dataset (owner, steward, governance assignee or super admin)"""
    return await get_accessible_dataset(db, dataset_id, current_user)


@router.delete("/datasets/{dataset_id}", status_code=204)
async def delete_dataset(
    dataset_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
    _: None = Depends(require_permission("datasets:manage")),
) -> None:
    """Permanently delete one of the caller's datasets: its versions and
    stored files, profiling elements, quality rules, results and issues."""
    dataset = await get_accessible_dataset(db, dataset_id, current_user)
    if not can_delete_dataset(dataset, current_user):
        raise HTTPException(status_code=403, detail="Only the dataset owner can delete it")

    file_paths = (
        await db.execute(select(DatasetVersion.file_path).where(DatasetVersion.dataset_id == dataset_id))
    ).scalars().all()
    name = dataset.name
    # Child rows (versions, elements, rules, results, issues, governance,
    # policies, check runs) are removed by ON DELETE CASCADE in the database.
    await db.execute(sa_delete(Dataset).where(Dataset.id == dataset_id))
    await log_audit_action(
        db=db, user_id=current_user.id, action="DELETE", entity_type="Dataset",
        entity_id=str(dataset_id), entity_name=name,
    )
    await db.commit()

    # Files go only after the database change is committed, so a failure
    # can never leave rows pointing at deleted files.
    for path in file_paths:
        try:
            file_storage_service.delete_file(path)
        except Exception as e:  # noqa: BLE001 - an orphaned file must not fail the request
            logger.warning(f"Could not remove stored file for deleted dataset {dataset_id}: {type(e).__name__}")
    file_storage_service.remove_dataset_dir(dataset_id)


@router.patch("/datasets/{dataset_id}/domain", response_model=DatasetResponse)
async def update_dataset_domain(
    dataset_id: UUID,
    request: DatasetDomainUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
    _: None = Depends(require_permission("datasets:manage")),
) -> DatasetResponse:
    """Assign, change, or clear (domain_id: null) the domain a dataset
    belongs to. A dataset is never required to have a domain."""
    await get_accessible_dataset(db, dataset_id, current_user)
    if request.domain_id is not None:
        await get_visible_domain(db, request.domain_id, current_user)
    try:
        dataset = await DataHierarchyService.update_dataset_domain(
            db, dataset_id, request.domain_id, current_user.id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


# ===== DATA ELEMENT ENDPOINTS =====

@router.get("/datasets/{dataset_id}/elements", response_model=list[DataElementResponse])
async def list_elements(
    dataset_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
    _: None = Depends(require_permission("datasets:view")),
) -> list:
    """List elements in a dataset"""
    await get_accessible_dataset(db, dataset_id, current_user)
    elements, _ = await DataHierarchyService.list_elements_in_dataset(
        db, dataset_id, page, page_size
    )
    return elements


@router.post("/elements", response_model=DataElementResponse, status_code=201)
async def create_element(
    request: DataElementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
    _: None = Depends(require_permission("datasets:manage")),
) -> DataElementResponse:
    """Create a new data element"""
    await get_accessible_dataset(db, request.dataset_id, current_user)
    element = await DataHierarchyService.create_element(
        db=db,
        name=request.name,
        dataset_id=request.dataset_id,
        data_type=request.data_type,
        description=request.description,
        business_term=request.business_term,
        business_definition=request.business_definition,
        column_position=request.column_position,
        is_primary_key=request.is_primary_key,
        is_foreign_key=request.is_foreign_key,
        nullable=request.nullable,
        classification=request.classification,
        data_owner_id=request.data_owner_id,
        current_user_id=current_user.id,
    )
    return element


# ===== SEARCH ENDPOINTS =====

@router.get("/search", response_model=SearchResultsResponse)
async def search(
    q: str = Query(..., min_length=2),
    search_type: str = Query("all", pattern="^(all|domain|dataset|element)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
    _: None = Depends(require_permission("datasets:view")),
) -> SearchResultsResponse:
    """Search across data hierarchy"""
    results = await DataHierarchyService.search_hierarchy(db, q, search_type, current_user)
    total = len(results["domains"]) + len(results["datasets"]) + len(results["elements"])
    
    return SearchResultsResponse(
        domains=results["domains"],
        datasets=results["datasets"],
        elements=results["elements"],
        total_results=total,
    )


# ===== DASHBOARD ENDPOINTS =====

@router.get("/dashboard/health", response_model=HealthScoreResponse)
async def get_health_score(
    dataset_id: Optional[UUID] = Query(None),
    days: int = Query(30, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
    _: None = Depends(require_permission("data_quality:view")),
) -> HealthScoreResponse:
    """Health score of the caller's own datasets"""
    health = await QualityAnalyticsService.calculate_overall_health_score(
        db, dataset_id=dataset_id, days=days, user=current_user
    )
    return HealthScoreResponse(**health)


@router.get("/dashboard/summary", response_model=DashboardHealthResponse)
async def get_dashboard_summary(
    dataset_id: Optional[UUID] = Query(None),
    days: int = Query(30, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
    _: None = Depends(require_permission("data_quality:view")),
) -> DashboardHealthResponse:
    """Dashboard summary of the caller's own data (every figure is scoped)"""
    health = await QualityAnalyticsService.calculate_overall_health_score(
        db, dataset_id=dataset_id, days=days, user=current_user
    )
    dimensions = await QualityAnalyticsService.quality_by_dimension(
        db, dataset_id=dataset_id, days=days, user=current_user
    )
    issues = await QualityAnalyticsService.issue_analytics(db, dataset_id=dataset_id, user=current_user)
    trends = await QualityAnalyticsService.quality_trends(
        db, dataset_id=dataset_id, days=days, user=current_user
    )

    from sqlalchemy import select, func
    from app.models.data_hierarchy import Dataset
    from app.models.data_quality_rule import DataQualityRule, RuleStatus

    # Count only datasets this user can open, so the card matches their list.
    total_datasets = (
        await db.execute(select(func.count(Dataset.id)).where(accessible_datasets_clause(current_user)))
    ).scalar() or 0
    total_quality_rules = (
        await db.execute(
            select(func.count(DataQualityRule.id)).where(
                DataQualityRule.status == RuleStatus.ACTIVE, visible_rules_clause(current_user)
            )
        )
    ).scalar() or 0

    return DashboardHealthResponse(
        health_score=health.get("health_score"),
        scanned_datasets=health.get("scanned_datasets", 0),
        status=health.get("status", "unknown"),
        dimensions={k: {"dimension": k, **v} for k, v in dimensions.items()},
        open_issues=issues.get("open_issues", 0),
        critical_issues=issues.get("critical_count", 0),
        recent_trend=trends.get("trend", "unknown"),
        total_datasets=total_datasets,
        total_quality_rules=total_quality_rules,
        daily_trend=trends.get("daily_data", []),
    )


@router.get("/quality-issues/open", response_model=list[QualityIssueSummaryResponse])
async def list_open_issues(
    limit: int = Query(10, ge=1, le=50),
    dataset_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
    _: None = Depends(require_permission("data_quality:view")),
) -> list:
    """List the most recent open quality issues, for dashboard display"""
    issues = await DataHierarchyService.get_open_issues(db, dataset_id=dataset_id, limit=limit, user=current_user)
    return [
        {
            "id": issue.id,
            "description": issue.description,
            "severity": issue.severity.value,
            "status": issue.status.value,
            "dataset_name": issue.dataset.name if issue.dataset else None,
            "detected_at": issue.detected_at,
        }
        for issue in issues
    ]


# Governance role assignments (create/list/update/revoke) live under
# /api/v1/governance/assignments — see app.api.v1.governance.
