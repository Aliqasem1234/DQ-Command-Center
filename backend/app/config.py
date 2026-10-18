from pydantic_settings import BaseSettings
from pydantic import field_validator, model_validator
from typing import List
from urllib.parse import unquote, urlsplit

VALID_ENVIRONMENTS = {"development", "test", "production"}

# Placeholder values that older versions of this project shipped as code
# defaults or in .env.example. They are refused everywhere for the JWT secret
# and in production for every secret.
INSECURE_DEFAULTS = {
    "change-me",
    "dev-secret-key-change-in-production",
    "change-this-to-a-random-secret-key-at-least-32-chars",
    "",
}

# Words that mark a database password as a development/example value.
WEAK_DB_PASSWORD_MARKERS = ("dev", "pass", "change", "example", "secret", "test", "demo")
MIN_SECRET_LENGTH = 32
MIN_PRODUCTION_DB_PASSWORD_LENGTH = 16


def _database_password(url: str) -> str:
    try:
        return unquote(urlsplit(url).password or "")
    except ValueError:
        return ""


class Settings(BaseSettings):
    # App
    APP_NAME: str = "DQ Command Center"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "DEBUG"
    # Validated in production but not otherwise used by the code today.
    SECRET_KEY: str = ""

    # Database - no default: credentials must come from the environment (.env
    # locally, real secrets in production). Startup fails if they are missing.
    DATABASE_URL: str
    DATABASE_URL_SYNC: str

    # JWT - no default; must be a random value of at least 32 characters in
    # every environment, otherwise anyone could forge tokens.
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Admin initialization (set via environment only; empty means no auto-created admin)
    INIT_ADMIN_EMAIL: str = ""
    INIT_ADMIN_PASSWORD: str = ""
    INIT_ADMIN_NAME: str = "Administrator"

    # Security
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:80,http://localhost"
    RATE_LIMIT_PER_MINUTE: int = 20
    LOCKOUT_THRESHOLD: int = 5
    LOCKOUT_DURATION_MINUTES: int = 15

    # Email
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@dqcommandcenter.com"
    SMTP_USE_TLS: bool = True

    # Echo email-verification / password-reset tokens in API responses so a
    # local setup without SMTP can complete those flows. Anyone who can call
    # the API could then reset ANY account's password, so this is opt-in and
    # honoured only when ENVIRONMENT=development - never enable it on a
    # server other people can reach.
    DEV_EXPOSE_AUTH_TOKENS: bool = False

    @property
    def expose_auth_tokens(self) -> bool:
        return self.ENVIRONMENT == "development" and self.DEV_EXPOSE_AUTH_TOKENS

    # File uploads (dataset ingestion)
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

    @field_validator("ENVIRONMENT", mode="before")
    @classmethod
    def _known_environment(cls, v: str) -> str:
        # Unknown values ("prod", "Production ", "staging") used to fall into
        # a half-development mode (API docs on, no secret checks) without any
        # warning. Normalise case/whitespace and refuse anything unexpected.
        v = str(v).strip().lower()
        if v not in VALID_ENVIRONMENTS:
            raise ValueError(f"ENVIRONMENT must be one of {sorted(VALID_ENVIRONMENTS)}, got {v!r}")
        return v

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @model_validator(mode="after")
    def _require_secrets(self) -> "Settings":
        # Docker Compose turns an unset ${VAR} into an empty string, so
        # "required" alone is not enough: refuse empty values explicitly.
        for name in ("DATABASE_URL", "DATABASE_URL_SYNC"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} must be set (see .env.example).")
        if self.JWT_SECRET_KEY in INSECURE_DEFAULTS or len(self.JWT_SECRET_KEY) < MIN_SECRET_LENGTH:
            raise ValueError(
                "JWT_SECRET_KEY must be set to a random value of at least 32 characters "
                "(python -c \"import secrets; print(secrets.token_hex(32))\")."
            )
        return self

    @model_validator(mode="after")
    def _reject_insecure_production_secrets(self) -> "Settings":
        if self.ENVIRONMENT == "production":
            if self.SECRET_KEY in INSECURE_DEFAULTS or len(self.SECRET_KEY) < MIN_SECRET_LENGTH:
                raise ValueError(
                    "SECRET_KEY must be set to a random value of at least 32 characters in production."
                )
            for name in ("DATABASE_URL", "DATABASE_URL_SYNC"):
                password = _database_password(getattr(self, name))
                if (
                    len(password) < MIN_PRODUCTION_DB_PASSWORD_LENGTH
                    or any(marker in password.lower() for marker in WEAK_DB_PASSWORD_MARKERS)
                ):
                    raise ValueError(
                        f"{name} must use a random database password of at least "
                        f"{MIN_PRODUCTION_DB_PASSWORD_LENGTH} characters in production "
                        "(development and example passwords are refused)."
                    )
            if self.DEV_EXPOSE_AUTH_TOKENS:
                raise ValueError("DEV_EXPOSE_AUTH_TOKENS must be false in production.")
            if "*" in self.cors_origins_list:
                # Credentials are allowed on CORS requests, so a wildcard
                # would let any site make authenticated calls.
                raise ValueError("CORS_ORIGINS must list explicit origins in production, not '*'.")
            if self.LOG_LEVEL.strip().upper() == "DEBUG":
                raise ValueError("LOG_LEVEL=DEBUG is not allowed in production (debug logs can carry request data).")
        return self

    # hide_input_in_errors: a validation error must never echo secrets into logs.
    model_config = {"env_file": ".env", "case_sensitive": True, "hide_input_in_errors": True}


settings = Settings()
