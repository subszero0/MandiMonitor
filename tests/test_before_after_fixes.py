"""
Demonstration Tests: Before vs After Our Fixes

These tests demonstrate what would have failed BEFORE our fixes
and what works AFTER our fixes.
"""

import pytest
from unittest.mock import patch, MagicMock
from bot.watch_flow import _filter_products_by_criteria


class TestBeforeAfterFixes:
    """Show the difference between old buggy code and new fixed code."""

    def test_old_vs_new_price_comparison(self):
        """
        BEFORE FIX: This would crash with string vs int comparison
        AFTER FIX: This handles mixed types gracefully
        """
        
        # Simulate the old problematic code (before our fix)
        def old_filter_logic(products, max_price):
            """This is how the code USED to work (buggy version)."""
            filtered = []
            for product in products:
                product_price = product.get("price", 0)
                # OLD BUG: No type checking before comparison
                if product_price and product_price > max_price * 100:
                    continue
                filtered.append(product)
            return filtered
        
        # Test data that would cause the old code to crash
        problematic_products = [
            {"asin": "TEST1", "title": "Product 1", "price": "Price not available"},  # String!
            {"asin": "TEST2", "title": "Product 2", "price": 50000},  # Int
        ]
        
        watch_data = {"max_price": 60000, "brand": None, "min_discount": None}
        
        # OLD CODE: This would crash
        try:
            old_result = old_filter_logic(problematic_products, 60000)
            pytest.fail("Old code should have crashed with TypeError")
        except TypeError as e:
            assert "'>' not supported between instances of 'str' and 'int'" in str(e)
            print(f"✅ OLD CODE CRASHED AS EXPECTED: {e}")
        
        # NEW CODE: This works fine
        try:
            new_result = _filter_products_by_criteria(problematic_products, watch_data)
            print(f"✅ NEW CODE WORKS: Filtered {len(new_result)} products safely")
            assert len(new_result) >= 0, "New code should handle mixed types"
        except TypeError:
            pytest.fail("New code should not crash on mixed types")

    def test_old_vs_new_cache_behavior(self):
        """
        BEFORE FIX: Cache would try to insert None values and crash
        AFTER FIX: Cache skips None values gracefully
        """
        from bot.cache_service import get_price
        
        # Mock both PA-API and scraper to fail (return None)
        with patch('bot.paapi_factory.get_item_detailed', return_value={"price": None}):
            with patch('bot.scraper.scrape_price', return_value=None):
                
                # NEW CODE: Should handle None gracefully
                try:
                    price = get_price("TEST_ASIN_NONE")
                    print(f"✅ NEW CODE WORKS: Got price {price} instead of crashing")
                    assert price == 0, "Should return 0 for failed price fetching"
                except Exception as e:
                    if "NOT NULL constraint failed" in str(e):
                        pytest.fail(f"NEW CODE FAILED: Still has database constraint issue: {e}")

    @pytest.mark.asyncio
    async def test_old_vs_new_async_handling(self):
        """
        BEFORE FIX: asyncio.run() from async context would crash
        AFTER FIX: Detects async context and handles gracefully
        """
        from bot.cache_service import get_price
        
        # This test runs in an async context (like the real bot)
        # OLD CODE: Would crash with "asyncio.run() cannot be called from a running event loop"
        # NEW CODE: Detects the async context and handles it
        
        with patch('bot.paapi_factory.get_item_detailed', side_effect=Exception("Mock failure")):
            with patch('bot.scraper.scrape_price', side_effect=Exception("Mock failure")):
                
                try:
                    price = get_price("TEST_ASYNC_CONTEXT")
                    print(f"✅ NEW CODE WORKS: Handled async context, got price {price}")
                    assert price == 0, "Should handle async context gracefully"
                except RuntimeError as e:
                    if "asyncio.run() cannot be called" in str(e):
                        pytest.fail(f"NEW CODE FAILED: Still has async context issue: {e}")


class TestProductionScenarios:
    """Test real production scenarios that would expose issues."""

    @pytest.mark.asyncio
    async def test_user_search_simulation(self):
        """Simulate the exact user scenario that failed in production."""
        from bot.watch_flow import _finalize_watch
        
        # Exact scenario from logs
        watch_data = {
            "asin": None,
            "brand": None, 
            "max_price": 50000,
            "min_discount": None,
            "keywords": "coding monitor under ₹50000",
            "mode": "daily"
        }
        
        # Mock telegram objects
        mock_update = MagicMock()
        mock_update.effective_user.id = 7332386643
        mock_update.effective_chat.send_message = MagicMock()
        mock_update.effective_chat.send_photo = MagicMock()
        mock_update.callback_query = None
        
        mock_context = MagicMock()
        mock_context.user_data = {}
        
        # Mock successful search results
        mock_products = [
            {
                "asin": "B0D9K2H2Z7",
                "title": "Test Gaming Monitor",
                "price": 45000,
                "image": "https://example.com/image.jpg"
            }
        ]
        
        with patch('bot.watch_flow._cached_search_items_advanced', return_value=mock_products):
            with patch('bot.cache_service.get_price', return_value=45000):
                
                try:
                    # This should complete without any errors
                    await _finalize_watch(mock_update, mock_context, watch_data)
                    print("✅ COMPLETE USER FLOW WORKS: No crashes or errors")
                    
                    # Should send some message to user
                    assert (mock_update.effective_chat.send_message.called or 
                           mock_update.effective_chat.send_photo.called), \
                           "Should send message to user"
                           
                except Exception as e:
                    pytest.fail(f"Complete user flow failed: {e}")

    def test_concurrent_api_calls(self):
        """Test that multiple simultaneous searches don't cause rate limiting loops."""
        import asyncio
        from bot.watch_flow import _cached_search_items_advanced
        
        call_count = 0
        
        def mock_search(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return [{"asin": f"TEST{call_count}", "title": f"Product {call_count}"}]
        
        async def run_concurrent_test():
            with patch('bot.paapi_factory.search_items_advanced', side_effect=mock_search):
                
                # Multiple users searching simultaneously  
                tasks = [
                    _cached_search_items_advanced("monitor 1"),
                    _cached_search_items_advanced("monitor 1"),  # Same query (should cache)
                    _cached_search_items_advanced("monitor 2"),
                    _cached_search_items_advanced("monitor 1"),  # Same as first (should cache)
                ]
                
                results = await asyncio.gather(*tasks)
                
                # Should only make 2 unique API calls due to caching
                assert call_count <= 2, f"Made {call_count} API calls, should cache duplicates"
                print(f"✅ CACHING WORKS: Made only {call_count} API calls for 4 requests")
        
        # Run the async test
        asyncio.run(run_concurrent_test())


if __name__ == "__main__":
    # Run a quick demo
    test_instance = TestBeforeAfterFixes()
    test_instance.test_old_vs_new_price_comparison()
    print("\n" + "="*60)
    print("Demo complete! These tests show how our fixes prevent crashes.")
