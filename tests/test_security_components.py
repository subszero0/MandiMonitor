"""Unit and integration tests for security components."""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

# Add the bot directory to Python path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.config import DevConfig, Settings
from bot.validation import DevInputValidator
from bot.auth import check_admin_auth
from bot.logging_config import setup_dev_logging, log_security_event


class TestDevConfig:
    """Unit tests for DevConfig class."""

    def test_dev_config_initialization(self):
        """Test DevConfig initializes with correct environment."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            config = DevConfig()
            assert config.env == 'development'

    def test_dev_config_load_env_file(self):
        """Test loading environment file with valid data."""
        # Create a temporary env file
        env_content = """TELEGRAM_TOKEN=test_token_12345
PAAPI_ACCESS_KEY=test_key_123
PAAPI_SECRET_KEY=test_secret_123
ADMIN_USER=test_admin
ADMIN_PASS=test_password_123
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write(env_content)
            temp_file = Path(f.name)

        try:
            config = DevConfig()
            config._load_env_file(temp_file)

            assert config.telegram_token == 'test_token_12345'
            assert config.paapi_access_key == 'test_key_123'
            assert config.paapi_secret_key == 'test_secret_123'
            assert config.admin_user == 'test_admin'
            assert config.admin_pass == 'test_password_123'
        finally:
            temp_file.unlink()

    def test_dev_config_validation(self):
        """Test credential validation in DevConfig."""
        config = DevConfig()

        # Test valid credentials
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("TELEGRAM_TOKEN=valid_token_123456789\n")
            temp_file = Path(f.name)

        try:
            config._load_env_file(temp_file)
            assert config.telegram_token == 'valid_token_123456789'
        finally:
            temp_file.unlink()

    def test_dev_config_invalid_credentials(self):
        """Test handling of invalid credentials."""
        config = DevConfig()

        # Test invalid credentials (too short)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("TELEGRAM_TOKEN=short\n")
            temp_file = Path(f.name)

        try:
            with pytest.raises(ValueError, match="Invalid TELEGRAM_TOKEN length"):
                config._load_env_file(temp_file)
        finally:
            temp_file.unlink()


class TestDevInputValidator:
    """Unit tests for DevInputValidator class."""

    def test_validate_search_query_valid(self):
        """Test validation of valid search queries."""
        result = DevInputValidator.validate_search_query("laptop under 50000")
        assert result == "laptop under 50000"

    def test_validate_search_query_empty(self):
        """Test validation of empty search query."""
        result = DevInputValidator.validate_search_query("")
        assert result is None

    def test_validate_search_query_too_long(self):
        """Test validation of overly long search query."""
        long_query = "a" * 201
        result = DevInputValidator.validate_search_query(long_query)
        assert result is None

    def test_validate_search_query_sanitization(self):
        """Test sanitization of dangerous characters."""
        result = DevInputValidator.validate_search_query('laptop<script>alert("xss")</script>')
        assert result == "laptopscriptalertxssscript"

    def test_validate_asin_valid(self):
        """Test validation of valid ASIN."""
        result = DevInputValidator.validate_asin("B08N5WRWNW")
        assert result == "B08N5WRWNW"

    def test_validate_asin_invalid(self):
        """Test validation of invalid ASIN."""
        result = DevInputValidator.validate_asin("INVALID")
        assert result is None

    def test_validate_asin_lowercase(self):
        """Test ASIN validation converts to uppercase."""
        result = DevInputValidator.validate_asin("b08n5wrwnw")
        assert result == "B08N5WRWNW"

    def test_validate_price_range_valid(self):
        """Test validation of valid price range."""
        min_price, max_price = DevInputValidator.validate_price_range(1000, 50000)
        assert min_price == 1000
        assert max_price == 50000

    def test_validate_price_range_invalid(self):
        """Test validation of invalid price range."""
        min_price, max_price = DevInputValidator.validate_price_range(50000, 1000)
        assert min_price is None
        assert max_price is None

    def test_validate_price_range_negative(self):
        """Test validation of negative prices."""
        min_price, max_price = DevInputValidator.validate_price_range(-1000, 50000)
        assert min_price is None
        assert max_price is None


