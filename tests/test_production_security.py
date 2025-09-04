"""Production security testing framework."""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the bot directory to Python path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_production_config_validation():
    """Test production configuration validation."""
    print("🧪 Testing production configuration validation...")

    # Create temporary production config
    prod_config_content = """ENVIRONMENT=production
TELEGRAM_TOKEN=prod_telegram_token_very_long_and_secure_123456789
PAAPI_ACCESS_KEY=prod_paapi_access_key_secure_and_long_123456789
PAAPI_SECRET_KEY=prod_paapi_secret_key_very_secure_and_long_123456789
ADMIN_USER=prod_admin
ADMIN_PASS=very_secure_production_password_123456789!
SECRET_KEY=very_long_secret_key_for_production_32_chars_minimum
DEBUG=false
LOG_LEVEL=WARNING
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.env.prod', delete=False) as f:
        f.write(prod_config_content)
        temp_config = Path(f.name)

    try:
        # Copy the config to expected location
        prod_env_path = Path('.env.prod')
        with open(temp_config, 'r') as src, open(prod_env_path, 'w') as dst:
            dst.write(src.read())

        # Test production config loading
        with patch.dict(os.environ, {'ENVIRONMENT': 'production'}):
            from bot.config_prod import ProdSecurityConfig

            config = ProdSecurityConfig()
            assert hasattr(config, 'prod_telegram_token')
            assert hasattr(config, 'prod_admin_pass')
            assert config.prod_admin_user == 'prod_admin'

        print("✅ Production configuration validation passed")
        return True

    except Exception as e:
        print(f"❌ Production configuration test failed: {e}")
        return False

    finally:
        # Cleanup
        if temp_config.exists():
            temp_config.unlink()
        if prod_env_path.exists():
            prod_env_path.unlink()


def test_production_security_headers():
    """Test production security headers configuration."""
    print("🧪 Testing production security headers...")

    try:
        from bot.config_prod import ProdSecurityConfig

        # Mock production environment
        with patch.dict(os.environ, {'ENVIRONMENT': 'production'}):
            # Create minimal prod config for testing
            prod_config_content = """ENVIRONMENT=production
TELEGRAM_TOKEN=test_prod_token_123456789012345678901234567890
PAAPI_ACCESS_KEY=test_prod_key_123456789012345678901234567890
PAAPI_SECRET_KEY=test_prod_secret_123456789012345678901234567890
ADMIN_USER=test_admin
ADMIN_PASS=test_prod_password_123456789!
SECRET_KEY=test_prod_secret_key_32_chars_minimum_123
"""

            with open('.env.prod', 'w') as f:
                f.write(prod_config_content)

            config = ProdSecurityConfig()

            headers = config.get_secure_headers()
            assert 'X-Content-Type-Options' in headers
            assert 'Strict-Transport-Security' in headers
            assert 'Content-Security-Policy' in headers

        print("✅ Production security headers test passed")
        return True

    except Exception as e:
        print(f"❌ Security headers test failed: {e}")
        return False

    finally:
        if Path('.env.prod').exists():
            Path('.env.prod').unlink()


def test_production_rate_limiting():
    """Test production rate limiting configuration."""
    print("🧪 Testing production rate limiting...")

    try:
        from bot.config_prod import ProdSecurityConfig

        with patch.dict(os.environ, {'ENVIRONMENT': 'production'}):
            prod_config_content = """ENVIRONMENT=production
