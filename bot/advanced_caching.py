"""Advanced multi-tier caching system for MandiMonitor Bot.

This module provides intelligent caching built on the existing cache_service.py
with multi-tier caching including memory, Redis, and database tiers.
"""

import asyncio
import json
import time
from collections import deque
from datetime import datetime, timedelta
from logging import getLogger
from typing import Any, Dict, List, Optional

import redis
from sqlmodel import Session

from .cache_service import engine, get_price
from .config import settings
from .models import Cache

log = getLogger(__name__)


class IntelligentCacheManager:
    """Advanced multi-tier caching extending the existing cache_service.py.
    
    Provides three tiers of caching:
    1. Memory cache (1 hour) - Fastest access
    2. Redis cache (24 hours) - Medium speed
    3. Database cache (existing Cache model) - Slowest but persistent
    """

    def __init__(self):
        """Initialize the intelligent cache manager."""
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        self.memory_max_size = 1000  # Maximum number of items in memory
        self.memory_access_order = deque()  # LRU tracking
        
        # Try to initialize Redis client
        try:
            self.redis_client = redis.Redis(
                host='localhost',
                port=6379,
                db=0,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test Redis connection
            self.redis_client.ping()
            self.redis_available = True
            log.info("Redis connection established for advanced caching")
        except (redis.ConnectionError, redis.TimeoutError) as e:
            log.warning("Redis not available, falling back to memory + database cache: %s", e)
            self.redis_client = None
            self.redis_available = False
        
        # Cache statistics
        self.stats = {
            "memory_hits": 0,
            "redis_hits": 0,
            "db_hits": 0,
            "api_calls": 0,
            "cache_misses": 0
        }

    async def get_cached_product(self, asin: str, resources: List[str] = None) -> Optional[Dict]:
        """Get cached product data with multi-tier lookup.
        
        Args:
            asin: Amazon Standard Identification Number
            resources: Optional list of PA-API resources needed
            
        Returns:
            Cached product data or None if not found
        """
        cache_key = self._build_cache_key(asin, resources)
        
        # Level 1: Memory cache (1 hour)
        memory_data = await self._get_from_memory(cache_key)
        if memory_data:
            self.stats["memory_hits"] += 1
            log.debug("Cache hit (memory) for key: %s", cache_key)
            return memory_data
            
        # Level 2: Redis cache (24 hours)
        if self.redis_available:
            redis_data = await self._get_from_redis(cache_key)
            if redis_data:
                self.stats["redis_hits"] += 1
                log.debug("Cache hit (redis) for key: %s", cache_key)
                # Store in memory cache for future access
                await self._store_in_memory(cache_key, redis_data)
                return redis_data
                
        # Level 3: Database cache (existing Cache model)
        if not resources or "price" in str(resources).lower():
            db_data = await self._get_from_database(asin)
            if db_data:
                self.stats["db_hits"] += 1
                log.debug("Cache hit (database) for ASIN: %s", asin)
                # Store in higher tiers
                await self._store_in_memory(cache_key, db_data)
                if self.redis_available:
                    await self._store_in_redis(cache_key, db_data, ttl=86400)
                return db_data
                
        # Cache miss
        self.stats["cache_misses"] += 1
        log.debug("Cache miss for key: %s", cache_key)
        return None

    async def store_product_data(self, asin: str, data: Dict, resources: List[str] = None) -> None:
        """Store product data in all available cache tiers.
        
        Args:
            asin: Amazon Standard Identification Number
            data: Product data to cache
            resources: Optional list of PA-API resources cached
        """
        cache_key = self._build_cache_key(asin, resources)
        
        # Store in all available tiers
        await self._store_in_memory(cache_key, data)
        
        if self.redis_available:
            await self._store_in_redis(cache_key, data, ttl=86400)  # 24 hours
            
        # Store basic price data in database if available
        if "price" in data:
            await self._store_in_database(asin, data["price"])

    async def invalidate_cache(self, asin: str) -> None:
        """Invalidate all cached data for a specific ASIN.
        
        Args:
            asin: Amazon Standard Identification Number to invalidate
        """
        # Invalidate memory cache
        keys_to_remove = [key for key in self.memory_cache.keys() if asin in key]
        for key in keys_to_remove:
            self.memory_cache.pop(key, None)
            # Remove from access order tracking
            try:
                self.memory_access_order.remove(key)
            except ValueError:
                pass
                
        # Invalidate Redis cache
        if self.redis_available:
            try:
                pattern = f"*{asin}*"
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
                    log.debug("Invalidated %d Redis keys for ASIN: %s", len(keys), asin)
            except Exception as e:
                log.warning("Failed to invalidate Redis cache for ASIN %s: %s", asin, e)
                
        log.info("Cache invalidated for ASIN: %s", asin)

    async def warm_cache(self, asins: List[str], resources: List[str] = None) -> None:
        """Warm cache for a list of ASINs.
        
        Args:
            asins: List of ASINs to warm cache for
            resources: Optional PA-API resources to cache
        """
        log.info("Starting cache warming for %d ASINs", len(asins))
        
        # Process ASINs in batches to avoid overwhelming the system
        batch_size = 10
        for i in range(0, len(asins), batch_size):
            batch = asins[i:i + batch_size]
            
            tasks = []
            for asin in batch:
                tasks.append(self._warm_single_asin(asin, resources))
                
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Small delay between batches
            await asyncio.sleep(1)
            
        log.info("Cache warming completed for %d ASINs", len(asins))

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics.
        
        Returns:
            Dictionary containing cache statistics
        """
        total_requests = sum([
            self.stats["memory_hits"],
            self.stats["redis_hits"], 
            self.stats["db_hits"],
            self.stats["cache_misses"]
        ])
        
        hit_rate = (
            self.stats["memory_hits"] + 
            self.stats["redis_hits"] + 
            self.stats["db_hits"]
        ) / max(total_requests, 1)
        
        return {
            **self.stats,
            "total_requests": total_requests,
            "hit_rate": hit_rate,
            "memory_cache_size": len(self.memory_cache),
            "redis_available": self.redis_available
        }

    def clear_memory_cache(self) -> None:
        """Clear the memory cache."""
        self.memory_cache.clear()
        self.memory_access_order.clear()
        log.info("Memory cache cleared")

    # Private methods

    def _build_cache_key(self, asin: str, resources: List[str] = None) -> str:
        """Build cache key from ASIN and resources."""
        if resources:
            resource_str = ":".join(sorted(resources))
            return f"product:{asin}:{resource_str}"
        return f"product:{asin}"

    async def _get_from_memory(self, cache_key: str) -> Optional[Dict]:
        """Get data from memory cache."""
        if cache_key in self.memory_cache:
            cache_entry = self.memory_cache[cache_key]
            
            # Check expiration (1 hour)
            if cache_entry["expires"] > datetime.utcnow():
                # Update access order for LRU
                try:
                    self.memory_access_order.remove(cache_key)
                except ValueError:
                    pass
                self.memory_access_order.append(cache_key)
                return cache_entry["data"]
            else:
                # Expired, remove from cache
                self.memory_cache.pop(cache_key, None)
                try:
                    self.memory_access_order.remove(cache_key)
                except ValueError:
                    pass
                    
        return None

    async def _get_from_redis(self, cache_key: str) -> Optional[Dict]:
        """Get data from Redis cache."""
        if not self.redis_available:
            return None
            
        try:
            redis_data = self.redis_client.get(cache_key)
            if redis_data:
                return json.loads(redis_data)
        except Exception as e:
            log.warning("Redis get failed for key %s: %s", cache_key, e)
            
        return None

    async def _get_from_database(self, asin: str) -> Optional[Dict]:
        """Get data from database cache using existing get_price function."""
        try:
            # Use existing synchronous get_price function
            price = get_price(asin)
            if price:
                return {
                    "price": price,
                    "source": "db_cache",
                    "cached_at": datetime.utcnow().isoformat()
                }
        except Exception as e:
            log.debug("Database cache lookup failed for ASIN %s: %s", asin, e)
            
        return None

    async def _store_in_memory(self, cache_key: str, data: Dict) -> None:
        """Store data in memory cache with LRU eviction."""
        # Check if we need to evict old entries
        if len(self.memory_cache) >= self.memory_max_size:
            # Remove oldest entry (LRU)
            if self.memory_access_order:
                oldest_key = self.memory_access_order.popleft()
                self.memory_cache.pop(oldest_key, None)
                
        # Store new entry
        self.memory_cache[cache_key] = {
            "data": data,
            "expires": datetime.utcnow() + timedelta(hours=1)
        }
        
        # Update access order
        try:
            self.memory_access_order.remove(cache_key)
        except ValueError:
            pass
        self.memory_access_order.append(cache_key)

    async def _store_in_redis(self, cache_key: str, data: Dict, ttl: int = 86400) -> None:
        """Store data in Redis cache."""
        if not self.redis_available:
            return
            
        try:
            self.redis_client.setex(cache_key, ttl, json.dumps(data))
        except Exception as e:
            log.warning("Redis store failed for key %s: %s", cache_key, e)

    async def _store_in_database(self, asin: str, price: int) -> None:
        """Store price data in database using existing Cache model."""
        try:
            with Session(engine) as session:
                cache_entry = Cache(asin=asin, price=price, fetched_at=datetime.utcnow())
                session.merge(cache_entry)
                session.commit()
        except Exception as e:
            log.warning("Database cache store failed for ASIN %s: %s", asin, e)

    async def _warm_single_asin(self, asin: str, resources: List[str] = None) -> None:
        """Warm cache for a single ASIN."""
        try:
            # Check if already cached
            cached_data = await self.get_cached_product(asin, resources)
            if cached_data:
                log.debug("ASIN %s already cached, skipping", asin)
                return
                
            # Try to get fresh data (this would normally come from PA-API)
            # For now, we'll try to get from existing database
            db_data = await self._get_from_database(asin)
            if db_data:
                await self.store_product_data(asin, db_data, resources)
                log.debug("Warmed cache for ASIN: %s", asin)
            else:
                log.debug("No data available to warm cache for ASIN: %s", asin)
                
        except Exception as e:
            log.warning("Cache warming failed for ASIN %s: %s", asin, e)


# Global cache manager instance
_cache_manager: Optional[IntelligentCacheManager] = None


def get_cache_manager() -> IntelligentCacheManager:
    """Get the global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = IntelligentCacheManager()
    return _cache_manager


async def get_cached_product_data(asin: str, resources: List[str] = None) -> Optional[Dict]:
    """Convenience function to get cached product data.
    
    Args:
        asin: Amazon Standard Identification Number
        resources: Optional list of PA-API resources needed
        
    Returns:
        Cached product data or None if not found
    """
    manager = get_cache_manager()
    return await manager.get_cached_product(asin, resources)


async def cache_product_data(asin: str, data: Dict, resources: List[str] = None) -> None:
    """Convenience function to cache product data.
    
    Args:
        asin: Amazon Standard Identification Number
        data: Product data to cache
        resources: Optional list of PA-API resources cached
    """
    manager = get_cache_manager()
    await manager.store_product_data(asin, data, resources)


async def invalidate_product_cache(asin: str) -> None:
    """Convenience function to invalidate cached product data.
    
    Args:
        asin: Amazon Standard Identification Number to invalidate
    """
    manager = get_cache_manager()
    await manager.invalidate_cache(asin)