class TestAuthentication:
    """Unit tests for authentication functions."""

    @patch('bot.auth.request')
    @patch('bot.auth.DevConfig')
    def test_check_admin_auth_success(self, mock_config, mock_request):
        """Test successful admin authentication."""
        # Mock the DevConfig class
        mock_config_instance = mock_config.return_value
        mock_config_instance.admin_user = 'test_admin'
        mock_config_instance.admin_pass = 'test_pass'

        # Mock Flask request with proper authorization object
        mock_auth = type('Auth', (), {
            'username': 'test_admin',
            'password': 'test_pass'
        })()
        mock_request.authorization = mock_auth

        result = check_admin_auth()
        assert result is True

    @patch('bot.auth.request')
    @patch('bot.auth.DevConfig')
    def test_check_admin_auth_failure(self, mock_config, mock_request):
        """Test failed admin authentication."""
        mock_config_instance = mock_config.return_value
        mock_config_instance.admin_user = 'test_admin'
        mock_config_instance.admin_pass = 'test_pass'

        # Mock Flask request with proper authorization object
        mock_auth = type('Auth', (), {
            'username': 'wrong_admin',
            'password': 'wrong_pass'
        })()
        mock_request.authorization = mock_auth

        result = check_admin_auth()
        assert result is False


class TestLoggingConfig:
    """Unit tests for logging configuration."""

    @patch('bot.logging_config.Path.mkdir')
    @patch('bot.logging_config.logging.basicConfig')
    @patch('bot.logging_config.logging.FileHandler')
    @patch('bot.logging_config.logging.StreamHandler')
    def test_setup_dev_logging(self, mock_stream_handler, mock_file_handler, mock_basic_config, mock_mkdir):
        """Test logging setup configuration."""
        logger = setup_dev_logging()

        # Verify logs directory creation
        mock_mkdir.assert_called_once_with(exist_ok=True)

        # Verify basicConfig was called
        mock_basic_config.assert_called_once()

        # Verify logger was returned
        assert logger is not None

    @patch('bot.logging_config.logging.getLogger')
    def test_log_security_event(self, mock_get_logger):
        """Test security event logging."""
        mock_logger = mock_get_logger.return_value

        log_security_event("TEST_EVENT", {"detail": "test"})

        # Verify the security logger was obtained and warning was called
        mock_get_logger.assert_called_with('security')
        mock_logger.warning.assert_called_once_with("SECURITY: TEST_EVENT", extra={"detail": "test"})


class TestSecurityIntegration:
    """Integration tests for security components working together."""

    def test_full_config_loading_development(self):
        """Test full configuration loading in development environment."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            # This tests the integration in bot/config.py
            from bot.config import settings

            # Verify settings object was created
            assert settings is not None

            # Check that we have some expected attributes
            assert hasattr(settings, 'telegram_token')

    def test_environment_file_loading_integration(self):
        """Test that environment files are loaded correctly."""
        # Verify .env.dev exists
        env_dev_path = Path('.env.dev')
        assert env_dev_path.exists()

        # Verify .env.test exists
        env_test_path = Path('.env.test')
        assert env_test_path.exists()

        # Read and verify content structure
        with open(env_dev_path, 'r') as f:
            content = f.read()
            assert 'TELEGRAM_TOKEN=' in content
            assert 'PAAPI_ACCESS_KEY=' in content
            assert 'ENVIRONMENT=development' in content

    def test_gitignore_excludes_env_files(self):
        """Test that environment files are properly excluded from git."""
        gitignore_path = Path('.gitignore')
        assert gitignore_path.exists()

        with open(gitignore_path, 'r') as f:
            content = f.read()
            assert '.env.dev' in content
            assert '.env.test' in content
            assert '.env.local' in content


class TestContainerSecurity:
    """Tests for container security implementation."""

    def test_dockerfile_dev_exists(self):
        """Test that Dockerfile.dev exists."""
        dockerfile_path = Path('Dockerfile.dev')
        assert dockerfile_path.exists()

    def test_dockerfile_dev_content(self):
        """Test Dockerfile.dev has security features."""
        dockerfile_path = Path('Dockerfile.dev')

        with open(dockerfile_path, 'r') as f:
            content = f.read()

            # Check for non-root user creation
            assert 'useradd' in content
            assert 'devuser' in content

            # Check for USER directive
            assert 'USER devuser' in content

            # Check for proper permissions
            assert 'chown' in content

    def test_docker_compose_security(self):
        """Test docker-compose.yml has security configuration."""
        compose_path = Path('docker-compose.yml')

        with open(compose_path, 'r') as f:
            content = f.read()

            # Check for Dockerfile.dev usage
            assert 'Dockerfile.dev' in content

            # Check for environment variable
            assert 'ENVIRONMENT=development' in content

            # Check for user specification
            assert 'user:' in content
