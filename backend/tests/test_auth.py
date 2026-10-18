import pytest
from httpx import AsyncClient
from app.core.security import hash_password, verify_password, create_access_token, decode_token


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app"] == "DQ Command Center"


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "username": "testuser",
            "password": "TestPass123!",
            "full_name": "Test User",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert "Registration successful" in data["message"]
    assert "Verification token" in data["detail"]


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    # Register first time
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "duplicate@example.com",
            "username": "duplicate1",
            "password": "TestPass123!",
            "full_name": "Test User",
        },
    )
    # Register second time with same email
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "duplicate@example.com",
            "username": "duplicate2",
            "password": "TestPass123!",
            "full_name": "Test User",
        },
    )
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_and_verify_email(client: AsyncClient):
    # Register
    reg_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "verify@example.com",
            "username": "verifyuser",
            "password": "TestPass123!",
            "full_name": "Verify User",
        },
    )
    assert reg_response.status_code == 201
    token = reg_response.json()["detail"].replace("Verification token: ", "")

    # Verify email
    response = await client.post(
        "/api/v1/auth/verify-email",
        json={"token": token},
    )
    assert response.status_code == 200
    assert "Email verified successfully" in response.json()["message"]


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    # Register
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "login@example.com",
            "username": "loginuser",
            "password": "TestPass123!",
            "full_name": "Login User",
        },
    )
    # Login
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "login@example.com",
            "password": "TestPass123!",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "login@example.com"


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "WrongPass123!",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient):
    # Register and login
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "refresh@example.com",
            "username": "refreshuser",
            "password": "TestPass123!",
            "full_name": "Refresh User",
        },
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "refresh@example.com",
            "password": "TestPass123!",
        },
    )
    refresh_token = login_response.json()["refresh_token"]

    # Refresh token
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_logout(client: AsyncClient):
    # Register and login
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "logout@example.com",
            "username": "logoutuser",
            "password": "TestPass123!",
            "full_name": "Logout User",
        },
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "logout@example.com",
            "password": "TestPass123!",
        },
    )
    refresh_token = login_response.json()["refresh_token"]

    # Logout
    response = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    assert "Logged out" in response.json()["message"]

    # Try to use old refresh token (should fail)
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_forgot_password(client: AsyncClient):
    # Register
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "forgot@example.com",
            "username": "forgotuser",
            "password": "TestPass123!",
            "full_name": "Forgot User",
        },
    )
    # Forgot password
    response = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "forgot@example.com"},
    )
    assert response.status_code == 200
    assert "password reset link" in response.json()["message"]


@pytest.mark.asyncio
async def test_reset_password(client: AsyncClient):
    # Register
    reg_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "reset@example.com",
            "username": "resetuser",
            "password": "TestPass123!",
            "full_name": "Reset User",
        },
    )
    assert reg_response.status_code == 201

    # Login
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "reset@example.com",
            "password": "TestPass123!",
        },
    )
    assert login_response.status_code == 200
    refresh_token = login_response.json()["refresh_token"]

    # Need to get reset token from the forgot-password flow
    # In dev mode, we can use the verification token pattern
    forgot_response = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "reset@example.com"},
    )
    assert forgot_response.status_code == 200

    # For test purposes, we need to generate a reset token manually via the DB
    # This test is a placeholder - full password reset requires the token
    # which is generated server-side and emailed

    # Verify we can still use the old password
    await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
    )


@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient):
    # Register and login
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "me@example.com",
            "username": "meuser",
            "password": "TestPass123!",
            "full_name": "Me User",
        },
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "me@example.com",
            "password": "TestPass123!",
        },
    )
    access_token = login_response.json()["access_token"]

    # Get current user
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@example.com"
    assert data["username"] == "meuser"
    assert data["full_name"] == "Me User"


@pytest.mark.asyncio
async def test_password_hashing():
    password = "TestPassword123!"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("WrongPassword", hashed)


@pytest.mark.asyncio
async def test_jwt_token():
    from uuid import uuid4
    user_id = uuid4()
    token = create_access_token(user_id)
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == str(user_id)
    assert payload["type"] == "access"


# ---------- registration regressions (QA register: QA-003) ----------

@pytest.mark.asyncio
async def test_register_without_username_derives_unique_one(client: AsyncClient):
    """The form doesn't collect a username, so short and shared email
    local-parts must not fail on a field the user never saw."""
    for email in ["ab@example.com", "ab@other.example", "anna@example.com", "anna@other.example"]:
        r = await client.post("/api/v1/auth/register", json={
            "email": email, "password": "ValidPass123!", "full_name": "Test",
        })
        assert r.status_code == 201, f"{email}: {r.text}"


