"""
Authorization regression tests, run through the real HTTP API.

Roles and permissions are seeded from the same constants the application
seeds production with (app.core.seed_secure), so these tests break if the
role model and the route guards drift apart.
"""
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import hash_password
from app.core.seed_secure import ROLE_PERMISSIONS, SYSTEM_PERMISSIONS, SYSTEM_ROLES
from app.models.role import Permission, Role, RolePermission, UserRole
from app.models.user import User

PASSWORD = "ValidPass123!"
TRIM = {"operations": [{"type": "trim_whitespace", "columns": "all"}]}
CSV = b"id,name,email\n1,Anna,anna@example.com\n2,Bo,\n3,Cecilia,cecilia@example.com\n"


@pytest_asyncio.fixture
async def rbac(test_session: AsyncSession):
    now = datetime.now(timezone.utc)
    roles = {}
    for r in SYSTEM_ROLES:
        role = Role(name=r["name"], description=r["description"], is_system=True, created_at=now, updated_at=now)
        test_session.add(role)
        roles[r["name"]] = role
    perms = {}
    for p in SYSTEM_PERMISSIONS:
        perm = Permission(name=p["name"], code=p["code"], module=p["module"], created_at=now)
        test_session.add(perm)
        perms[p["code"]] = perm
    await test_session.flush()
    for role_name, codes in ROLE_PERMISSIONS.items():
        for code in codes:
            test_session.add(RolePermission(role_id=roles[role_name].id, permission_id=perms[code].id))
    await test_session.commit()
    return roles


async def make_user(session: AsyncSession, roles: dict, email: str, role: str | None, super_admin=False) -> User:
    now = datetime.now(timezone.utc)
    user = User(
        email=email, username=email.split("@")[0], password_hash=hash_password(PASSWORD),
        full_name=email, is_active=True, is_verified=True, is_super_admin=super_admin,
        created_at=now, updated_at=now,
    )
    session.add(user)
    await session.flush()
    if role:
        session.add(UserRole(user_id=user.id, role_id=roles[role].id))
    await session.commit()
    return user


async def token_for(client: AsyncClient, email: str) -> dict:
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def upload_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    return tmp_path


async def upload(client: AsyncClient, headers: dict, name="Owned data") -> dict:
    r = await client.post(
        "/api/v1/dataset-files/upload", headers=headers,
        data={"name": name}, files={"file": ("people.csv", CSV, "text/csv")},
    )
    assert r.status_code == 201, r.text
    return r.json()


# ---------- registration -> usable account ----------

async def test_registered_user_gets_least_privileged_role_and_can_use_app(client, test_session, rbac):
    r = await client.post("/api/v1/auth/register", json={
        "email": "new.person@example.com", "password": PASSWORD, "full_name": "New Person",
    })
    assert r.status_code == 201, r.text

    login = await client.post("/api/v1/auth/login", json={"email": "new.person@example.com", "password": PASSWORD})
    assert login.status_code == 200
    body = login.json()["user"]
    assert body["roles"] == ["User"]
    assert body["is_super_admin"] is False
    assert "datasets:view" in body["permissions"]
    assert "users:manage" not in body["permissions"]

    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert (await client.get("/api/v1/datasets", headers=headers)).status_code == 200
    assert (await client.get("/api/v1/dashboard/summary", headers=headers)).status_code == 200
    me = await client.get("/api/v1/auth/me", headers=headers)
    assert me.json()["permissions"] == body["permissions"]


async def test_registration_cannot_self_assign_privileges(client, test_session, rbac):
    r = await client.post("/api/v1/auth/register", json={
        "email": "sneaky@example.com", "password": PASSWORD, "full_name": "Sneaky",
        "is_super_admin": True, "roles": ["Super Admin"],
    })
    assert r.status_code == 201
    user = (await test_session.execute(select(User).where(User.email == "sneaky@example.com"))).scalar_one()
    assert user.is_super_admin is False
    login = await client.post("/api/v1/auth/login", json={"email": "sneaky@example.com", "password": PASSWORD})
    assert login.json()["user"]["roles"] == ["User"]


# ---------- admin endpoints ----------

