from pydantic_settings import BaseSettings
from pydantic import field_validator, model_validator
from typing import List

VALID_ENVIRONMENTS = {"development", "test", "production"}

INSECURE_DEFAULTS = {
    "change-me",
    "dev-secret-key-change-in-production",
    "",
}


class Settings(BaseSettings):
    # App
    APP_NAME: str = "DQ Command Center"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "DEBUG"
    SECRET_KEY: str = "change-me"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://dqadmin:[REDACTED-DEV-CREDENTIAL]@postgres:5432/dq_command_center"
    DATABASE_URL_SYNC: str = "postgresql://dqadmin:[REDACTED-DEV-CREDENTIAL]@postgres:5432/dq_command_center"

    # JWT
    JWT_SECRET_KEY: str = "dev-secret-key-change-in-production"
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
    def _reject_insecure_production_secrets(self) -> "Settings":
        if self.ENVIRONMENT == "production":
            if self.SECRET_KEY in INSECURE_DEFAULTS or len(self.SECRET_KEY) < 32:
                raise ValueError(
                    "SECRET_KEY must be set to a random value of at least 32 characters in production."
                )
            if self.JWT_SECRET_KEY in INSECURE_DEFAULTS or len(self.JWT_SECRET_KEY) < 32:
                raise ValueError(
                    "JWT_SECRET_KEY must be set to a random value of at least 32 characters in production."
                )
            if "[REDACTED-DEV-CREDENTIAL]" in self.DATABASE_URL or "[REDACTED-DEV-CREDENTIAL]" in self.DATABASE_URL_SYNC:
                raise ValueError(
                    "DATABASE_URL still contains the development default password in production."
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

    model_config = {"env_file": ".env", "case_sensitive": True}


settings = Settings()
