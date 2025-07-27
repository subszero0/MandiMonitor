"""Configuration management for MandiMonitor Bot."""

import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    TELEGRAM_TOKEN: str
    PAAPI_ACCESS_KEY: str | None = None
    PAAPI_SECRET_KEY: str | None = None
    PAAPI_TAG: str | None = None
    ADMIN_USER: str = "admin"
    ADMIN_PASS: str = "changeme"
    SENTRY_DSN: str | None = None
    TIMEZONE: str = "Asia/Kolkata"

settings = Settings(_env_file=".env") 