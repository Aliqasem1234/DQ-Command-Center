"""
Every registered user gets the whole product, and only ever sees their own
data. Two ordinary self-registered users ("alice", "bob") are used
throughout; nothing here relies on admin roles.
"""
import pytest
from httpx import AsyncClient

from tests.test_rbac import PASSWORD, make_user, rbac, token_for, upload_dir  # noqa: F401 (fixtures)

DIRTY_CSV = (
    "customer_id,name,email\n"
    "1,Anna,anna@example.com\n"
    "2,Bo,\n"
    "2,Bo,\n"
    "4,Cia,not-an-email\n"
)


async def register(client: AsyncClient, email: str) -> dict:
    r = await client.post("/api/v1/auth/register", json={"email": email, "password": PASSWORD, "full_name": email})
    assert r.status_code == 201, r.text
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def upload(client, headers, name="Kunder", csv=DIRTY_CSV, domain_id=None):
    data = {"name": name}
    if domain_id:
        data["domain_id"] = domain_id
    return await client.post(
        "/api/v1/dataset-files/upload", headers=headers, data=data,
        files={"file": ("kunder.csv", csv.encode(), "text/csv")},
    )


@pytest.fixture
async def two_users(client, rbac, upload_dir):  # noqa: F811
    alice = await register(client, "alice@example.com")
    bob = await register(client, "bob@example.com")
    return alice, bob


async def test_registered_user_has_full_product_but_no_administration(client, two_users):
    alice, _ = two_users
    perms = set((await client.get("/api/v1/auth/me", headers=alice)).json()["permissions"])
    assert {"datasets:manage", "data_quality:manage", "data_governance:manage", "reports:create"} <= perms
    assert not perms & {"users:manage", "roles:manage", "departments:manage", "audit:view"}
    for path in ["/api/v1/users", "/api/v1/roles", "/api/v1/audit/logs", "/api/v1/dashboard/stats", "/api/v1/dashboard/enhanced"]:
        assert (await client.get(path, headers=alice)).status_code == 403, path


async def test_complete_workflow_for_a_regular_user(client, two_users, upload_dir):  # noqa: F811
    alice, _ = two_users
    # empty state
    summary = (await client.get("/api/v1/dashboard/summary", headers=alice)).json()
    assert summary["total_datasets"] == 0 and summary["health_score"] is None and summary["status"] == "no_data"

    version = (await upload(client, alice)).json()
    ds, vid = version["dataset_id"], version["id"]
    base = f"/api/v1/dataset-files/{ds}/versions/{vid}"
    assert (await client.post(f"{base}/profile", headers=alice)).status_code == 200
    scan = (await client.post(f"{base}/scan", headers=alice)).json()
    issues = (await client.get(f"/api/v1/quality-issues/open?dataset_id={ds}", headers=alice)).json()
    assert len(issues) == scan["issues_found"] > 0

    clean = await client.post(f"{base}/clean", headers=alice, json={"operations": [{"type": "remove_duplicate_rows"}]})
    assert clean.status_code == 201, clean.text
    cleaned = clean.json()
    download = await client.get(f"/api/v1/dataset-files/{ds}/versions/{cleaned['id']}/download", headers=alice)
    assert download.status_code == 200
    assert download.text.count("\n") == 4  # header + 3 rows (the duplicate is gone)

    # The dashboard reflects this user's real data: health equals the score
    # of the only scanned dataset.
    summary = (await client.get("/api/v1/dashboard/summary", headers=alice)).json()
    assert summary["total_datasets"] == 1
    assert summary["health_score"] == scan["quality_score"]
    assert summary["open_issues"] == len(issues)
    assert summary["daily_trend"] and summary["daily_trend"][-1]["pass_rate"] == scan["quality_score"]

    # delete
    assert (await client.delete(f"/api/v1/datasets/{ds}", headers=alice)).status_code == 204
    assert (await client.get(f"/api/v1/datasets/{ds}", headers=alice)).status_code == 404
    assert list(upload_dir.rglob("*.csv")) == []
    summary = (await client.get("/api/v1/dashboard/summary", headers=alice)).json()
    assert summary["total_datasets"] == 0 and summary["open_issues"] == 0 and summary["total_quality_rules"] == 0