@pytest.mark.parametrize("path", ["/api/v1/users", "/api/v1/roles", "/api/v1/departments", "/api/v1/audit/logs", "/api/v1/permissions"])
async def test_regular_user_is_forbidden_from_admin_endpoints(client, test_session, rbac, path):
    await make_user(test_session, rbac, "regular@example.com", "User")
    headers = await token_for(client, "regular@example.com")
    assert (await client.get(path, headers=headers)).status_code == 403


@pytest.mark.parametrize("path", ["/api/v1/users", "/api/v1/datasets", "/api/v1/dataset-files/00000000-0000-0000-0000-000000000000/versions"])
async def test_protected_endpoints_reject_missing_and_forged_tokens(client, path):
    assert (await client.get(path)).status_code == 401
    assert (await client.get(path, headers={"Authorization": "Bearer not.a.jwt"})).status_code == 401


async def test_admin_cannot_escalate_to_super_admin(client, test_session, rbac):
    admin = await make_user(test_session, rbac, "useradmin@example.com", "Admin")
    root = await make_user(test_session, rbac, "root@example.com", "Super Admin", super_admin=True)
    headers = await token_for(client, "useradmin@example.com")

    r = await client.put(f"/api/v1/users/{admin.id}/roles", headers=headers, json={"roles": ["Super Admin"]})
    assert r.status_code == 403
    r = await client.post("/api/v1/users", headers=headers, json={
        "email": "minted@example.com", "username": "minted", "password": PASSWORD,
        "full_name": "Minted", "roles": ["Super Admin"],
    })
    assert r.status_code == 403
    # Changing a super admin's email would allow a takeover via password reset.
    r = await client.put(f"/api/v1/users/{root.id}", headers=headers, json={"email": "attacker@example.com"})
    assert r.status_code == 403
    assert (await client.delete(f"/api/v1/users/{root.id}", headers=headers)).status_code == 403

    # ...while ordinary user administration still works.
    r = await client.post("/api/v1/users", headers=headers, json={
        "email": "staff@example.com", "username": "staff", "password": PASSWORD, "full_name": "Staff",
    })
    assert r.status_code == 201, r.text
    assert r.json()["roles"] == ["User"]


async def test_super_admin_can_reassign_roles_including_existing_ones(client, test_session, rbac):
    await make_user(test_session, rbac, "root@example.com", "Super Admin", super_admin=True)
    target = await make_user(test_session, rbac, "target@example.com", "User")
    headers = await token_for(client, "root@example.com")
    # Keeping "User" while adding "Analyst" must not trip the unique (user, role) constraint.
    r = await client.put(f"/api/v1/users/{target.id}/roles", headers=headers, json={"roles": ["User", "Analyst"]})
    assert r.status_code == 200, r.text
    assert sorted(r.json()["roles"]) == ["Analyst", "User"]


async def test_user_list_rejects_arbitrary_sort_columns(client, test_session, rbac):
    await make_user(test_session, rbac, "root@example.com", "Super Admin", super_admin=True)
    headers = await token_for(client, "root@example.com")
    assert (await client.get("/api/v1/users?sort_by=password_hash", headers=headers)).status_code == 422
    assert (await client.get("/api/v1/users?department_id=not-a-uuid", headers=headers)).status_code == 422
    assert (await client.get("/api/v1/users?sort_by=email&sort_order=asc", headers=headers)).status_code == 200


# ---------- dataset ownership ----------

