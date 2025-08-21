"""Tests for API rate limiter."""

import asyncio
import time
from unittest.mock import patch

import pytest

from bot.api_rate_limiter import APIRateLimiter, get_rate_limiter, acquire_api_permission


@pytest.fixture
def rate_limiter():
    """Create a fresh rate limiter for testing."""
    return APIRateLimiter()


@pytest.mark.asyncio
async def test_rate_limiter_respects_limits(rate_limiter):
    """Test rate limiter prevents API abuse."""
    start_time = time.time()
    
    # Make 3 requests in sequence
    await rate_limiter.acquire()
    await rate_limiter.acquire()
    await rate_limiter.acquire()
    
    end_time = time.time()
    
    # Should take at least 2 seconds (1 second between each request after the first)
    elapsed = end_time - start_time
    assert elapsed >= 2.0, f"Rate limiting not enforced, took {elapsed} seconds"


@pytest.mark.asyncio
async def test_burst_limit_handling(rate_limiter):
    """Test burst limit is properly managed."""
    start_time = time.time()
    
    # Make 10 requests quickly (should use burst capacity)
    tasks = []
    for _ in range(10):
        tasks.append(rate_limiter.acquire())
    
    await asyncio.gather(*tasks)
    
    # Now try one more request - should be delayed by burst window
    await rate_limiter.acquire()
    
    end_time = time.time()
    elapsed = end_time - start_time
    
    # Should take at least 10 seconds due to burst window
    assert elapsed >= 10.0, f"Burst limit not enforced, took {elapsed} seconds"


@pytest.mark.asyncio
async def test_priority_handling(rate_limiter):
    """Test priority affects rate limiting timing."""
    # Test high priority gets faster processing
    start_time = time.time()
    await rate_limiter.acquire("high")
    await rate_limiter.acquire("high")
    high_priority_time = time.time() - start_time
    
    # Reset rate limiter state
    rate_limiter.requests.clear()
    
    # Test normal priority
    start_time = time.time()
    await rate_limiter.acquire("normal")
    await rate_limiter.acquire("normal")
    normal_priority_time = time.time() - start_time
    
    # High priority should be faster
    assert high_priority_time < normal_priority_time


@pytest.mark.asyncio
async def test_usage_statistics(rate_limiter):
    """Test usage statistics are accurate."""
    # Initially empty
    stats = rate_limiter.get_current_usage()
    assert stats["requests_last_second"] == 0
    assert stats["burst_requests"] == 0
    
    # After one request
    await rate_limiter.acquire()
    stats = rate_limiter.get_current_usage()
    assert stats["requests_last_second"] == 1
    assert stats["burst_requests"] == 1
    
    # Check configuration values
    assert stats["rate_limit"] == 1
    assert stats["burst_limit"] == 10
    assert stats["burst_window"] == 10


@pytest.mark.asyncio
async def test_wait_for_capacity(rate_limiter):
    """Test capacity waiting functionality."""
    # Initially should have capacity
    wait_time = await rate_limiter.wait_for_capacity(1)
    assert wait_time == 0.0
    
    # Fill burst capacity
    for _ in range(10):
        await rate_limiter.acquire()
    
    # Now should need to wait
    wait_time = await rate_limiter.wait_for_capacity(1)
    assert wait_time > 0


@pytest.mark.asyncio
async def test_concurrent_requests(rate_limiter):
    """Test rate limiter handles concurrent requests correctly."""
    async def make_request():
        await rate_limiter.acquire()
        return time.time()
    
    # Make 5 concurrent requests
    tasks = [make_request() for _ in range(5)]
    timestamps = await asyncio.gather(*tasks)
    
    # Verify requests were properly spaced
    for i in range(1, len(timestamps)):
        time_diff = timestamps[i] - timestamps[i-1]
        # Allow some tolerance for test timing
        assert time_diff >= 0.9, f"Requests too close: {time_diff} seconds apart"


@pytest.mark.asyncio
async def test_global_rate_limiter():
    """Test global rate limiter functionality."""
    limiter1 = get_rate_limiter()
    limiter2 = get_rate_limiter()
    
    # Should be the same instance
    assert limiter1 is limiter2


@pytest.mark.asyncio
async def test_acquire_api_permission():
    """Test convenience function for API permission."""
    start_time = time.time()
    
    # Make two calls
    await acquire_api_permission("normal")
    await acquire_api_permission("high")
    
    end_time = time.time()
    elapsed = end_time - start_time
    
    # Should respect rate limiting
    assert elapsed >= 0.8  # Allow some tolerance


@pytest.mark.asyncio
async def test_rate_limiter_thread_safety():
    """Test rate limiter is thread-safe."""
    rate_limiter = APIRateLimiter()
    
    async def concurrent_acquire():
        await rate_limiter.acquire()
        return True
    
    # Launch many concurrent requests
    tasks = [concurrent_acquire() for _ in range(20)]
    results = await asyncio.gather(*tasks)
    
    # All should succeed
    assert all(results)
    assert len(results) == 20


@pytest.mark.asyncio
async def test_rate_limiter_cleanup():
    """Test old requests are properly cleaned up."""
    rate_limiter = APIRateLimiter()
    
    # Make a request
    await rate_limiter.acquire()
    assert len(rate_limiter.requests) == 1
    assert len(rate_limiter.burst_requests) == 1
    
    # Wait for cleanup time
    await asyncio.sleep(1.1)
    
    # Check usage - should trigger cleanup
    stats = rate_limiter.get_current_usage()
    assert stats["requests_last_second"] == 0


@pytest.mark.asyncio
async def test_rate_limiter_with_config():
    """Test rate limiter uses configuration values."""
    with patch('bot.api_rate_limiter.settings') as mock_settings:
        mock_settings.PAAPI_RATE_LIMIT_PER_SECOND = 2
        mock_settings.PAAPI_BURST_LIMIT = 5
        mock_settings.PAAPI_BURST_WINDOW_SECONDS = 5
        
        rate_limiter = APIRateLimiter()
        
        assert rate_limiter.rate_limit == 2
        assert rate_limiter.burst_limit == 5
        assert rate_limiter.burst_window == 5


@pytest.mark.asyncio
async def test_rate_limiter_performance():
    """Test rate limiter performance under load."""
    rate_limiter = APIRateLimiter()
    
    start_time = time.time()
    
    # Make many sequential requests
    for _ in range(10):
        await rate_limiter.acquire("low")
    
    end_time = time.time()
    elapsed = end_time - start_time
    
    # Should complete in reasonable time with proper spacing
    expected_min_time = 9.0  # 9 seconds for 10 requests with 1 second spacing
    expected_max_time = 15.0  # Allow some overhead
    
    assert expected_min_time <= elapsed <= expected_max_time, f"Performance issue: took {elapsed} seconds"


@pytest.mark.asyncio
async def test_edge_cases():
    """Test edge cases and error conditions."""
    rate_limiter = APIRateLimiter()
    
    # Test with empty priority (should default to normal)
    await rate_limiter.acquire("")
    
    # Test with None priority (should handle gracefully)
    await rate_limiter.acquire(None)
    
    # Test invalid priority (should handle gracefully)
    await rate_limiter.acquire("invalid_priority")
