"""PA-API health check and cooldown management."""

import time
from logging import getLogger
from typing import Optional

log = getLogger(__name__)

# Global cooldown state
_last_rate_limit_time: Optional[float] = None
_cooldown_duration = 600  # 10 minutes default cooldown


def set_rate_limit_cooldown(duration: int = 600) -> None:
    """Set a manual cooldown period after rate limiting."""
    global _last_rate_limit_time, _cooldown_duration
    _last_rate_limit_time = time.time()
    _cooldown_duration = duration
    log.warning("PA-API cooldown activated for %d seconds", duration)


def is_in_cooldown() -> bool:
    """Check if we're currently in a cooldown period."""
    global _last_rate_limit_time, _cooldown_duration
    if _last_rate_limit_time is None:
        return False
    
    elapsed = time.time() - _last_rate_limit_time
    if elapsed < _cooldown_duration:
        remaining = _cooldown_duration - elapsed
        log.info("PA-API still in cooldown for %.1f more seconds", remaining)
        return True
    
    # Cooldown expired
    _last_rate_limit_time = None
    log.info("PA-API cooldown period expired, ready for requests")
    return False


def clear_cooldown() -> None:
    """Manually clear the cooldown period."""
    global _last_rate_limit_time
    _last_rate_limit_time = None
    log.info("PA-API cooldown manually cleared")


def get_cooldown_status() -> dict:
    """Get current cooldown status."""
    global _last_rate_limit_time, _cooldown_duration
    if _last_rate_limit_time is None:
        return {"in_cooldown": False, "remaining_seconds": 0}
    
    elapsed = time.time() - _last_rate_limit_time
    remaining = max(0, _cooldown_duration - elapsed)
    
    return {
        "in_cooldown": remaining > 0,
        "remaining_seconds": remaining,
        "total_duration": _cooldown_duration
    }
