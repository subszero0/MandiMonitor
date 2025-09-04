"""Simple authentication utilities for MandiMonitor Bot."""

from flask import request, abort
from bot.config import DevConfig


def check_admin_auth():
    """Simple admin authentication for dev."""
    auth = request.authorization
    if not auth:
        return False

    config = DevConfig()
    return (auth.username == getattr(config, 'admin_user', None) and
            auth.password == getattr(config, 'admin_pass', None))


def require_admin_auth():
    """Require admin authentication for protected routes."""
    if not check_admin_auth():
        abort(401, "Authentication required")


def log_security_event(event: str, details: dict = None):
    """Log security events in development."""
    import logging
    security_logger = logging.getLogger('security')
    security_logger.warning(f"SECURITY: {event}", extra=details or {})
