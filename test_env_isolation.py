#!/usr/bin/env python3
"""Test environment isolation separately."""

import os
import sys
from pathlib import Path
from unittest.mock import patch

# Add the bot directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_production_environment_isolation():
    """Test that production environment is properly isolated."""
    print("🧪 Testing production environment isolation...")

    # Create test config file first
    prod_config_content = """ENVIRONMENT=production
TELEGRAM_TOKEN=test_prod_token_123456789012345678901234567890
PAAPI_ACCESS_KEY=test_prod_key_123456789012345678901234567890
PAAPI_SECRET_KEY=test_prod_secret_123456789012345678901234567890
ADMIN_USER=test_admin
ADMIN_PASS=test_prod_password_123456789!
SECRET_KEY=test_prod_secret_key_32_chars_minimum_123
"""

    try:
        # Test that production config requires ENVIRONMENT=production
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            with open('.env.prod', 'w') as f:
                f.write(prod_config_content)

            try:
                from bot.config_prod import ProdSecurityConfig
                ProdSecurityConfig()
                print("❌ Production config should not load in non-production environment")
                return False
            except RuntimeError:
                print("✅ Production config correctly rejects non-production environment")

        # Test that production config loads in production environment
        with patch.dict(os.environ, {'ENVIRONMENT': 'production'}):
            try:
                from bot.config_prod import ProdSecurityConfig
                config = ProdSecurityConfig()
                print("✅ Production config loads correctly in production environment")
                return True

            except Exception as e:
                print(f"❌ Production config failed to load: {e}")
                return False

    finally:
        if Path('.env.prod').exists():
            Path('.env.prod').unlink()

if __name__ == "__main__":
    result = test_production_environment_isolation()
    print(f"\nTest result: {'PASSED' if result else 'FAILED'}")
    sys.exit(0 if result else 1)
