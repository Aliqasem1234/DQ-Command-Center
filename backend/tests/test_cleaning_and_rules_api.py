"""Preview == apply, restore, executable rules, empty datasets, isolation."""
import pytest

from tests.test_rbac import PASSWORD, make_user, rbac, token_for, upload_dir  # noqa: F401 (fixtures)

CSV = "id,email,age\n1,a@x.se, 30\n2,,40\n2,,40\n4,bad,200\n"


async def setup_user(client, test_session, rbac, email):  # noqa: F811
    await make_user(test_session, rbac, email, "User")
    return await token_for(client, email)


async def upload(client, headers, csv=CSV, name="Kunder"):
    r = await client.post("/api/v1/dataset-files/upload", headers=headers, data={"name": name},
                          files={"file": ("k.csv", csv.encode(), "text/csv")})
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
async def alice(client, test_session, rbac, upload_dir):  # noqa: F811
    headers = await setup_user(client, test_session, rbac, "alice@example.com")
    return headers, await upload(client, headers)


async def test_preview_matches_what_apply_saves(client, alice):
    headers, v = alice
    base = f"/api/v1/dataset-files/{v['dataset_id']}/versions/{v['id']}"
    ops = {"operations": [{"type": "trim_whitespace"}, {"type": "remove_duplicate_rows"}]}
    preview = (await client.post(f"{base}/clean/preview", headers=headers, json=ops)).json()
    assert (preview["rows_removed"], preview["rows_modified"], preview["values_changed"]) == (1, 1, 1)
    assert preview["changed_columns"] == {"age": 1}
    assert preview["removes_rows"] is True
    assert preview["quality_score_before"] is not None and preview["quality_score_after"] is not None
    removed = [s for s in preview["sample_changes"] if s["after"] is None]
    assert [s["row"] for s in removed] == [3]

    applied = (await client.post(f"{base}/clean", headers=headers, json=ops)).json()
    assert applied["row_count"] == preview["result_row_count"] == 3
    assert applied["rows_changed"] == preview["rows_changed"]
    body = (await client.get(f"/api/v1/dataset-files/{v['dataset_id']}/versions/{applied['id']}/download", headers=headers)).text
    assert body.splitlines() == ["id,email,age", "1,a@x.se,30", "2,,40", "4,bad,200"]


async def test_audit_entry_for_cleaning_holds_no_cell_values(client, alice):
    headers, v = alice
    base = f"/api/v1/dataset-files/{v['dataset_id']}/versions/{v['id']}"
    ops = {"operations": [{"type": "fill_missing", "columns": ["email"], "strategy": "fill_value", "value": "secret@example.com"}]}
    assert (await client.post(f"{base}/clean", headers=headers, json=ops)).status_code == 201
    logs = (await client.get("/api/v1/audit/my-logs", headers=headers)).json()["items"]
    assert any(l["action"] == "CLEAN" for l in logs)
    assert "secret@example.com" not in str(logs)


async def test_restore_creates_a_new_version_and_keeps_history(client, alice):
    headers, v = alice
    ds, base = v["dataset_id"], f"/api/v1/dataset-files/{v['dataset_id']}/versions"
    cleaned = (await client.post(f"{base}/{v['id']}/clean", headers=headers, json={"operations": [{"type": "remove_duplicate_rows"}]})).json()
    restored = await client.post(f"{base}/{v['id']}/restore", headers=headers)
    assert restored.status_code == 201
    r = restored.json()
    assert r["version_number"] == 3 and r["row_count"] == 4
    assert r["cleaning_operations"] == [{"type": "restore", "from_version": 1}]
    versions = (await client.get(base, headers=headers)).json()
    assert [x["version_number"] for x in versions] == [3, 2, 1]          # nothing overwritten
    original = (await client.get(f"{base}/{v['id']}/download", headers=headers)).text
    copy = (await client.get(f"{base}/{r['id']}/download", headers=headers)).text
    assert copy == original                                              # an exact copy of v1
    assert cleaned["version_number"] == 2


