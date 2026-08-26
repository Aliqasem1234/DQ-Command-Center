import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_permission
from app.models.user import User
from app.schemas.data_governance import (
    DataAssetCreate,
    DataAssetUpdate,
    DataAssetResponse,
    DataAssetListResponse,
    GovernancePolicyCreate,
    GovernancePolicyUpdate,
    GovernancePolicyResponse,
    GovernancePolicyListResponse,
    DataStewardshipCreate,
    DataStewardshipUpdate,
    DataStewardshipResponse,
    DataStewardshipListResponse,
)
from app.services.governance_service import GovernanceService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/governance", tags=["Data Governance"])


# Data Asset Endpoints
@router.post(
    "/assets",
    response_model=DataAssetResponse,
    status_code=201,
    summary="Create data asset",
)
async def create_data_asset(
    data: DataAssetCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_governance:manage")),
):
    """Create a new data asset"""
    asset = await GovernanceService.create_data_asset(db, data, current_user.id)
    return {
        **asset.__dict__,
        "data_owner_name": asset.data_owner.full_name if asset.data_owner else None,
        "data_steward_name": asset.data_steward.full_name if asset.data_steward else None,
    }


@router.get(
    "/assets",
    response_model=DataAssetListResponse,
    summary="List data assets",
)
async def list_data_assets(
    asset_type: str = Query(None),
    classification: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_governance:view")),
):
    """List data assets with filtering"""
    assets, total = await GovernanceService.list_data_assets(
        db, asset_type=asset_type, classification=classification, page=page, page_size=page_size
    )

    items = [
        {
            **asset.__dict__,
            "data_owner_name": asset.data_owner.full_name if asset.data_owner else None,
            "data_steward_name": asset.data_steward.full_name if asset.data_steward else None,
        }
        for asset in assets
    ]

    total_pages = (total + page_size - 1) // page_size

    return DataAssetListResponse(
        items=items, total=total, page=page, page_size=page_size, total_pages=total_pages
    )


@router.get(
    "/assets/{asset_id}",
    response_model=DataAssetResponse,
    summary="Get data asset",
)
async def get_data_asset(
    asset_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_governance:view")),
):
    """Get a specific data asset"""
    asset = await GovernanceService.get_data_asset(db, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    return {
        **asset.__dict__,
        "data_owner_name": asset.data_owner.full_name if asset.data_owner else None,
        "data_steward_name": asset.data_steward.full_name if asset.data_steward else None,
    }


@router.put(
    "/assets/{asset_id}",
    response_model=DataAssetResponse,
    summary="Update data asset",
)
async def update_data_asset(
    asset_id: UUID,
    data: DataAssetUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_governance:manage")),
):
    """Update a data asset"""
    asset = await GovernanceService.update_data_asset(db, asset_id, data, current_user.id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    return {
        **asset.__dict__,
        "data_owner_name": asset.data_owner.full_name if asset.data_owner else None,
        "data_steward_name": asset.data_steward.full_name if asset.data_steward else None,
    }


@router.delete(
    "/assets/{asset_id}",
    status_code=204,
    summary="Delete data asset",
)
async def delete_data_asset(
    asset_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_governance:manage")),
):
    """Delete a data asset"""
    success = await GovernanceService.delete_data_asset(db, asset_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Asset not found")


# Governance Policy Endpoints
@router.post(
    "/policies",
    response_model=GovernancePolicyResponse,
    status_code=201,
    summary="Create governance policy",
)
async def create_policy(
    data: GovernancePolicyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_governance:manage")),
):
    """Create a governance policy"""
    policy = await GovernanceService.create_governance_policy(db, data, current_user.id)
    return {
        **policy.__dict__,
        "created_by_name": policy.created_by.full_name if policy.created_by else None,
    }


@router.get(
    "/policies",
    response_model=GovernancePolicyListResponse,
    summary="List governance policies",
)
async def list_policies(
    policy_type: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_governance:view")),
):
    """List governance policies"""
    policies, total = await GovernanceService.list_governance_policies(
        db, policy_type=policy_type, page=page, page_size=page_size
    )

    items = [
        {
            **policy.__dict__,
            "created_by_name": policy.created_by.full_name if policy.created_by else None,
        }
        for policy in policies
    ]

    total_pages = (total + page_size - 1) // page_size

    return GovernancePolicyListResponse(
        items=items, total=total, page=page, page_size=page_size, total_pages=total_pages
    )


# Data Stewardship Endpoints
@router.post(
    "/stewardships",
    response_model=DataStewardshipResponse,
    status_code=201,
    summary="Create data stewardship",
)
async def create_stewardship(
    data: DataStewardshipCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_governance:manage")),
):
    """Create a data stewardship relationship"""
    stewardship = await GovernanceService.create_data_stewardship(db, data, current_user.id)
    return {
        **stewardship.__dict__,
        "user_name": stewardship.user.full_name if stewardship.user else None,
        "data_asset_name": stewardship.data_asset.name if stewardship.data_asset else None,
    }


@router.get(
    "/stewardships",
    response_model=DataStewardshipListResponse,
    summary="List data stewardships",
)
async def list_stewardships(
    data_asset_id: UUID = Query(None),
    responsibility_type: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_governance:view")),
):
    """List data stewardships"""
    stewardships, total = await GovernanceService.list_data_stewardships(
        db, data_asset_id=data_asset_id, responsibility_type=responsibility_type, page=page, page_size=page_size
    )

    items = [
        {
            **stewardship.__dict__,
            "user_name": stewardship.user.full_name if stewardship.user else None,
            "data_asset_name": stewardship.data_asset.name if stewardship.data_asset else None,
        }
        for stewardship in stewardships
    ]

    total_pages = (total + page_size - 1) // page_size

    return DataStewardshipListResponse(
        items=items, total=total, page=page, page_size=page_size, total_pages=total_pages
    )
