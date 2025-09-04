"""Comprehensive Rate Limiting System for MandiMonitor Bot.

This module provides multi-layered rate limiting for:
- PA-API calls (existing)
- User input validation
- Admin interface access
- Telegram bot commands
- General API protection
"""

import asyncio
import time
import hashlib
from collections import deque, defaultdict
from logging import getLogger
from typing import Optional, Dict, Tuple, List, Any
from dataclasses import dataclass
from enum import Enum

from .config import settings
from .logging_config import SecurityEventLogger

log = getLogger(__name__)
security_logger = SecurityEventLogger()


class RateLimitType(Enum):
    """Types of rate limiting."""
    API_CALL = "api_call"
    USER_INPUT = "user_input"
    ADMIN_ACCESS = "admin_access"
    TELEGRAM_COMMAND = "telegram_command"
    SEARCH_QUERY = "search_query"


class RateLimitStrategy(Enum):
    """Rate limiting strategies."""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"


@dataclass
class RateLimitRule:
    """Rate limiting rule configuration."""
    requests_per_window: int
    window_seconds: int
    strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW
    burst_allowance: int = 0
    cooldown_seconds: int = 60


@dataclass
class RateLimitResult:
    """Result of rate limit check."""
    allowed: bool
    remaining_requests: int
    reset_time: float
    retry_after: Optional[float] = None
    exceeded_by: Optional[int] = None


class SlidingWindowLimiter:
    """Sliding window rate limiter for precise control."""

    def __init__(self, requests_per_window: int, window_seconds: int):
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.requests: deque = deque()

    def check_limit(self, identifier: str) -> RateLimitResult:
        """Check if request is within rate limit."""
        now = time.time()

        # Remove old requests outside the window
        while self.requests and self.requests[0] < now - self.window_seconds:
            self.requests.popleft()

        # Check if limit exceeded
        if len(self.requests) >= self.requests_per_window:
            # Calculate reset time
            oldest_request = self.requests[0]
            reset_time = oldest_request + self.window_seconds
            retry_after = reset_time - now

            return RateLimitResult(
                allowed=False,
                remaining_requests=0,
                reset_time=reset_time,
                retry_after=max(0, retry_after),
                exceeded_by=len(self.requests) - self.requests_per_window + 1
            )

        # Add current request
        self.requests.append(now)

        return RateLimitResult(
            allowed=True,
            remaining_requests=self.requests_per_window - len(self.requests),
            reset_time=now + self.window_seconds
        )


class TokenBucketLimiter:
    """Token bucket rate limiter for burst handling."""

    def __init__(self, rate_per_second: float, burst_capacity: int):
        self.rate_per_second = rate_per_second
        self.burst_capacity = burst_capacity
        self.tokens = burst_capacity
        self.last_update = time.time()

    def check_limit(self, identifier: str) -> RateLimitResult:
        """Check if request can be served."""
        now = time.time()

        # Add tokens based on elapsed time
        elapsed = now - self.last_update
        tokens_to_add = elapsed * self.rate_per_second
        self.tokens = min(self.burst_capacity, self.tokens + tokens_to_add)
        self.last_update = now

        if self.tokens >= 1:
            self.tokens -= 1
            return RateLimitResult(
                allowed=True,
                remaining_requests=int(self.tokens),
                reset_time=now + 1.0 / self.rate_per_second
            )
        else:
            # Calculate when next token will be available
            deficit = 1 - self.tokens
            retry_after = deficit / self.rate_per_second

            return RateLimitResult(
                allowed=False,
                remaining_requests=0,
                reset_time=now + retry_after,
                retry_after=retry_after
            )