async def test_dataset_contents_are_private_to_their_owner(client, test_session, rbac, upload_dir):
    await make_user(test_session, rbac, "owner@example.com", "Analyst")
    await make_user(test_session, rbac, "other@example.com", "Analyst")
    await make_user(test_session, rbac, "root@example.com", "Super Admin", super_admin=True)
    owner = await token_for(client, "owner@example.com")
    other = await token_for(client, "other@example.com")
    root = await token_for(client, "root@example.com")

    version = await upload(client, owner)
    ds, vid = version["dataset_id"], version["id"]

    owner_paths = [
        f"/api/v1/datasets/{ds}",
        f"/api/v1/datasets/{ds}/elements",
        f"/api/v1/dataset-files/{ds}/versions",
        f"/api/v1/dataset-files/{ds}/versions/{vid}",
        f"/api/v1/dataset-files/{ds}/versions/{vid}/rows",
        f"/api/v1/dataset-files/{ds}/versions/{vid}/download",
        f"/api/v1/dataset-files/{ds}/quality-comparison",
    ]
    for path in owner_paths:
        assert (await client.get(path, headers=owner)).status_code == 200, path
        assert (await client.get(path, headers=root)).status_code == 200, path
        # 404, not 403: a non-owner must not learn that the ID exists.
        assert (await client.get(path, headers=other)).status_code == 404, path

    download = await client.get(f"/api/v1/dataset-files/{ds}/versions/{vid}/download", headers=owner)
    assert download.content == CSV
    preview = await client.post(f"/api/v1/dataset-files/{ds}/versions/{vid}/clean/preview", headers=owner, json=TRIM)
    assert preview.status_code == 200, preview.text

    writes = [
        ("post", f"/api/v1/dataset-files/{ds}/versions/{vid}/profile", None),
        ("post", f"/api/v1/dataset-files/{ds}/versions/{vid}/scan", None),
        ("post", f"/api/v1/dataset-files/{ds}/versions/{vid}/clean/preview", TRIM),
        ("post", f"/api/v1/dataset-files/{ds}/versions/{vid}/clean", TRIM),
        ("patch", f"/api/v1/datasets/{ds}/domain", {"domain_id": None}),
    ]
    for method, path, body in writes:
        r = await client.request(method.upper(), path, headers=other, json=body)
        assert r.status_code == 404, f"{path}: {r.status_code}"
    r = await client.post(
        f"/api/v1/dataset-files/{ds}/versions/upload", headers=other,
        files={"file": ("x.csv", b"a\n1\n", "text/csv")},
    )
    assert r.status_code == 404

    owner_list = (await client.get("/api/v1/datasets", headers=owner)).json()
    other_list = (await client.get("/api/v1/datasets", headers=other)).json()
    root_list = (await client.get("/api/v1/datasets", headers=root)).json()
    assert [d["id"] for d in owner_list] == [ds]
    assert other_list == []
    assert [d["id"] for d in root_list] == [ds]

    search = (await client.get("/api/v1/search?q=Owned", headers=other)).json()
    assert search["datasets"] == []


async def test_quality_rules_issues_and_counts_follow_dataset_access(client, test_session, rbac, upload_dir):
    await make_user(test_session, rbac, "owner@example.com", "Manager")
    await make_user(test_session, rbac, "other@example.com", "Manager")
    owner = await token_for(client, "owner@example.com")
    other = await token_for(client, "other@example.com")

    version = await upload(client, owner)
    ds, vid = version["dataset_id"], version["id"]
    scan = await client.post(f"/api/v1/dataset-files/{ds}/versions/{vid}/scan", headers=owner)
    assert scan.status_code == 200, scan.text

    owner_rules = (await client.get("/api/v1/data-quality/rules?page_size=100", headers=owner)).json()
    assert owner_rules["total"] > 0, "the CSV has a missing email, so discovery must create rules"
    rule_id = owner_rules["items"][0]["id"]

    other_rules = (await client.get("/api/v1/data-quality/rules?page_size=100", headers=other)).json()
    assert other_rules["total"] == 0 and other_rules["items"] == []
    assert (await client.get(f"/api/v1/data-quality/rules/{rule_id}", headers=other)).status_code == 404
    assert (await client.get(f"/api/v1/data-quality/rules/{rule_id}/results", headers=other)).status_code == 404
    assert (await client.delete(f"/api/v1/data-quality/rules/{rule_id}", headers=other)).status_code == 404
    assert (await client.get(f"/api/v1/data-quality/rules/{rule_id}", headers=owner)).status_code == 200

    owner_issues = (await client.get("/api/v1/quality-issues/open?limit=50", headers=owner)).json()
    other_issues = (await client.get("/api/v1/quality-issues/open?limit=50", headers=other)).json()
    assert len(owner_issues) > 0
    assert other_issues == []

    owner_summary = (await client.get("/api/v1/dashboard/summary", headers=owner)).json()
    other_summary = (await client.get("/api/v1/dashboard/summary", headers=other)).json()
    assert owner_summary["total_datasets"] == 1
    assert other_summary["total_datasets"] == 0


