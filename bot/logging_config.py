"""Logging configuration for MandiMonitor Bot."""

import logging
import sys
from pathlib import Path


def setup_dev_logging():
    """Setup logging for development environment."""

    # Create logs directory
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_dir / 'dev.log'),
            logging.FileHandler(log_dir / 'security.log', level=logging.WARNING)
        ]
    )

    # Security-specific logger
    security_logger = logging.getLogger('security')
    security_logger.setLevel(logging.WARNING)

    return logging.getLogger(__name__)


def log_security_event(event: str, details: dict = None):
    """Log security events in development."""
    security_logger = logging.getLogger('security')
    security_logger.warning(f"SECURITY: {event}", extra=details or {})


def log_auth_attempt(success: bool, username: str, ip_address: str = None):
    """Log authentication attempts."""
    event = "AUTH_SUCCESS" if success else "AUTH_FAILURE"
    details = {
        'username': username,
        'ip_address': ip_address,
        'timestamp': None  # Will be added by logging formatter
    }
    log_security_event(event, details)


def log_input_validation_failure(field: str, value: str, reason: str):
    """Log input validation failures."""
    details = {
        'field': field,
        'value_length': len(value) if value else 0,
        'reason': reason
    }
    log_security_event("INPUT_VALIDATION_FAILURE", details)
