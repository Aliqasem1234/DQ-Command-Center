"""Regression tests for the 2026-10-25 security hardening pass."""
import secrets
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from pydantic import ValidationError
from sqlalchemy import update

from app.config import Settings, settings
from app.core.security import create_access_token, decode_token
from app.models.user import User
from tests.test_product_isolation import register, upload
from tests.test_rbac import PASSWORD, rbac, upload_dir  # noqa: F401 (fixtures)


async def _login(client, email, password):
    return await client.post("/api/v1/auth/login", json={"email": email, "password": password})


async def test_password_change_ends_other_sessions_and_keeps_this_one(client, rbac):  # noqa: F811
    await register(client, "carol@example.com")
    other_device = (await _login(client, "carol@example.com", PASSWORD)).json()
    this_device = (await _login(client, "carol@example.com", PASSWORD)).json()
    new_password = secrets.token_urlsafe(16)  # generated per run, never a fixed value

    r = await client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {this_device['access_token']}"},
        json={"current_password": PASSWORD, "new_password": new_password},
    )
    assert r.status_code == 200, r.text
    fresh = r.json()

    # Every refresh token issued before the change is dead, on every device.
    for old in (other_device, this_device):
        refreshed = await client.post("/api/v1/auth/refresh", json={"refresh_token": old["refresh_token"]})
        assert refreshed.status_code == 401
    # The pair returned with the change keeps this session alive.
    assert (await client.post("/api/v1/auth/refresh", json={"refresh_token": fresh["refresh_token"]})).status_code == 200
    assert (await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {fresh['access_token']}"})).status_code == 200
    # Old password no longer works, the new one does.
    assert (await _login(client, "carol@example.com", PASSWORD)).status_code == 401
    assert (await _login(client, "carol@example.com", new_password)).status_code == 200


async def test_deactivated_status_is_only_revealed_with_the_correct_password(client, test_session, rbac):  # noqa: F811
    await register(client, "dave@example.com")
    await test_session.execute(update(User).where(User.email == "dave@example.com").values(is_active=False))
    await test_session.flush()

    wrong = await _login(client, "dave@example.com", secrets.token_urlsafe(12))
    assert wrong.status_code == 401
    assert wrong.json()["detail"] == "Invalid email or password"

    right = await _login(client, "dave@example.com", PASSWORD)
    assert right.status_code == 401
    assert right.json()["detail"] == "Account is deactivated"


async def test_unknown_account_still_runs_a_password_hash(client, monkeypatch):
    # Equal work for known and unknown e-mails, so response time doesn't
    # reveal which addresses are registered.
    from app.services import auth_service

    calls = []
    real = auth_service.verify_password
    monkeypatch.setattr(auth_service, "verify_password", lambda p, h: calls.append(h) or real(p, h))
    r = await _login(client, "nobody@example.com", secrets.token_urlsafe(12))
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid email or password"
    assert len(calls) == 1


def test_tokens_without_expiry_or_with_other_algorithms_are_rejected():
    now = datetime.now(timezone.utc)
    claims = {"sub": "00000000-0000-0000-0000-000000000001", "type": "access", "iat": now}
    no_exp = jwt.encode(claims, settings.JWT_SECRET_KEY, algorithm="HS256")
    assert decode_token(no_exp) is None

    expired = jwt.encode({**claims, "exp": now - timedelta(minutes=1)}, settings.JWT_SECRET_KEY, algorithm="HS256")
    assert decode_token(expired) is None

    unsigned = jwt.encode({**claims, "exp": now + timedelta(minutes=5)}, None, algorithm="none")
    assert decode_token(unsigned) is None

    other_key = jwt.encode({**claims, "exp": now + timedelta(minutes=5)}, "x" * 40, algorithm="HS256")
    assert decode_token(other_key) is None

    assert decode_token(create_access_token("00000000-0000-0000-0000-000000000001"))["type"] == "access"


@pytest.mark.parametrize("algorithm", ["none", "RS256", "ES256", "hs256"])
def test_only_hmac_jwt_algorithms_are_accepted(algorithm):
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            DATABASE_URL="postgresql+asyncpg://dq:x@postgres/dq",
            DATABASE_URL_SYNC="postgresql://dq:x@postgres/dq",
            JWT_SECRET_KEY="j" * 40,
            JWT_ALGORITHM=algorithm,
        )


