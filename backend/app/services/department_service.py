import logging
from datetime import datetime, timezone
from typing import Optional, Tuple, List
from uuid import UUID
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.department import Department
from app.models.user import User
from app.core.rbac import require_permission
from app.utils.audit_logger import create_audit_log
from app.schemas.department import DepartmentCreate, DepartmentUpdate, DepartmentResponse, DepartmentListResponse

logger = logging.getLogger(__name__)


async def list_departments(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    sort_by: str = "name",
    sort_order: str = "asc",
) -> DepartmentListResponse:
    query = select(Department)
    count_query = select(func.count(Department.id))

    if search:
        search_filter = Department.name.ilike(f"%{search}%")
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    sort_column = getattr(Department, sort_by, Department.name)
    if sort_order == "desc":
        sort_column = sort_column.desc()
    query = query.order_by(sort_column)

    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    departments = result.scalars().all()

    items = []
    for dept in departments:
        user_count_result = await db.execute(
            select(func.count(User.id)).where(User.department_id == dept.id)
        )
        user_count = user_count_result.scalar() or 0
        items.append(_department_to_response(dept, user_count))

    return DepartmentListResponse(
        items=items, total=total, page=page, page_size=page_size
    )


async def get_department(db: AsyncSession, department_id: UUID) -> Optional[DepartmentResponse]:
    result = await db.execute(select(Department).where(Department.id == department_id))
    dept = result.scalar_one_or_none()
    if dept is None:
        return None
    user_count_result = await db.execute(
        select(func.count(User.id)).where(User.department_id == dept.id)
    )
    user_count = user_count_result.scalar() or 0
    return _department_to_response(dept, user_count)


async def create_department(
    db: AsyncSession,
    data: DepartmentCreate,
    actor_user_id: Optional[UUID] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> DepartmentResponse:
    now = datetime.now(timezone.utc)
    existing = await db.execute(select(Department).where(Department.name == data.name))
    if existing.scalar_one_or_none():
        raise ValueError("Department with this name already exists")

    dept = Department(
        name=data.name,
        description=data.description,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db.add(dept)
    await db.flush()

    await create_audit_log(
        db, actor_user_id, "CREATE", "department", str(dept.id),
        new_values={"name": data.name, "description": data.description},
        ip_address=ip_address, user_agent=user_agent,
    )

    await db.commit()
    return _department_to_response(dept, 0)


async def update_department(
    db: AsyncSession,
    department_id: UUID,
    data: DepartmentUpdate,
    actor_user_id: Optional[UUID] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Optional[DepartmentResponse]:
    result = await db.execute(select(Department).where(Department.id == department_id))
    dept = result.scalar_one_or_none()
    if dept is None:
        return None

    old_values = {"name": dept.name, "description": dept.description, "is_active": dept.is_active}

    if data.name is not None:
        existing = await db.execute(
            select(Department).where(Department.name == data.name, Department.id != department_id)
        )
        if existing.scalar_one_or_none():
            raise ValueError("Department with this name already exists")
        dept.name = data.name
    if data.description is not None:
        dept.description = data.description
    if data.is_active is not None:
        dept.is_active = data.is_active
    dept.updated_at = datetime.now(timezone.utc)

    await db.flush()
    await create_audit_log(
        db, actor_user_id, "UPDATE", "department", str(dept.id),
        old_values=old_values,
        new_values={"name": dept.name, "description": dept.description, "is_active": dept.is_active},
        ip_address=ip_address, user_agent=user_agent,
    )
    await db.commit()

    user_count_result = await db.execute(
        select(func.count(User.id)).where(User.department_id == dept.id)
    )
    user_count = user_count_result.scalar() or 0
    return _department_to_response(dept, user_count)


async def delete_department(
    db: AsyncSession,
    department_id: UUID,
    actor_user_id: Optional[UUID] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> bool:
    result = await db.execute(select(Department).where(Department.id == department_id))
    dept = result.scalar_one_or_none()
    if dept is None:
        return False

    await db.execute(
        select(User).where(User.department_id == department_id)
    )
    users_result = await db.execute(
        select(User).where(User.department_id == department_id)
    )
    users = users_result.scalars().all()
    for user in users:
        user.department_id = None

    await create_audit_log(
        db, actor_user_id, "DELETE", "department", str(dept.id),
        old_values={"name": dept.name},
        ip_address=ip_address, user_agent=user_agent,
    )

    await db.delete(dept)
    await db.commit()
    return True


async def list_all_departments_simple(db: AsyncSession) -> List[dict]:
    result = await db.execute(
        select(Department).where(Department.is_active == True).order_by(Department.name)
    )
    departments = result.scalars().all()
    return [{"id": str(d.id), "name": d.name} for d in departments]


def _department_to_response(dept: Department, user_count: int = 0) -> DepartmentResponse:
    return DepartmentResponse(
        id=str(dept.id),
        name=dept.name,
        description=dept.description,
        is_active=dept.is_active,
        created_at=dept.created_at,
        updated_at=dept.updated_at,
        user_count=user_count,
    )
