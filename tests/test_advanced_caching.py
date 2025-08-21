"""Tests for advanced caching system."""

import asyncio
import json
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
import redis
from sqlmodel import Session, select

from bot.advanced_caching import (
    IntelligentCacheManager,
    cache_product_data,
    get_cache_manager,
    get_cached_product_data,
    invalidate_product_cache,
)
from bot.models import Cache


class TestIntelligentCacheManager:
    """Test the IntelligentCacheManager class."""

    @pytest.fixture
    def cache_manager(self):
        """Create a cache manager for testing."""
        with patch('bot.advanced_caching.redis.Redis') as mock_redis:
            # Mock Redis to be unavailable for consistent testing
            mock_redis.side_effect = redis.ConnectionError("Redis unavailable")
            manager = IntelligentCacheManager()
            return manager

    @pytest.fixture
    def cache_manager_with_redis(self):
        """Create a cache manager with Redis mocked as available."""
        with patch('bot.advanced_caching.redis.Redis') as mock_redis:
            mock_client = Mock()
            mock_client.ping.return_value = True
            mock_client.get.return_value = None
            mock_client.setex.return_value = True
            mock_client.delete.return_value = 1
            mock_client.keys.return_value = []
            mock_redis.return_value = mock_client
            
            manager = IntelligentCacheManager()
            return manager, mock_client

    def test_initialization_without_redis(self, cache_manager):
        """Test initialization when Redis is not available."""
        assert not cache_manager.redis_available
        assert cache_manager.redis_client is None
        assert cache_manager.memory_cache == {}
        assert len(cache_manager.memory_access_order) == 0

    def test_initialization_with_redis(self):
        """Test initialization when Redis is available."""
        with patch('bot.advanced_caching.redis.Redis') as mock_redis:
            mock_client = Mock()
            mock_client.ping.return_value = True
            mock_redis.return_value = mock_client
            
            manager = IntelligentCacheManager()
            assert manager.redis_available
            assert manager.redis_client is not None

    @pytest.mark.asyncio
    async def test_memory_cache_hit(self, cache_manager):
        """Test memory cache hit."""
        asin = "B0TEST123"
        test_data = {"price": 12345, "title": "Test Product"}
        
        # Store in memory cache
        await cache_manager._store_in_memory("product:B0TEST123", test_data)
        
        # Retrieve from cache
        result = await cache_manager.get_cached_product(asin)
        
        assert result == test_data
        assert cache_manager.stats["memory_hits"] == 1

    @pytest.mark.asyncio
    async def test_memory_cache_expiration(self, cache_manager):
        """Test memory cache expiration."""
        asin = "B0TEST123"
        test_data = {"price": 12345, "title": "Test Product"}
        
        # Store in memory cache with immediate expiration
        cache_key = "product:B0TEST123"
        cache_manager.memory_cache[cache_key] = {
            "data": test_data,
            "expires": datetime.utcnow() - timedelta(minutes=1)  # Expired
        }
        
        # Mock database fallback to return None
        with patch('bot.advanced_caching.get_price') as mock_get_price:
            mock_get_price.side_effect = ValueError("No price found")
            
            # Try to retrieve
            result = await cache_manager.get_cached_product(asin)
            
            assert result is None
            assert cache_key not in cache_manager.memory_cache

    @pytest.mark.asyncio
    async def test_redis_cache_hit(self):
        """Test Redis cache hit."""
        with patch('bot.advanced_caching.redis.Redis') as mock_redis:
            mock_client = Mock()
            mock_client.ping.return_value = True
            test_data = {"price": 12345, "title": "Test Product"}
            mock_client.get.return_value = json.dumps(test_data)
            mock_redis.return_value = mock_client
            
            manager = IntelligentCacheManager()
            result = await manager.get_cached_product("B0TEST123")
            
            assert result == test_data
            assert manager.stats["redis_hits"] == 1

    @pytest.mark.asyncio
    async def test_database_cache_hit(self, cache_manager):
        """Test database cache hit."""
        asin = "B0TEST123"
        
        with patch('bot.advanced_caching.get_price') as mock_get_price:
            mock_get_price.return_value = 12345
            
            result = await cache_manager.get_cached_product(asin)
            
            assert result is not None
            assert result["price"] == 12345
            assert result["source"] == "db_cache"
            assert cache_manager.stats["db_hits"] == 1

    @pytest.mark.asyncio
    async def test_cache_miss(self, cache_manager):
        """Test complete cache miss."""
        with patch('bot.advanced_caching.get_price') as mock_get_price:
            mock_get_price.side_effect = ValueError("No price found")
            
            result = await cache_manager.get_cached_product("B0NONEXISTENT")
            
            assert result is None
            assert cache_manager.stats["cache_misses"] == 1

    @pytest.mark.asyncio
    async def test_store_product_data(self, cache_manager):
        """Test storing product data in cache."""
        asin = "B0TEST123"
        test_data = {"price": 12345, "title": "Test Product"}
        
        with patch.object(cache_manager, '_store_in_database') as mock_db_store:
            await cache_manager.store_product_data(asin, test_data)
            
            # Check memory cache
            cached_data = await cache_manager._get_from_memory("product:B0TEST123")
            assert cached_data == test_data
            
            # Check database store was called
            mock_db_store.assert_called_once_with(asin, 12345)

    @pytest.mark.asyncio
    async def test_invalidate_cache(self, cache_manager):
        """Test cache invalidation."""
        asin = "B0TEST123"
        test_data = {"price": 12345}
        
        # Store some data
        await cache_manager._store_in_memory("product:B0TEST123", test_data)
        await cache_manager._store_in_memory("product:B0TEST123:offers", test_data)
        
        # Invalidate
        await cache_manager.invalidate_cache(asin)
        
        # Check that cache is cleared
        assert len(cache_manager.memory_cache) == 0

    @pytest.mark.asyncio
    async def test_warm_cache(self, cache_manager):
        """Test cache warming functionality."""
        asins = ["B0TEST123", "B0TEST456"]
        
        with patch.object(cache_manager, '_warm_single_asin') as mock_warm:
            mock_warm.return_value = None
            
            await cache_manager.warm_cache(asins)
            
            assert mock_warm.call_count == len(asins)

    @pytest.mark.asyncio
    async def test_lru_eviction(self, cache_manager):
        """Test LRU eviction in memory cache."""
        # Set small cache size for testing
        cache_manager.memory_max_size = 2
        
        # Store items beyond capacity
        await cache_manager._store_in_memory("key1", {"data": "1"})
        await cache_manager._store_in_memory("key2", {"data": "2"})
        await cache_manager._store_in_memory("key3", {"data": "3"})  # Should evict key1
        
        assert len(cache_manager.memory_cache) == 2
        assert "key1" not in cache_manager.memory_cache
        assert "key2" in cache_manager.memory_cache
        assert "key3" in cache_manager.memory_cache

    def test_build_cache_key(self, cache_manager):
        """Test cache key building."""
        asin = "B0TEST123"
        
        # Without resources
        key1 = cache_manager._build_cache_key(asin)
        assert key1 == "product:B0TEST123"
        
        # With resources
        resources = ["offers", "images"]
        key2 = cache_manager._build_cache_key(asin, resources)
        assert key2 == "product:B0TEST123:images:offers"  # Sorted

    def test_get_cache_stats(self, cache_manager):
        """Test cache statistics."""
        # Simulate some activity
        cache_manager.stats["memory_hits"] = 10
        cache_manager.stats["redis_hits"] = 5
        cache_manager.stats["db_hits"] = 3
        cache_manager.stats["cache_misses"] = 2
        
        stats = cache_manager.get_cache_stats()
        
        assert stats["memory_hits"] == 10
        assert stats["total_requests"] == 20
        assert stats["hit_rate"] == 0.9  # 18/20

    def test_clear_memory_cache(self, cache_manager):
        """Test clearing memory cache."""
        # Add some data
        cache_manager.memory_cache["test"] = {"data": "test"}
        cache_manager.memory_access_order.append("test")
        
        cache_manager.clear_memory_cache()
        
        assert len(cache_manager.memory_cache) == 0
        assert len(cache_manager.memory_access_order) == 0

    @pytest.mark.asyncio
    async def test_redis_error_handling(self):
        """Test Redis error handling."""
        with patch('bot.advanced_caching.redis.Redis') as mock_redis:
            mock_client = Mock()
            mock_client.ping.return_value = True
            mock_client.get.side_effect = redis.ConnectionError("Connection lost")
            mock_redis.return_value = mock_client
            
            manager = IntelligentCacheManager()
            
            # Should handle Redis errors gracefully
            result = await manager._get_from_redis("test_key")
            assert result is None

    @pytest.mark.asyncio
    async def test_database_error_handling(self, cache_manager):
        """Test database error handling."""
        with patch('bot.advanced_caching.get_price') as mock_get_price:
            mock_get_price.side_effect = Exception("Database error")
            
            result = await cache_manager._get_from_database("B0TEST123")
            assert result is None


