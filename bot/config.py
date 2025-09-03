"""Configuration management for MandiMonitor Bot."""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings


class DevConfig:
    """Development configuration with basic security."""

    def __init__(self):
        self.env = os.getenv('ENVIRONMENT', 'development')

        # Load environment-specific config
        if self.env == 'development':
            self._load_dev_config()
        elif self.env == 'test':
            self._load_test_config()
        else:
            self._load_prod_config()

    def _load_dev_config(self):
        """Load development config with basic protection."""
        env_file = Path('.env.dev')
        if env_file.exists():
            self._load_env_file(env_file)
        else:
            # Fallback to basic dev values
            self.telegram_token = "dev_token_placeholder"
            self.paapi_key = "dev_key_placeholder"

    def _load_test_config(self):
        """Load test config with basic protection."""
        env_file = Path('.env.test')
        if env_file.exists():
            self._load_env_file(env_file)
        else:
            # Fallback to basic test values
            self.telegram_token = "test_token_placeholder"
            self.paapi_key = "test_key_placeholder"

    def _load_prod_config(self):
        """Load production config from main .env."""
        env_file = Path('.env')
        if env_file.exists():
            self._load_env_file(env_file)
        else:
            raise ValueError("Production config requires .env file")

    def _load_env_file(self, file_path: Path):
        """Load environment file with basic validation."""
        with open(file_path) as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    try:
                        key, value = line.strip().split('=', 1)
                        key_lower = key.lower()

                        # Basic validation for sensitive keys
                        if key in ['TELEGRAM_TOKEN', 'PAAPI_ACCESS_KEY', 'PAAPI_SECRET_KEY']:
                            if len(value) < 10:  # Basic validation
                                raise ValueError(f"Invalid {key} length: must be at least 10 characters")
                            if 'placeholder' in value.lower() and self.env in ['development', 'test']:
                                print(f"WARNING: Using placeholder value for {key} in {self.env} environment")
                        elif key in ['ADMIN_PASS']:
                            if len(value) < 12 and self.env == 'development':
                                print(f"WARNING: Admin password too short for {self.env} environment")

                        setattr(self, key_lower, value)
                    except ValueError as e:
                        print(f"Error parsing {file_path}: {e}")
                        raise

    def _validate_dev_admin_creds(self):
        """Basic validation for dev admin credentials."""
        if len(getattr(self, 'admin_pass', '')) < 12:
            print("WARNING: Admin password too short for dev")
        if getattr(self, 'admin_user', '') == 'admin':
            print("WARNING: Using default admin username")


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
    
    # PA-API Configuration (using official paapi5-python-sdk only)
    
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


# Initialize configuration based on environment
env = os.getenv('ENVIRONMENT', 'development')

if env in ['development', 'test']:
    # Use DevConfig for development and test environments
    try:
        dev_config = DevConfig()
        # Create a settings-like object from DevConfig for compatibility
        class DevSettings:
            def __init__(self, dev_config):
                # Copy all attributes from dev_config
                for attr in dir(dev_config):
                    if not attr.startswith('_'):
                        setattr(self, attr, getattr(dev_config, attr))

        settings = DevSettings(dev_config)
    except Exception as e:
        print(f"Error loading dev config: {e}")
        settings = Settings()  # Fallback
else:
    # Use production settings
    try:
        settings = Settings(_env_file=".env")
    except FileNotFoundError:
        # For CI/testing environments where .env might not exist
        settings = Settings()