TELEGRAM_TOKEN=test_prod_token_123456789012345678901234567890
PAAPI_ACCESS_KEY=test_prod_key_123456789012345678901234567890
PAAPI_SECRET_KEY=test_prod_secret_123456789012345678901234567890
ADMIN_USER=test_admin
ADMIN_PASS=test_prod_password_123456789!
SECRET_KEY=test_prod_secret_key_32_chars_minimum_123
"""

            with open('.env.prod', 'w') as f:
                f.write(prod_config_content)

            config = ProdSecurityConfig()
            limits = config.get_rate_limits()

            assert limits['telegram_messages'] <= 30  # Reasonable limit
            assert limits['api_requests'] <= 100
            assert limits['admin_actions'] <= 10

        print("✅ Production rate limiting test passed")
        return True

    except Exception as e:
        print(f"❌ Rate limiting test failed: {e}")
        return False

    finally:
        if Path('.env.prod').exists():
            Path('.env.prod').unlink()


def test_production_dockerfile_security():
    """Test production Dockerfile security features."""
    print("🧪 Testing production Dockerfile security...")

    dockerfile_path = Path('Dockerfile.prod')
    if not dockerfile_path.exists():
        print("❌ Dockerfile.prod not found")
        return False

    try:
        with open(dockerfile_path, 'r') as f:
            content = f.read()

        # Check for security features
        security_checks = [
            'useradd' in content,  # Non-root user creation
            'USER appuser' in content,  # Switch to non-root user
            'HEALTHCHECK' in content,  # Health check
            'curl' in content,  # Minimal packages only
            '--no-cache-dir' in content,  # No cache for smaller image
        ]

        if all(security_checks):
            print("✅ Production Dockerfile security features verified")
            return True
        else:
            print("❌ Missing security features in Dockerfile.prod")
            return False

    except Exception as e:
        print(f"❌ Dockerfile security test failed: {e}")
        return False


def test_production_compose_security():
    """Test production docker-compose security configuration."""
    print("🧪 Testing production docker-compose security...")

    compose_path = Path('docker-compose.prod.yml')
    if not compose_path.exists():
        print("❌ docker-compose.prod.yml not found")
        return False

    try:
        with open(compose_path, 'r') as f:
            content = f.read()

        # Check for security features
        security_checks = [
            'Dockerfile.prod' in content,  # Uses secure Dockerfile
            'no-new-privileges:true' in content,  # Security options
            'read_only: true' in content,  # Read-only root filesystem
            'tmpfs:' in content,  # Temporary filesystem
            'healthcheck:' in content,  # Health checks
        ]

        if all(security_checks):
            print("✅ Production docker-compose security features verified")
            return True
        else:
            print("❌ Missing security features in docker-compose.prod.yml")
            return False

    except Exception as e:
        print(f"❌ Docker compose security test failed: {e}")
        return False


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


def test_production_monitoring_config():
    """Test production monitoring configuration."""
    print("🧪 Testing production monitoring configuration...")

    try:
        from bot.config_prod import ProdSecurityConfig

        with patch.dict(os.environ, {'ENVIRONMENT': 'production'}):
            prod_config_content = """ENVIRONMENT=production
TELEGRAM_TOKEN=test_prod_token_123456789012345678901234567890
PAAPI_ACCESS_KEY=test_prod_key_123456789012345678901234567890
PAAPI_SECRET_KEY=test_prod_secret_123456789012345678901234567890
ADMIN_USER=test_admin
ADMIN_PASS=test_prod_password_123456789!
SECRET_KEY=test_prod_secret_key_32_chars_minimum_123
"""

            with open('.env.prod', 'w') as f:
                f.write(prod_config_content)

            config = ProdSecurityConfig()
            monitoring = config.get_monitoring_config()

            assert monitoring['metrics_enabled'] is True
            assert monitoring['health_checks_enabled'] is True
            assert monitoring['error_reporting_enabled'] is True

        print("✅ Production monitoring configuration test passed")
        return True

    except Exception as e:
        print(f"❌ Monitoring configuration test failed: {e}")
        return False

    finally:
        if Path('.env.prod').exists():
            Path('.env.prod').unlink()


def run_production_security_tests():
    """Run all production security tests."""
    print("🚀 Starting Production Security Tests")
    print("=" * 60)

    tests = [
        test_production_config_validation,
        test_production_security_headers,
        test_production_rate_limiting,
        test_production_dockerfile_security,
        test_production_compose_security,
        test_production_environment_isolation,
        test_production_monitoring_config,
    ]

    passed = 0
    total = len(tests)

    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test_func.__name__} crashed: {e}")
        print()

    print("=" * 60)
    print(f"🎯 Production Security Test Results: {passed}/{total} passed")

    if passed == total:
        print("🎉 All production security tests PASSED!")
        print("✅ Production deployment is ready!")
        return True
    else:
        print(f"❌ {total - passed} production security tests FAILED!")
        print("⚠️  Production deployment needs attention before proceeding!")
        return False


if __name__ == "__main__":
    success = run_production_security_tests()
    sys.exit(0 if success else 1)