@pytest.mark.asyncio
async def test_register_validation_errors_keep_fastapi_contract(client: AsyncClient):
    """The frontend maps these into readable messages; they must stay a
    list of {loc, msg, type} objects (rendering one raw crashed React)."""
    r = await client.post("/api/v1/auth/register", json={
        "email": "not-an-email", "password": "short", "full_name": "   ",
    })
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert isinstance(detail, list)
    fields = {e["loc"][-1] for e in detail}
    assert {"email", "password", "full_name"} <= fields
    assert all(isinstance(e["msg"], str) and isinstance(e["type"], str) for e in detail)


@pytest.mark.asyncio
async def test_register_duplicate_email_is_readable_string(client: AsyncClient):
    body = {"email": "dupe@example.com", "password": "ValidPass123!", "full_name": "Dupe"}
    assert (await client.post("/api/v1/auth/register", json=body)).status_code == 201
    r = await client.post("/api/v1/auth/register", json=body)
    assert r.status_code == 400
    assert r.json() == {"detail": "Email already registered"}


@pytest.mark.asyncio
async def test_login_nonexistent_and_wrong_password_are_indistinguishable(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "email": "real@example.com", "password": "ValidPass123!", "full_name": "Real",
    })
    wrong = await client.post("/api/v1/auth/login", json={"email": "real@example.com", "password": "WrongPass123!"})
    missing = await client.post("/api/v1/auth/login", json={"email": "ghost@example.com", "password": "WrongPass123!"})
    assert wrong.status_code == missing.status_code == 401
    assert wrong.json() == missing.json()


@pytest.mark.asyncio
async def test_password_reset_ends_existing_sessions(client: AsyncClient):
    """Resetting a password must revoke sessions opened with the old one."""
    email = "reset.sessions@example.com"
    await client.post("/api/v1/auth/register", json={"email": email, "password": "ValidPass123!", "full_name": "R"})
    old_refresh = (await client.post("/api/v1/auth/login", json={"email": email, "password": "ValidPass123!"})).json()["refresh_token"]

    forgot = await client.post("/api/v1/auth/forgot-password", json={"email": email})
    token = forgot.json()["detail"].split(": ", 1)[1]
    assert (await client.post("/api/v1/auth/reset-password", json={"token": token, "password": "NewValid456!"})).status_code == 200

    assert (await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})).status_code == 401
    assert (await client.post("/api/v1/auth/login", json={"email": email, "password": "ValidPass123!"})).status_code == 401
    assert (await client.post("/api/v1/auth/login", json={"email": email, "password": "NewValid456!"})).status_code == 200
    # The reset link is single-use.
    assert (await client.post("/api/v1/auth/reset-password", json={"token": token, "password": "Another789!"})).status_code == 400


@pytest.mark.asyncio
async def test_reset_and_verification_tokens_are_not_echoed_by_default(client: AsyncClient, monkeypatch):
    """Echoing the reset token lets any caller reset any account; it must
    require the explicit local-only flag, not merely ENVIRONMENT=development."""
    from app.config import settings
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(settings, "DEV_EXPOSE_AUTH_TOKENS", False)
    r = await client.post("/api/v1/auth/register", json={"email": "victim@example.com", "password": "ValidPass123!", "full_name": "V"})
    assert r.status_code == 201 and r.json()["detail"] is None
    r = await client.post("/api/v1/auth/forgot-password", json={"email": "victim@example.com"})
    assert r.status_code == 200 and r.json()["detail"] is None


@pytest.mark.asyncio
async def test_health_reports_unhealthy_when_database_is_unreachable(client: AsyncClient):
    """Container health checks rely on /health; it must fail when the DB does."""
    from app.main import app
    from app.database import get_db

    class BrokenSession:
        async def execute(self, *args, **kwargs):
            raise ConnectionRefusedError("database down")

    async def broken_db():
        yield BrokenSession()

    app.dependency_overrides[get_db] = broken_db
    response = await client.get("/health")
    assert response.status_code == 503
    assert response.json()["status"] == "unhealthy"
    assert response.json()["database"] == "unreachable"


@pytest.mark.asyncio
async def test_demo_accounts_cannot_sign_in_in_production(client: AsyncClient, test_session, monkeypatch):
    # A development database reused in production must not expose the seeded
    # demo accounts, whatever their password is.
    import secrets
    from datetime import datetime, timezone
    from app.config import settings
    from app.models.user import User

    password = secrets.token_urlsafe(16)  # generated per run, never a fixed value
    now = datetime.now(timezone.utc)
    test_session.add(User(
        email="demo1@dqcommandcenter.io", username="demo1", password_hash=hash_password(password),
        full_name="Demo", is_active=True, is_verified=True, created_at=now, updated_at=now,
    ))
    await test_session.flush()
    body = {"email": "demo1@dqcommandcenter.io", "password": password}

    assert (await client.post("/api/v1/auth/login", json=body)).status_code == 200

    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    response = await client.post("/api/v1/auth/login", json=body)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"
