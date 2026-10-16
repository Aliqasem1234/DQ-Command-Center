"""
Row-level access to datasets.

Permissions (datasets:view / datasets:manage) say what kind of action a user
may take; this module says *which* datasets they may take it on. Every
endpoint that reads or changes a specific dataset - its metadata, elements,
versions, file rows or downloads - must go through `get_accessible_dataset`,
and every listing must apply `accessible_datasets_clause`, so the rule lives
in one place instead of being re-implemented (or forgotten) per route.

A user can access a dataset when they are a super admin, its data owner, its
data steward, or hold an active governance assignment on it.
"""
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import and_, exists, or_, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.data_hierarchy import Dataset, DataDomain, DataGovernance
from app.models.data_quality_rule import DataQualityRule
from app.models.user import User
from app.dependencies import get_current_user_from_token

SUPER_ADMIN_ROLE = "Super Admin"


def has_global_dataset_access(user: User) -> bool:
    if user.is_super_admin:
        return True
    return any(ur.role is not None and ur.role.name == SUPER_ADMIN_ROLE for ur in user.roles)


def accessible_datasets_clause(user: User):
    """SQL filter selecting the datasets `user` may see."""
    if has_global_dataset_access(user):
        return true()
    governed = exists().where(
        DataGovernance.dataset_id == Dataset.id,
        DataGovernance.user_id == user.id,
        DataGovernance.is_active.is_(True),
    )
    return or_(Dataset.data_owner_id == user.id, Dataset.data_steward_id == user.id, governed)


def accessible_dataset_ids(user: User):
    """Subquery of the IDs of datasets `user` may see."""
    return select(Dataset.id).where(accessible_datasets_clause(user))


def scoped_to_accessible_datasets(column, user: User, allow_unscoped: bool = False):
    """Filter for rows tied to a dataset via `column` (e.g. a rule's or an
    issue's dataset_id). With allow_unscoped, rows not tied to any dataset
    (organisation-wide rules) stay visible."""
    if has_global_dataset_access(user):
        return true()
    in_scope = column.in_(accessible_dataset_ids(user))
    return or_(column.is_(None), in_scope) if allow_unscoped else in_scope


def owned_dataset_ids(user: User):
    """IDs of datasets `user` owns (all of them for super admins). Owning -
    not merely having access - is what lets someone share or delete."""
    if has_global_dataset_access(user):
        return select(Dataset.id)
    return select(Dataset.id).where(Dataset.data_owner_id == user.id)


def visible_rules_clause(user: User):
    """Rules a user may see: those on datasets they can access, plus rules
    not tied to any dataset that they created or own. Everything derived
    from rules (results, metrics, trends, reports) is scoped through this."""
    if has_global_dataset_access(user):
        return true()
    return or_(
        DataQualityRule.dataset_id.in_(accessible_dataset_ids(user)),
        and_(
            DataQualityRule.dataset_id.is_(None),
            or_(DataQualityRule.created_by_id == user.id, DataQualityRule.owner_id == user.id),
        ),
    )


def visible_rule_ids(user: User):
    return select(DataQualityRule.id).where(visible_rules_clause(user))


def visible_domains_clause(user: User):
    """Domains are each user's own way of grouping their datasets."""
    if has_global_dataset_access(user):
        return true()
    return DataDomain.owner_id == user.id


def can_delete_dataset(dataset: Dataset, user: User) -> bool:
    # Stewards and governance assignees may work on a dataset; only its
    # owner (or a super admin) may delete it.
    return has_global_dataset_access(user) or dataset.data_owner_id == user.id


async def get_visible_domain(db: AsyncSession, domain_id: UUID, user: User) -> DataDomain:
    result = await db.execute(select(DataDomain).where(DataDomain.id == domain_id, visible_domains_clause(user)))
    domain = result.scalar_one_or_none()
    if domain is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found")
    return domain


async def require_global_data_access(current_user: User = Depends(get_current_user_from_token)) -> User:
    """For platform-wide aggregates across every user's data."""
    if not has_global_dataset_access(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return current_user


async def can_access_dataset(db: AsyncSession, dataset_id: UUID, user: User) -> bool:
    result = await db.execute(
        select(Dataset.id).where(Dataset.id == dataset_id, accessible_datasets_clause(user))
    )
    return result.first() is not None


async def get_accessible_dataset(db: AsyncSession, dataset_id: UUID, user: User) -> Dataset:
    """Return the dataset, or 404 whether it is missing or merely not the
    caller's - answering 403 would confirm to a non-owner that the ID exists."""
    result = await db.execute(
        select(Dataset).where(Dataset.id == dataset_id, accessible_datasets_clause(user))
    )
    dataset = result.scalar_one_or_none()
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    return dataset
