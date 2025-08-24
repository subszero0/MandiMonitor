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
    
    # PA-API Migration Feature Flag
    USE_NEW_PAAPI_SDK: bool = False  # Feature flag for migrating to official paapi5-python-sdk
    
    # NEW: Regional configuration for official PA-API SDK
    PAAPI_HOST: str = "webservices.amazon.in"
    PAAPI_REGION: str = "eu-west-1"
    PAAPI_MARKETPLACE: str = "www.amazon.in"
    PAAPI_LANGUAGE: str = "en_IN"
    
    # Enhanced models configuration
    ENABLE_ENHANCED_MODELS: bool = True
    JSON_FIELD_MAX_SIZE: int = 65535  # Maximum size for JSON fields
    PRICE_HISTORY_RETENTION_DAYS: int = 365  # Keep price history for 1 year
    ENRICHMENT_BATCH_SIZE: int = 10  # Batch size for data enrichment
    
    # PA-API rate limiting configuration - more conservative
    PAAPI_RATE_LIMIT_PER_SECOND: int = 1
    PAAPI_BURST_LIMIT: int = 5  # Reduced from 10 to 5
    PAAPI_BURST_WINDOW_SECONDS: int = 10


try:
    settings = Settings(_env_file=".env")
except FileNotFoundError:
    # For CI/testing environments where .env might not exist
    settings = Settings()
