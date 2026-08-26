from pydantic_settings import BaseSettings
from typing import List
import os


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

    # Super Admin
    SUPER_ADMIN_EMAIL: str = "admin@dqcommandcenter.com"
    SUPER_ADMIN_PASSWORD: str = "[REDACTED-DEV-CREDENTIAL]"
    SUPER_ADMIN_NAME: str = "Super Admin"

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

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    model_config = {"env_file": ".env", "case_sensitive": True}


settings = Settings()
