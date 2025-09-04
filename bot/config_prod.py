"""Production security configuration for MandiMonitor Bot."""

import os
import secrets
from pathlib import Path
from typing import Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class ProdSecurityConfig:
    """Production security configuration with enhanced security measures."""

    def __init__(self):
        # Validate we're in production environment
        env = os.getenv('ENVIRONMENT', 'development')
        if env != 'production':
            raise RuntimeError("ProdSecurityConfig should only be used in production environment")

        # Load production environment file
        env_file = Path('.env.prod')
        if not env_file.exists():
            raise FileNotFoundError("Production environment file (.env.prod) not found")

        self._load_prod_config(env_file)

        # Validate production security requirements
        self._validate_prod_security()

    def _load_prod_config(self, env_file: Path):
        """Load production configuration with enhanced validation."""
        with open(env_file, 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    try:
                        key, value = line.strip().split('=', 1)

                        # Enhanced validation for production
                        if key in ['TELEGRAM_TOKEN', 'PAAPI_ACCESS_KEY', 'PAAPI_SECRET_KEY']:
                            if not value or len(value) < 20:
                                raise ValueError(f"Production {key} is too short or empty")
                            if 'placeholder' in value.lower():
                                raise ValueError(f"Production {key} cannot contain placeholder values")

                        elif key in ['ADMIN_PASS']:
                            if len(value) < 16:
                                raise ValueError("Production admin password must be at least 16 characters")

                        elif key in ['SECRET_KEY']:
                            if not value or len(value) < 32:
                                raise ValueError("Production SECRET_KEY must be at least 32 characters")

                        # Set attribute with production prefix for clarity
                        setattr(self, f"prod_{key.lower()}", value.strip())

                    except ValueError as e:
                        print(f"❌ PRODUCTION SECURITY ERROR: {e}")
                        raise

    def _validate_prod_security(self):
        """Validate production security requirements."""
        required_fields = [
            'prod_telegram_token',
            'prod_paapi_access_key',
            'prod_paapi_secret_key',
            'prod_admin_user',
            'prod_admin_pass',
            'prod_secret_key'
        ]

        missing_fields = []
        for field in required_fields:
            if not hasattr(self, field) or not getattr(self, field):
                missing_fields.append(field)

        if missing_fields:
            raise ValueError(f"Missing required production fields: {missing_fields}")

        # Additional production validations
        if getattr(self, 'prod_debug', 'false').lower() == 'true':
            print("⚠️  WARNING: DEBUG mode is enabled in production!")

        print("✅ Production security configuration validated")

    def get_secure_headers(self):
        """Get production security headers."""
        return {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Content-Security-Policy': "default-src 'self'",
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        }

    def get_rate_limits(self):
        """Get production rate limiting configuration."""
        return {
            'telegram_messages': 30,  # per minute
            'api_requests': 100,     # per minute
            'admin_actions': 10      # per minute
        }

    def get_monitoring_config(self):
        """Get production monitoring configuration."""
        return {
            'metrics_enabled': True,
            'health_checks_enabled': True,
            'error_reporting_enabled': True,
            'performance_monitoring': True
        }


class ProductionSettings(BaseSettings):
    """Production settings with security hardening."""

    # Environment validation
    ENVIRONMENT: str = "development"

    # Security settings
    SECRET_KEY: str = Field(..., min_length=32)
    DEBUG: bool = False
    LOG_LEVEL: str = "WARNING"

    # Security headers
    SECURE_HEADERS: bool = True
    HSTS_MAX_AGE: int = 31536000
    FORCE_HTTPS: bool = True

    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    MAX_REQUESTS_PER_MINUTE: int = 100

    # Monitoring
    SENTRY_DSN: Optional[str] = None
    METRICS_ENABLED: bool = True
    HEALTH_CHECK_ENABLED: bool = True

    # Database security
    DB_SSL_MODE: str = "require"
    DB_CONNECTION_TIMEOUT: int = 30

    class Config:
        env_file = ".env.prod"
        case_sensitive = True
        extra = "allow"  # Allow extra fields for flexibility

    @validator('SECRET_KEY')
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError('SECRET_KEY must be at least 32 characters long')
        return v

    @validator('LOG_LEVEL')
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'LOG_LEVEL must be one of {valid_levels}')
        return v.upper()


# Global production configuration instances
try:
    if os.getenv('ENVIRONMENT') == 'production':
        prod_security = ProdSecurityConfig()
        prod_settings = ProductionSettings()
        print("🔒 Production security configuration loaded successfully")
    else:
        prod_security = None
        prod_settings = None
        print("ℹ️  Production security not loaded (not in production environment)")
except Exception as e:
    print(f"❌ Failed to load production configuration: {e}")
    prod_security = None
    prod_settings = None
