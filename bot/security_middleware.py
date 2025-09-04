"""Security middleware and utilities for MandiMonitor.

This module provides security-focused middleware, decorators, and utilities
to protect against common web vulnerabilities and attacks.
"""

import time
import hashlib
import hmac
import secrets
from functools import wraps
from typing import Dict, Any, Optional, Callable, List
from urllib.parse import urlparse
import logging

from flask import request, g, abort, Response

from .logging_config import SecurityEventLogger
from .api_rate_limiter import check_admin_access_rate_limit, check_user_input_rate_limit

logger = logging.getLogger(__name__)
security_logger = SecurityEventLogger()


class SecurityMiddleware:
    """Security middleware collection for Flask applications."""

    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Initialize middleware with Flask app."""
        app.before_request(self.before_request)
        app.after_request(self.after_request)

        # Register error handlers
        app.register_error_handler(400, self.handle_bad_request)
        app.register_error_handler(401, self.handle_unauthorized)
        app.register_error_handler(403, self.handle_forbidden)
        app.register_error_handler(429, self.handle_rate_limit)

    def before_request(self):
        """Execute security checks before each request."""
        # Store request start time for performance monitoring
        g.request_start_time = time.time()

        # Get client information
        client_ip = self._get_client_ip()
        user_agent = request.headers.get('User-Agent', '')
        g.client_ip = client_ip
        g.user_agent = user_agent

        # Security headers validation
        self._validate_security_headers()

        # Request size limits
        self._check_request_size()

        # Suspicious pattern detection
        if self._detect_suspicious_patterns():
            security_logger.log_security_event(
                "SUSPICIOUS_REQUEST_DETECTED",
                "medium",
                {
                    'path': request.path,
                    'method': request.method,
                    'user_agent': user_agent[:100]
                },
                None,
                client_ip
            )
            abort(400, "Invalid request")

    def after_request(self, response):
        """Execute security measures after each request."""
        # Add comprehensive security headers
        response = self._add_security_headers(response)

        # Log request completion
        duration = time.time() - getattr(g, 'request_start_time', time.time())

        # Log slow requests
        if duration > 5.0:
            security_logger.log_security_event(
                "SLOW_REQUEST",
                "low",
                {
                    'path': request.path,
                    'method': request.method,
                    'duration': duration,
                    'status_code': response.status_code
                },
                getattr(g, 'username', None),
                getattr(g, 'client_ip', None)
            )

        return response

    def _get_client_ip(self) -> str:
        """Get real client IP address with proxy support."""
        # Check for X-Forwarded-For header (behind proxy/load balancer)
        x_forwarded_for = request.headers.get('X-Forwarded-For')
        if x_forwarded_for:
            # Take the first IP if multiple (most recent proxy)
            return x_forwarded_for.split(',')[0].strip()

        # Check for X-Real-IP header
        x_real_ip = request.headers.get('X-Real-IP')
        if x_real_ip:
            return x_real_ip

        # Check for Cloudflare headers
        cf_connecting_ip = request.headers.get('CF-Connecting-IP')
        if cf_connecting_ip:
            return cf_connecting_ip

        # Fallback to remote address
        return request.remote_addr or 'unknown'

    def _validate_security_headers(self):
        """Validate important security headers."""
        # Check for suspicious user agents
        user_agent = request.headers.get('User-Agent', '').lower()
        suspicious_agents = [
            'sqlmap', 'nmap', 'nikto', 'dirbuster', 'gobuster',
            'wpscan', 'joomlavs', 'drupal', 'acunetix'
        ]

        for agent in suspicious_agents:
            if agent in user_agent:
                security_logger.log_security_event(
                    "SUSPICIOUS_USER_AGENT",
                    "high",
                    {
                        'user_agent': user_agent[:200],
                        'path': request.path
                    },
                    None,
                    self._get_client_ip()
                )
                abort(403, "Access denied")

    def _check_request_size(self):
        """Check request size limits."""
        # Limit request body size
        if request.content_length and request.content_length > 10 * 1024 * 1024:  # 10MB
            security_logger.log_security_event(
                "REQUEST_TOO_LARGE",
                "medium",
                {
                    'content_length': request.content_length,
                    'path': request.path
                },
                None,
                self._get_client_ip()
            )
            abort(413, "Request too large")

    def _detect_suspicious_patterns(self) -> bool:
        """Detect suspicious patterns in request."""
        # Check URL for suspicious patterns
        url = request.url.lower()
        suspicious_patterns = [
            '../../../', '..\\..\\', '%2e%2e%2f', '%2e%2e/',
            '<script', 'javascript:', 'vbscript:', 'onload=',
            'union select', '1=1', 'or 1=1', 'xp_cmdshell'
        ]

        for pattern in suspicious_patterns:
            if pattern in url:
                return True

        # Check query parameters for suspicious content
        for key, value in request.args.items():
            if isinstance(value, str):
                value_lower = value.lower()
                for pattern in suspicious_patterns:
                    if pattern in value_lower:
                        return True

        return False

    def _add_security_headers(self, response: Response) -> Response:
        """Add comprehensive security headers to response."""
        # Content Security Policy
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        response.headers['Content-Security-Policy'] = csp

        # Security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'

        # HSTS (only for HTTPS)
        if request.is_secure:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'

        # Remove server header to avoid information disclosure
        response.headers.pop('Server', None)

        return response

    def handle_bad_request(self, error):
        """Handle 400 Bad Request errors."""
        security_logger.log_security_event(
            "BAD_REQUEST",
            "low",
            {
                'error': str(error),
                'path': request.path,
                'method': request.method
            },
            None,
            self._get_client_ip()
        )
        return {"error": "Bad request", "code": 400}, 400

    def handle_unauthorized(self, error):
        """Handle 401 Unauthorized errors."""
        security_logger.log_security_event(
            "UNAUTHORIZED_ACCESS",
            "medium",
            {
                'error': str(error),
                'path': request.path,
                'method': request.method
            },
            None,
            self._get_client_ip()
        )
        return {"error": "Unauthorized", "code": 401}, 401

    def handle_forbidden(self, error):
        """Handle 403 Forbidden errors."""
        security_logger.log_security_event(
            "FORBIDDEN_ACCESS",
            "high",
            {
                'error': str(error),
                'path': request.path,
                'method': request.method
            },
            None,
            self._get_client_ip()
        )
        return {"error": "Forbidden", "code": 403}, 403

    def handle_rate_limit(self, error):
        """Handle 429 Rate Limit errors."""
        security_logger.log_security_event(
            "RATE_LIMIT_TRIGGERED",
            "medium",
            {
                'error': str(error),
                'path': request.path,
                'method': request.method
            },
            None,
            self._get_client_ip()
        )
        return {"error": "Rate limit exceeded", "code": 429}, 429


# Security decorators
def require_rate_limit(limit_type: str = "user_input"):
    """Decorator to enforce rate limiting on endpoints."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = SecurityMiddleware()._get_client_ip()

            # Choose appropriate rate limiter
            if limit_type == "admin":
                rate_limit_result = check_admin_access_rate_limit(client_ip)
            else:
                # Use user input rate limiter by default
                rate_limit_result = check_user_input_rate_limit(client_ip)

            if not rate_limit_result.allowed:
                security_logger.log_security_event(
                    "RATE_LIMIT_EXCEEDED",
                    "high",
                    {
                        'limit_type': limit_type,
                        'retry_after': rate_limit_result.retry_after
                    },
                    None,
                    client_ip
                )
                abort(429, f"Rate limit exceeded. Try again in {rate_limit_result.retry_after:.0f} seconds")

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_secure_headers(required_headers: List[str] = None):
    """Decorator to require specific security headers."""
    if required_headers is None:
        required_headers = ['User-Agent']

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            missing_headers = []
            for header in required_headers:
                if not request.headers.get(header):
                    missing_headers.append(header)

            if missing_headers:
                security_logger.log_security_event(
                    "MISSING_SECURITY_HEADERS",
                    "low",
                    {
                        'missing_headers': missing_headers,
                        'path': request.path
                    },
                    None,
                    SecurityMiddleware()._get_client_ip()
                )
                # Don't block, just log for monitoring

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def audit_log(action: str, sensitive: bool = False):
    """Decorator to log auditable actions."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = SecurityMiddleware()._get_client_ip()
            username = getattr(g, 'username', None)

            # Log action start
            security_logger.log_security_event(
                f"AUDIT_{action.upper()}_START",
                "low",
                {
                    'path': request.path,
                    'method': request.method,
                    'sensitive_operation': sensitive
                },
                username,
                client_ip
            )

            try:
                result = f(*args, **kwargs)

                # Log successful action
                security_logger.log_security_event(
                    f"AUDIT_{action.upper()}_SUCCESS",
                    "low",
                    {'path': request.path},
                    username,
                    client_ip
                )

                return result

            except Exception as e:
                # Log failed action
                security_logger.log_security_event(
                    f"AUDIT_{action.upper()}_FAILED",
                    "medium",
                    {
                        'error': str(e),
                        'path': request.path
                    },
                    username,
                    client_ip
                )
                raise

        return decorated_function
    return decorator


class CSRFProtection:
    """CSRF protection utilities."""

    SECRET_KEY = secrets.token_hex(32)
    TOKEN_LIFETIME = 3600  # 1 hour

    @classmethod
    def generate_token(cls, session_id: str) -> str:
        """Generate CSRF token for session."""
        timestamp = str(int(time.time()))
        message = f"{session_id}:{timestamp}"
        signature = hmac.new(
            cls.SECRET_KEY.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

        return f"{timestamp}:{signature}"

    @classmethod
    def validate_token(cls, token: str, session_id: str) -> bool:
        """Validate CSRF token."""
        try:
            timestamp_str, signature = token.split(':', 1)
            timestamp = int(timestamp_str)

            # Check token age
            if time.time() - timestamp > cls.TOKEN_LIFETIME:
                return False

            # Validate signature
            message = f"{session_id}:{timestamp_str}"
            expected_signature = hmac.new(
                cls.SECRET_KEY.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(signature, expected_signature)

        except (ValueError, TypeError):
            return False


# Request sanitization utilities
class RequestSanitizer:
    """Utilities for sanitizing request data."""

    @staticmethod
    def sanitize_string(value: str, max_length: int = 1000) -> str:
        """Sanitize string input."""
        if not value:
            return ""

        # Remove null bytes and control characters
        sanitized = ''.join(c for c in value if ord(c) >= 32)

        # Limit length
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]

        return sanitized.strip()

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename to prevent path traversal."""
        if not filename:
            return ""

        # Remove path separators and dangerous characters
        dangerous_chars = ['/', '\\', '..', '<', '>', ':', '*', '?', '"', '|']
        sanitized = filename

        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '_')

        # Remove leading/trailing dots and spaces
        sanitized = sanitized.strip('. ')

        return sanitized or "unnamed_file"
