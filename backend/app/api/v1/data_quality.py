import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_permission
from app.models.user import User
from app.schemas.data_quality_rule import (
    DataQualityRuleCreate,
    DataQualityRuleUpdate,
    DataQualityRuleResponse,
    DataQualityRuleListResponse,
    DataQualityResultResponse,
    DataQualityMetrics,
)
from app.services.data_quality_service import DataQualityService
from app.services.monitoring_service import MonitoringService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data-quality", tags=["Data Quality"])


@router.post(
    "/rules",
    response_model=DataQualityRuleResponse,
    status_code=201,
    summary="Create a data quality rule",
)
async def create_rule(
    data: DataQualityRuleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_quality:manage")),
):
    """Create a new data quality rule"""
    rule = await DataQualityService.create_rule(db, data, current_user.id)

    if not rule:
        raise HTTPException(status_code=400, detail="Failed to create rule")

    return {
        **rule.__dict__,
        "owner_name": rule.owner.full_name if rule.owner else None,
        "created_by_name": rule.created_by.full_name if rule.created_by else None,
    }


@router.get(
    "/rules",
    response_model=DataQualityRuleListResponse,
    summary="List data quality rules",
)
async def list_rules(
    dimension: str = Query(None),
    status: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_quality:view")),
):
    """List all data quality rules with optional filtering"""
    rules, total = await DataQualityService.list_rules(
        db, dimension=dimension, status=status, page=page, page_size=page_size
    )

    items = [
        {
            **rule.__dict__,
            "owner_name": rule.owner.full_name if rule.owner else None,
            "created_by_name": rule.created_by.full_name if rule.created_by else None,
        }
        for rule in rules
    ]

    total_pages = (total + page_size - 1) // page_size

    return DataQualityRuleListResponse(
        items=items, total=total, page=page, page_size=page_size, total_pages=total_pages
    )


@router.get(
    "/rules/{rule_id}",
    response_model=DataQualityRuleResponse,
    summary="Get a data quality rule",
)
async def get_rule(
    rule_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_quality:view")),
):
    """Get a specific data quality rule"""
    rule = await DataQualityService.get_rule(db, rule_id)

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    return {
        **rule.__dict__,
        "owner_name": rule.owner.full_name if rule.owner else None,
        "created_by_name": rule.created_by.full_name if rule.created_by else None,
    }


@router.put(
    "/rules/{rule_id}",
    response_model=DataQualityRuleResponse,
    summary="Update a data quality rule",
)
async def update_rule(
    rule_id: UUID,
    data: DataQualityRuleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_quality:manage")),
):
    """Update a data quality rule"""
    rule = await DataQualityService.update_rule(db, rule_id, data, current_user.id)

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    return {
        **rule.__dict__,
        "owner_name": rule.owner.full_name if rule.owner else None,
        "created_by_name": rule.created_by.full_name if rule.created_by else None,
    }


@router.delete(
    "/rules/{rule_id}",
    status_code=204,
    summary="Delete a data quality rule",
)
async def delete_rule(
    rule_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_quality:manage")),
):
    """Delete a data quality rule"""
    success = await DataQualityService.delete_rule(db, rule_id, current_user.id)

    if not success:
        raise HTTPException(status_code=404, detail="Rule not found")

    return None


@router.get(
    "/rules/{rule_id}/results",
    response_model=DataQualityResultResponse,
    summary="Get results for a data quality rule",
)
async def get_rule_results(
    rule_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_quality:view")),
):
    """Get all execution results for a specific rule"""
    # Verify rule exists
    rule = await DataQualityService.get_rule(db, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    results, total = await DataQualityService.get_rule_results(
        db, rule_id, page=page, page_size=page_size
    )

    items = [
        {
            **result.__dict__,
            "pass_rate": (
                (result.records_passed / result.records_checked * 100)
                if result.records_checked and result.records_checked > 0
                else None
            ),
        }
        for result in results
    ]

    total_pages = (total + page_size - 1) // page_size

    return DataQualityRuleListResponse(
        items=items, total=total, page=page, page_size=page_size, total_pages=total_pages
    )


@router.get(
    "/metrics",
    response_model=DataQualityMetrics,
    summary="Get data quality metrics",
)
async def get_metrics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_quality:view")),
):
    """Get overall data quality metrics and dimension stats"""
    metrics = await DataQualityService.calculate_metrics(db)
    return metrics


# Monitoring Endpoints
@router.get(
    "/monitoring/trend",
    summary="Get pass rate trend over time",
)
async def get_trend(
    days: int = Query(30, ge=1, le=365),
    dimension: str = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_quality:view")),
):
    """Get pass rate trend for the specified time period"""
    trend = await MonitoringService.get_pass_rate_trend(db, days=days, dimension=dimension)
    return {"days": days, "dimension": dimension, "trend": trend}


@router.get(
    "/monitoring/dimension-trends",
    summary="Get trends for all dimensions",
)
async def get_dimension_trends(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_quality:view")),
):
    """Get pass rate trends for all dimensions"""
    trends = await MonitoringService.get_dimension_trends(db, days=days)
    return {"days": days, "dimensions": trends}


@router.get(
    "/monitoring/rule-performance",
    summary="Get rule performance metrics",
)
async def get_rule_performance(
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_quality:view")),
):
    """Get performance metrics for all rules"""
    performance = await MonitoringService.get_rule_performance(db, limit=limit)
    return {"limit": limit, "rules": performance}


@router.get(
    "/monitoring/failing-rules",
    summary="Get top failing rules",
)
async def get_failing_rules(
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_quality:view")),
):
    """Get the top failing rules with recent failures"""
    failing = await MonitoringService.get_failing_rules(db, limit=limit)
    return {"limit": limit, "failing_rules": failing}


@router.get(
    "/monitoring/health-score",
    summary="Get overall health score",
)
async def get_health_score(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_quality:view")),
):
    """Get overall data quality health score and status"""
    health = await MonitoringService.get_health_score(db)
    return health
