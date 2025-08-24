"""
PA-API Best Practices Implementation
Based on Amazon PA-API 5.0 guidelines and web research findings
"""

import asyncio
import random
import time
from logging import getLogger
from typing import Dict, List, Optional

from amazon_paapi import AmazonApi

from .config import settings

log = getLogger(__name__)


class PaapiRateLimiter:
    """Implements exponential backoff and proper rate limiting for PA-API"""
    
    def __init__(self):
        self.last_request_time = 0
        self.min_interval = 1.0  # 1 second minimum between requests
        
    async def wait_if_needed(self):
        """Ensure minimum interval between API calls"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_interval:
            wait_time = self.min_interval - time_since_last
            log.info(f"Rate limiting: waiting {wait_time:.2f}s before next API call")
            await asyncio.sleep(wait_time)
        
        self.last_request_time = time.time()


class PaapiClient:
    """Enhanced PA-API client with best practices implementation"""
    
    def __init__(self):
        self.rate_limiter = PaapiRateLimiter()
        
    def _create_api_instance(self) -> AmazonApi:
        """Create PA-API instance with correct configuration"""
        return AmazonApi(
            key=settings.PAAPI_ACCESS_KEY,
            secret=settings.PAAPI_SECRET_KEY,
            tag=settings.PAAPI_TAG,
            country="IN",  # India marketplace
        )
    
    async def search_with_backoff(
        self, 
        keywords: str,
        item_count: int = 5,
        max_retries: int = 3
    ) -> List[Dict]:
        """
        Search with exponential backoff retry strategy
        
        Based on PA-API best practices:
        - 1 request per second rate limiting
        - Exponential backoff for 429 errors
        - Maximum retry attempts
        """
        
        for attempt in range(max_retries):
            try:
                # Enforce rate limiting
                await self.rate_limiter.wait_if_needed()
                
                log.info(f"PA-API search attempt {attempt + 1}/{max_retries} for: {keywords}")
                
                # Make API call
                api = self._create_api_instance()
                result = api.search_items(
                    keywords=keywords,
                    item_count=min(item_count, 10),  # PA-API max is 10
                    # Note: resources parameter omitted to avoid conflicts
                )
                
                log.info(f"PA-API search successful: {len(result) if result else 0} results")
                return result or []
                
            except Exception as e:
                error_str = str(e)
                
                if "TooManyRequests" in error_str or "Requests limit reached" in error_str:
                    if attempt < max_retries - 1:
                        # Exponential backoff with jitter
                        base_delay = 2 ** attempt  # 1s, 2s, 4s
                        jitter = random.uniform(0, 1)
                        wait_time = base_delay + jitter
                        
                        log.warning(
                            f"Rate limited on attempt {attempt + 1}, "
                            f"retrying in {wait_time:.2f}s"
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        log.error("Rate limit exceeded, max retries reached")
                        raise Exception("PA-API rate limit exceeded") from e
                else:
                    log.error(f"PA-API error on attempt {attempt + 1}: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1)  # Brief wait before retry
                        continue
                    else:
                        raise
        
        return []
    
    async def get_item_with_backoff(
        self,
        asin: str,
        max_retries: int = 3
    ) -> Optional[Dict]:
        """Get item details with exponential backoff"""
        
        for attempt in range(max_retries):
            try:
                await self.rate_limiter.wait_if_needed()
                
                log.info(f"PA-API get_item attempt {attempt + 1}/{max_retries} for: {asin}")
                
                api = self._create_api_instance()
                result = api.get_items(item_ids=[asin])
                
                if result and len(result) > 0:
                    log.info(f"PA-API get_item successful for: {asin}")
                    return result[0]
                else:
                    log.warning(f"No data returned for ASIN: {asin}")
                    return None
                    
            except Exception as e:
                error_str = str(e)
                
                if "TooManyRequests" in error_str:
                    if attempt < max_retries - 1:
                        base_delay = 2 ** attempt
                        jitter = random.uniform(0, 1)
                        wait_time = base_delay + jitter
                        
                        log.warning(
                            f"Rate limited getting {asin}, "
                            f"retrying in {wait_time:.2f}s"
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        raise Exception("PA-API rate limit exceeded") from e
                else:
                    log.error(f"PA-API error getting {asin}: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1)
                        continue
                    else:
                        raise
        
        return None
    
    async def batch_get_items(
        self, 
        asins: List[str],
        max_retries: int = 3
    ) -> Dict[str, Dict]:
        """
        Batch get items (up to 10 per request - PA-API limit)
        More efficient than individual calls
        """
        results = {}
        
        # Process in batches of 10 (PA-API maximum)
        for i in range(0, len(asins), 10):
            batch = asins[i:i + 10]
            
            for attempt in range(max_retries):
                try:
                    await self.rate_limiter.wait_if_needed()
                    
                    log.info(f"PA-API batch_get attempt {attempt + 1} for {len(batch)} items")
                    
                    api = self._create_api_instance()
                    batch_results = api.get_items(item_ids=batch)
                    
                    if batch_results:
                        for item in batch_results:
                            asin = item.get('asin')
                            if asin:
                                results[asin] = item
                    
                    log.info(f"Batch get successful: {len(batch_results or [])} items")
                    break  # Success, move to next batch
                    
                except Exception as e:
                    error_str = str(e)
                    
                    if "TooManyRequests" in error_str:
                        if attempt < max_retries - 1:
                            base_delay = 2 ** attempt
                            jitter = random.uniform(0, 1)
                            wait_time = base_delay + jitter
                            
                            log.warning(f"Batch rate limited, retrying in {wait_time:.2f}s")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            log.error("Batch operation failed: rate limit exceeded")
                            break  # Skip this batch, continue with next
                    else:
                        log.error(f"Batch operation error: {e}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(1)
                            continue
                        else:
                            break
        
        return results


# Global instance
paapi_client = PaapiClient()


async def search_items_with_best_practices(
    keywords: str,
    item_count: int = 5
) -> List[Dict]:
    """
    Search items using PA-API best practices
    
    This replaces direct search_items_advanced calls
    """
    return await paapi_client.search_with_backoff(keywords, item_count)


async def get_item_with_best_practices(asin: str) -> Optional[Dict]:
    """
    Get item details using PA-API best practices
    
    This replaces direct get_item_detailed calls
    """
    return await paapi_client.get_item_with_backoff(asin)


async def batch_get_items_with_best_practices(asins: List[str]) -> Dict[str, Dict]:
    """
    Batch get items using PA-API best practices
    
    More efficient than individual calls
    """
    return await paapi_client.batch_get_items(asins)