class ComprehensiveRateLimiter:
    """Comprehensive rate limiting system with multiple strategies."""

    # Default rate limit rules
    DEFAULT_RULES = {
        RateLimitType.USER_INPUT: RateLimitRule(
            requests_per_window=10,
            window_seconds=60,
            burst_allowance=2
        ),
        RateLimitType.ADMIN_ACCESS: RateLimitRule(
            requests_per_window=5,
            window_seconds=300,  # 5 minutes
            burst_allowance=0
        ),
        RateLimitType.TELEGRAM_COMMAND: RateLimitRule(
            requests_per_window=20,
            window_seconds=60,
            burst_allowance=5
        ),
        RateLimitType.SEARCH_QUERY: RateLimitRule(
            requests_per_window=5,
            window_seconds=60,
            burst_allowance=1
        ),
        RateLimitType.API_CALL: RateLimitRule(
            requests_per_window=1,
            window_seconds=1,
            burst_allowance=0
        )
    }

    def __init__(self):
        self.limiters: Dict[str, Dict[RateLimitType, Any]] = defaultdict(dict)
        self.blocked_until: Dict[str, float] = {}
        self.violation_counts: Dict[str, int] = defaultdict(int)

    def check_rate_limit(self, identifier: str, limit_type: RateLimitType,
                        custom_rule: Optional[RateLimitRule] = None) -> RateLimitResult:
        """Check rate limit for a given identifier and type."""

        # Check if identifier is currently blocked
        if identifier in self.blocked_until:
            if time.time() < self.blocked_until[identifier]:
                reset_time = self.blocked_until[identifier]
                return RateLimitResult(
                    allowed=False,
                    remaining_requests=0,
                    reset_time=reset_time,
                    retry_after=reset_time - time.time()
                )
            else:
                # Block expired, remove it
                del self.blocked_until[identifier]
                if identifier in self.violation_counts:
                    del self.violation_counts[identifier]

        # Get or create limiter for this identifier and type
        rule = custom_rule or self.DEFAULT_RULES.get(limit_type, self.DEFAULT_RULES[RateLimitType.USER_INPUT])

        limiter_key = f"{identifier}:{limit_type.value}"
        if limiter_key not in self.limiters:
            if rule.strategy == RateLimitStrategy.TOKEN_BUCKET:
                # Convert sliding window to token bucket
                rate_per_second = rule.requests_per_window / rule.window_seconds
                burst_capacity = rule.requests_per_window + rule.burst_allowance
                self.limiters[limiter_key] = TokenBucketLimiter(rate_per_second, burst_capacity)
            else:
                # Default to sliding window
                requests_per_window = rule.requests_per_window + rule.burst_allowance
                self.limiters[limiter_key] = SlidingWindowLimiter(requests_per_window, rule.window_seconds)

        limiter = self.limiters[limiter_key]
        result = limiter.check_limit(identifier)

        # Handle violations
        if not result.allowed:
            self._handle_violation(identifier, limit_type, rule)

        return result

    def _handle_violation(self, identifier: str, limit_type: RateLimitType, rule: RateLimitRule):
        """Handle rate limit violations."""
        self.violation_counts[identifier] += 1

        # Progressive penalties
        violation_count = self.violation_counts[identifier]

        if violation_count >= 5:
            # Block for cooldown period
            self.blocked_until[identifier] = time.time() + rule.cooldown_seconds
            security_logger.log_rate_limit_exceeded(
                identifier=identifier,
                limit=rule.requests_per_window,
                window=rule.window_seconds
            )
            log.warning(f"Rate limit violation blocked: {identifier} ({violation_count} violations)")

    def get_usage_stats(self, identifier: str, limit_type: RateLimitType) -> Dict[str, Any]:
        """Get usage statistics for an identifier."""
        limiter_key = f"{identifier}:{limit_type.value}"
        limiter = self.limiters.get(limiter_key)

        if not limiter:
            return {"requests_in_window": 0, "window_remaining": 0}

        # Get stats based on limiter type
        if isinstance(limiter, SlidingWindowLimiter):
            return {
                "requests_in_window": len(limiter.requests),
                "window_remaining": limiter.requests_per_window - len(limiter.requests),
                "window_seconds": limiter.window_seconds
            }
        elif isinstance(limiter, TokenBucketLimiter):
            return {
                "available_tokens": limiter.tokens,
                "burst_capacity": limiter.burst_capacity,
                "rate_per_second": limiter.rate_per_second
            }

        return {}

    def reset_identifier(self, identifier: str):
        """Reset rate limiting for a specific identifier (admin function)."""
        # Remove all limiters for this identifier
        keys_to_remove = [key for key in self.limiters.keys() if key.startswith(f"{identifier}:")]
        for key in keys_to_remove:
            del self.limiters[key]

        # Remove blocks and violation counts
        if identifier in self.blocked_until:
            del self.blocked_until[identifier]
        if identifier in self.violation_counts:
            del self.violation_counts[identifier]

        log.info(f"Rate limiting reset for identifier: {identifier}")


