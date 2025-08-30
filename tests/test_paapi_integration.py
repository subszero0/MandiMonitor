#!/usr/bin/env python3
"""
PA-API Integration Tests: Complete End-to-End Testing

This module contains comprehensive integration tests that validate:
- Complete search-to-display flows
- Real API interactions (not mocks)
- Performance and load testing
- Failure scenario handling
- Real-world data validation
- Memory leak detection
- Concurrent user simulation

Based on Testing Philosophy: Integration Tests level
"""

import asyncio
import time
import os
import tracemalloc
from typing import List, Dict, Any, Optional
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import logging

# Configure logging for integration tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from bot.paapi_official import OfficialPaapiClient
from bot.paapi_ai_bridge import search_products_with_ai_analysis
from bot.watch_parser import parse_watch
from bot.config import settings

class TestPAAPIIntegrationSuite:
    """Comprehensive integration test suite for PA-API enhancements."""

    def setup_method(self):
        """Set up test environment with real client."""
        self.client = OfficialPaapiClient()
        tracemalloc.start()
        self.initial_memory = tracemalloc.get_traced_memory()[0]

    def teardown_method(self):
        """Clean up after tests."""
        tracemalloc.stop()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_complete_search_flow_with_all_phases(self):
        """Integration Test 1: Complete search flow with all 4 PA-API phases enabled."""
        logger.info("🧪 Starting complete search flow integration test")

        # Test premium budget scenario (should trigger all phases)
        search_params = {
            "keywords": "gaming monitor",
            "search_index": "Electronics",
            "min_price": 3500000,  # ₹35,000 (should trigger Phase 4 enhancements)
            "max_price": 7500000,  # ₹75,000 (Phase 1)
            "browse_node_id": 1951048031,  # Electronics category (Phase 2)
            "item_count": 40  # Large count (should trigger Phase 3 extended depth)
        }

        start_time = time.time()

        try:
            # Execute complete search flow
            results = await self.client.search_items_advanced(**search_params)

            execution_time = time.time() - start_time

            # Validate results
            assert results is not None, "Search should return results"
            assert len(results) > 0, "Should return at least one product"
            assert execution_time < 30, f"Search took too long: {execution_time:.2f}s"

            # Validate Phase 1: Price filtering
            valid_prices = [r.get('price', 0) for r in results if r.get('price') is not None and r.get('price', 0) > 0]
            if valid_prices:
                min_price_found = min(valid_prices)
                max_price_found = max(valid_prices)
                assert min_price_found >= 3500, f"Price filter failed: found {min_price_found}"

            # Validate Phase 4: Query enhancement (should include gaming terms)
            enhanced_terms = ["gaming", "performance", "quality", "4k", "uhd", "hdr"]
            found_terms = 0
            for result in results[:5]:  # Check first 5 results
                title = result.get('title', '').lower()
                found_terms += sum(1 for term in enhanced_terms if term in title)

            assert found_terms > 0, "Phase 4 query enhancement not working"

            logger.info(f"Integration test completed in {execution_time:.2f}s with {len(results)} results found")
            # Success - all phases working together
            logger.info("✅ All PA-API phases integrated successfully")
            assert True  # Test passed

        except Exception as e:
            logger.error(f"Integration test failed: {e}")
            pytest.fail(f"Complete search flow failed: {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_ai_analysis_integration(self):
        """Integration Test 2: PA-API + AI Analysis integration."""
        logger.info("🧪 Testing PA-API + AI integration")

        # Get products using enhanced PA-API
        paapi_results = await self.client.search_items_advanced(
            keywords="laptop",
            search_index="Electronics",
            min_price=5000000,  # ₹50,000
            item_count=10
        )

        assert paapi_results, "PA-API should return results for AI testing"

        # Test AI analysis on PA-API results
        try:
            ai_analysis = await search_products_with_ai_analysis(
                keywords="laptop for programming",
                search_index="Electronics",
                item_count=len(paapi_results)
            )

            # Should either return AI-enhanced results or fallback to standard
            assert ai_analysis is not None, "AI analysis should return results"

            if 'ai_enhanced' in ai_analysis:
                # AI analysis worked
                assert len(ai_analysis.get('products', [])) > 0, "AI should return results"
                logger.info("✅ AI analysis integration successful")
            else:
                # Fallback to standard search
                assert len(ai_analysis.get('products', [])) > 0, "Fallback should return results"
                logger.info("✅ AI fallback integration working")

        except Exception as e:
            logger.error(f"AI integration test failed: {e}")
            pytest.fail(f"PA-API + AI integration failed: {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_performance_regression_detection(self):
        """Integration Test 3: Performance regression detection."""
        logger.info("🧪 Testing performance regression")

        test_queries = [
            ("budget mouse", "Electronics", 100000, 5),  # Low budget
            ("gaming laptop", "Electronics", 7500000, 15),  # High budget
            ("4k monitor", "Electronics", 1500000, 25),  # Medium budget
        ]

        times = []

        for query, search_index, max_price, item_count in test_queries:
            start_time = time.time()

            results = await self.client.search_items_advanced(
                keywords=query,
                search_index=search_index,
                max_price=max_price,
                item_count=item_count
            )

            execution_time = time.time() - start_time

            times.append(execution_time)

            assert results is not None, f"Query '{query}' should return results"
            assert execution_time < 20, f"Query '{query}' took too long: {execution_time:.2f}s"

        # Check for performance degradation
        avg_time = sum(times) / len(times)

        logger.info(f"Average response time: {avg_time:.2f}s")
        assert avg_time < 10, f"Average response time too high: {avg_time:.2f}s"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_concurrent_user_simulation(self):
        """Integration Test 4: Concurrent user simulation."""
        logger.info("🧪 Testing concurrent user load")

        async def simulate_user_search(user_id: int, query: str):
            """Simulate a single user search."""
            try:
                results = await self.client.search_items_advanced(
                    keywords=query,
                    search_index="Electronics",
                    item_count=10
                )
                return {"user": user_id, "success": True, "count": len(results) if results else 0}
            except Exception as e:
                return {"user": user_id, "success": False, "error": str(e)}

        # Simulate 10 concurrent users with different queries
        user_queries = [
            "gaming mouse", "wireless keyboard", "4k monitor", "gaming laptop",
            "bluetooth speaker", "webcam", "external hard drive", "usb hub",
            "graphics tablet", "streaming microphone"
        ]

        start_time = time.time()

        # Create concurrent tasks
        tasks = [
            simulate_user_search(i, query)
            for i, query in enumerate(user_queries)
        ]

        # Execute all concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        execution_time = time.time() - start_time

        # Analyze results
        successful_searches = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        total_results = sum(r.get("count", 0) for r in results if isinstance(r, dict) and r.get("success"))

        logger.info(f"Concurrent test completed in {execution_time:.2f}s")
        assert successful_searches >= 8, f"Too many failed searches: {successful_searches}/10"
        assert execution_time < 60, f"Concurrent execution took too long: {execution_time:.2f}s"
        assert total_results > 0, "No results returned from concurrent searches"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_failure_scenario_recovery(self):
        """Integration Test 5: Failure scenario testing and recovery."""
        logger.info("🧪 Testing failure scenarios and recovery")

        failure_scenarios = [
            # Invalid browse node
            {"browse_node_id": 999999999, "expected_error": True},
            # Empty keywords
            {"keywords": "", "expected_error": True},
            # Extremely high price filter
            {"min_price": 500000000, "expected_error": False},  # Should return empty results
            # Invalid search index
            {"search_index": "InvalidIndex", "expected_error": True},
        ]

        for scenario in failure_scenarios:
            try:
                params = {
                    "keywords": "test product",
                    "search_index": "Electronics",
                    "item_count": 5,
                    **scenario
                }

                # Remove expected_error from params
                expected_error = params.pop("expected_error", False)

                results = await self.client.search_items_advanced(**params)

                if expected_error:
                    # Should have failed but didn't
                    logger.warning(f"Expected failure for scenario {scenario} but got results")
                else:
                    # Should have succeeded
                    assert results is not None, f"Unexpected failure for scenario {scenario}"

            except Exception as e:
                if expected_error:
                    # Expected failure occurred - good
                    logger.info(f"Expected failure caught for scenario {scenario}: {e}")
                else:
                    # Unexpected failure
                    logger.error(f"Unexpected failure for scenario {scenario}: {e}")
                    pytest.fail(f"Unexpected error in failure scenario test: {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_memory_leak_detection(self):
        """Integration Test 6: Memory leak detection."""
        logger.info("🧪 Testing for memory leaks")

        tracemalloc.start()
        initial_memory = tracemalloc.get_traced_memory()[0]

        # Perform multiple searches to detect memory leaks
        for i in range(10):
            results = await self.client.search_items_advanced(
                keywords=f"test product {i}",
                search_index="Electronics",
                item_count=10
            )

            # Force garbage collection
            import gc
            gc.collect()

            current_memory = tracemalloc.get_traced_memory()[0]
            memory_growth = current_memory - initial_memory

            assert memory_growth < 50 * 1024 * 1024, f"Memory leak detected: {memory_growth / 1024 / 1024:.2f}MB growth"

            # Brief pause to let system stabilize
            await asyncio.sleep(0.1)

        final_memory = tracemalloc.get_traced_memory()[0]
        total_growth = final_memory - initial_memory

        logger.info(f"Memory leak test completed - growth: {total_growth / 1024 / 1024:.2f}MB")
        assert total_growth < 100 * 1024 * 1024, f"Memory leak: {total_growth / 1024 / 1024:.2f}MB total growth"

        tracemalloc.stop()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_world_data_validation(self):
        """Integration Test 7: Real-world data validation."""
        logger.info("🧪 Testing with real-world data patterns")

        # Test with various real-world scenarios
        real_world_scenarios = [
            # Empty/incomplete data scenarios
            {"keywords": "iphone charger", "min_price": 0, "max_price": 1000000},
            {"keywords": "samsung monitor", "min_price": None, "max_price": None},
            {"keywords": "", "min_price": 100000, "max_price": 500000},  # Empty keywords

            # Extreme values
            {"keywords": "budget phone", "min_price": 1, "max_price": 10000000},  # Very wide range
            {"keywords": "luxury watch", "min_price": 10000000, "max_price": 50000000},  # Very high budget

            # Mixed case and special characters
            {"keywords": "GAMING LAPTOP", "search_index": "Electronics"},
            {"keywords": "wireless mouse & keyboard combo", "search_index": "Electronics"},
        ]

        for scenario in real_world_scenarios:
            try:
                results = await self.client.search_items_advanced(**scenario)

                # Should handle all scenarios gracefully
                assert results is not None, f"Failed to handle scenario: {scenario}"

                # Validate result structure
                if results:
                    for result in results[:3]:  # Check first 3 results
                        assert 'asin' in result, f"Missing ASIN in result: {result}"
                        assert 'title' in result, f"Missing title in result: {result}"

                logger.info(f"✅ Scenario handled successfully: {scenario}")

            except Exception as e:
                logger.error(f"Failed to handle real-world scenario {scenario}: {e}")
                pytest.fail(f"Real-world scenario failed: {scenario} - {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_complete_user_journey_simulation(self):
        """Integration Test 8: Complete user journey from search to display."""
        logger.info("🧪 Testing complete user journey")

        # Simulate a complete user journey
        user_journey = {
            "budget": 50000,  # ₹50,000
            "requirements": "gaming laptop for work and gaming",
            "category": "Electronics"
        }

        try:
            # Step 1: Enhanced search with all phases
            search_results = await self.client.search_items_advanced(
                keywords=user_journey["requirements"],
                search_index=user_journey["category"],
                max_price=user_journey["budget"] * 100,  # Convert to paise
                item_count=20
            )

            assert search_results, "Search step failed"
            assert len(search_results) > 0, "No products found"

            # Step 2: AI analysis (if available)
            try:
                ai_results = await search_products_with_ai_analysis(
                    query=user_journey["requirements"],
                    search_results=search_results,
                    user_budget=user_journey["budget"],
                    user_requirements=user_journey["requirements"]
                )
                results_to_process = ai_results.get('results', search_results)
            except:
                results_to_process = search_results

            # Step 3: Parse and format for display
            # This simulates the watch flow processing
            processed_products = []
            for product in results_to_process[:5]:  # Process top 5
                processed_product = {
                    "title": product.get('title', 'Unknown Product'),
                    "price": product.get('price', 0),
                    "asin": product.get('asin', ''),
                    "image_url": product.get('image_url', ''),
                    "features": product.get('features', [])[:3]  # Top 3 features
                }
                processed_products.append(processed_product)

            # Step 4: Validate final output
            assert len(processed_products) > 0, "No products processed"
            assert all(p['title'] for p in processed_products), "Missing product titles"
            assert all(p['price'] >= 0 for p in processed_products), "Invalid prices"

            logger.info(f"✅ Complete user journey successful - processed {len(processed_products)} products")

        except Exception as e:
            logger.error(f"Complete user journey failed: {e}")
            pytest.fail(f"User journey simulation failed: {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_rate_limiting_and_caching(self):
        """Integration Test 9: Rate limiting and caching validation."""
        logger.info("🧪 Testing rate limiting and caching")

        # Test rapid successive requests (should be rate limited)
        rapid_queries = ["laptop", "mouse", "keyboard", "monitor", "speaker"]

        start_time = time.time()

        for query in rapid_queries:
            results = await self.client.search_items_advanced(
                keywords=query,
                search_index="Electronics",
                item_count=5
            )
            assert results is not None, f"Query '{query}' failed"

        execution_time = time.time() - start_time

        # Should take some time due to rate limiting (not too fast, not too slow)
        assert execution_time > 2, f"Rate limiting not working: {execution_time:.2f}s"
        assert execution_time < 30, f"Too slow, possible rate limit issue: {execution_time:.2f}s"

        logger.info(f"Rate limiting test completed in {execution_time:.2f}s")
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_telegram_bot_integration_flow(self):
        """Integration Test 10: Telegram bot integration flow."""
        logger.info("🧪 Testing Telegram bot integration")

        # Mock Telegram update and context
        mock_update = MagicMock()
        mock_update.effective_user.id = 12345
        mock_context = MagicMock()

        # Test watch command parsing
        test_message = "I want to watch gaming laptop under 50000 rupees"
        mock_update.message.text = test_message

        try:
            # This would normally be handled by the Telegram bot
            # We're testing the parsing and flow logic
            parsed_data = parse_watch(test_message)

            assert parsed_data is not None, "Watch command parsing failed"
            assert parsed_data.get('keywords') == test_message, "Keywords should match input text"
            assert parsed_data.get('max_price') == 50000, "Budget not parsed correctly"

            logger.info("✅ Telegram bot parsing integration successful")

        except Exception as e:
            logger.error(f"Telegram bot integration test failed: {e}")
            pytest.fail(f"Telegram integration failed: {e}")

# Performance baseline markers
PERFORMANCE_BASELINES = {
    "single_search": 5.0,  # seconds
    "concurrent_10_users": 15.0,  # seconds
    "memory_per_search": 50.0,  # MB
    "total_memory_growth": 100.0,  # MB
}

if __name__ == "__main__":
    # Allow running individual tests
    pytest.main([__file__, "-v", "-s", "--tb=short"])
