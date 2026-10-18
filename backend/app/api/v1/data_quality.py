import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user_from_token
from app.core.rbac import require_permission
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
from sqlalchemy import select, func
from sqlalchemy.orm import aliased
from app.core.dataset_access import get_accessible_dataset, visible_rules_clause
from app.models.data_quality_rule import DataQualityRule, DataQualityResult
from app.services import rule_engine, quality_discovery_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data-quality", tags=["Data Quality"])



def _rule_dict(rule: DataQualityRule, last) -> dict:
    executable = rule_engine.is_executable(rule.rule_type, rule.dataset_id, rule.target_field, rule.rule_definition)
    return {
        **rule.__dict__,
        "owner_name": rule.owner.full_name if rule.owner else None,
        "created_by_name": rule.created_by.full_name if rule.created_by else None,
        # Whether the platform actually runs this rule; other rules are
        # stored definitions only and are never presented as executed.
        "executable": executable,
        "last_result_status": last.status if last else None,
        "last_result_at": last.execution_timestamp if last else None,
        "last_records_checked": last.records_checked if last else None,
        "last_records_failed": last.records_failed if last else None,
    }


async def _latest_results(db: AsyncSession, rule_ids: list) -> dict:
    if not rule_ids:
        return {}
    ranked = (
        select(DataQualityResult, func.row_number().over(
            partition_by=DataQualityResult.rule_id, order_by=DataQualityResult.execution_timestamp.desc()
        ).label("rn"))
        .where(DataQualityResult.rule_id.in_(rule_ids))
        .subquery()
    )
    latest = aliased(DataQualityResult, ranked)
    rows = (await db.execute(select(latest).where(ranked.c.rn == 1))).scalars().all()
    return {r.rule_id: r for r in rows}


async def _rule_response(db: AsyncSession, rule: DataQualityRule) -> dict:
    latest = await _latest_results(db, [rule.id])
    return _rule_dict(rule, latest.get(rule.id))


def _validate_executable(rule_type: str, dataset_id, target_field, definition) -> dict | None:
    """Executable rule types must be complete and correct; anything else is
    accepted as a documentation-only definition."""
    if rule_type not in rule_engine.EXECUTABLE_RULE_TYPES:
        return definition
    if dataset_id is None:
        raise HTTPException(status_code=422, detail="This rule type needs a dataset to run against.")
    try:
        return rule_engine.validate_definition(rule_type, target_field, definition)
    except rule_engine.RuleDefinitionError as e:
        raise HTTPException(status_code=422, detail=str(e))

async def _get_visible_rule(db: AsyncSession, rule_id: UUID, user: User):
    """A rule is visible when its dataset is accessible to `user`, or - for a
    rule with no dataset - when `user` created or owns it. Anything else is
    reported as missing so rule IDs can't be probed."""
    rule = await DataQualityService.get_rule(db, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    visible = await db.execute(select(DataQualityRule.id).where(DataQualityRule.id == rule_id, visible_rules_clause(user)))
    if visible.first() is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule

@router.post(
    "/rules",
    response_model=DataQualityRuleResponse,
    status_code=201,
    summary="Create a data quality rule",
)
async def create_rule(
    data: DataQualityRuleCreate,
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_quality:manage")),
):
    """Create a new data quality rule"""
    if data.dataset_id is not None:
        await get_accessible_dataset(db, data.dataset_id, current_user)
    data.rule_definition = _validate_executable(data.rule_type, data.dataset_id, data.target_field, data.rule_definition)
    rule = await DataQualityService.create_rule(db, data, current_user.id)

    if not rule:
        raise HTTPException(status_code=400, detail="Failed to create rule")

    return await _rule_response(db, rule)


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
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_quality:view")),
):
    """List all data quality rules with optional filtering"""
    rules, total = await DataQualityService.list_rules(
        db, dimension=dimension, status=status, page=page, page_size=page_size, user=current_user
    )

    latest = await _latest_results(db, [r.id for r in rules])
    items = [_rule_dict(rule, latest.get(rule.id)) for rule in rules]

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
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_quality:view")),
):
    """Get a specific data quality rule"""
    rule = await _get_visible_rule(db, rule_id, current_user)

    return await _rule_response(db, rule)


