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
    DatasetResponse, DatasetCreate,
    DataElementResponse, DataElementCreate,
    HealthScoreResponse, DashboardHealthResponse,
    SearchResultsResponse,
)
from app.services.data_hierarchy_service import DataHierarchyService
from app.services.quality_analytics_service import QualityAnalyticsService
from app.dependencies import get_current_user_from_token
from app.core.rbac import require_permission
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
    """List all data domains"""
    domains, _ = await DataHierarchyService.list_domains(db, page, page_size)
    return domains


@router.post("/domains", response_model=DataDomainResponse, status_code=201)
async def create_domain(
    request: DataDomainCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
    _: None = Depends(require_permission("datasets:manage")),
) -> DataDomainResponse:
    """Create a new data domain"""
    domain = await DataHierarchyService.create_domain(
        db=db,
        name=request.name,
        description=request.description,
        business_owner_id=request.business_owner_id,
        domain_steward_id=request.domain_steward_id,
        current_user_id=current_user.id,
    )
    return domain


@router.get("/domains/{domain_id}", response_model=DataDomainResponse)
async def get_domain(
    domain_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
    _: None = Depends(require_permission("datasets:view")),
) -> DataDomainResponse:
    """Get a specific domain"""
    domain = await DataHierarchyService.get_domain(db, domain_id)
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    return domain


@router.put("/domains/{domain_id}", response_model=DataDomainResponse)
async def update_domain(
    domain_id: UUID,
    request: DataDomainUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
    _: None = Depends(require_permission("datasets:manage")),
) -> DataDomainResponse:
    """Update a domain"""
    domain = await DataHierarchyService.get_domain(db, domain_id)
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    
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
    """List all datasets across all domains"""
    datasets, _ = await DataHierarchyService.list_all_datasets(db, page, page_size)
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
    """List datasets in a domain"""
    datasets, _ = await DataHierarchyService.list_datasets_in_domain(
        db, domain_id, page, page_size
    )
    return datasets


@router.post("/datasets", response_model=DatasetResponse, status_code=201)
async def create_dataset(
    request: DatasetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
    _: None = Depends(require_permission("datasets:manage")),
) -> DatasetResponse:
    """Create a new dataset"""
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
    """Get a specific dataset"""
    dataset = await DataHierarchyService.get_dataset(db, dataset_id)
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
    results = await DataHierarchyService.search_hierarchy(db, q, search_type)
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
    """Get overall health score"""
    health = await QualityAnalyticsService.calculate_overall_health_score(
        db, dataset_id=dataset_id, days=days
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
    """Get complete dashboard summary"""
    health = await QualityAnalyticsService.calculate_overall_health_score(
        db, dataset_id=dataset_id, days=days
    )
    dimensions = await QualityAnalyticsService.quality_by_dimension(
        db, dataset_id=dataset_id, days=days
    )
    issues = await QualityAnalyticsService.issue_analytics(db, dataset_id=dataset_id)
    trends = await QualityAnalyticsService.quality_trends(
        db, dataset_id=dataset_id, days=days
    )
    
    return DashboardHealthResponse(
        health_score=health.get("health_score", 0),
        status=health.get("status", "unknown"),
        dimensions={k: {"dimension": k, **v} for k, v in dimensions.items()},
        open_issues=issues.get("open_issues", 0),
        critical_issues=issues.get("critical_count", 0),
        recent_trend=trends.get("trend", "unknown"),
    )


# Governance role assignments (create/list/update/revoke) live under
# /api/v1/governance/assignments — see app.api.v1.governance.