async def test_aggregates_never_include_other_users_data(client, two_users):
    alice, bob = two_users
    version = (await upload(client, alice)).json()
    await client.post(f"/api/v1/dataset-files/{version['dataset_id']}/versions/{version['id']}/scan", headers=alice)

    a = (await client.get("/api/v1/dashboard/summary", headers=alice)).json()
    b = (await client.get("/api/v1/dashboard/summary", headers=bob)).json()
    assert a["total_datasets"] == 1 and a["open_issues"] > 0 and a["total_quality_rules"] > 0
    assert (b["total_datasets"], b["open_issues"], b["total_quality_rules"], b["health_score"]) == (0, 0, 0, None)
    assert b["daily_trend"] == []

    a_metrics = (await client.get("/api/v1/data-quality/metrics", headers=alice)).json()
    b_metrics = (await client.get("/api/v1/data-quality/metrics", headers=bob)).json()
    assert a_metrics["total_rules"] > 0 and a_metrics["total_results"] > 0
    assert b_metrics["total_rules"] == 0 and b_metrics["total_results"] == 0

    assert (await client.get("/api/v1/data-quality/monitoring/health-score", headers=bob)).json()["results_evaluated"] == 0
    assert (await client.get("/api/v1/data-quality/monitoring/rule-performance", headers=bob)).json()["rules"] == []
    assert (await client.get("/api/v1/data-quality/monitoring/failing-rules", headers=bob)).json()["failing_rules"] == []
    # (this endpoint always errored before: a broken SQL cast)
    assert len((await client.get("/api/v1/data-quality/monitoring/rule-performance", headers=alice)).json()["rules"]) > 0
    assert (await client.get("/api/v1/data-quality/monitoring/trend", headers=bob)).json()["trend"] == []
    assert len((await client.get("/api/v1/data-quality/monitoring/trend", headers=alice)).json()["trend"]) > 0
    report = (await client.get("/api/v1/results/quality-report", headers=bob)).json()
    assert report.get("rules_by_status", {}) in ({}, None) or sum(report["rules_by_status"].values()) == 0

    rule_id = (await client.get("/api/v1/data-quality/rules?page_size=100", headers=alice)).json()["items"][0]["id"]
    for path in [f"/api/v1/results/{rule_id}/statistics", f"/api/v1/results/{rule_id}/timeline",
                 f"/api/v1/results/{rule_id}/failure-analysis", f"/api/v1/results/errors/summary?rule_id={rule_id}"]:
        assert (await client.get(path, headers=bob)).status_code == 404, path
        assert (await client.get(path, headers=alice)).status_code == 200, path

    # A foreign dataset_id in the query must not widen the scope.
    foreign = (await client.get(f"/api/v1/dashboard/summary?dataset_id={version['dataset_id']}", headers=bob)).json()
    assert foreign["open_issues"] == 0 and foreign["health_score"] is None


async def test_domains_and_dataset_names_are_per_user(client, two_users):
    alice, bob = two_users
    a_dom = await client.post("/api/v1/domains", headers=alice, json={"name": "Finance"})
    b_dom = await client.post("/api/v1/domains", headers=bob, json={"name": "Finance"})
    assert a_dom.status_code == b_dom.status_code == 201
    assert (await client.post("/api/v1/domains", headers=alice, json={"name": "Finance"})).status_code == 409
    a_id = a_dom.json()["id"]

    assert [d["id"] for d in (await client.get("/api/v1/domains", headers=bob)).json()] == [b_dom.json()["id"]]
    assert (await client.get(f"/api/v1/domains/{a_id}", headers=bob)).status_code == 404
    assert (await client.put(f"/api/v1/domains/{a_id}", headers=bob, json={"name": "Hacked"})).status_code == 404
    assert (await client.get(f"/api/v1/domains/{a_id}/datasets", headers=bob)).status_code == 404
    assert (await upload(client, bob, domain_id=a_id)).status_code == 404

    # Same dataset name for two users is fine (it used to be global).
    assert (await upload(client, alice, name="Kunder")).status_code == 201
    bob_ds = await upload(client, bob, name="Kunder")
    assert bob_ds.status_code == 201
    patch = await client.patch(f"/api/v1/datasets/{bob_ds.json()['dataset_id']}/domain", headers=bob, json={"domain_id": a_id})
    assert patch.status_code == 404

    search = (await client.get("/api/v1/search?q=Fin", headers=bob)).json()
    assert [d["id"] for d in search["domains"]] == [b_dom.json()["id"]]


