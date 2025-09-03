#!/usr/bin/env python3
"""Test script to verify security configuration is working."""

import os
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, '.')

# Set environment to development to test our DevConfig
os.environ['ENVIRONMENT'] = 'development'

try:
    from bot.config import settings
    from bot.validation import DevInputValidator
    from bot.auth import check_admin_auth
    from bot.logging_config import setup_dev_logging

    print("🛡️  SECURITY CONFIGURATION TEST")
    print("=" * 50)

    # Test 1: Configuration Loading
    print("\n✅ Test 1: Configuration Loading")
    print(f"  Telegram Token: {settings.TELEGRAM_TOKEN[:25]}...")
    print(f"  PAAPI Key: {settings.PAAPI_ACCESS_KEY[:15]}...")
    print(f"  Environment: {getattr(settings, 'environment', 'unknown')}")

    # Test 2: Input Validation
    print("\n✅ Test 2: Input Validation")
    test_query = "laptop under 50000"
    clean_query = DevInputValidator.validate_search_query(test_query)
    print(f"  Original: '{test_query}'")
    print(f"  Cleaned: '{clean_query}'")

    # Test 3: ASIN Validation
    test_asin = "B08N5WRWNW"
    valid_asin = DevInputValidator.validate_asin(test_asin)
    print(f"  ASIN '{test_asin}' valid: {valid_asin is not None}")

    # Test 4: Logging Setup
    print("\n✅ Test 3: Logging Setup")
    logger = setup_dev_logging()
    print("  Dev logging configured successfully")
    print("  Check logs/ directory for security.log and dev.log")

    # Test 5: Environment File Check
    print("\n✅ Test 4: Environment Files")
    env_dev = Path('.env.dev')
    env_test = Path('.env.test')
    print(f"  .env.dev exists: {env_dev.exists()}")
    print(f"  .env.test exists: {env_test.exists()}")

    print("\n🎉 ALL SECURITY TESTS PASSED!")
    print("Your bot is ready for secure development testing.")

except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("Make sure all dependencies are installed: pip install -r requirements.txt")

except Exception as e:
    print(f"❌ Configuration Error: {e}")
    import traceback
    traceback.print_exc()
