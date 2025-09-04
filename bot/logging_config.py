"""Secure logging configuration for MandiMonitor Bot.

This module provides enterprise-grade logging with PII filtering, structured logging,
audit trails, and security event monitoring.
"""

import logging
import logging.handlers
import json
import re
import hashlib
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum


class LogLevel(Enum):
    """Enhanced log levels for security events."""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL
    SECURITY = 25  # Custom level for security events
    AUDIT = 26     # Custom level for audit events


class PIISeverity(Enum):
    """PII detection severity levels."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PIIFilterResult:
    """Result of PII filtering."""
    filtered_content: str
    pii_detected: bool
    severity: PIISeverity
    pii_types: List[str]


class PIIFilter:
    """Advanced PII detection and filtering system."""

    # PII patterns for Indian context
    PII_PATTERNS = {
        'indian_phone': r'\b(?:\+91[\s\-\.]?)?[6-9]\d{9}\b',
        'indian_aadhaar': r'\b\d{4}[\s\-\.]?\d{4}[\s\-\.]?\d{4}\b',
        'indian_pan': r'\b[A-Z]{5}[0-9]{4}[A-Z]\b',
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'credit_card': r'\b\d{4}[\s\-\.]?\d{4}[\s\-\.]?\d{4}[\s\-\.]?\d{4}\b',
        'bank_account': r'\b\d{9,18}\b',  # Indian bank account numbers
        'ifsc_code': r'\b[A-Z]{4}0[A-Z0-9]{6}\b',
        'indian_pincode': r'\b\d{6}\b',
        'indian_gst': r'\b\d{2}[A-Z]{5}\d{4}[A-Z]\d[Z]\b',
    }

    SENSITIVE_KEYWORDS = [
        'password', 'secret', 'key', 'token', 'credential', 'auth',
        'session', 'cookie', 'apikey', 'bearer', 'authorization'
    ]

    @classmethod
    def filter_pii(cls, content: str, context: str = "general") -> PIIFilterResult:
        """Filter PII from log content."""
        if not content:
            return PIIFilterResult("", False, PIISeverity.NONE, [])

        filtered_content = content
        pii_detected = False
        pii_types = []
        max_severity = PIISeverity.NONE

        # Check for sensitive keywords in keys (for structured data)
        if isinstance(content, dict):
            filtered_content = cls._filter_dict_pii(content)
            return PIIFilterResult(
                json.dumps(filtered_content),
                True,  # Assume PII if we're filtering dict
                PIISeverity.MEDIUM,
                ['structured_data']
            )

        # Pattern-based PII detection
        for pii_type, pattern in cls.PII_PATTERNS.items():
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                pii_detected = True
                pii_types.append(pii_type)

                # Replace with hash
                for match in matches:
                    hash_value = cls._hash_pii(match)
                    filtered_content = filtered_content.replace(match, f"[PII:{pii_type}:{hash_value}]")

                # Determine severity
                if pii_type in ['credit_card', 'indian_aadhaar', 'indian_pan']:
                    max_severity = max(max_severity, PIISeverity.CRITICAL)
                elif pii_type in ['email', 'indian_phone']:
                    max_severity = max(max_severity, PIISeverity.HIGH)
                else:
                    max_severity = max(max_severity, PIISeverity.MEDIUM)

        # Keyword-based filtering
        for keyword in cls.SENSITIVE_KEYWORDS:
            if keyword.lower() in content.lower():
                pii_detected = True
                pii_types.append(f"keyword_{keyword}")
                max_severity = max(max_severity, PIISeverity.HIGH)

                # Replace sensitive values
                pattern = rf'({keyword}\s*[=:]\s*)([^\s,]*)'
                filtered_content = re.sub(pattern, r'\1[REDACTED]', filtered_content, flags=re.IGNORECASE)

        return PIIFilterResult(filtered_content, pii_detected, max_severity, pii_types)

    @classmethod
    def _filter_dict_pii(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Filter PII from dictionary data."""
        filtered = {}

        for key, value in data.items():
            key_lower = key.lower()

            # Check if key contains sensitive information
            if any(sensitive in key_lower for sensitive in cls.SENSITIVE_KEYWORDS):
                filtered[key] = "[REDACTED]"
            elif isinstance(value, str):
                pii_result = cls.filter_pii(value, key)
                filtered[key] = pii_result.filtered_content
            elif isinstance(value, dict):
                filtered[key] = cls._filter_dict_pii(value)
            elif isinstance(value, list):
                filtered[key] = [cls._filter_dict_pii(item) if isinstance(item, dict) else item for item in value]
            else:
                filtered[key] = value

        return filtered

    @classmethod
    def _hash_pii(cls, value: str) -> str:
        """Create a consistent hash for PII values for correlation."""
        return hashlib.sha256(value.encode()).hexdigest()[:8]


