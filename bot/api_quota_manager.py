"""Advanced API Quota Management for PA-API with intelligent prioritization.

This module provides sophisticated quota management built on the existing
api_rate_limiter.py with enhanced request prioritization, circuit breaker
pattern, and intelligent quota handling.
"""

import asyncio
import time
from collections import defaultdict, deque
from enum import Enum
from logging import getLogger
from typing import Any, Callable, Dict, List, Optional

from .api_rate_limiter import get_rate_limiter
from .config import settings
from .errors import QuotaExceededError

log = getLogger(__name__)


class RequestPriority(Enum):
    """Request priority levels for intelligent queue management."""
    
    USER_TRIGGERED = 1  # Highest priority - direct user requests
    ACTIVE_WATCH = 2    # High priority - active price monitoring
    DATA_ENRICHMENT = 3 # Medium priority - background data enrichment
    ANALYTICS = 4       # Lowest priority - analytics and reporting


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    
    CLOSED = "closed"     # Normal operation
    OPEN = "open"         # Circuit is open, requests are failing
    HALF_OPEN = "half_open"  # Testing if service has recovered


class APIQuotaManager:
    """Intelligent quota management for PA-API with circuit breaker pattern.
    
    Features:
    - Priority-based request queuing
    - Circuit breaker pattern for graceful degradation
    - Intelligent quota tracking and prediction
    - Request deduplication and batching
    """

    def __init__(self):
        """Initialize the API quota manager."""
        # Request queues by priority
        self.request_queues = {
            priority: deque() for priority in RequestPriority
        }
        
        # Rate limiter integration
        self.rate_limiter = get_rate_limiter()
        
        # Circuit breaker state
        self.circuit_state = CircuitBreakerState.CLOSED
        self.circuit_failure_count = 0
        self.circuit_last_failure_time = 0
        self.circuit_next_attempt_time = 0
        
        # Circuit breaker configuration
        self.failure_threshold = 5  # Failures before opening circuit
        self.recovery_timeout = 60  # Seconds to wait before half-open
        self.success_threshold = 3  # Successes needed to close circuit
        
        # Quota tracking
        self.daily_quota_used = 0
        self.daily_quota_limit = 8640  # PA-API daily limit
        self.quota_reset_time = self._get_next_quota_reset()
        
        # Request deduplication
        self.pending_requests = {}  # asin -> Future
        self.request_cache = {}  # Request cache for deduplication
        
        # Performance metrics
        self.metrics = {
            "requests_processed": 0,
            "requests_queued": 0,
            "requests_deduplicated": 0,
            "circuit_breaker_activations": 0,
            "quota_exceeded_events": 0
        }
        
        # Background task for processing queues
        self._processing_task = None
        self._shutdown_event = asyncio.Event()

    async def start(self) -> None:
        """Start the quota manager background processing."""
        if self._processing_task is None:
            self._processing_task = asyncio.create_task(self._process_request_queues())
            log.info("API Quota Manager started")

    async def stop(self) -> None:
        """Stop the quota manager background processing."""
        if self._processing_task:
            self._shutdown_event.set()
            await self._processing_task
            self._processing_task = None
            log.info("API Quota Manager stopped")

    async def queue_request(
        self,
        request_func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        priority: RequestPriority = RequestPriority.DATA_ENRICHMENT,
        request_id: Optional[str] = None
    ) -> Any:
        """Queue an API request with priority and deduplication.
        
        Args:
            request_func: The API function to call
            args: Function arguments
            kwargs: Function keyword arguments
            priority: Request priority level
            request_id: Optional unique request ID for deduplication
            
        Returns:
            Future that will contain the API response
        """
        if kwargs is None:
            kwargs = {}
            
        # Check for duplicate requests
        if request_id and request_id in self.pending_requests:
            log.debug("Deduplicating request: %s", request_id)
            self.metrics["requests_deduplicated"] += 1
            return await self.pending_requests[request_id]
            
        # Create request future
        future = asyncio.Future()
        
        # Build request object
        request = {
            "id": request_id or f"req_{int(time.time() * 1000)}",
            "func": request_func,
            "args": args,
            "kwargs": kwargs,
            "priority": priority,
            "future": future,
            "queued_at": time.time()
        }
        
        # Add to pending requests for deduplication
        if request_id:
            self.pending_requests[request_id] = future
            
        # Queue the request
        self.request_queues[priority].append(request)
        self.metrics["requests_queued"] += 1
        
        log.debug(
            "Queued request %s with priority %s", 
            request["id"], 
            priority.name
        )
        
        return await future

    async def execute_with_quota_management(
        self,
        api_function: Callable,
        *args,
        priority: RequestPriority = RequestPriority.DATA_ENRICHMENT,
        **kwargs
    ) -> Any:
        """Execute API calls with quota management and circuit breaker.
        
        Args:
            api_function: The API function to execute
            *args: Function arguments
            priority: Request priority
            **kwargs: Function keyword arguments
            
        Returns:
            API response
            
        Raises:
            QuotaExceededError: When quota is exceeded or circuit is open
        """
        # Check circuit breaker
        if not await self._check_circuit_breaker():
            raise QuotaExceededError("Circuit breaker is open")
            
        # Check daily quota
        if not await self._check_daily_quota():
            raise QuotaExceededError("Daily quota exceeded")
            
        try:
            # Wait for rate limiter permission
            await self.rate_limiter.acquire(priority.name.lower())
            
            # Execute the API call
            start_time = time.time()
            result = await api_function(*args, **kwargs)
            duration = time.time() - start_time
            
            # Record successful request
            await self._record_successful_request(duration)
            
            return result
            
        except QuotaExceededError:
            await self._record_quota_exceeded()
            raise
        except Exception as e:
            await self._record_failed_request(e)
            raise

    def get_quota_status(self) -> Dict[str, Any]:
        """Get current quota usage and status.
        
        Returns:
            Dictionary containing quota information
        """
        time_until_reset = max(0, self.quota_reset_time - time.time())
        
        return {
            "daily_quota_used": self.daily_quota_used,
            "daily_quota_limit": self.daily_quota_limit,
            "quota_remaining": max(0, self.daily_quota_limit - self.daily_quota_used),
            "quota_usage_percentage": (self.daily_quota_used / self.daily_quota_limit) * 100,
            "time_until_reset": time_until_reset,
            "circuit_state": self.circuit_state.value,
            "circuit_failure_count": self.circuit_failure_count,
            "queue_sizes": {
                priority.name: len(queue) 
                for priority, queue in self.request_queues.items()
            }
        }

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for monitoring.
        
        Returns:
            Dictionary containing performance metrics
        """
        total_queue_size = sum(len(queue) for queue in self.request_queues.values())
        
        return {
            **self.metrics,
            "total_queue_size": total_queue_size,
            "pending_requests": len(self.pending_requests),
            "circuit_state": self.circuit_state.value,
            "quota_status": self.get_quota_status()
        }

    async def clear_queues(self) -> None:
        """Clear all request queues (emergency operation)."""
        for queue in self.request_queues.values():
            while queue:
                request = queue.popleft()
                if not request["future"].done():
                    request["future"].set_exception(
                        QuotaExceededError("Request queue cleared")
                    )
                    
        self.pending_requests.clear()
        log.warning("All request queues cleared")

    # Private methods

    async def _process_request_queues(self) -> None:
        """Background task to process request queues by priority."""
        log.info("Request queue processing started")
        
        while not self._shutdown_event.is_set():
            try:
                # Process requests in priority order
                request_processed = False
                
                for priority in RequestPriority:
                    queue = self.request_queues[priority]
                    
                    if queue and await self._can_process_request():
                        request = queue.popleft()
                        asyncio.create_task(self._execute_request(request))
                        request_processed = True
                        break
                        
                # If no request was processed, wait a bit
                if not request_processed:
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                log.error("Error in request queue processing: %s", e)
                await asyncio.sleep(1)
                
        log.info("Request queue processing stopped")

    async def _execute_request(self, request: Dict) -> None:
        """Execute a single queued request."""
        try:
            result = await self.execute_with_quota_management(
                request["func"],
                *request["args"],
                priority=request["priority"],
                **request["kwargs"]
            )
            
            if not request["future"].done():
                request["future"].set_result(result)
                
        except Exception as e:
            if not request["future"].done():
                request["future"].set_exception(e)
                
        finally:
            # Clean up pending requests
            if request["id"] in self.pending_requests:
                del self.pending_requests[request["id"]]
                
            self.metrics["requests_processed"] += 1

    async def _can_process_request(self) -> bool:
        """Check if we can process a request right now."""
        # Check circuit breaker
        if self.circuit_state == CircuitBreakerState.OPEN:
            # Check if we should try half-open
            if time.time() >= self.circuit_next_attempt_time:
                self.circuit_state = CircuitBreakerState.HALF_OPEN
                log.info("Circuit breaker moved to HALF_OPEN state")
                return True
            return False
            
        # Check daily quota
        return await self._check_daily_quota()

    async def _check_circuit_breaker(self) -> bool:
        """Check if circuit breaker allows requests."""
        if self.circuit_state == CircuitBreakerState.OPEN:
            # Check if we should try half-open
            if time.time() >= self.circuit_next_attempt_time:
                self.circuit_state = CircuitBreakerState.HALF_OPEN
                log.info("Circuit breaker moved to HALF_OPEN state")
                return True
            return False
            
        return True

    async def _check_daily_quota(self) -> bool:
        """Check if we have daily quota remaining."""
        # Reset quota if it's a new day
        if time.time() >= self.quota_reset_time:
            self.daily_quota_used = 0
            self.quota_reset_time = self._get_next_quota_reset()
            log.info("Daily quota reset")
            
        # Check if we have quota remaining
        return self.daily_quota_used < self.daily_quota_limit

    async def _record_successful_request(self, duration: float) -> None:
        """Record a successful API request."""
        self.daily_quota_used += 1
        
        # Circuit breaker handling
        if self.circuit_state == CircuitBreakerState.HALF_OPEN:
            # Count successes in half-open state
            self.circuit_failure_count = max(0, self.circuit_failure_count - 1)
            if self.circuit_failure_count == 0:
                self.circuit_state = CircuitBreakerState.CLOSED
                log.info("Circuit breaker closed after successful requests")
                
        log.debug("Recorded successful API request (duration: %.2fs)", duration)

    async def _record_failed_request(self, error: Exception) -> None:
        """Record a failed API request."""
        self.circuit_failure_count += 1
        self.circuit_last_failure_time = time.time()
        
        # Check if we should open the circuit
        if (self.circuit_failure_count >= self.failure_threshold and 
            self.circuit_state != CircuitBreakerState.OPEN):
            
            self.circuit_state = CircuitBreakerState.OPEN
            self.circuit_next_attempt_time = time.time() + self.recovery_timeout
            self.metrics["circuit_breaker_activations"] += 1
            
            log.warning(
                "Circuit breaker opened after %d failures. Next attempt in %ds",
                self.circuit_failure_count,
                self.recovery_timeout
            )
            
        log.warning("Recorded failed API request: %s", error)

    async def _record_quota_exceeded(self) -> None:
        """Record a quota exceeded event."""
        self.metrics["quota_exceeded_events"] += 1
        
        # This might indicate we hit daily quota
        if self.daily_quota_used >= self.daily_quota_limit:
            log.warning("Daily quota limit reached: %d/%d", 
                       self.daily_quota_used, self.daily_quota_limit)

    def _get_next_quota_reset(self) -> float:
        """Get timestamp for next quota reset (midnight UTC)."""
        import datetime
        
        now = datetime.datetime.utcnow()
        tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
        return tomorrow.timestamp()


# Global quota manager instance
_quota_manager: Optional[APIQuotaManager] = None


def get_quota_manager() -> APIQuotaManager:
    """Get the global quota manager instance."""
    global _quota_manager
    if _quota_manager is None:
        _quota_manager = APIQuotaManager()
    return _quota_manager


async def execute_with_quota(
    api_function: Callable,
    *args,
    priority: RequestPriority = RequestPriority.DATA_ENRICHMENT,
    **kwargs
) -> Any:
    """Convenience function to execute API calls with quota management.
    
    Args:
        api_function: The API function to execute
        *args: Function arguments
        priority: Request priority
        **kwargs: Function keyword arguments
        
    Returns:
        API response
    """
    manager = get_quota_manager()
    return await manager.execute_with_quota_management(
        api_function, *args, priority=priority, **kwargs
    )


async def queue_api_request(
    request_func: Callable,
    args: tuple = (),
    kwargs: dict = None,
    priority: RequestPriority = RequestPriority.DATA_ENRICHMENT,
    request_id: Optional[str] = None
) -> Any:
    """Convenience function to queue API requests.
    
    Args:
        request_func: The API function to call
        args: Function arguments
        kwargs: Function keyword arguments
        priority: Request priority level
        request_id: Optional unique request ID for deduplication
        
    Returns:
        Future that will contain the API response
    """
    manager = get_quota_manager()
    return await manager.queue_request(
        request_func, args, kwargs, priority, request_id
    )
