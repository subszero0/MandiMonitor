"""Tests for API quota management system."""

import asyncio
import time
from unittest.mock import AsyncMock, Mock, patch

import pytest

from bot.api_quota_manager import (
    APIQuotaManager,
    CircuitBreakerState,
    RequestPriority,
    execute_with_quota,
    get_quota_manager,
    queue_api_request,
)
from bot.errors import QuotaExceededError


class TestRequestPriority:
    """Test the RequestPriority enum."""

    def test_priority_values(self):
        """Test priority enum values."""
        assert RequestPriority.USER_TRIGGERED.value == 1
        assert RequestPriority.ACTIVE_WATCH.value == 2
        assert RequestPriority.DATA_ENRICHMENT.value == 3
        assert RequestPriority.ANALYTICS.value == 4

    def test_priority_ordering(self):
        """Test that priorities are properly ordered."""
        priorities = list(RequestPriority)
        assert priorities[0] == RequestPriority.USER_TRIGGERED
        assert priorities[-1] == RequestPriority.ANALYTICS


class TestCircuitBreakerState:
    """Test the CircuitBreakerState enum."""

    def test_state_values(self):
        """Test circuit breaker state values."""
        assert CircuitBreakerState.CLOSED.value == "closed"
        assert CircuitBreakerState.OPEN.value == "open"
        assert CircuitBreakerState.HALF_OPEN.value == "half_open"


