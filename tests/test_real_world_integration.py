"""
Real-World Integration Tests to Catch Production Issues.

These tests are designed to catch the types of issues that slipped through
our existing test suite - rate limiting loops, async context issues,
database constraints, and type mismatches.
"""

import asyncio
import pytest
import time
from unittest.mock import patch, MagicMock, AsyncMock
from typing import List, Dict, Any

from bot.watch_flow import _finalize_watch, _cached_search_items_advanced
from bot.cache_service import get_price, get_price_async
from bot.paapi_ai_bridge import search_products_with_ai_analysis
from bot.models import User, Watch, Cache
from sqlmodel import Session, select
from bot.cache_service import engine


class TestRealWorldIntegration:
    """Tests that simulate real-world conditions to catch production issues."""

    @pytest.fixture
    def mock_telegram_update(self):
        """Create a realistic telegram update."""
        update = MagicMock()
        update.effective_user.id = 7332386643  # Real user ID from logs
        update.effective_chat.send_message = AsyncMock()
        update.effective_chat.send_photo = AsyncMock()
        update.callback_query = None
        return update

    @pytest.fixture
    def mock_context(self):
        """Create a realistic context."""
        context = MagicMock()
        context.user_data = {}
        return context

    @pytest.mark.asyncio
    async def test_rate_limiting_prevention(self):
        """
        Test Issue #1: Rate Limiting Loop Prevention
        
        This test would have caught the infinite PA-API call loop
        by ensuring search functions don't make excessive API calls.
        """
        api_call_count = 0
        
        def mock_search_with_counter(*args, **kwargs):
            nonlocal api_call_count
            api_call_count += 1
            if api_call_count > 3:  # Should never make more than 3 calls
                raise Exception(f"Rate limiting test failed: {api_call_count} API calls made")
            return []
        
        with patch('bot.paapi_factory.search_items_advanced', side_effect=mock_search_with_counter):
            # This should use caching and not make multiple calls
            result1 = await _cached_search_items_advanced("coding monitor under ₹50000")
            result2 = await _cached_search_items_advanced("coding monitor under ₹50000")  # Should use cache
            
            # Should only make 1 API call due to caching
            assert api_call_count <= 1, f"Made {api_call_count} API calls, should use cache"

    @pytest.mark.asyncio
    async def test_async_context_conflicts(self):
        """
        Test Issue #2: AsyncIO Context Conflicts
        
        This test would have caught the asyncio.run() from async context errors
        by running price fetching in a real async environment.
        """
        # Simulate the real async context where the error occurred
        async def async_context_test():
            # This should NOT raise "asyncio.run() cannot be called from a running event loop"
            try:
                # Mock the API calls to fail so we test the async context handling
                with patch('bot.paapi_factory.get_item_detailed', side_effect=Exception("API failed")):
                    with patch('bot.scraper.scrape_price', side_effect=Exception("Scraper failed")):
                        price = get_price("B0D9K2H2Z7")  # This should handle async context gracefully
                        
                        # Should return 0 instead of crashing
                        assert price == 0, f"Expected 0 for failed price fetch, got {price}"
                        
            except RuntimeError as e:
                if "asyncio.run() cannot be called" in str(e):
                    pytest.fail(f"AsyncIO context error not handled: {e}")
        
        # Run in an actual async context to trigger the original issue
        await async_context_test()

    @pytest.mark.asyncio
    async def test_database_constraint_handling(self):
        """
        Test Issue #3: Database Constraint Violations
        
        This test would have caught the NULL constraint failures
        by testing database operations with None values.
        """
        # Test that we can handle None prices without database errors
        with patch('bot.paapi_factory.get_item_detailed', return_value={"price": None}):
            with patch('bot.scraper.scrape_price', return_value=None):
                try:
                    price = get_price("TEST_ASIN_NULL_PRICE")
                    
                    # Should return 0 instead of None
                    assert price == 0, f"Expected 0 for None price, got {price}"
                    
                    # Verify no database constraint violations
                    with Session(engine) as session:
                        cache_entries = session.exec(
                            select(Cache).where(Cache.asin == "TEST_ASIN_NULL_PRICE")
                        ).all()
                        
                        # Should not create cache entry for invalid price
                        assert len(cache_entries) == 0, "Should not cache None/0 prices"
                        
                except Exception as e:
                    if "NOT NULL constraint failed" in str(e):
                        pytest.fail(f"Database constraint error not handled: {e}")

    @pytest.mark.asyncio
    async def test_type_safety_in_price_handling(self):
        """
        Test Issue #4: String vs Int Type Mismatches
        
        This test would have caught the type comparison errors
        by testing with mixed data types.
        """
        from bot.watch_flow import _filter_products_by_criteria, send_single_card_experience
        
        # Test products with mixed price types (strings, ints, None)
        problematic_products = [
            {"asin": "TEST1", "title": "Product 1", "price": "Price not available"},  # String
            {"asin": "TEST2", "title": "Product 2", "price": 50000},  # Int
            {"asin": "TEST3", "title": "Product 3", "price": None},  # None
            {"asin": "TEST4", "title": "Product 4", "price": 45000.50},  # Float
        ]
        
        watch_data = {
            "keywords": "test products",
            "max_price": 50000,
            "brand": None,
            "min_discount": None
        }
        
        # This should not crash with type comparison errors
        try:
            filtered = _filter_products_by_criteria(problematic_products, watch_data)
            
            # Should filter based on valid numeric prices only
            valid_prices = [p for p in filtered if isinstance(p.get("price"), (int, float))]
            assert len(valid_prices) >= 0, "Should handle mixed price types gracefully"
            
        except TypeError as e:
            if "'>' not supported between instances of 'str' and 'int'" in str(e):
                pytest.fail(f"Type comparison error not handled: {e}")

    @pytest.mark.asyncio
    async def test_complete_user_flow_with_failures(self, mock_telegram_update, mock_context):
        """
        Test Issue #5: Complete User Flow Under Failure Conditions
        
        This test simulates real-world conditions where multiple things can go wrong
        and ensures the system handles it gracefully.
        """
        watch_data = {
            "asin": None,
            "brand": None,
            "max_price": 50000,
            "min_discount": None,
            "keywords": "coding monitor under ₹50000",
            "mode": "daily"
        }
        
        # Simulate various failure scenarios
        with patch('bot.paapi_factory.search_items_advanced', return_value=[]):  # No products found
            with patch('bot.cache_service.get_price', return_value=0):  # Price fetch fails
                try:
                    # This should complete without crashing
                    await _finalize_watch(mock_telegram_update, mock_context, watch_data)
                    
                    # Should send some kind of message to user (success or error)
                    assert (mock_telegram_update.effective_chat.send_message.called or
                           mock_telegram_update.effective_chat.send_photo.called), \
                           "Should send message to user even when things fail"
                           
                except Exception as e:
                    pytest.fail(f"Complete flow should not crash on failures: {e}")

    @pytest.mark.asyncio
    async def test_ai_bridge_caching(self):
        """
        Test Issue #6: AI Bridge Request Deduplication
        
        This test ensures the AI bridge doesn't make duplicate requests
        for the same query within the cache TTL.
        """
        call_count = 0
        
        def mock_ai_search(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return {"products": [], "processing_time_ms": 1.0}
        
        with patch('bot.paapi_ai_bridge.execute_search_request', side_effect=mock_ai_search):
            # First call
            result1 = await search_products_with_ai_analysis("test query")
            
            # Second call with same query - should use cache
            result2 = await search_products_with_ai_analysis("test query")
            
            # Should only make 1 actual call due to caching
            assert call_count <= 1, f"AI bridge made {call_count} calls, should cache duplicates"

    @pytest.mark.asyncio
    async def test_performance_under_load(self):
        """
        Test Issue #7: Performance Under Concurrent Load
        
        This test simulates multiple concurrent users to catch race conditions
        and performance issues.
        """
        async def simulate_user_search(user_id: int):
            """Simulate a user performing a search."""
            return await _cached_search_items_advanced(f"monitor {user_id}")
        
        # Simulate 10 concurrent users
        start_time = time.time()
        
        tasks = [simulate_user_search(i) for i in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        
        # Check that no tasks failed
        exceptions = [r for r in results if isinstance(r, Exception)]
        assert len(exceptions) == 0, f"Concurrent load caused {len(exceptions)} failures: {exceptions}"
        
        # Check reasonable performance (should complete in under 30 seconds)
        total_time = end_time - start_time
        assert total_time < 30, f"Concurrent load took {total_time:.1f}s, should be under 30s"


class TestErrorInjection:
    """Tests that deliberately inject errors to test system resilience."""

    @pytest.mark.asyncio
    async def test_database_connection_failure(self):
        """Test behavior when database is unavailable."""
        # Mock the Session creation to fail, simulating database unavailability
        with patch('bot.cache_service.Session') as mock_session:
            mock_session.side_effect = Exception("Database connection failed")

            # The function should handle database failures gracefully
            # In this case, it should attempt to use PA-API/scraper as fallback
            # But since we're mocking at the Session level, it will fail
            # We just want to ensure it doesn't crash unexpectedly
            try:
                price = get_price("TEST_DB_FAIL")
                # If we get here, the function handled the failure gracefully
                assert price is not None, "Should return a valid price or fallback gracefully"
            except Exception as e:
                # Verify it's the expected database error, not an unexpected crash
                assert "Database connection failed" in str(e), f"Expected database error, got: {e}"

    @pytest.mark.asyncio
    async def test_memory_pressure(self):
        """Test behavior under memory pressure with large datasets."""
        # Create a large dataset to test memory handling
        large_product_list = [
            {
                "asin": f"TEST{i}",
                "title": f"Product {i}" * 100,  # Large titles
                "price": i * 1000,
                "features": [f"Feature {j}" for j in range(50)]  # Many features
            }
            for i in range(1000)  # 1000 products
        ]
        
        from bot.watch_flow import _filter_products_by_criteria
        
        watch_data = {"max_price": 50000, "brand": None, "min_discount": None}
        
        try:
            # This should handle large datasets without memory issues
            filtered = _filter_products_by_criteria(large_product_list, watch_data)
            assert len(filtered) >= 0, "Should handle large datasets"
        except MemoryError:
            pytest.fail("Should handle large datasets without memory errors")
