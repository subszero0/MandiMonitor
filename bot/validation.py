"""Secure input validation framework for MandiMonitor Bot.

This module provides comprehensive input validation, sanitization, and security controls
to prevent injection attacks, XSS, and other input-based vulnerabilities.
"""

import re
import html
import logging
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Severity levels for validation failures."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ValidationResult:
    """Result of input validation."""
    is_valid: bool
    sanitized_value: Optional[Any] = None
    error_message: Optional[str] = None
    severity: ValidationSeverity = ValidationSeverity.LOW


class SecurityInputValidator:
    """Enterprise-grade input validation with security focus."""

    # Security patterns for detecting malicious input
    SQL_INJECTION_PATTERNS = [
        r';\s*(?:select|insert|update|delete|drop|create|alter)',
        r'union\s+select',
        r'--\s*$',
        r'#\s*$',
        r'/\*\s*\*/',
        r'xp_cmdshell',
        r'exec\s*\(',
    ]

    XSS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'vbscript:',
        r'on\w+\s*=',
        r'<iframe[^>]*>',
        r'<object[^>]*>',
        r'<embed[^>]*>',
    ]

    SHELL_INJECTION_PATTERNS = [
        r';\s*(?:rm|ls|cat|echo|wget|curl)',
        r'\|\s*(?:rm|ls|cat|echo|wget|curl)',
        r'&&\s*(?:rm|ls|cat|echo|wget|curl)',
        r'\|\|\s*(?:rm|ls|cat|echo|wget|curl)',
        r'`.*?`',
        r'\$\([^)]+\)',
    ]

    # Allowlist for safe characters
    SAFE_TEXT_PATTERN = r'^[a-zA-Z0-9\s\.,!?\-_]+$'
    SAFE_SEARCH_PATTERN = r'^[a-zA-Z0-9\s\.,!?\-_\(\)\[\]\+\&\*\:\'\"]+$'

    @classmethod
    def validate_search_query(cls, query: str) -> ValidationResult:
        """Comprehensive search query validation with security checks."""
        if not query:
            return ValidationResult(False, None, "Query cannot be empty", ValidationSeverity.MEDIUM)

        query = query.strip()
        if len(query) > 500:  # Increased limit for rich queries
            return ValidationResult(False, None, "Query too long (max 500 chars)", ValidationSeverity.MEDIUM)

        if len(query) < 2:
            return ValidationResult(False, None, "Query too short (min 2 chars)", ValidationSeverity.LOW)

        # Security checks
        security_issues = cls._check_security_patterns(query)
        if security_issues:
            logger.warning(f"Security pattern detected in search query: {security_issues}")
            return ValidationResult(False, None, "Invalid characters detected", ValidationSeverity.HIGH)

        # Content validation
        if not re.match(cls.SAFE_SEARCH_PATTERN, query):
            return ValidationResult(False, None, "Query contains invalid characters", ValidationSeverity.MEDIUM)

        # Sanitize and normalize
        sanitized = cls._sanitize_search_query(query)

        return ValidationResult(True, sanitized)

    @classmethod
    def validate_asin(cls, asin: str) -> ValidationResult:
        """Enhanced ASIN validation with security checks."""
        if not asin:
            return ValidationResult(False, None, "ASIN cannot be empty", ValidationSeverity.MEDIUM)

        asin = asin.strip().upper()

        # Security checks first
        security_issues = cls._check_security_patterns(asin)
        if security_issues:
            logger.warning(f"Security pattern detected in ASIN: {security_issues}")
            return ValidationResult(False, None, "Invalid ASIN format", ValidationSeverity.HIGH)

        # ASIN format validation: 10 alphanumeric characters
        if not re.match(r'^[A-Z0-9]{10}$', asin):
            return ValidationResult(False, None, "Invalid ASIN format (must be 10 alphanumeric chars)", ValidationSeverity.MEDIUM)

        # Additional validation for Amazon ASIN patterns
        if not cls._is_valid_asin_pattern(asin):
            return ValidationResult(False, None, "Invalid ASIN pattern", ValidationSeverity.MEDIUM)

        return ValidationResult(True, asin)

    @classmethod
    def validate_price_range(cls, min_price: Optional[float], max_price: Optional[float]) -> ValidationResult:
        """Secure price range validation."""
        # Check for None values first
        if min_price is None and max_price is None:
            return ValidationResult(True, (None, None))

        # Validate numeric types and ranges
        validated_prices = cls._validate_price_values(min_price, max_price)
        if validated_prices is None:
            return ValidationResult(False, None, "Invalid price values", ValidationSeverity.MEDIUM)

        min_val, max_val = validated_prices

        # Business logic validation
        if min_val is not None and max_val is not None:
            if min_val > max_val:
                return ValidationResult(False, None, "Minimum price cannot exceed maximum price", ValidationSeverity.LOW)

            # Prevent unreasonable price ranges
            if max_val > 10000000:  # 1 crore INR limit
                return ValidationResult(False, None, "Maximum price too high", ValidationSeverity.MEDIUM)

            if min_val < 0:
                return ValidationResult(False, None, "Prices cannot be negative", ValidationSeverity.LOW)

        return ValidationResult(True, (min_val, max_val))

    @classmethod
    def validate_telegram_message(cls, text: str) -> ValidationResult:
        """Comprehensive Telegram message validation."""
        if not text:
            return ValidationResult(True, "")

        text = text.strip()
        if len(text) > 4096:  # Telegram message limit
            return ValidationResult(False, None, "Message too long", ValidationSeverity.MEDIUM)

        # Security checks
        security_issues = cls._check_security_patterns(text)
        if security_issues:
            logger.warning(f"Security pattern detected in message: {security_issues}")
            return ValidationResult(False, None, "Message contains invalid content", ValidationSeverity.HIGH)

        # XSS protection
        xss_issues = cls._check_xss_patterns(text)
        if xss_issues:
            logger.warning(f"XSS pattern detected in message: {xss_issues}")
            return ValidationResult(False, None, "Message contains potentially harmful content", ValidationSeverity.CRITICAL)

        # Sanitize for safe display
        sanitized = cls._sanitize_telegram_message(text)

        return ValidationResult(True, sanitized)

    @classmethod
    def validate_user_input(cls, input_type: str, value: Any) -> ValidationResult:
        """Generic user input validation dispatcher."""
        validators = {
            'search_query': cls.validate_search_query,
            'asin': cls.validate_asin,
            'telegram_message': cls.validate_telegram_message,
            'price_range': lambda v: cls.validate_price_range(v.get('min'), v.get('max')),
        }

        validator = validators.get(input_type)
        if not validator:
            return ValidationResult(False, None, f"Unknown input type: {input_type}", ValidationSeverity.MEDIUM)

        return validator(value)

    @classmethod
    def _check_security_patterns(cls, input_str: str) -> List[str]:
        """Check for security pattern violations."""
        issues = []

        # SQL injection patterns
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, input_str, re.IGNORECASE):
                issues.append(f"SQL injection pattern: {pattern}")

        # Shell injection patterns
        for pattern in cls.SHELL_INJECTION_PATTERNS:
            if re.search(pattern, input_str, re.IGNORECASE):
                issues.append(f"Shell injection pattern: {pattern}")

        return issues

    @classmethod
    def _check_xss_patterns(cls, input_str: str) -> List[str]:
        """Check for XSS pattern violations."""
        issues = []

        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, input_str, re.IGNORECASE):
                issues.append(f"XSS pattern: {pattern}")

        return issues

    @classmethod
    def _sanitize_search_query(cls, query: str) -> str:
        """Sanitize search query while preserving useful characters."""
        # HTML escape
        sanitized = html.escape(query)

        # Remove dangerous characters but preserve search-relevant ones
        sanitized = re.sub(r'[<>]', '', sanitized)

        # Normalize whitespace
        sanitized = ' '.join(sanitized.split())

        return sanitized

    @classmethod
    def _sanitize_telegram_message(cls, text: str) -> str:
        """Sanitize Telegram message content."""
        # HTML escape for web display
        sanitized = html.escape(text)

        # Remove dangerous HTML/script content
        sanitized = re.sub(r'<[^>]+>', '', sanitized)

        # Normalize whitespace
        sanitized = ' '.join(sanitized.split())

        return sanitized

    @classmethod
    def _is_valid_asin_pattern(cls, asin: str) -> bool:
        """Validate ASIN follows known Amazon patterns."""
        # ASINs typically start with letters B, 0, 1, or 6
        if asin[0] not in ['B', '0', '1', '6']:
            return False

        # Additional pattern checks can be added here
        return True

    @classmethod
    def _validate_price_values(cls, min_price: Optional[float], max_price: Optional[float]) -> Optional[Tuple[Optional[float], Optional[float]]]:
        """Validate and convert price values."""
        try:
            validated_min = float(min_price) if min_price is not None else None
            validated_max = float(max_price) if max_price is not None else None
            return validated_min, validated_max
        except (ValueError, TypeError):
            return None


# Backward compatibility
class DevInputValidator(SecurityInputValidator):
    """Backward compatibility wrapper for existing code."""

    @staticmethod
    def validate_search_query(query: str) -> Optional[str]:
        result = SecurityInputValidator.validate_search_query(query)
        return result.sanitized_value if result.is_valid else None

    @staticmethod
    def validate_asin(asin: str) -> Optional[str]:
        result = SecurityInputValidator.validate_asin(asin)
        return result.sanitized_value if result.is_valid else None

    @staticmethod
    def validate_price_range(min_price: Optional[float], max_price: Optional[float]) -> tuple[Optional[float], Optional[float]]:
        result = SecurityInputValidator.validate_price_range(min_price, max_price)
        return result.sanitized_value if result.is_valid else (None, None)

    @staticmethod
    def sanitize_telegram_message(text: str) -> str:
        result = SecurityInputValidator.validate_telegram_message(text)
        return result.sanitized_value if result.is_valid else ""
