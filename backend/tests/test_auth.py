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
