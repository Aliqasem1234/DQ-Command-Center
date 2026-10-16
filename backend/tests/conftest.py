import pytest
import pytest_asyncio
import asyncio
from typing import AsyncGenerator
from uuid import uuid4
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.core.security import hash_password
from app.models.user import User
from app.models.role import Role, UserRole, Permission, RolePermission
from app.models.department import Department

TEST_DATABASE_URL = "sqlite+aiosqlite://"


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session
        await session.rollback()
        await session.close()


@pytest.fixture(autouse=True)
def expose_auth_tokens(monkeypatch):
    # Tests complete verify/reset flows without SMTP by reading the token
    # from the response, which the app only does when explicitly enabled.
    from app.config import settings
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(settings, "DEV_EXPOSE_AUTH_TOKENS", True)


@pytest_asyncio.fixture(autouse=True)
async def disable_rate_limits():
    app.state.limiter.enabled = False
    yield
    app.state.limiter.enabled = True


@pytest_asyncio.fixture(autouse=True)
async def clean_db(test_engine):
    yield
    async with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


@pytest_asyncio.fixture
async def client(test_session) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield test_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def seed_super_admin(test_session: AsyncSession):
    now = datetime.now(timezone.utc)
    result = await test_session.execute(
        User.__table__.select().where(User.email == "admin@test.com")
    )
    user = result.scalar_one_or_none()
    if not user:
        user = User(
            email="admin@test.com",
            username="superadmin",
            password_hash=hash_password("AdminPass123!"),
            full_name="Super Admin",
            is_active=True,
            is_verified=True,
            is_super_admin=True,
            created_at=now,
            updated_at=now,
        )
        test_session.add(user)
        await test_session.flush()

        # Create Super Admin role
        role = Role(name="Super Admin", description="Full access", is_system=True, created_at=now, updated_at=now)
        test_session.add(role)
        await test_session.flush()

        # Create other system roles
        for rname in ["Admin", "Manager", "Analyst", "User"]:
            r = Role(name=rname, description=f"{rname} role", is_system=True, created_at=now, updated_at=now)
            test_session.add(r)
        await test_session.flush()

        # Seed permissions
        perm_defs = [
            ("View Dashboard", "dashboard:view", "Dashboard"),
            ("Manage Users", "users:manage", "Admin"),
            ("View Audit Logs", "audit:view", "Admin"),
            ("Manage Roles", "roles:manage", "Admin"),
            ("Manage Departments", "departments:manage", "Admin"),
            ("Edit Profile", "profile:edit", "Profile"),
            ("Upload Datasets", "datasets:upload", "Datasets"),
            ("View Datasets", "datasets:view", "Datasets"),
        ]
        for pname, pcode, pmodule in perm_defs:
            p = Permission(name=pname, code=pcode, module=pmodule, created_at=now)
            test_session.add(p)
        await test_session.flush()

        # Assign role to user
        ur = UserRole(user_id=user.id, role_id=role.id)
        test_session.add(ur)
        await test_session.flush()

    return user


@pytest_asyncio.fixture
async def super_admin_token(client: AsyncClient, seed_super_admin):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "AdminPass123!"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def test_department_id(client: AsyncClient, super_admin_token: str) -> str:
    response = await client.post(
        "/api/v1/departments",
        headers={"Authorization": f"Bearer {super_admin_token}"},
        json={"name": "TestDept", "description": "Test Department"},
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest_asyncio.fixture
async def test_user_id(client: AsyncClient, super_admin_token: str) -> str:
    response = await client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {super_admin_token}"},
        json={
            "email": "testuser@test.com",
            "username": "testuser",
            "password": "TestPass123!",
            "full_name": "Test User",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest_asyncio.fixture
async def test_role_id(client: AsyncClient, super_admin_token: str) -> str:
    # Get the Super Admin role id
    response = await client.get(
        "/api/v1/roles",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )
    assert response.status_code == 200
    roles = response.json()["items"]
    for role in roles:
        if role["name"] == "Super Admin":
            return role["id"]
    return ""
