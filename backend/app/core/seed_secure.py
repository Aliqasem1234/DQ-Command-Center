"""
Secure seed/initialization module for admin provisioning.

DO NOT log credentials or expose them in any form.
Admin setup should only be visible in secure provisioning flow.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from sqlalchemy import select
from app.database import async_session_factory
from app.models.user import User
from app.models.role import Role, UserRole, Permission, RolePermission
from app.models.department import Department
from app.models.data_hierarchy import DataDomain
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
    {"name": "View Data Quality", "code": "data_quality:view", "module": "Data Quality"},
    {"name": "Manage Data Quality", "code": "data_quality:manage", "module": "Data Quality"},
    {"name": "View Data Governance", "code": "data_governance:view", "module": "Data Governance"},
    {"name": "Manage Data Governance", "code": "data_governance:manage", "module": "Data Governance"},
    {"name": "View Datasets", "code": "datasets:view", "module": "Datasets"},
    {"name": "Manage Datasets", "code": "datasets:manage", "module": "Datasets"},
    {"name": "View Analytics", "code": "analytics:view", "module": "Analytics"},
    {"name": "View Reports", "code": "reports:view", "module": "Reports"},
    {"name": "Create Reports", "code": "reports:create", "module": "Reports"},
    {"name": "Export Reports", "code": "reports:export", "module": "Reports"},
    {"name": "Manage Users", "code": "users:manage", "module": "Admin"},
    {"name": "View Audit Logs", "code": "audit:view", "module": "Admin"},
    {"name": "Manage Roles", "code": "roles:manage", "module": "Admin"},
    {"name": "Manage Departments", "code": "departments:manage", "module": "Admin"},
    {"name": "Edit Profile", "code": "profile:edit", "module": "Profile"},
]

DEMO_DEPARTMENTS = [
    {"name": "Finance", "description": "Financial data management"},
    {"name": "Sales", "description": "Sales and customer data"},
    {"name": "Operations", "description": "Operational data"},
    {"name": "Technology", "description": "Technology and infrastructure"},
]


async def initialize_system_data():
    """
    Initialize system data (roles, permissions, departments).
    Safe to run multiple times - will only create missing items.
    """
    async with async_session_factory() as db:
        try:
            now = datetime.now(timezone.utc)

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
                    logger.info(f"Created role: {role_data['name']}")

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
                    logger.info(f"Created permission: {perm_data['code']}")

            # Create departments
            for dept_data in DEMO_DEPARTMENTS:
                result = await db.execute(
                    select(Department).where(Department.name == dept_data["name"])
                )
                existing_dept = result.scalar_one_or_none()
                if not existing_dept:
                    dept = Department(
                        name=dept_data["name"],
                        description=dept_data["description"],
                        created_at=now,
                        updated_at=now,
                    )
                    db.add(dept)
                    await db.flush()
                    logger.info(f"Created department: {dept_data['name']}")

            # Assign permissions to Super Admin role
            super_admin_role = role_map.get("Super Admin")
            if super_admin_role:
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
            logger.info("System data initialized successfully")

        except Exception as e:
            await db.rollback()
            logger.error(f"Error initializing system data: {e}")
            raise


async def create_super_admin(email: str, password: str, full_name: str = "Administrator"):
    """
    Create a super admin user with the given credentials.
    This should ONLY be called during secure initialization.
    Credentials must never be logged or exposed.
    """
    async with async_session_factory() as db:
        try:
            now = datetime.now(timezone.utc)

            # Check if super admin already exists
            result = await db.execute(select(User).where(User.email == email))
            existing = result.scalar_one_or_none()
            if existing:
                logger.warning(f"User with email {email} already exists")
                return False

            # Create super admin user
            admin_user = User(
                email=email,
                username=email.split("@")[0],
                password_hash=hash_password(password),
                full_name=full_name,
                is_active=True,
                is_verified=True,
                is_super_admin=True,
                department="Administration",
                created_at=now,
                updated_at=now,
            )
            db.add(admin_user)
            await db.flush()

            # Assign Super Admin role
            result = await db.execute(select(Role).where(Role.name == "Super Admin"))
            super_admin_role = result.scalar_one_or_none()
            if super_admin_role:
                user_role = UserRole(
                    user_id=admin_user.id,
                    role_id=super_admin_role.id,
                )
                db.add(user_role)

            await db.commit()
            logger.info(f"Super admin user created successfully (not logging credentials)")
            return True

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating super admin: {e}")
            raise


async def seed_demo_data():
    """
    Seed realistic demo data for testing/showcase.
    This creates sample domains, datasets, quality rules, and issues.
    """
    async with async_session_factory() as db:
        try:
            # Import here to avoid circular imports
            from app.services.seed_data_service import SeedDataService
            
            # Get or create demo admin for demo data
            result = await db.execute(
                select(User).where(User.is_super_admin == True).limit(1)
            )
            admin = result.scalar_one_or_none()
            
            if admin:
                # Create demo users (idempotent - skip any that already exist)
                now = datetime.now(timezone.utc)
                demo_users = []
                for i, name in enumerate(["Alice Chen", "Bob Johnson", "Carol Davis"]):
                    email = f"demo{i+1}@dqcommandcenter.io"
                    existing = await db.execute(select(User).where(User.email == email))
                    existing_user = existing.scalar_one_or_none()
                    if existing_user:
                        demo_users.append(existing_user)
                        continue

                    user = User(
                        email=email,
                        username=f"demo{i+1}",
                        password_hash=hash_password("[REDACTED-DEV-CREDENTIAL]"),
                        full_name=name,
                        is_active=True,
                        is_verified=True,
                        department="Demo",
                        created_at=now,
                        updated_at=now,
                    )
                    db.add(user)
                    demo_users.append(user)

                await db.commit()

                # Get departments
                result = await db.execute(select(Department).limit(4))
                demo_departments = result.scalars().all()

                # Seed quality data (idempotent - skip if already populated)
                existing_domain = await db.execute(
                    select(DataDomain).where(DataDomain.name == "Finance")
                )
                if existing_domain.scalar_one_or_none() is None:
                    await SeedDataService.populate_demo_data(
                        db=db,
                        admin_user=admin,
                        demo_users=demo_users,
                        demo_departments=demo_departments,
                    )
                    await db.commit()
                    logger.info("Demo data seeded successfully")
                else:
                    logger.info("Demo data already present, skipping")

        except Exception as e:
            await db.rollback()
            logger.error(f"Error seeding demo data: {e}")
            # Don't raise - demo data is optional


async def secure_initialize():
    """
    Securely initialize the system.
    
    1. Initialize system data (roles, permissions, departments)
    2. Create super admin if configured via environment
    3. Seed demo data if in development mode
    """
    logger.info("Starting secure system initialization")
    
    # Always initialize system data
    await initialize_system_data()
    
    # Create super admin only if credentials provided via environment
    admin_email = os.getenv("INIT_ADMIN_EMAIL")
    admin_password = os.getenv("INIT_ADMIN_PASSWORD")
    admin_name = os.getenv("INIT_ADMIN_NAME", "Administrator")
    
    if admin_email and admin_password:
        created = await create_super_admin(admin_email, admin_password, admin_name)
        if created:
            logger.info(
                "Super admin created. "
                "Login with provided credentials and change password immediately."
            )
        # Do NOT log credentials
    else:
        logger.warning(
            "No admin credentials provided via INIT_ADMIN_EMAIL/INIT_ADMIN_PASSWORD. "
            "Register first user through UI or provide credentials for automatic setup."
        )
    
    # Seed demo data if in development
    if settings.ENVIRONMENT == "development":
        await seed_demo_data()
    
    logger.info("System initialization complete")


if __name__ == "__main__":
    asyncio.run(secure_initialize())