async def test_processing_errors_do_not_leak_internal_details(client, rbac, upload_dir, monkeypatch):  # noqa: F811
    from app.api.v1 import dataset_files

    headers = await register(client, "erin@example.com")
    version = (await upload(client, headers)).json()
    marker = "/internal/path/and-sql-detail"

    async def boom(*args, **kwargs):
        raise RuntimeError(marker)

    monkeypatch.setattr(dataset_files, "profile_dataset_version", boom)
    monkeypatch.setattr(dataset_files, "scan_dataset_version", boom)
    base = f"/api/v1/dataset-files/{version['dataset_id']}/versions/{version['id']}"
    for action in ("profile", "scan"):
        r = await client.post(f"{base}/{action}", headers=headers)
        assert r.status_code == 422
        assert marker not in r.text


def test_sql_echo_is_opt_in():
    base = dict(
        _env_file=None,
        DATABASE_URL="postgresql+asyncpg://dq:x@postgres/dq",
        DATABASE_URL_SYNC="postgresql://dq:x@postgres/dq",
        JWT_SECRET_KEY="j" * 40,
        ENVIRONMENT="development",
    )
    assert Settings(**base).SQL_ECHO is False


def _xlsx_bytes() -> bytes:
    import io
    import openpyxl

    wb = openpyxl.Workbook()
    wb.active.append(["customer_id", "name"])
    wb.active.append(["1", "Anna"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


async def _upload_file(client, headers, filename, content):
    return await client.post(
        "/api/v1/dataset-files/upload", headers=headers, data={"name": filename},
        files={"file": (filename, content, "application/octet-stream")},
    )


async def test_upload_accepts_real_xlsx_and_rejects_xls_and_fake_xlsx(client, rbac, upload_dir):  # noqa: F811
    headers = await register(client, "frank@example.com")
    assert (await _upload_file(client, headers, "ok.xlsx", _xlsx_bytes())).status_code == 201

    legacy = await _upload_file(client, headers, "old.xls", b"\xd0\xcf\x11\xe0 legacy workbook")
    assert legacy.status_code == 400

    fake = await _upload_file(client, headers, "fake.xlsx", b"customer_id,name\n1,Anna\n")
    assert fake.status_code == 400
    assert "not a valid .xlsx" in fake.json()["detail"]
    # A rejected upload leaves no file behind.
    assert sorted(p.name for p in upload_dir.rglob("*") if p.is_file() and p.suffix == ".xls") == []


async def test_upload_rejects_workbook_that_unpacks_too_large(client, rbac, upload_dir, monkeypatch):  # noqa: F811
    from app.services import file_storage_service

    headers = await register(client, "gina@example.com")
    monkeypatch.setattr(file_storage_service, "MAX_XLSX_UNCOMPRESSED_BYTES", 1024)
    r = await _upload_file(client, headers, "bomb.xlsx", _xlsx_bytes())
    assert r.status_code == 400
    assert "too large when unpacked" in r.json()["detail"]
    assert [p for p in upload_dir.rglob("*.xlsx")] == []


# Made by passlib 1.7.4 (the previous hashing library) with the project's
# Argon2 settings, for this throw-away value. Not a password of any account.
_PASSLIB_HASH = "$argon2id$v=19$m=65536,t=3,p=4$tdaaszamVMq519o7ZwzhHA$xJugYEmstYfdb6vK11R5Fqn3dtWkjc0z484FCpWHunk"
_PASSLIB_VALUE = "legacy-format-check-not-a-password"


def test_existing_passlib_hashes_still_verify():
    from app.core.security import hash_password, verify_password

    assert verify_password(_PASSLIB_VALUE, _PASSLIB_HASH)
    assert not verify_password(_PASSLIB_VALUE + "x", _PASSLIB_HASH)
    assert not verify_password(_PASSLIB_VALUE, "not-a-real-hash")
    new = hash_password(_PASSLIB_VALUE)
    assert new.startswith("$argon2id$v=19$m=65536,t=3,p=4$")
    assert new != hash_password(_PASSLIB_VALUE)  # random salt
    assert verify_password(_PASSLIB_VALUE, new)


async def test_validation_errors_do_not_echo_submitted_values(client):
    short = "Ab1!" + secrets.token_hex(1)  # too short on purpose; random per run
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": "harry@example.com", "password": short, "full_name": "Harry"},
    )
    assert r.status_code == 422
    assert short not in r.text
    item = r.json()["detail"][0]
    assert item["loc"] == ["body", "password"]
    assert item["type"] == "string_too_short"
    assert item["ctx"]["min_length"] == 8
    assert "input" not in item