@router.put(
    "/rules/{rule_id}",
    response_model=DataQualityRuleResponse,
    summary="Update a data quality rule",
)
async def update_rule(
    rule_id: UUID,
    data: DataQualityRuleUpdate,
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_quality:manage")),
):
    """Update a data quality rule"""
    existing = await _get_visible_rule(db, rule_id, current_user)
    if (existing.rule_definition or {}).get("source") == "auto_discovery":
        raise HTTPException(status_code=400, detail="Automatic checks are managed by scans and can't be edited.")
    merged_type = data.rule_type or existing.rule_type
    merged_field = data.target_field if data.target_field is not None else existing.target_field
    merged_def = data.rule_definition if data.rule_definition is not None else existing.rule_definition
    validated = _validate_executable(merged_type, existing.dataset_id, merged_field, merged_def)
    if merged_type in rule_engine.EXECUTABLE_RULE_TYPES:
        data.rule_definition = validated
    rule = await DataQualityService.update_rule(db, rule_id, data, current_user.id)

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    return await _rule_response(db, rule)


@router.delete(
    "/rules/{rule_id}",
    status_code=204,
    summary="Delete a data quality rule",
)
async def delete_rule(
    rule_id: UUID,
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_quality:manage")),
):
    """Delete a data quality rule"""
    await _get_visible_rule(db, rule_id, current_user)
    success = await DataQualityService.delete_rule(db, rule_id, current_user.id)

    if not success:
        raise HTTPException(status_code=404, detail="Rule not found")

    return None


@router.post(
    "/rules/{rule_id}/run",
    summary="Run an executable rule against the latest version of its dataset",
)
async def run_rule(
    rule_id: UUID,
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_quality:manage")),
):
    rule = await _get_visible_rule(db, rule_id, current_user)
    if not rule_engine.is_executable(rule.rule_type, rule.dataset_id, rule.target_field, rule.rule_definition):
        raise HTTPException(status_code=400, detail="This rule is a definition only and cannot be run.")
    try:
        return await quality_discovery_service.run_rule(db, rule)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/rules/{rule_id}/results",
    response_model=DataQualityResultResponse,
    summary="Get results for a data quality rule",
)
async def get_rule_results(
    rule_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_quality:view")),
):
    """Get all execution results for a specific rule"""
    await _get_visible_rule(db, rule_id, current_user)

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
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_quality:view")),
):
    """Get overall data quality metrics and dimension stats"""
    metrics = await DataQualityService.calculate_metrics(db, user=current_user)
    return metrics


# Monitoring Endpoints
@router.get(
    "/monitoring/trend",
    summary="Get pass rate trend over time",
)
async def get_trend(
    days: int = Query(30, ge=1, le=365),
    dimension: str = Query(None),
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_quality:view")),
):
    """Get pass rate trend for the specified time period"""
    trend = await MonitoringService.get_pass_rate_trend(db, days=days, dimension=dimension, user=current_user)
    return {"days": days, "dimension": dimension, "trend": trend}


@router.get(
    "/monitoring/dimension-trends",
    summary="Get trends for all dimensions",
)
async def get_dimension_trends(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_quality:view")),
):
    """Get pass rate trends for all dimensions"""
    trends = await MonitoringService.get_dimension_trends(db, days=days, user=current_user)
    return {"days": days, "dimensions": trends}


@router.get(
    "/monitoring/rule-performance",
    summary="Get rule performance metrics",
)
async def get_rule_performance(
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_quality:view")),
):
    """Get performance metrics for all rules"""
    performance = await MonitoringService.get_rule_performance(db, limit=limit, user=current_user)
    return {"limit": limit, "rules": performance}


@router.get(
    "/monitoring/failing-rules",
    summary="Get top failing rules",
)
async def get_failing_rules(
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_quality:view")),
):
    """Get the top failing rules with recent failures"""
    failing = await MonitoringService.get_failing_rules(db, limit=limit, user=current_user)
    return {"limit": limit, "failing_rules": failing}


@router.get(
    "/monitoring/health-score",
    summary="Get overall health score",
)
async def get_health_score(
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_quality:view")),
):
    """Get overall data quality health score and status"""
    health = await MonitoringService.get_health_score(db, user=current_user)
    return health
