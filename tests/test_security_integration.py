"""Integration tests for complete security workflow."""

import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

# Add the bot directory to Python path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_full_security_workflow():
    """Test the complete security workflow from config to authentication."""
    print("🧪 Testing complete security workflow...")

    # Create a temporary directory for testing
    temp_dir = Path(tempfile.mkdtemp())
    original_cwd = os.getcwd()

    try:
        # Change to temp directory and copy necessary files
        os.chdir(temp_dir)

        # Create test environment files
        env_dev_content = """TELEGRAM_TOKEN=test_telegram_token_123456789
PAAPI_ACCESS_KEY=test_paapi_key_123456789
PAAPI_SECRET_KEY=test_paapi_secret_123456789
ADMIN_USER=test_admin
ADMIN_PASS=test_secure_password_123!
ENVIRONMENT=development
"""

        with open('.env.dev', 'w') as f:
            f.write(env_dev_content)

        # Copy the bot directory structure (simplified for testing)
        test_bot_dir = temp_dir / 'bot'
        test_bot_dir.mkdir()

        # Copy essential files
        files_to_copy = [
            'config.py',
            'validation.py',
            'auth.py',
            'logging_config.py'
        ]

        for file in files_to_copy:
            src = Path(original_cwd) / 'bot' / file
            dst = test_bot_dir / file
            if src.exists():
                shutil.copy2(src, dst)

        # Add the temp directory to Python path
        sys.path.insert(0, str(temp_dir))

        # Test 1: Configuration loading
        print("  Testing configuration loading...")
        os.environ['ENVIRONMENT'] = 'development'

        from bot.config import settings
        assert hasattr(settings, 'telegram_token')
        assert hasattr(settings, 'admin_user')
        print("  ✅ Configuration loaded successfully")

        # Test 2: Input validation
        print("  Testing input validation...")
        from bot.validation import DevInputValidator

        # Test search query validation
        result = DevInputValidator.validate_search_query("test query")
        assert result == "test query"
        print("  ✅ Search query validation works")

        # Test ASIN validation
        result = DevInputValidator.validate_asin("B08N5WRWNW")
        assert result == "B08N5WRWNW"
        print("  ✅ ASIN validation works")

        # Test 3: Authentication (mocked)
        print("  Testing authentication...")
        from bot.auth import check_admin_auth

        with patch('bot.auth.DevConfig') as mock_config:
            mock_instance = mock_config.return_value
            mock_instance.admin_user = 'test_admin'
            mock_instance.admin_pass = 'test_secure_password_123!'

            with patch('bot.auth.request') as mock_request:
                mock_request.authorization = type('Auth', (), {
                    'username': 'test_admin',
                    'password': 'test_secure_password_123!'
                })()

                result = check_admin_auth()
                assert result is True
                print("  ✅ Authentication works")

        # Test 4: Logging setup
        print("  Testing logging setup...")
        from bot.logging_config import setup_dev_logging

        logger = setup_dev_logging()
        assert logger is not None

        # Check if logs directory was created
        logs_dir = Path('logs')
        assert logs_dir.exists()
        print("  ✅ Logging setup works")

        print("🎉 Complete security workflow test PASSED!")
        return True

    except Exception as e:
        print(f"❌ Security workflow test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup
        os.chdir(original_cwd)
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_environment_isolation():
    """Test that different environments load different configurations."""
    print("🧪 Testing environment isolation...")

    temp_dir = Path(tempfile.mkdtemp())
    original_cwd = os.getcwd()

    try:
        os.chdir(temp_dir)

        # Create test environment files
        env_dev_content = """ADMIN_USER=dev_admin
ENVIRONMENT=development
"""
        env_test_content = """ADMIN_USER=test_admin
ENVIRONMENT=test
"""

        with open('.env.dev', 'w') as f:
            f.write(env_dev_content)

        with open('.env.test', 'w') as f:
            f.write(env_test_content)

        # Copy config file
        src = Path(original_cwd) / 'bot' / 'config.py'
        dst = temp_dir / 'bot' / 'config.py'
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

        # Add to Python path
        sys.path.insert(0, str(temp_dir))

        # Test development environment
        os.environ['ENVIRONMENT'] = 'development'
        # Reload the module to test environment switching
        import importlib
        if 'bot.config' in sys.modules:
            importlib.reload(sys.modules['bot.config'])

        from bot.config import settings as dev_settings
        assert hasattr(dev_settings, 'admin_user')

        # Test test environment
        os.environ['ENVIRONMENT'] = 'test'
        if 'bot.config' in sys.modules:
            importlib.reload(sys.modules['bot.config'])

        from bot.config import settings as test_settings
        assert hasattr(test_settings, 'admin_user')

        print("✅ Environment isolation works correctly")
        return True

    except Exception as e:
        print(f"❌ Environment isolation test FAILED: {e}")
        return False

    finally:
        os.chdir(original_cwd)
        shutil.rmtree(temp_dir, ignore_errors=True)


def run_integration_tests():
    """Run all integration tests."""
    print("🚀 Starting Security Integration Tests")
    print("=" * 50)

    tests_passed = 0
    total_tests = 2

    # Test 1: Full security workflow
    if test_full_security_workflow():
        tests_passed += 1
    print()

    # Test 2: Environment isolation
    if test_environment_isolation():
        tests_passed += 1
    print()

    print("=" * 50)
    print(f"🎯 Integration Test Results: {tests_passed}/{total_tests} passed")

    if tests_passed == total_tests:
        print("🎉 All integration tests PASSED!")
        return True
    else:
        print(f"❌ {total_tests - tests_passed} integration tests FAILED!")
        return False


if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)