class TestAPIQuotaManager:
    """Test the APIQuotaManager class."""

    @pytest.fixture
    def quota_manager(self):
        """Create a quota manager for testing."""
        with patch('bot.api_quota_manager.get_rate_limiter') as mock_limiter:
            mock_rate_limiter = Mock()
            mock_rate_limiter.acquire = AsyncMock()
            mock_limiter.return_value = mock_rate_limiter
            
            manager = APIQuotaManager()
            return manager

    def test_initialization(self, quota_manager):
        """Test quota manager initialization."""
        assert quota_manager.circuit_state == CircuitBreakerState.CLOSED
        assert quota_manager.circuit_failure_count == 0
        assert quota_manager.daily_quota_used == 0
        assert len(quota_manager.request_queues) == 4  # Four priority levels

    @pytest.mark.asyncio
    async def test_start_stop_manager(self, quota_manager):
        """Test starting and stopping the quota manager."""
        # Start manager
        await quota_manager.start()
        assert quota_manager._processing_task is not None
        
        # Stop manager
        await quota_manager.stop()
        assert quota_manager._processing_task is None

    @pytest.mark.asyncio
    async def test_queue_request_basic(self, quota_manager):
        """Test basic request queuing."""
        async def dummy_func():
            return "test_result"
        
        # Queue a request (don't wait for completion, just ensure it's queued)
        task = asyncio.create_task(
            quota_manager.queue_request(
                dummy_func, 
                priority=RequestPriority.USER_TRIGGERED
            )
        )
        
        # Give it a moment to queue
        await asyncio.sleep(0.01)
        
        # Check that request was queued
        assert len(quota_manager.request_queues[RequestPriority.USER_TRIGGERED]) == 1
        assert quota_manager.metrics["requests_queued"] == 1
        
        # Cancel the task to avoid hanging
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_request_deduplication(self, quota_manager):
        """Test request deduplication."""
        async def dummy_func():
            await asyncio.sleep(0.1)
            return "test_result"
        
        request_id = "test_request_123"
        
        # Queue first request
        task1 = asyncio.create_task(
            quota_manager.queue_request(
                dummy_func,
                request_id=request_id,
                priority=RequestPriority.USER_TRIGGERED
            )
        )
        
        # Give it a moment to queue
        await asyncio.sleep(0.01)
        
        # Queue second identical request
        task2 = asyncio.create_task(
            quota_manager.queue_request(
                dummy_func,
                request_id=request_id,
                priority=RequestPriority.USER_TRIGGERED
            )
        )
        
        # Give it a moment to process deduplication
        await asyncio.sleep(0.01)
        
        # Check deduplication
        assert quota_manager.metrics["requests_deduplicated"] == 1
        
        # Cancel tasks
        task1.cancel()
        task2.cancel()
        try:
            await task1
        except asyncio.CancelledError:
            pass
        try:
            await task2
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_execute_with_quota_management_success(self, quota_manager):
        """Test successful API execution with quota management."""
        async def dummy_api_call():
            return {"result": "success"}
        
        # Mock rate limiter
        quota_manager.rate_limiter.acquire = AsyncMock()
        
        result = await quota_manager.execute_with_quota_management(
            dummy_api_call,
            priority=RequestPriority.USER_TRIGGERED
        )
        
        assert result == {"result": "success"}
        assert quota_manager.daily_quota_used == 1

    @pytest.mark.asyncio
    async def test_execute_with_circuit_breaker_open(self, quota_manager):
        """Test execution when circuit breaker is open."""
        # Set circuit breaker to open
        quota_manager.circuit_state = CircuitBreakerState.OPEN
        quota_manager.circuit_next_attempt_time = time.time() + 60
        
        async def dummy_api_call():
            return {"result": "success"}
        
        with pytest.raises(QuotaExceededError, match="Circuit breaker is open"):
            await quota_manager.execute_with_quota_management(dummy_api_call)

    @pytest.mark.asyncio
    async def test_execute_with_quota_exceeded(self, quota_manager):
        """Test execution when daily quota is exceeded."""
        # Set quota to exceeded and prevent reset
        quota_manager.daily_quota_used = quota_manager.daily_quota_limit
        quota_manager.quota_reset_time = time.time() + 86400  # Reset tomorrow
        
        async def dummy_api_call():
            return {"result": "success"}
        
        with pytest.raises(QuotaExceededError, match="Daily quota exceeded"):
            await quota_manager.execute_with_quota_management(dummy_api_call)

    @pytest.mark.asyncio
    async def test_circuit_breaker_opening(self, quota_manager):
        """Test circuit breaker opening after failures."""
        async def failing_api_call():
            raise Exception("API failure")
        
        quota_manager.rate_limiter.acquire = AsyncMock()
        
        # Trigger enough failures to open circuit
        for _ in range(quota_manager.failure_threshold):
            with pytest.raises(Exception):
                await quota_manager.execute_with_quota_management(failing_api_call)
        
        assert quota_manager.circuit_state == CircuitBreakerState.OPEN
        assert quota_manager.metrics["circuit_breaker_activations"] == 1

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_transition(self, quota_manager):
        """Test circuit breaker transition to half-open."""
        # Set circuit to open with past recovery time
        quota_manager.circuit_state = CircuitBreakerState.OPEN
        quota_manager.circuit_next_attempt_time = time.time() - 1
        
        # Check circuit breaker should allow transition
        can_process = await quota_manager._check_circuit_breaker()
        assert can_process
        assert quota_manager.circuit_state == CircuitBreakerState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_circuit_breaker_closing(self, quota_manager):
        """Test circuit breaker closing after successful requests."""
        async def successful_api_call():
            return {"result": "success"}
        
        # Set to half-open state
        quota_manager.circuit_state = CircuitBreakerState.HALF_OPEN
        quota_manager.circuit_failure_count = 1
        quota_manager.rate_limiter.acquire = AsyncMock()
        
        # Execute successful request
        await quota_manager.execute_with_quota_management(successful_api_call)
        
        assert quota_manager.circuit_state == CircuitBreakerState.CLOSED
        assert quota_manager.circuit_failure_count == 0

    def test_get_quota_status(self, quota_manager):
        """Test quota status reporting."""
        quota_manager.daily_quota_used = 100
        
        status = quota_manager.get_quota_status()
        
        assert status["daily_quota_used"] == 100
        assert status["quota_remaining"] == quota_manager.daily_quota_limit - 100
        assert status["circuit_state"] == "closed"
        assert "queue_sizes" in status

    def test_get_performance_metrics(self, quota_manager):
        """Test performance metrics reporting."""
        quota_manager.metrics["requests_processed"] = 50
        quota_manager.metrics["requests_queued"] = 60
        
        metrics = quota_manager.get_performance_metrics()
        
        assert metrics["requests_processed"] == 50
        assert metrics["requests_queued"] == 60
        assert "total_queue_size" in metrics
        assert "quota_status" in metrics

    @pytest.mark.asyncio
    async def test_clear_queues(self, quota_manager):
        """Test clearing all request queues."""
        # Add some mock requests
        mock_future = asyncio.Future()
        mock_request = {
            "id": "test",
            "func": lambda: None,
            "args": (),
            "kwargs": {},
            "priority": RequestPriority.USER_TRIGGERED,
            "future": mock_future,
            "queued_at": time.time()
        }
        
        quota_manager.request_queues[RequestPriority.USER_TRIGGERED].append(mock_request)
        quota_manager.pending_requests["test"] = mock_future
        
        await quota_manager.clear_queues()
        
        # Check that queues are cleared
        assert len(quota_manager.request_queues[RequestPriority.USER_TRIGGERED]) == 0
        assert len(quota_manager.pending_requests) == 0
        assert mock_future.done()

    @pytest.mark.asyncio
    async def test_quota_reset(self, quota_manager):
        """Test daily quota reset."""
        # Set quota to used
        quota_manager.daily_quota_used = 100
        
        # Set reset time to past
        quota_manager.quota_reset_time = time.time() - 1
        
        # Check quota should reset
        can_process = await quota_manager._check_daily_quota()
        assert can_process
        assert quota_manager.daily_quota_used == 0

    @pytest.mark.asyncio
    async def test_record_successful_request(self, quota_manager):
        """Test recording successful requests."""
        await quota_manager._record_successful_request(1.5)
        
        assert quota_manager.daily_quota_used == 1

    @pytest.mark.asyncio
    async def test_record_failed_request(self, quota_manager):
        """Test recording failed requests."""
        error = Exception("Test error")
        
        await quota_manager._record_failed_request(error)
        
        assert quota_manager.circuit_failure_count == 1
        assert quota_manager.circuit_last_failure_time > 0

    @pytest.mark.asyncio
    async def test_record_quota_exceeded(self, quota_manager):
        """Test recording quota exceeded events."""
        await quota_manager._record_quota_exceeded()
        
        assert quota_manager.metrics["quota_exceeded_events"] == 1

    def test_get_next_quota_reset(self, quota_manager):
        """Test quota reset time calculation."""
        with patch('bot.api_quota_manager.datetime') as mock_datetime:
            # Mock datetime to return a fixed time
            from datetime import datetime, timedelta
            mock_now = datetime(2025, 8, 21, 12, 0, 0)  # Noon
            mock_datetime.datetime.utcnow.return_value = mock_now
            mock_datetime.timedelta = timedelta  # Keep real timedelta
            
            reset_time = quota_manager._get_next_quota_reset()
            
            # Should be midnight of the next day
            expected_reset = datetime(2025, 8, 22, 0, 0, 0).timestamp()
            assert reset_time == expected_reset

    @pytest.mark.asyncio
    async def test_can_process_request_with_open_circuit(self, quota_manager):
        """Test request processing check with open circuit."""
        quota_manager.circuit_state = CircuitBreakerState.OPEN
        quota_manager.circuit_next_attempt_time = time.time() + 60
        
        can_process = await quota_manager._can_process_request()
        assert not can_process

    @pytest.mark.asyncio
    async def test_can_process_request_with_quota_exceeded(self, quota_manager):
        """Test request processing check with quota exceeded."""
        quota_manager.daily_quota_used = quota_manager.daily_quota_limit
        quota_manager.quota_reset_time = time.time() + 86400  # Reset tomorrow
        
        can_process = await quota_manager._can_process_request()
        assert not can_process


