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
from app.core.dataset_access import (
    get_accessible_dataset, get_visible_domain, has_global_dataset_access,
    accessible_dataset_ids, visible_domains_clause, owned_dataset_ids,
)
from app.models.data_hierarchy import Dataset, DataElement, DataDomain, DataGovernance, GovernancePolicy
from sqlalchemy import select, func, or_, and_, true

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/governance", tags=["Data Governance"])


@router.get(
    "/assignable-users",
    summary="Look up one active user by exact email address, to share data with them",
)
async def find_assignable_user(
    email: str = Query(..., min_length=3, max_length=255),
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("data_governance:manage")),
) -> list[dict]:
    # Anyone can register, so listing every account would hand any user the
    # full list of registered people and their emails. Sharing works by
    # exact email instead: you can only find someone whose address you
    # already know.
    result = await db.execute(
        select(User.id, User.full_name, User.email)
        .where(User.is_active.is_(True), func.lower(User.email) == email.strip().lower())
    )
    return [{"id": str(r.id), "full_name": r.full_name, "email": r.email} for r in result.all()]


def _managed_assignments_clause(user: User):
    """Assignments on data the user controls: their datasets (or elements
    of them) and their own domains."""
    if has_global_dataset_access(user):
        return true()
    # Ownership, not access: someone a dataset was shared with must not be
    # able to revoke the owner's sharing or re-share it onwards.
    owned = owned_dataset_ids(user)
    return or_(
        DataGovernance.dataset_id.in_(owned),
        DataGovernance.domain_id.in_(select(DataDomain.id).where(visible_domains_clause(user))),
        DataGovernance.element_id.in_(select(DataElement.id).where(DataElement.dataset_id.in_(owned))),
    )


def _visible_assignments_clause(user: User):
    # ...plus assignments that name the user, so people can see what has
    # been shared with them.
    if has_global_dataset_access(user):
        return true()
    return or_(_managed_assignments_clause(user), DataGovernance.user_id == user.id)


def _visible_policies_clause(user: User):
    if has_global_dataset_access(user):
        return true()
    return or_(
        GovernancePolicy.dataset_id.in_(accessible_dataset_ids(user)),
        GovernancePolicy.domain_id.in_(select(DataDomain.id).where(visible_domains_clause(user))),
        and_(GovernancePolicy.dataset_id.is_(None), GovernancePolicy.domain_id.is_(None),
             GovernancePolicy.created_by_id == user.id),
    )


async def _ensure_target_owned(db: AsyncSession, data, user: User) -> None:
    """Only the owner of a dataset (or of the element's dataset) may share it."""
    dataset_id = getattr(data, "dataset_id", None)
    element_id = getattr(data, "element_id", None)
    if dataset_id is None and element_id is not None:
        dataset_id = (await db.execute(select(DataElement.dataset_id).where(DataElement.id == element_id))).scalar()
    if dataset_id is None:
        return
    owned = await db.execute(select(Dataset.id).where(Dataset.id == dataset_id, Dataset.id.in_(owned_dataset_ids(user))))
    if owned.first() is None:
        raise HTTPException(status_code=403, detail="Only the dataset owner can share it")


async def _ensure_assignment_managed(db: AsyncSession, assignment_id: UUID, user: User) -> None:
    found = await db.execute(
        select(DataGovernance.id).where(DataGovernance.id == assignment_id, _managed_assignments_clause(user))
    )
    if found.first() is None:
        raise HTTPException(status_code=404, detail="Assignment not found")


async def _ensure_policy_visible(db: AsyncSession, policy_id: UUID, user: User) -> None:
    found = await db.execute(
        select(GovernancePolicy.id).where(GovernancePolicy.id == policy_id, _visible_policies_clause(user))
    )
    if found.first() is None:
        raise HTTPException(status_code=404, detail="Policy not found")


async def _ensure_target_dataset_access(db: AsyncSession, data, user: User) -> None:
    # Assigning someone as owner/steward of a dataset grants them access to
    # it, so only those who can already access the dataset may do so -
    # otherwise data_governance:manage would let a user claim any dataset.
    dataset_id = getattr(data, "dataset_id", None)
    element_id = getattr(data, "element_id", None)
    if dataset_id is None and element_id is not None:
        element = (await db.execute(select(DataElement).where(DataElement.id == element_id))).scalar_one_or_none()
        if element is None:
            raise HTTPException(status_code=404, detail="Element not found")
        dataset_id = element.dataset_id
    if dataset_id is not None:
        await get_accessible_dataset(db, dataset_id, user)
    domain_id = getattr(data, "domain_id", None)
    if domain_id is not None:
        await get_visible_domain(db, domain_id, user)


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
    await _ensure_target_dataset_access(db, data, current_user)
    await _ensure_target_owned(db, data, current_user)
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
        scope=_visible_assignments_clause(current_user),
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
    await _ensure_assignment_managed(db, assignment_id, current_user)
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
    await _ensure_assignment_managed(db, assignment_id, current_user)
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
    await _ensure_target_dataset_access(db, data, current_user)
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
        db, domain_id=domain_id, dataset_id=dataset_id, policy_type=policy_type, page=page, page_size=page_size,
        scope=_visible_policies_clause(current_user),
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
    await _ensure_policy_visible(db, policy_id, current_user)
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
    await _ensure_policy_visible(db, policy_id, current_user)
    if getattr(data, "dataset_id", None) is not None or getattr(data, "domain_id", None) is not None:
        await _ensure_target_dataset_access(db, data, current_user)
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
    await _ensure_policy_visible(db, policy_id, current_user)
    success = await GovernanceService.delete_policy(db, policy_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Policy not found")
