import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy import select
from app.database import async_session_factory
from app.models.user import User
from app.models.role import Role, UserRole, Permission, RolePermission
from app.core.security import hash_password
from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_ROLES = [
    {"name": "Super Admin", "description": "Full system access"},
    {"name": "Admin", "description": "Administrative access"},
    {"name": "Manager", "description": "Management access"},
    {"name": "Analyst", "description": "Data analysis access"},
    {"name": "User", "description": "Basic user access"},
]

SYSTEM_PERMISSIONS = [
    {"name": "View Dashboard", "code": "dashboard:view", "module": "Dashboard"},
    {"name": "Upload Datasets", "code": "datasets:upload", "module": "Datasets"},
    {"name": "View Datasets", "code": "datasets:view", "module": "Datasets"},
    {"name": "Delete Datasets", "code": "datasets:delete", "module": "Datasets"},
    {"name": "Validate Datasets", "code": "datasets:validate", "module": "Datasets"},
    {"name": "Export Datasets", "code": "datasets:export", "module": "Datasets"},
    {"name": "View Analytics", "code": "analytics:view", "module": "Analytics"},
    {"name": "View Reports", "code": "reports:view", "module": "Reports"},
    {"name": "Create Reports", "code": "reports:create", "module": "Reports"},
    {"name": "Export Reports", "code": "reports:export", "module": "Reports"},
    {"name": "Schedule Reports", "code": "reports:schedule", "module": "Reports"},
    {"name": "Manage Users", "code": "users:manage", "module": "Admin"},
    {"name": "View Audit Logs", "code": "audit:view", "module": "Admin"},
    {"name": "Manage Roles", "code": "roles:manage", "module": "Admin"},
    {"name": "Manage Departments", "code": "departments:manage", "module": "Admin"},
    {"name": "Edit Profile", "code": "profile:edit", "module": "Profile"},
    {"name": "View Data Quality", "code": "data_quality:view", "module": "Data Quality"},
    {"name": "Manage Data Quality", "code": "data_quality:manage", "module": "Data Quality"},
    {"name": "View Data Governance", "code": "data_governance:view", "module": "Data Governance"},
    {"name": "Manage Data Governance", "code": "data_governance:manage", "module": "Data Governance"},
]


async def seed_super_admin():
    async with async_session_factory() as db:
        try:
            now = datetime.now(timezone.utc)

            # Check if super admin exists
            result = await db.execute(
                select(User).where(User.email == settings.SUPER_ADMIN_EMAIL)
            )
            existing = result.scalar_one_or_none()
            if existing:
                logger.info("Super admin already exists, skipping seed.")
                return

            # Create super admin
            super_admin = User(
                email=settings.SUPER_ADMIN_EMAIL,
                username="superadmin",
                password_hash=hash_password(settings.SUPER_ADMIN_PASSWORD),
                full_name=settings.SUPER_ADMIN_NAME,
                is_active=True,
                is_verified=True,
                is_super_admin=True,
                department="Administration",
                created_at=now,
                updated_at=now,
            )
            db.add(super_admin)
            await db.flush()

            # Create system roles
            role_map = {}
            for role_data in SYSTEM_ROLES:
                result = await db.execute(
                    select(Role).where(Role.name == role_data["name"])
                )
                existing_role = result.scalar_one_or_none()
                if existing_role:
                    role_map[role_data["name"]] = existing_role
                else:
                    role = Role(
                        name=role_data["name"],
                        description=role_data["description"],
                        is_system=True,
                        created_at=now,
                        updated_at=now,
                    )
                    db.add(role)
                    await db.flush()
                    role_map[role_data["name"]] = role

            # Create permissions
            perm_map = {}
            for perm_data in SYSTEM_PERMISSIONS:
                result = await db.execute(
                    select(Permission).where(Permission.code == perm_data["code"])
                )
                existing_perm = result.scalar_one_or_none()
                if existing_perm:
                    perm_map[perm_data["code"]] = existing_perm
                else:
                    perm = Permission(
                        name=perm_data["name"],
                        code=perm_data["code"],
                        module=perm_data["module"],
                        created_at=now,
                    )
                    db.add(perm)
                    await db.flush()
                    perm_map[perm_data["code"]] = perm

            # Assign Super Admin role to super admin user
            super_admin_role = role_map.get("Super Admin")
            if super_admin_role:
                user_role = UserRole(
                    user_id=super_admin.id,
                    role_id=super_admin_role.id,
                )
                db.add(user_role)

                # Assign all permissions to Super Admin role
                for perm in perm_map.values():
                    result = await db.execute(
                        select(RolePermission).where(
                            RolePermission.role_id == super_admin_role.id,
                            RolePermission.permission_id == perm.id,
                        )
                    )
                    existing_rp = result.scalar_one_or_none()
                    if not existing_rp:
                        rp = RolePermission(
                            role_id=super_admin_role.id,
                            permission_id=perm.id,
                        )
                        db.add(rp)

            await db.commit()
            logger.info("Super admin and system roles seeded successfully.")

        except Exception as e:
            await db.rollback()
            logger.error(f"Error seeding data: {e}")
            raise