# ---------- email handling ----------

async def test_email_is_case_insensitive(client, test_session, rbac):
    r = await client.post("/api/v1/auth/register", json={
        "email": "Mixed.Case@Example.com", "password": PASSWORD, "full_name": "Mixed",
    })
    assert r.status_code == 201
    dup = await client.post("/api/v1/auth/register", json={
        "email": "mixed.case@example.com", "password": PASSWORD, "full_name": "Dup",
    })
    assert dup.status_code == 400
    login = await client.post("/api/v1/auth/login", json={"email": "MIXED.case@example.COM", "password": PASSWORD})
    assert login.status_code == 200


# ---------- governance ----------

async def test_manager_can_pick_assignees_but_not_claim_foreign_datasets(client, test_session, rbac, upload_dir):
    await make_user(test_session, rbac, "owner@example.com", "Manager")
    manager = await make_user(test_session, rbac, "manager@example.com", "Manager")
    owner = await token_for(client, "owner@example.com")
    mgr = await token_for(client, "manager@example.com")

    # Managers lack users:manage; sharing works by looking up an exact email.
    assert (await client.get("/api/v1/users", headers=mgr)).status_code == 403
    picker = await client.get("/api/v1/governance/assignable-users?email=OWNER@example.com", headers=mgr)
    assert picker.status_code == 200
    assert [u["email"] for u in picker.json()] == ["owner@example.com"]
    assert {"id", "email"} == set(picker.json()[0].keys())

    ds = (await upload(client, owner))["dataset_id"]
    claim = {"dataset_id": ds, "user_id": str(manager.id), "role": "owner"}
    r = await client.post("/api/v1/governance/assignments", headers=mgr, json=claim)
    assert r.status_code == 404, r.text
    assert (await client.get(f"/api/v1/datasets/{ds}", headers=mgr)).status_code == 404

    # The dataset's owner can delegate it, which then grants access.
    r = await client.post("/api/v1/governance/assignments", headers=owner, json=claim)
    assert r.status_code == 201, r.text
    assert (await client.get(f"/api/v1/datasets/{ds}", headers=mgr)).status_code == 200


async def test_users_cannot_enumerate_accounts_through_sharing(client, test_session, rbac):
    """Open registration means the sharing lookup must not reveal the list
    of registered people: no listing, only an exact email match."""
    await make_user(test_session, rbac, "regular@example.com", "User")
    await make_user(test_session, rbac, "someone@example.com", "User")
    headers = await token_for(client, "regular@example.com")
    assert (await client.get("/api/v1/governance/assignable-users", headers=headers)).status_code == 422
    assert (await client.get("/api/v1/governance/assignable-users?email=example.com", headers=headers)).json() == []
    assert (await client.get("/api/v1/governance/assignable-users?email=some", headers=headers)).json() == []
    found = (await client.get("/api/v1/governance/assignable-users?email=someone@example.com", headers=headers)).json()
    assert [u["email"] for u in found] == ["someone@example.com"]


# ---------- deactivation ----------

@pytest.mark.parametrize("how", ["delete", "update"])
async def test_deactivated_user_loses_existing_sessions_immediately(client, test_session, rbac, how):
    await make_user(test_session, rbac, "root@example.com", "Super Admin", super_admin=True)
    target = await make_user(test_session, rbac, "leaver@example.com", "User")
    root = await token_for(client, "root@example.com")
    login = (await client.post("/api/v1/auth/login", json={"email": "leaver@example.com", "password": PASSWORD})).json()
    access = {"Authorization": f"Bearer {login['access_token']}"}
    assert (await client.get("/api/v1/datasets", headers=access)).status_code == 200

    if how == "delete":
        assert (await client.delete(f"/api/v1/users/{target.id}", headers=root)).status_code == 204
    else:
        r = await client.put(f"/api/v1/users/{target.id}", headers=root, json={"is_active": False})
        assert r.status_code == 200

    # Previously both of these kept working, so deactivation never ended a session.
    assert (await client.get("/api/v1/datasets", headers=access)).status_code == 401
    assert (await client.post("/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]})).status_code == 401
    assert (await client.post("/api/v1/auth/login", json={"email": "leaver@example.com", "password": PASSWORD})).status_code == 401
