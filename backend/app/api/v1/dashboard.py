from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user_from_token
from app.core.rbac import require_permission
from app.models.user import User
from app.schemas.dashboard import DashboardResponse
from app.services import dashboard_service
from app.services.enhanced_dashboard_service import EnhancedDashboardService

router = APIRouter(prefix="/dashboard")


@router.get(
    "/stats",
    response_model=DashboardResponse,
    summary="Get dashboard statistics and charts",
)
async def get_dashboard(
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
):
    return await dashboard_service.get_dashboard_data(db)


@router.get(
    "/enhanced",
    summary="Get enhanced dashboard with DQ metrics",
)
async def get_enhanced_dashboard(
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
):
    """Get complete dashboard with data quality and governance metrics"""
    return await EnhancedDashboardService.get_full_dashboard(db)


@router.get(
    "/data-quality",
    summary="Get data quality dashboard section",
)
async def get_dq_section(
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_quality:view")),
):
    """Get data quality section for dashboard"""
    return await EnhancedDashboardService.get_dq_dashboard_section(db)


@router.get(
    "/governance",
    summary="Get governance dashboard section",
)
async def get_governance_section(
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_governance:view")),
):
    """Get governance section for dashboard"""
    return await EnhancedDashboardService.get_governance_dashboard_section(db)