# Global rate limiter instances
_user_rate_limiter = ComprehensiveRateLimiter()
_admin_rate_limiter = ComprehensiveRateLimiter()

# PA-API specific rate limiter (existing)
_paapi_rate_limiter: Optional['APIRateLimiter'] = None


class APIRateLimiter:
    """Rate limiter respecting PA-API constraints.

    PA-API limits:
    - 1 request per second sustained rate
    - Burst capacity of up to 10 requests in 10 seconds
    """

    def __init__(self):
        """Initialize rate limiter with PA-API constraints."""
        self.requests = deque()  # Track requests for 1/second limit
        self.burst_requests = deque()  # Track burst requests
        self.rate_limit = settings.PAAPI_RATE_LIMIT_PER_SECOND
        self.burst_limit = settings.PAAPI_BURST_LIMIT
        self.burst_window = settings.PAAPI_BURST_WINDOW_SECONDS
        self._lock = asyncio.Lock()

    async def acquire(self, priority: str = "normal") -> None:
        """Acquire permission for API call.

        Args:
        ----
            priority: Request priority ("high", "normal", "low")
                     High priority requests get faster processing
        """
        async with self._lock:
            now = time.time()

            # Clean old requests from tracking
            self._clean_old_requests(now)

            # Check burst limit first
            await self._enforce_burst_limit(now)

            # Check rate limit
            await self._enforce_rate_limit(now, priority)

            # Record this request
            self.requests.append(now)
            self.burst_requests.append(now)

            log.debug("API rate limiter: granted request (priority: %s)", priority)

    def _clean_old_requests(self, now: float) -> None:
        """Remove old requests from tracking queues."""
        # Clean requests older than 1 second
        while self.requests and self.requests[0] < now - 1:
            self.requests.popleft()

        # Clean burst requests older than burst window
        while self.burst_requests and self.burst_requests[0] < now - self.burst_window:
            self.burst_requests.popleft()

    async def _enforce_burst_limit(self, now: float) -> None:
        """Enforce burst limit (10 requests in 10 seconds)."""
        if len(self.burst_requests) >= self.burst_limit:
            # Calculate how long to wait
            oldest_burst = self.burst_requests[0]
            sleep_time = self.burst_window - (now - oldest_burst)

            if sleep_time > 0:
                log.info(
                    "API rate limiter: burst limit reached, sleeping %.2fs", sleep_time
                )
                await asyncio.sleep(sleep_time)

    async def _enforce_rate_limit(self, now: float, priority: str) -> None:
        """Enforce rate limit (1 request per second with conservative buffer)."""
        if self.requests:
            last_request = self.requests[-1]
            # Add 0.5s buffer to be more conservative
            sleep_time = 1.5 - (now - last_request)

            # Adjust sleep time based on priority
            if priority == "high":
                sleep_time *= 0.9  # High priority gets 10% faster processing
            elif priority == "low":
                sleep_time *= 1.3  # Low priority gets 30% slower processing

            if sleep_time > 0:
                log.info(
                    "API rate limiter: rate limit, sleeping %.2fs (priority: %s)",
                    sleep_time,
                    priority,
                )
                await asyncio.sleep(sleep_time)

    def get_current_usage(self) -> dict:
        """Get current rate limiter usage statistics."""
        now = time.time()
        self._clean_old_requests(now)

        return {
            "requests_last_second": len(self.requests),
            "burst_requests": len(self.burst_requests),
            "rate_limit": self.rate_limit,
            "burst_limit": self.burst_limit,
            "burst_window": self.burst_window,
        }

    async def wait_for_capacity(self, required_requests: int = 1) -> float:
        """Wait until there's capacity for the specified number of requests.

        Args:
        ----
            required_requests: Number of requests needed

        Returns:
        -------
            Estimated wait time in seconds
        """
        now = time.time()
        self._clean_old_requests(now)

        # Check if we have burst capacity
        available_burst = self.burst_limit - len(self.burst_requests)
        if available_burst >= required_requests:
            return 0.0

        # Calculate wait time for burst capacity
        if self.burst_requests:
            oldest_burst = self.burst_requests[0]
            wait_time = self.burst_window - (now - oldest_burst)
            return max(0.0, wait_time)

        return 0.0


