from pydantic_settings import BaseSettings
from pydantic import model_validator
from typing import List

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

    # File uploads (dataset ingestion)
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

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
            if "[REDACTED-DEV-CREDENTIAL]" in self.DATABASE_URL:
                raise ValueError(
                    "DATABASE_URL still contains the development default password in production."
                )
        return self

    model_config = {"env_file": ".env", "case_sensitive": True}


settings = Settings()
