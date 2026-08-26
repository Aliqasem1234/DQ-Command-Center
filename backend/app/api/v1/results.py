from fastapi import APIRouter, Depends, Query
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user_from_token
from app.core.rbac import require_permission
from app.models.user import User
from app.services.results_reporting_service import ResultsReportingService

router = APIRouter(prefix="/results", tags=["Results Reporting"])


@router.get("/{rule_id}/statistics", summary="Get result statistics for a rule")
async def get_statistics(
    rule_id: UUID,
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_quality:view")),
):
    """Get detailed statistics for results of a specific rule"""
    stats = await ResultsReportingService.get_result_statistics(db, rule_id=rule_id, days=days)
    return {"rule_id": str(rule_id), "days": days, **stats}


@router.get("/errors/summary", summary="Get error summary")
async def get_error_summary(
    rule_id: UUID = Query(None),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_quality:view")),
):
    """Get summary of recent errors"""
    errors = await ResultsReportingService.get_error_summary(db, rule_id=rule_id, limit=limit)
    return {"limit": limit, "errors": errors}


@router.get("/{rule_id}/timeline", summary="Get result timeline for a rule")
async def get_timeline(
    rule_id: UUID,
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_quality:view")),
):
    """Get timeline of recent results for a rule"""
    timeline = await ResultsReportingService.get_result_timeline(db, rule_id=rule_id, limit=limit)
    return {"rule_id": str(rule_id), "limit": limit, "timeline": timeline}


@router.get("/{rule_id}/failure-analysis", summary="Analyze failure patterns")
async def analyze_failures(
    rule_id: UUID,
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_quality:view")),
):
    """Analyze failure patterns and trends for a rule"""
    analysis = await ResultsReportingService.get_failure_analysis(db, rule_id=rule_id, days=days)
    return {"rule_id": str(rule_id), "days": days, **analysis}


@router.get("/quality-report", summary="Generate quality report")
async def generate_report(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_quality:view")),
):
    """Generate comprehensive quality report"""
    report = await ResultsReportingService.get_quality_report(db, days=days)
    return report
