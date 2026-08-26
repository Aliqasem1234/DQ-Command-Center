import pytest
from httpx import AsyncClient
from uuid import uuid4


@pytest.mark.asyncio
async def test_list_departments_empty(client: AsyncClient, super_admin_token: str):
    response = await client.get(
        "/api/v1/departments",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_create_department(client: AsyncClient, super_admin_token: str):
    response = await client.post(
        "/api/v1/departments",
        headers={"Authorization": f"Bearer {super_admin_token}"},
        json={"name": "Engineering", "description": "Engineering Department"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Engineering"
    assert data["is_active"] == True
    assert "id" in data

    # Duplicate name
    response = await client.post(
        "/api/v1/departments",
        headers={"Authorization": f"Bearer {super_admin_token}"},
        json={"name": "Engineering"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_department(client: AsyncClient, super_admin_token: str, test_department_id: str):
    response = await client.get(
        f"/api/v1/departments/{test_department_id}",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_department_id

    # Not found
    response = await client.get(
        f"/api/v1/departments/{uuid4()}",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_department(client: AsyncClient, super_admin_token: str, test_department_id: str):
    response = await client.put(
        f"/api/v1/departments/{test_department_id}",
        headers={"Authorization": f"Bearer {super_admin_token}"},
        json={"description": "Updated description"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["description"] == "Updated description"


@pytest.mark.asyncio
async def test_list_all_departments(client: AsyncClient, super_admin_token: str):
    response = await client.get(
        "/api/v1/departments/all",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_list_users(client: AsyncClient, super_admin_token: str):
    response = await client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_get_user(client: AsyncClient, super_admin_token: str, test_user_id: str):
    response = await client.get(
        f"/api/v1/users/{test_user_id}",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_user_id


@pytest.mark.asyncio
async def test_admin_create_user(client: AsyncClient, super_admin_token: str, test_department_id: str):
    response = await client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {super_admin_token}"},
        json={
            "email": "newuser@test.com",
            "username": "newuser",
            "password": "TestPass123!",
            "full_name": "New User",
            "department_id": test_department_id,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@test.com"
    assert data["department_id"] == test_department_id

    # Duplicate email
    response = await client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {super_admin_token}"},
        json={
            "email": "newuser@test.com",
            "username": "newuser2",
            "password": "TestPass123!",
            "full_name": "New User 2",
        },
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_update_user(client: AsyncClient, super_admin_token: str, test_user_id: str):
    response = await client.put(
        f"/api/v1/users/{test_user_id}",
        headers={"Authorization": f"Bearer {super_admin_token}"},
        json={"full_name": "Updated Name"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Updated Name"


@pytest.mark.asyncio
async def test_assign_user_roles(client: AsyncClient, super_admin_token: str, test_user_id: str):
    response = await client.put(
        f"/api/v1/users/{test_user_id}/roles",
        headers={"Authorization": f"Bearer {super_admin_token}"},
        json={"roles": ["Analyst"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert "Analyst" in data["roles"]


@pytest.mark.asyncio
async def test_deactivate_user(client: AsyncClient, super_admin_token: str, test_user_id: str):
    response = await client.delete(
        f"/api/v1/users/{test_user_id}",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_list_roles(client: AsyncClient, super_admin_token: str):
    response = await client.get(
        "/api/v1/roles",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_get_role(client: AsyncClient, super_admin_token: str, test_role_id: str):
    response = await client.get(
        f"/api/v1/roles/{test_role_id}",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_role_id


@pytest.mark.asyncio
async def test_create_role(client: AsyncClient, super_admin_token: str):
    response = await client.post(
        "/api/v1/roles",
        headers={"Authorization": f"Bearer {super_admin_token}"},
        json={"name": "CustomRole", "description": "A custom role"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "CustomRole"
    assert data["is_system"] == False

    # Duplicate name
    response = await client.post(
        "/api/v1/roles",
        headers={"Authorization": f"Bearer {super_admin_token}"},
        json={"name": "CustomRole"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_update_role(client: AsyncClient, super_admin_token: str, test_role_id: str):
    # Create a non-system role first
    create_resp = await client.post(
        "/api/v1/roles",
        headers={"Authorization": f"Bearer {super_admin_token}"},
        json={"name": "UpdatableRole", "description": "Will be updated"},
    )
    role_id = create_resp.json()["id"]

    response = await client.put(
        f"/api/v1/roles/{role_id}",
        headers={"Authorization": f"Bearer {super_admin_token}"},
        json={"description": "Updated description"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["description"] == "Updated description"

    # Cannot update system role
    response = await client.put(
        f"/api/v1/roles/{test_role_id}",
        headers={"Authorization": f"Bearer {super_admin_token}"},
        json={"description": "Should fail"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_list_permissions(client: AsyncClient, super_admin_token: str):
    response = await client.get(
        "/api/v1/permissions",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "code" in data[0]


@pytest.mark.asyncio
async def test_list_all_roles(client: AsyncClient, super_admin_token: str):
    response = await client.get(
        "/api/v1/roles/all",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_audit_logs(client: AsyncClient, super_admin_token: str):
    response = await client.get(
        "/api/v1/audit/logs",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_dashboard_stats(client: AsyncClient, super_admin_token: str):
    response = await client.get(
        "/api/v1/dashboard/stats",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "stats" in data
    assert "registration_chart" in data
    assert "login_chart" in data
    assert "recent_activity" in data
    assert data["stats"]["total_users"] >= 0
    assert data["stats"]["active_users"] >= 0
    assert data["stats"]["roles_count"] >= 0
    assert data["stats"]["departments_count"] >= 0
    assert data["stats"]["audit_events_today"] >= 0


@pytest.mark.asyncio
async def test_unauthorized_access(client: AsyncClient):
    response = await client.get("/api/v1/users")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_delete_role(client: AsyncClient, super_admin_token: str):
    create_resp = await client.post(
        "/api/v1/roles",
        headers={"Authorization": f"Bearer {super_admin_token}"},
        json={"name": "DeleteMeRole", "description": "Will be deleted"},
    )
    role_id = create_resp.json()["id"]

    response = await client.delete(
        f"/api/v1/roles/{role_id}",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )
    assert response.status_code == 204

    # Cannot delete system role
    response = await client.delete(
        f"/api/v1/roles/{uuid4()}",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_department(client: AsyncClient, super_admin_token: str):
    create_resp = await client.post(
        "/api/v1/departments",
        headers={"Authorization": f"Bearer {super_admin_token}"},
        json={"name": "DeleteMeDept", "description": "Will be deleted"},
    )
    dept_id = create_resp.json()["id"]

    response = await client.delete(
        f"/api/v1/departments/{dept_id}",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )
    assert response.status_code == 204
