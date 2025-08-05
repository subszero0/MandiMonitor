"""Configuration management for MandiMonitor Bot."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    TELEGRAM_TOKEN: str = "dummy_token_for_testing"
    PAAPI_ACCESS_KEY: str | None = None
    PAAPI_SECRET_KEY: str | None = None
    PAAPI_TAG: str | None = None
    ADMIN_USER: str = "admin"
    ADMIN_PASS: str = "changeme"
    SENTRY_DSN: str | None = None
    TIMEZONE: str = "Asia/Kolkata"
    AMAZON_COOKIES: str | None = None  # Optional cookies for enhanced scraping


try:
    settings = Settings(_env_file=".env")
except FileNotFoundError:
    # For CI/testing environments where .env might not exist
    settings = Settings()