async def test_rules_policies_and_assignments_are_private(client, two_users):
    alice, bob = two_users
    a_ds = (await upload(client, alice)).json()["dataset_id"]
    b_ds = (await upload(client, bob, name="B data")).json()["dataset_id"]
    rule = {"name": "Email required", "dimension": "completeness", "rule_type": "required_field", "status": "active"}

    loose = (await client.post("/api/v1/data-quality/rules", headers=alice, json=rule)).json()
    on_ds = await client.post("/api/v1/data-quality/rules", headers=alice, json={**rule, "dataset_id": a_ds})
    assert on_ds.status_code == 201 and on_ds.json()["dataset_id"] == a_ds
    assert (await client.post("/api/v1/data-quality/rules", headers=alice, json={**rule, "dataset_id": b_ds})).status_code == 404
    for method in ["GET", "PUT", "DELETE"]:
        r = await client.request(method, f"/api/v1/data-quality/rules/{loose['id']}", headers=bob,
                                 json={"name": "x"} if method == "PUT" else None)
        assert r.status_code == 404, method
    assert (await client.get("/api/v1/data-quality/rules", headers=bob)).json()["total"] == 0

    policy = await client.post("/api/v1/governance/policies", headers=alice,
                               json={"name": "Retention", "policy_type": "retention", "dataset_id": a_ds})
    assert policy.status_code == 201, policy.text
    pid = policy.json()["id"]
    assert (await client.get("/api/v1/governance/policies", headers=bob)).json()["total"] == 0
    for method in ["GET", "PUT", "DELETE"]:
        r = await client.request(method, f"/api/v1/governance/policies/{pid}", headers=bob,
                                 json={"name": "x"} if method == "PUT" else None)
        assert r.status_code == 404, method
    assert (await client.post("/api/v1/governance/policies", headers=bob,
                              json={"name": "x", "policy_type": "retention", "dataset_id": a_ds})).status_code == 404

    a_dom = (await client.post("/api/v1/domains", headers=alice, json={"name": "Sales"})).json()["id"]
    me_bob = (await client.get("/api/v1/auth/me", headers=bob)).json()["id"]
    claim = await client.post("/api/v1/governance/assignments", headers=bob,
                              json={"domain_id": a_dom, "user_id": me_bob, "role": "owner"})
    assert claim.status_code == 404
    assert (await client.get("/api/v1/governance/assignments", headers=bob)).json()["total"] == 0


async def test_sharing_by_email_grants_access_but_not_deletion(client, two_users):
    alice, bob = two_users
    ds = (await upload(client, alice)).json()["dataset_id"]
    bob_user = (await client.get("/api/v1/governance/assignable-users?email=bob@example.com", headers=alice)).json()[0]
    share = await client.post("/api/v1/governance/assignments", headers=alice,
                              json={"dataset_id": ds, "user_id": bob_user["id"], "role": "steward"})
    assert share.status_code == 201
    assert (await client.get(f"/api/v1/datasets/{ds}", headers=bob)).status_code == 200
    # Bob sees what was shared with him, but can't revoke it or delete the data.
    assert (await client.get("/api/v1/governance/assignments", headers=bob)).json()["total"] == 1
    assert (await client.delete(f"/api/v1/governance/assignments/{share.json()['id']}", headers=bob)).status_code == 404
    assert (await client.delete(f"/api/v1/datasets/{ds}", headers=bob)).status_code == 403
    # ...nor share it onwards.
    alice_id = (await client.get("/api/v1/auth/me", headers=alice)).json()["id"]
    reshare = await client.post("/api/v1/governance/assignments", headers=bob,
                                json={"dataset_id": ds, "user_id": alice_id, "role": "analyst"})
    assert reshare.status_code == 403
    assert (await client.delete(f"/api/v1/datasets/{ds}", headers=alice)).status_code == 204


async def test_dataset_cannot_be_created_for_someone_else(client, two_users):
    alice, bob = two_users
    bob_id = (await client.get("/api/v1/auth/me", headers=bob)).json()["id"]
    r = await client.post("/api/v1/datasets", headers=alice,
                          json={"name": "Planted", "dataset_type": "file", "data_owner_id": bob_id})
    assert r.status_code == 201, r.text
    assert r.json()["data_owner_id"] != bob_id
    assert (await client.get("/api/v1/datasets", headers=bob)).json() == []


async def test_audit_history_is_personal(client, two_users, test_session):
    alice, bob = two_users
    await upload(client, alice)
    a_logs = (await client.get("/api/v1/audit/my-logs", headers=alice)).json()
    b_logs = (await client.get("/api/v1/audit/my-logs", headers=bob)).json()
    me_a = (await client.get("/api/v1/auth/me", headers=alice)).json()["email"]
    assert a_logs["total"] > 0 and all(i["user_email"] == me_a for i in a_logs["items"] if i.get("user_email"))
    assert b_logs["total"] == 0
    assert (await client.get("/api/v1/audit/logs", headers=alice)).status_code == 403


async def test_manager_no_longer_reads_the_global_audit_log(client, test_session, rbac):  # noqa: F811
    await make_user(test_session, rbac, "manager@example.com", "Manager")
    headers = await token_for(client, "manager@example.com")
    assert (await client.get("/api/v1/audit/logs", headers=headers)).status_code == 403
    assert (await client.get("/api/v1/audit/my-logs", headers=headers)).status_code == 200


async def test_super_admin_platform_views_still_work(client, test_session, rbac):  # noqa: F811
    await make_user(test_session, rbac, "root@example.com", "Super Admin", super_admin=True)
    headers = await token_for(client, "root@example.com")
    for path in ["/api/v1/dashboard/stats", "/api/v1/dashboard/enhanced", "/api/v1/audit/logs", "/api/v1/users"]:
        assert (await client.get(path, headers=headers)).status_code == 200, path
