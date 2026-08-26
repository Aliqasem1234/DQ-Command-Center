import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user_from_token
from app.core.rbac import require_permission
from app.models.user import User
from app.schemas.data_governance import (
    GovernanceAssignmentCreate,
    GovernanceAssignmentUpdate,
    GovernanceAssignmentResponse,
    GovernanceAssignmentListResponse,
    GovernancePolicyCreate,
    GovernancePolicyUpdate,
    GovernancePolicyResponse,
    GovernancePolicyListResponse,
)
from app.services.governance_service import GovernanceService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/governance", tags=["Data Governance"])


def _assignment_to_response(assignment) -> dict:
    scope_name = None
    if assignment.domain:
        scope_name = assignment.domain.name
    elif assignment.dataset:
        scope_name = assignment.dataset.name
    elif assignment.element:
        scope_name = assignment.element.name

    return {
        "id": assignment.id,
        "domain_id": assignment.domain_id,
        "dataset_id": assignment.dataset_id,
        "element_id": assignment.element_id,
        "role": assignment.role,
        "user_id": assignment.user_id,
        "user_name": assignment.user.full_name if assignment.user else None,
        "department_id": assignment.department_id,
        "responsibility_description": assignment.responsibility_description,
        "start_date": assignment.start_date,
        "end_date": assignment.end_date,
        "is_active": assignment.is_active,
        "assigned_date": assignment.assigned_date,
        "scope_name": scope_name,
    }


def _policy_to_response(policy) -> dict:
    return {
        **{k: v for k, v in policy.__dict__.items() if not k.startswith("_")},
        "created_by_name": policy.created_by.full_name if policy.created_by else None,
    }


# Governance Assignment Endpoints (owner / steward / curator / analyst)
@router.post(
    "/assignments",
    response_model=GovernanceAssignmentResponse,
    status_code=201,
    summary="Assign a governance role (owner/steward/curator/analyst) to a domain, dataset, or element",
)
async def create_assignment(
    data: GovernanceAssignmentCreate,
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_governance:manage")),
):
    assignment = await GovernanceService.create_assignment(db, data, current_user.id)
    return _assignment_to_response(assignment)


@router.get(
    "/assignments",
    response_model=GovernanceAssignmentListResponse,
    summary="List governance role assignments",
)
async def list_assignments(
    domain_id: UUID = Query(None),
    dataset_id: UUID = Query(None),
    element_id: UUID = Query(None),
    role: str = Query(None),
    is_active: bool = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_governance:view")),
):
    assignments, total = await GovernanceService.list_assignments(
        db,
        domain_id=domain_id,
        dataset_id=dataset_id,
        element_id=element_id,
        role=role,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )

    items = [_assignment_to_response(a) for a in assignments]
    total_pages = (total + page_size - 1) // page_size

    return GovernanceAssignmentListResponse(
        items=items, total=total, page=page, page_size=page_size, total_pages=total_pages
    )


@router.put(
    "/assignments/{assignment_id}",
    response_model=GovernanceAssignmentResponse,
    summary="Update a governance role assignment",
)
async def update_assignment(
    assignment_id: UUID,
    data: GovernanceAssignmentUpdate,
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_governance:manage")),
):
    assignment = await GovernanceService.update_assignment(db, assignment_id, data, current_user.id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return _assignment_to_response(assignment)


@router.delete(
    "/assignments/{assignment_id}",
    status_code=204,
    summary="Revoke a governance role assignment",
)
async def revoke_assignment(
    assignment_id: UUID,
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_governance:manage")),
):
    success = await GovernanceService.revoke_assignment(db, assignment_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Assignment not found")


# Governance Policy Endpoints
@router.post(
    "/policies",
    response_model=GovernancePolicyResponse,
    status_code=201,
    summary="Create governance policy",
)
async def create_policy(
    data: GovernancePolicyCreate,
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_governance:manage")),
):
    policy = await GovernanceService.create_policy(db, data, current_user.id)
    policy = await GovernanceService.get_policy(db, policy.id)
    return _policy_to_response(policy)


@router.get(
    "/policies",
    response_model=GovernancePolicyListResponse,
    summary="List governance policies",
)
async def list_policies(
    domain_id: UUID = Query(None),
    dataset_id: UUID = Query(None),
    policy_type: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_governance:view")),
):
    policies, total = await GovernanceService.list_policies(
        db, domain_id=domain_id, dataset_id=dataset_id, policy_type=policy_type, page=page, page_size=page_size
    )

    items = [_policy_to_response(p) for p in policies]
    total_pages = (total + page_size - 1) // page_size

    return GovernancePolicyListResponse(
        items=items, total=total, page=page, page_size=page_size, total_pages=total_pages
    )


@router.get(
    "/policies/{policy_id}",
    response_model=GovernancePolicyResponse,
    summary="Get governance policy",
)
async def get_policy(
    policy_id: UUID,
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_governance:view")),
):
    policy = await GovernanceService.get_policy(db, policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return _policy_to_response(policy)


@router.put(
    "/policies/{policy_id}",
    response_model=GovernancePolicyResponse,
    summary="Update governance policy",
)
async def update_policy(
    policy_id: UUID,
    data: GovernancePolicyUpdate,
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_governance:manage")),
):
    policy = await GovernanceService.update_policy(db, policy_id, data, current_user.id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return _policy_to_response(policy)


@router.delete(
    "/policies/{policy_id}",
    status_code=204,
    summary="Delete governance policy",
)
async def delete_policy(
    policy_id: UUID,
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_governance:manage")),
):
    success = await GovernanceService.delete_policy(db, policy_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Policy not found")