class SecureJSONFormatter(logging.Formatter):
    """JSON formatter with PII filtering and structured data."""

    def __init__(self, include_pii_filter: bool = True):
        super().__init__()
        self.include_pii_filter = include_pii_filter

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as secure JSON."""
        # Create base log entry
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, 'extra_data'):
            log_entry['extra'] = record.extra_data

        # PII filtering
        if self.include_pii_filter:
            pii_result = PIIFilter.filter_pii(json.dumps(log_entry))
            if pii_result.pii_detected:
                log_entry = json.loads(pii_result.filtered_content)
                log_entry['pii_filtered'] = True
                log_entry['pii_severity'] = pii_result.severity.value
                log_entry['pii_types'] = pii_result.pii_types

        return json.dumps(log_entry, ensure_ascii=False)


class SecurityEventLogger:
    """Specialized logger for security events."""

    def __init__(self):
        self.logger = logging.getLogger('mandimonitor.security')
        self.logger.setLevel(LogLevel.SECURITY.value)

    def log_security_event(self, event_type: str, severity: str, details: Dict[str, Any],
                          user_id: Optional[str] = None, ip_address: Optional[str] = None):
        """Log a security event with full context."""
        event_data = {
            'event_type': event_type,
            'severity': severity,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'user_id': user_id,
            'ip_address': ip_address,
            'details': details
        }

        self.logger.log(LogLevel.SECURITY.value, f"Security Event: {event_type}", extra={
            'extra_data': event_data
        })

    def log_auth_attempt(self, success: bool, username: str, ip_address: Optional[str] = None,
                        user_agent: Optional[str] = None):
        """Log authentication attempts."""
        event_type = "AUTH_SUCCESS" if success else "AUTH_FAILURE"
        severity = "low" if success else "high"

        details = {
            'username': username,
            'user_agent': user_agent,
            'failure_reason': None if success else "Invalid credentials"
        }

        self.log_security_event(event_type, severity, details, username, ip_address)

    def log_input_validation_failure(self, field: str, value_preview: str, reason: str,
                                   user_id: Optional[str] = None):
        """Log input validation failures."""
        details = {
            'field': field,
            'value_length': len(value_preview) if value_preview else 0,
            'validation_reason': reason,
            'value_preview': value_preview[:50] + "..." if len(value_preview or "") > 50 else value_preview
        }

        self.log_security_event("INPUT_VALIDATION_FAILURE", "medium", details, user_id)

    def log_rate_limit_exceeded(self, identifier: str, limit: int, window: int,
                               user_id: Optional[str] = None):
        """Log rate limit violations."""
        details = {
            'identifier': identifier,
            'limit': limit,
            'window_seconds': window,
            'limit_type': 'user' if user_id else 'ip'
        }

        self.log_security_event("RATE_LIMIT_EXCEEDED", "high", details, user_id)


def setup_secure_logging(log_level: str = "INFO", log_to_file: bool = True,
                        enable_pii_filter: bool = True) -> SecurityEventLogger:
    """Setup comprehensive secure logging system."""

    # Create logs directory
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)

    # Clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    # Set root logger level
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Console handler with JSON formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = SecureJSONFormatter(include_pii_filter=enable_pii_filter)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handlers
    if log_to_file:
        # General application log
        app_handler = logging.handlers.RotatingFileHandler(
            log_dir / 'app.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        app_handler.setFormatter(console_formatter)
        root_logger.addHandler(app_handler)

        # Security-specific log
        security_handler = logging.handlers.RotatingFileHandler(
            log_dir / 'security.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=10  # Keep more security logs
        )
        security_formatter = SecureJSONFormatter(include_pii_filter=True)
        security_handler.setFormatter(security_formatter)
        security_handler.setLevel(LogLevel.SECURITY.value)

        # Create security logger and add handler
        security_logger = logging.getLogger('mandimonitor.security')
        security_logger.addHandler(security_handler)
        security_logger.propagate = False  # Don't propagate to root

        # Audit log for compliance
        audit_handler = logging.handlers.RotatingFileHandler(
            log_dir / 'audit.log',
            maxBytes=50*1024*1024,  # 50MB
            backupCount=30  # Keep for 30 days
        )
        audit_formatter = SecureJSONFormatter(include_pii_filter=True)
        audit_handler.setFormatter(audit_formatter)
        audit_handler.setLevel(LogLevel.AUDIT.value)

        audit_logger = logging.getLogger('mandimonitor.audit')
        audit_logger.addHandler(audit_handler)
        audit_logger.propagate = False

    # Add custom log levels
    logging.addLevelName(LogLevel.SECURITY.value, 'SECURITY')
    logging.addLevelName(LogLevel.AUDIT.value, 'AUDIT')

    return SecurityEventLogger()


# Backward compatibility functions
def setup_dev_logging():
    """Setup logging for development environment."""
    return setup_secure_logging("DEBUG", True, True)


def log_security_event(event: str, details: dict = None):
    """Log security events (backward compatibility)."""
    security_logger = SecurityEventLogger()
    severity = "medium"  # Default severity
    security_logger.log_security_event(event, severity, details or {})


def log_auth_attempt(success: bool, username: str, ip_address: str = None):
    """Log authentication attempts (backward compatibility)."""
    security_logger = SecurityEventLogger()
    security_logger.log_auth_attempt(success, username, ip_address)


def log_input_validation_failure(field: str, value: str, reason: str):
    """Log input validation failures (backward compatibility)."""
    security_logger = SecurityEventLogger()
    security_logger.log_input_validation_failure(field, value[:100], reason)
