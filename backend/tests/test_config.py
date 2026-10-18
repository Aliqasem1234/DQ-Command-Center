"""Configuration must refuse missing secrets and unsafe development fallbacks.

Every value below is a test-only placeholder; none is used by any real
database or deployment.
"""
import pytest
from pydantic import ValidationError

from app.config import Settings

DEV_REQUIRED = dict(
    DATABASE_URL="postgresql+asyncpg://dq:test-only-placeholder@postgres:5432/dq",
    DATABASE_URL_SYNC="postgresql://dq:test-only-placeholder@postgres:5432/dq",
    JWT_SECRET_KEY="j" * 40,
)

SAFE_PRODUCTION = dict(
    DEV_REQUIRED,
    ENVIRONMENT="production",
    SECRET_KEY="s" * 40,
    DATABASE_URL="postgresql+asyncpg://dq:Q7vR2mXk9LpW4tZs8NbY@postgres:5432/dq",
    DATABASE_URL_SYNC="postgresql://dq:Q7vR2mXk9LpW4tZs8NbY@postgres:5432/dq",
    LOG_LEVEL="INFO",
    CORS_ORIGINS="https://dq.example.org",
    DEV_EXPOSE_AUTH_TOKENS=False,
)


def build(**overrides) -> Settings:
    return Settings(_env_file=None, **{**SAFE_PRODUCTION, **overrides})


def dev(**overrides) -> Settings:
    return Settings(_env_file=None, **{**DEV_REQUIRED, "ENVIRONMENT": "development", **overrides})


def test_safe_production_settings_are_accepted():
    settings = build()
    assert settings.ENVIRONMENT == "production"
    assert settings.expose_auth_tokens is False


def test_environment_is_normalised():
    assert build(ENVIRONMENT="  Production ").ENVIRONMENT == "production"


@pytest.mark.parametrize("overrides", [
    {"ENVIRONMENT": "prod"},
    {"ENVIRONMENT": "staging"},
    {"SECRET_KEY": "change-me"},
    {"SECRET_KEY": "short"},
    {"SECRET_KEY": ""},
    {"JWT_SECRET_KEY": "dev-secret-key-change-in-production"},
    # Development-style or short database passwords.
    {"DATABASE_URL": "postgresql+asyncpg://dqadmin:dqadmin_dev_placeholder_9@postgres:5432/dq"},
    {"DATABASE_URL_SYNC": "postgresql://dqadmin:dqadmin_dev_placeholder_9@postgres:5432/dq"},
    {"DATABASE_URL": "postgresql+asyncpg://dq:Sh0rtPw@postgres:5432/dq"},
    {"DATABASE_URL_SYNC": "postgresql://dq@postgres:5432/dq"},
    {"DEV_EXPOSE_AUTH_TOKENS": True},
    {"CORS_ORIGINS": "*"},
    {"LOG_LEVEL": "DEBUG"},
])
def test_unsafe_production_settings_are_rejected(overrides):
    with pytest.raises(ValidationError):
        build(**overrides)


@pytest.mark.parametrize("missing", ["DATABASE_URL", "DATABASE_URL_SYNC", "JWT_SECRET_KEY"])
def test_secrets_have_no_code_default(missing, monkeypatch):
    # No silent fallback: without the variable, startup fails in every environment.
    monkeypatch.delenv(missing, raising=False)
    values = {k: v for k, v in DEV_REQUIRED.items() if k != missing}
    with pytest.raises(ValidationError):
        Settings(_env_file=None, ENVIRONMENT="development", **values)


@pytest.mark.parametrize("overrides", [
    {"DATABASE_URL": ""},                    # Compose turns an unset ${VAR} into ""
    {"DATABASE_URL_SYNC": "   "},
    {"JWT_SECRET_KEY": ""},
    {"JWT_SECRET_KEY": "dev-secret-key-change-in-production"},
    {"JWT_SECRET_KEY": "change-this-to-a-random-secret-key-at-least-32-chars"},
    {"JWT_SECRET_KEY": "too-short"},
])
def test_empty_or_default_secrets_are_rejected_even_in_development(overrides):
    with pytest.raises(ValidationError):
        dev(**overrides)


def test_development_accepts_local_database_password():
    # Local development is not forced to use production-grade DB passwords.
    assert dev().ENVIRONMENT == "development"


def test_token_echo_defaults_off_even_in_development():
    settings = dev()
    assert settings.DEV_EXPOSE_AUTH_TOKENS is False
    assert settings.expose_auth_tokens is False
    assert dev(DEV_EXPOSE_AUTH_TOKENS=True).expose_auth_tokens is True
    # The flag is ignored outside development.
    assert dev(ENVIRONMENT="test", DEV_EXPOSE_AUTH_TOKENS=True).expose_auth_tokens is False


def test_validation_errors_do_not_echo_secret_values():
    marker = "unique-db-secret-marker-xyz"
    with pytest.raises(ValidationError) as excinfo:
        dev(DATABASE_URL=f"postgresql+asyncpg://dq:{marker}@postgres/dq", JWT_SECRET_KEY="")
    assert marker not in str(excinfo.value)
