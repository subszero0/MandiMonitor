"""API Rate Limiter for PA-API quota management."""

import asyncio
import time
from collections import deque
from logging import getLogger
from typing import Optional

from .config import settings

log = getLogger(__name__)


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


# Global rate limiter instance
_rate_limiter: Optional[APIRateLimiter] = None


def get_rate_limiter() -> APIRateLimiter:
    """Get the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = APIRateLimiter()
    return _rate_limiter


async def acquire_api_permission(priority: str = "normal") -> None:
    """Convenience function to acquire API permission.

    Args:
    ----
        priority: Request priority ("high", "normal", "low")
    """
    limiter = get_rate_limiter()
    await limiter.acquire(priority)


def reset_rate_limiter() -> None:
    """Reset the rate limiter state (useful for testing or recovery)."""
    global _rate_limiter
    if _rate_limiter:
        _rate_limiter.requests.clear()
        _rate_limiter.burst_requests.clear()
        log.info("Rate limiter state reset")