class TestCacheManagerIntegration:
    """Test cache manager integration and convenience functions."""

    @pytest.mark.asyncio
    async def test_get_cached_product_data_convenience(self):
        """Test convenience function for getting cached data."""
        with patch('bot.advanced_caching.get_cache_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_manager.get_cached_product = AsyncMock(return_value={"price": 12345})
            mock_get_manager.return_value = mock_manager
            
            result = await get_cached_product_data("B0TEST123")
            
            assert result == {"price": 12345}
            mock_manager.get_cached_product.assert_called_once_with("B0TEST123", None)

    @pytest.mark.asyncio
    async def test_cache_product_data_convenience(self):
        """Test convenience function for caching data."""
        with patch('bot.advanced_caching.get_cache_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_manager.store_product_data = AsyncMock()
            mock_get_manager.return_value = mock_manager
            
            test_data = {"price": 12345}
            await cache_product_data("B0TEST123", test_data)
            
            mock_manager.store_product_data.assert_called_once_with("B0TEST123", test_data, None)

    @pytest.mark.asyncio
    async def test_invalidate_product_cache_convenience(self):
        """Test convenience function for cache invalidation."""
        with patch('bot.advanced_caching.get_cache_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_manager.invalidate_cache = AsyncMock()
            mock_get_manager.return_value = mock_manager
            
            await invalidate_product_cache("B0TEST123")
            
            mock_manager.invalidate_cache.assert_called_once_with("B0TEST123")

    def test_global_cache_manager_singleton(self):
        """Test that cache manager is a singleton."""
        with patch('bot.advanced_caching.redis.Redis') as mock_redis:
            mock_redis.side_effect = redis.ConnectionError("Redis unavailable")
            
            manager1 = get_cache_manager()
            manager2 = get_cache_manager()
            
            assert manager1 is manager2


class TestCacheManagerPerformance:
    """Test cache manager performance characteristics."""

    @pytest.fixture
    def cache_manager(self):
        """Create a cache manager for performance testing."""
        with patch('bot.advanced_caching.redis.Redis') as mock_redis:
            # Mock Redis to be unavailable for consistent testing
            mock_redis.side_effect = redis.ConnectionError("Redis unavailable")
            manager = IntelligentCacheManager()
            return manager

    @pytest.mark.asyncio
    async def test_concurrent_access(self, cache_manager):
        """Test concurrent cache access."""
        asin = "B0TEST123"
        test_data = {"price": 12345}
        
        # Store data
        await cache_manager.store_product_data(asin, test_data)
        
        # Concurrent reads
        tasks = [
            cache_manager.get_cached_product(asin)
            for _ in range(10)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All should return the same data
        for result in results:
            assert result == test_data

    @pytest.mark.asyncio
    async def test_cache_warming_performance(self, cache_manager):
        """Test cache warming with multiple ASINs."""
        asins = [f"B0TEST{i:03d}" for i in range(20)]
        
        with patch.object(cache_manager, '_warm_single_asin') as mock_warm:
            mock_warm.return_value = None
            
            start_time = time.time()
            await cache_manager.warm_cache(asins)
            duration = time.time() - start_time
            
            # Should complete reasonably quickly
            assert duration < 5.0  # 5 seconds max
            assert mock_warm.call_count == len(asins)

    def test_memory_efficiency(self, cache_manager):
        """Test memory usage with large number of cache entries."""
        # Store many items up to the limit
        max_size = cache_manager.memory_max_size
        
        for i in range(max_size + 10):
            key = f"key_{i}"
            data = {"data": f"value_{i}"}
            asyncio.run(cache_manager._store_in_memory(key, data))
        
        # Should not exceed max size
        assert len(cache_manager.memory_cache) <= max_size
        assert len(cache_manager.memory_access_order) <= max_size


@pytest.mark.integration
class TestCacheManagerIntegrationWithDatabase:
    """Integration tests with actual database operations."""

    @pytest.fixture
    def setup_database(self):
        """Set up test database."""
        from bot.cache_service import engine
        from bot.models import SQLModel
        
        SQLModel.metadata.create_all(engine)
        yield
        # Cleanup handled by test framework

    @pytest.mark.asyncio
    async def test_database_integration(self, setup_database):
        """Test integration with actual database."""
        asin = "B0TEST123"
        price = 12345
        
        # Store in database via cache service
        with patch('bot.advanced_caching.get_price') as mock_get_price:
            mock_get_price.return_value = price
            
            manager = IntelligentCacheManager()
            manager.redis_available = False  # Force database lookup
            
            result = await manager.get_cached_product(asin)
            
            assert result is not None
            assert result["price"] == price
            assert result["source"] == "db_cache"

    @pytest.mark.asyncio
    async def test_database_storage(self, setup_database):
        """Test storing data in database."""
        from bot.cache_service import engine
        from bot.models import Cache
        
        manager = IntelligentCacheManager()
        asin = "B0TEST123"
        price = 12345
        
        await manager._store_in_database(asin, price)
        
        # Verify storage
        with Session(engine) as session:
            cache_entry = session.get(Cache, asin)
            assert cache_entry is not None
            assert cache_entry.price == price