async def test_executable_rules_run_and_affect_the_score(client, alice):
    headers, v = alice
    ds = v["dataset_id"]
    bad = await client.post("/api/v1/data-quality/rules", headers=headers, json={
        "name": "Age range", "dimension": "validity", "rule_type": "numeric_range", "status": "active",
        "dataset_id": ds, "target_field": "age", "rule_definition": {"min": 50}})
    assert bad.status_code == 201
    no_dataset = await client.post("/api/v1/data-quality/rules", headers=headers, json={
        "name": "x", "dimension": "validity", "rule_type": "numeric_range", "target_field": "age", "rule_definition": {"min": 0}})
    assert no_dataset.status_code == 422
    invalid = await client.post("/api/v1/data-quality/rules", headers=headers, json={
        "name": "x", "dimension": "validity", "rule_type": "numeric_range", "dataset_id": ds, "target_field": "age", "rule_definition": {}})
    assert invalid.status_code == 422

    rule = bad.json()
    assert rule["executable"] is True and rule["last_result_status"] is None
    run = (await client.post(f"/api/v1/data-quality/rules/{rule['id']}/run", headers=headers)).json()
    assert (run["status"], run["records_checked"], run["records_failed"], run["failing_rows"]) == ("failed", 4, 3, [1, 2, 3])
    listed = (await client.get("/api/v1/data-quality/rules?page_size=100", headers=headers)).json()["items"]
    mine = next(r for r in listed if r["id"] == rule["id"])
    assert (mine["last_result_status"], mine["last_records_failed"]) == ("failed", 3)

    issues = (await client.get(f"/api/v1/quality-issues/open?dataset_id={ds}", headers=headers)).json()
    assert any("Age range" in i["description"] for i in issues)

    # The scan runs it too and it counts in the score: same file with/without the rule.
    scan_with = (await client.post(f"/api/v1/dataset-files/{ds}/versions/{v['id']}/scan", headers=headers)).json()
    assert scan_with["custom_rules_run"] == 1
    await client.put(f"/api/v1/data-quality/rules/{rule['id']}", headers=headers, json={"status": "inactive"})
    scan_without = (await client.post(f"/api/v1/dataset-files/{ds}/versions/{v['id']}/scan", headers=headers)).json()
    assert scan_without["custom_rules_run"] == 0
    assert scan_with["quality_score"] < scan_without["quality_score"]


async def test_documentation_only_rules_cannot_be_run(client, alice):
    headers, v = alice
    doc = (await client.post("/api/v1/data-quality/rules", headers=headers, json={
        "name": "Policy note", "dimension": "validity", "rule_type": "manual_review", "dataset_id": v["dataset_id"]})).json()
    assert doc["executable"] is False
    r = await client.post(f"/api/v1/data-quality/rules/{doc['id']}/run", headers=headers)
    assert r.status_code == 400


async def test_empty_dataset_has_no_score(client, test_session, rbac, upload_dir):  # noqa: F811
    headers = await setup_user(client, test_session, rbac, "empty@example.com")
    v = await upload(client, headers, csv="id,email\n", name="Tom")
    scan = (await client.post(f"/api/v1/dataset-files/{v['dataset_id']}/versions/{v['id']}/scan", headers=headers)).json()
    assert scan["quality_score"] is None
    summary = (await client.get("/api/v1/dashboard/summary", headers=headers)).json()
    assert summary["health_score"] is None


async def test_other_users_cannot_clean_restore_or_run_rules(client, test_session, rbac, alice):  # noqa: F811
    headers, v = alice
    rule = (await client.post("/api/v1/data-quality/rules", headers=headers, json={
        "name": "Email", "dimension": "validity", "rule_type": "email_format", "status": "active",
        "dataset_id": v["dataset_id"], "target_field": "email"})).json()
    bob = await setup_user(client, test_session, rbac, "bob@example.com")
    base = f"/api/v1/dataset-files/{v['dataset_id']}/versions/{v['id']}"
    trim = {"operations": [{"type": "trim_whitespace"}]}
    assert (await client.post(f"{base}/clean/preview", headers=bob, json=trim)).status_code == 404
    assert (await client.post(f"{base}/clean", headers=bob, json=trim)).status_code == 404
    assert (await client.post(f"{base}/restore", headers=bob)).status_code == 404
    assert (await client.post(f"/api/v1/data-quality/rules/{rule['id']}/run", headers=bob)).status_code == 404
