"""Production configuration must refuse unsafe development fallbacks."""
import pytest
from pydantic import ValidationError

from app.config import Settings

SAFE_PRODUCTION = dict(
    ENVIRONMENT="production",
    SECRET_KEY="s" * 40,
    JWT_SECRET_KEY="j" * 40,
    DATABASE_URL="postgresql+asyncpg://dq:not-the-dev-password@postgres:5432/dq",
    DATABASE_URL_SYNC="postgresql://dq:not-the-dev-password@postgres:5432/dq",
    LOG_LEVEL="INFO",
    CORS_ORIGINS="https://dq.example.org",
    DEV_EXPOSE_AUTH_TOKENS=False,
)


def build(**overrides) -> Settings:
    return Settings(_env_file=None, **{**SAFE_PRODUCTION, **overrides})


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
    {"JWT_SECRET_KEY": "dev-secret-key-change-in-production"},
    {"DATABASE_URL": "postgresql+asyncpg://dqadmin:[REDACTED-DEV-CREDENTIAL]@postgres:5432/dq"},
    {"DATABASE_URL_SYNC": "postgresql://dqadmin:[REDACTED-DEV-CREDENTIAL]@postgres:5432/dq"},
    {"DEV_EXPOSE_AUTH_TOKENS": True},
    {"CORS_ORIGINS": "*"},
    {"LOG_LEVEL": "DEBUG"},
])
def test_unsafe_production_settings_are_rejected(overrides):
    with pytest.raises(ValidationError):
        build(**overrides)


def test_token_echo_defaults_off_even_in_development():
    settings = Settings(_env_file=None, ENVIRONMENT="development")
    assert settings.DEV_EXPOSE_AUTH_TOKENS is False
    assert settings.expose_auth_tokens is False
    assert Settings(_env_file=None, ENVIRONMENT="development", DEV_EXPOSE_AUTH_TOKENS=True).expose_auth_tokens is True
    # The flag is ignored outside development.
    assert Settings(_env_file=None, ENVIRONMENT="test", DEV_EXPOSE_AUTH_TOKENS=True).expose_auth_tokens is False