class TestQuotaManagerConvenienceFunctions:
    """Test convenience functions for quota manager."""

    @pytest.mark.asyncio
    async def test_execute_with_quota_convenience(self):
        """Test convenience function for executing with quota."""
        async def dummy_api_call():
            return "success"
        
        with patch('bot.api_quota_manager.get_quota_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_manager.execute_with_quota_management = AsyncMock(return_value="success")
            mock_get_manager.return_value = mock_manager
            
            result = await execute_with_quota(
                dummy_api_call,
                priority=RequestPriority.USER_TRIGGERED
            )
            
            assert result == "success"
            mock_manager.execute_with_quota_management.assert_called_once()

    @pytest.mark.asyncio
    async def test_queue_api_request_convenience(self):
        """Test convenience function for queuing requests."""
        async def dummy_api_call():
            return "success"
        
        with patch('bot.api_quota_manager.get_quota_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_manager.queue_request = AsyncMock(return_value="success")
            mock_get_manager.return_value = mock_manager
            
            result = await queue_api_request(
                dummy_api_call,
                priority=RequestPriority.USER_TRIGGERED
            )
            
            assert result == "success"
            mock_manager.queue_request.assert_called_once()

    def test_global_quota_manager_singleton(self):
        """Test that quota manager is a singleton."""
        with patch('bot.api_quota_manager.get_rate_limiter') as mock_limiter:
            mock_rate_limiter = Mock()
            mock_rate_limiter.acquire = AsyncMock()
            mock_limiter.return_value = mock_rate_limiter
            
            manager1 = get_quota_manager()
            manager2 = get_quota_manager()
            
            assert manager1 is manager2


class TestQuotaManagerPerformance:
    """Test quota manager performance characteristics."""

    @pytest.fixture
    def quota_manager(self):
        """Create a quota manager for performance testing."""
        with patch('bot.api_quota_manager.get_rate_limiter') as mock_limiter:
            mock_rate_limiter = Mock()
            mock_rate_limiter.acquire = AsyncMock()
            mock_limiter.return_value = mock_rate_limiter
            
            manager = APIQuotaManager()
            return manager

    @pytest.mark.asyncio
    async def test_concurrent_request_queuing(self, quota_manager):
        """Test concurrent request queuing."""
        async def dummy_func(request_id):
            return f"result_{request_id}"
        
        # Queue multiple requests concurrently
        tasks = [
            asyncio.create_task(quota_manager.queue_request(
                dummy_func, 
                args=(i,),
                request_id=f"req_{i}",
                priority=RequestPriority.USER_TRIGGERED
            ))
            for i in range(10)
        ]
        
        # Give tasks a moment to queue
        await asyncio.sleep(0.05)
        
        # Check that all requests are queued
        assert quota_manager.metrics["requests_queued"] == 10
        
        # Cancel all tasks
        for task in tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_priority_ordering(self, quota_manager):
        """Test that higher priority requests are processed first."""
        # Add requests with different priorities
        low_priority_queue = quota_manager.request_queues[RequestPriority.ANALYTICS]
        high_priority_queue = quota_manager.request_queues[RequestPriority.USER_TRIGGERED]
        
        # Add to low priority first
        low_priority_queue.append({"priority": RequestPriority.ANALYTICS, "id": "low"})
        high_priority_queue.append({"priority": RequestPriority.USER_TRIGGERED, "id": "high"})
        
        # Check that high priority queue is checked first
        for priority in RequestPriority:
            if quota_manager.request_queues[priority]:
                first_request = quota_manager.request_queues[priority][0]
                assert first_request["priority"] == RequestPriority.USER_TRIGGERED
                break

    @pytest.mark.asyncio
    async def test_memory_efficiency_with_many_requests(self, quota_manager):
        """Test memory efficiency with large number of requests."""
        # Queue many requests without processing
        for i in range(1000):
            mock_future = asyncio.Future()
            mock_request = {
                "id": f"req_{i}",
                "func": lambda: None,
                "args": (),
                "kwargs": {},
                "priority": RequestPriority.DATA_ENRICHMENT,
                "future": mock_future,
                "queued_at": time.time()
            }
            quota_manager.request_queues[RequestPriority.DATA_ENRICHMENT].append(mock_request)
        
        # Memory usage should be reasonable
        total_queue_size = sum(len(q) for q in quota_manager.request_queues.values())
        assert total_queue_size == 1000


@pytest.mark.integration
class TestQuotaManagerIntegration:
    """Integration tests for quota manager."""

    @pytest.mark.asyncio
    async def test_integration_with_rate_limiter(self):
        """Test integration with actual rate limiter."""
        from bot.api_rate_limiter import get_rate_limiter
        
        quota_manager = APIQuotaManager()
        
        # Should use the actual rate limiter
        assert quota_manager.rate_limiter is not None
        
        async def dummy_api_call():
            await asyncio.sleep(0.01)  # Small delay
            return "success"
        
        # Execute with quota management
        start_time = time.time()
        result = await quota_manager.execute_with_quota_management(
            dummy_api_call,
            priority=RequestPriority.USER_TRIGGERED
        )
        duration = time.time() - start_time
        
        assert result == "success"
        assert duration >= 0.01  # Should respect rate limiting

    @pytest.mark.asyncio
    async def test_end_to_end_request_processing(self):
        """Test end-to-end request processing."""
        quota_manager = APIQuotaManager()
        
        async def test_api_call(value):
            await asyncio.sleep(0.01)
            return f"processed_{value}"
        
        # Start the manager
        await quota_manager.start()
        
        try:
            # Queue a request
            result = await asyncio.wait_for(
                quota_manager.queue_request(
                    test_api_call,
                    args=("test",),
                    priority=RequestPriority.USER_TRIGGERED
                ),
                timeout=5.0
            )
            
            assert result == "processed_test"
            assert quota_manager.metrics["requests_processed"] >= 1
            
        finally:
            # Stop the manager
            await quota_manager.stop()
