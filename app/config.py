"""Application configuration using Pydantic settings."""

from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Database Configuration
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://livechat_user:livechat_pass@localhost:5432/livechat_sync",
        description="PostgreSQL database URL with asyncpg driver"
    )

    # Redis Configuration
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )

    # LiveChat API Configuration
    LIVECHAT_CLIENT_ID: str = Field(default="", description="LiveChat OAuth client ID")
    LIVECHAT_CLIENT_SECRET: str = Field(default="", description="LiveChat OAuth client secret")
    LIVECHAT_ACCESS_TOKEN: str = Field(default="", description="LiveChat API access token")
    LIVECHAT_WEBHOOK_SECRET: str = Field(default="", description="LiveChat webhook signature secret")
    LIVECHAT_API_URL: str = Field(
        default="https://api.livechatinc.com/v3.5",
        description="LiveChat API base URL"
    )

    # RingCentral API Configuration
    RINGCENTRAL_CLIENT_ID: str = Field(default="", description="RingCentral OAuth client ID")
    RINGCENTRAL_CLIENT_SECRET: str = Field(default="", description="RingCentral OAuth client secret")
    RINGCENTRAL_JWT_TOKEN: str = Field(default="", description="RingCentral JWT token")
    RINGCENTRAL_WEBHOOK_SECRET: str = Field(default="", description="RingCentral webhook signature secret")
    RINGCENTRAL_API_URL: str = Field(
        default="https://platform.ringcentral.com",
        description="RingCentral API base URL"
    )
    RINGCENTRAL_SERVER_URL: str = Field(
        default="https://platform.ringcentral.com",
        description="RingCentral server URL"
    )

    # Application Configuration
    APP_ENV: str = Field(default="development", description="Application environment")
    APP_DEBUG: bool = Field(default=True, description="Enable debug mode")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")

    # Webhook Configuration
    WEBHOOK_BASE_URL: str = Field(
        default="http://localhost:8000",
        description="Base URL for webhook endpoints"
    )

    # Retry Configuration
    MAX_RETRIES: int = Field(default=3, description="Maximum retry attempts for API calls")
    RETRY_BACKOFF_FACTOR: int = Field(default=2, description="Exponential backoff factor")

    # Celery Configuration
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Celery broker URL"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/0",
        description="Celery result backend URL"
    )

    # Security
    SECRET_KEY: str = Field(
        default="change-me-in-production",
        description="Secret key for signing"
    )

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}")
        return v_upper

    @field_validator("APP_ENV")
    @classmethod
    def validate_app_env(cls, v: str) -> str:
        """Validate application environment."""
        valid_envs = ["development", "staging", "production", "test"]
        v_lower = v.lower()
        if v_lower not in valid_envs:
            raise ValueError(f"APP_ENV must be one of {valid_envs}")
        return v_lower


# Create global settings instance
settings = Settings()