# Global rate limiter instances
_paapi_rate_limiter: Optional[APIRateLimiter] = None
_user_rate_limiter = ComprehensiveRateLimiter()
_admin_rate_limiter = ComprehensiveRateLimiter()


# Convenience functions for different rate limiting types
def check_user_input_rate_limit(user_id: str) -> RateLimitResult:
    """Check rate limit for user input validation."""
    return _user_rate_limiter.check_rate_limit(user_id, RateLimitType.USER_INPUT)


def check_admin_access_rate_limit(ip_address: str) -> RateLimitResult:
    """Check rate limit for admin interface access."""
    return _admin_rate_limiter.check_rate_limit(ip_address, RateLimitType.ADMIN_ACCESS)


def check_telegram_command_rate_limit(user_id: str) -> RateLimitResult:
    """Check rate limit for Telegram bot commands."""
    return _user_rate_limiter.check_rate_limit(user_id, RateLimitType.TELEGRAM_COMMAND)


def check_search_query_rate_limit(user_id: str) -> RateLimitResult:
    """Check rate limit for search queries."""
    return _user_rate_limiter.check_rate_limit(user_id, RateLimitType.SEARCH_QUERY)


# PA-API specific functions (backward compatibility)
def get_rate_limiter() -> APIRateLimiter:
    """Get the global PA-API rate limiter instance."""
    global _paapi_rate_limiter
    if _paapi_rate_limiter is None:
        _paapi_rate_limiter = APIRateLimiter()
    return _paapi_rate_limiter


async def acquire_api_permission(priority: str = "normal") -> None:
    """Convenience function to acquire PA-API permission.

    Args:
    ----
        priority: Request priority ("high", "normal", "low")
    """
    limiter = get_rate_limiter()
    await limiter.acquire(priority)


def reset_rate_limiter() -> None:
    """Reset the PA-API rate limiter state (useful for testing or recovery)."""
    global _paapi_rate_limiter
    if _paapi_rate_limiter:
        _paapi_rate_limiter.requests.clear()
        _paapi_rate_limiter.burst_requests.clear()
        log.info("PA-API rate limiter state reset")


# Administrative functions
def reset_user_rate_limits(user_id: str):
    """Reset all rate limits for a specific user (admin function)."""
    _user_rate_limiter.reset_identifier(user_id)
    log.info(f"User rate limits reset for: {user_id}")


def get_rate_limit_stats(identifier: str, limit_type: RateLimitType) -> Dict[str, Any]:
    """Get rate limiting statistics for debugging."""
    return _user_rate_limiter.get_usage_stats(identifier, limit_type)


def get_admin_rate_limit_stats(ip_address: str) -> Dict[str, Any]:
    """Get admin interface rate limiting statistics."""
    return _admin_rate_limiter.get_usage_stats(ip_address, RateLimitType.ADMIN_ACCESS)
