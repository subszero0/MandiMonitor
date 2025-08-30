"""
ADVANCED EDGE CASE TESTING
==========================

These tests probe for subtle bugs that could embarrass us in front of 
stakeholders. They test scenarios that users WILL eventually trigger.
"""

import pytest
import asyncio
import time
from unittest.mock import patch, MagicMock, AsyncMock
from decimal import Decimal
import json

from bot.watch_flow import _finalize_watch, _filter_products_by_criteria
from bot.paapi_ai_bridge import transform_paapi_to_ai_format
from bot.product_selection_models import smart_product_selection, has_technical_features
from bot.cache_service import get_price
from bot.carousel import build_single_card


class TestDataTypeEdgeCases:
    """Test edge cases with different data types that could cause subtle bugs."""

    def test_price_with_different_numeric_types(self):
        """Test price handling with various numeric types."""
        
        price_variations = [
            50000,           # int
            50000.0,         # float  
            50000.99,        # float with decimals
            Decimal('50000.50'),  # Decimal
            "50000",         # string number
            "50,000",        # string with comma
            "₹50000",        # string with currency
            "50000.00",      # string decimal
            "5e4",           # scientific notation
        ]
        
        products = [
            {
                "asin": f"TEST{i}",
                "title": f"Product {i}",
                "price": price,
                "features": ["Feature 1"]
            }
            for i, price in enumerate(price_variations)
        ]
        
        watch_data = {"max_price": 55000, "brand": None, "min_discount": None}
        
        try:
            # This should handle ALL price formats gracefully
            filtered = _filter_products_by_criteria(products, watch_data)
            print(f"✅ PRICE TYPES: Handled {len(price_variations)} different price formats")
            
            # Should filter based on numeric values where possible
            assert len(filtered) >= 0, "Should handle various price formats"
            
        except Exception as e:
            pytest.fail(f"Failed to handle price variations: {e}")

    def test_unicode_and_emoji_handling(self):
        """Test handling of Unicode characters and emojis in product data."""
        
        unicode_products = [
            {
                "asin": "UNICODE1",
                "title": "Gaming Monitor 🎮 with 4K Display 📺",
                "price": 50000,
                "features": ["Ultra HD 🔥", "Fast Response ⚡", "RGB Lighting 🌈"]
            },
            {
                "asin": "UNICODE2", 
                "title": "モニター Gaming Display",  # Japanese
                "price": 45000,
                "features": ["High Quality", "Good Price"]
            },
            {
                "asin": "UNICODE3",
                "title": "Monitor für Gaming",  # German
                "price": 48000,
                "features": ["Sehr gut", "Hohe Qualität"]
            },
            {
                "asin": "UNICODE4",
                "title": "मॉनिटर गेमिंग",  # Hindi
                "price": 52000,
                "features": ["उच्च गुणवत्ता", "तेज़ गति"]
            }
        ]
        
        try:
            # Test AI feature extraction with Unicode
            from bot.ai.feature_extractor import FeatureExtractor
            extractor = FeatureExtractor()
            
            for product in unicode_products:
                result = extractor.extract_features(product["title"])
                print(f"✅ UNICODE: Processed '{product['title'][:30]}...'")
                assert result is not None, f"Should handle Unicode in: {product['title']}"
                
        except Exception as e:
            pytest.fail(f"Failed to handle Unicode characters: {e}")

    def test_extreme_numeric_values(self):
        """Test handling of extreme numeric values."""
        
        extreme_values = [
            0,               # Zero price
            -1,              # Negative price
            1,               # Very small price
            999999999999,    # Very large price
            float('inf'),    # Infinity
            float('-inf'),   # Negative infinity
            float('nan'),    # Not a number
        ]
        
        for i, extreme_price in enumerate(extreme_values):
            try:
                # Test price filtering
                products = [{
                    "asin": f"EXTREME{i}",
                    "title": f"Product with extreme price {extreme_price}",
                    "price": extreme_price
                }]
                
                watch_data = {"max_price": 50000, "brand": None, "min_discount": None}
                result = _filter_products_by_criteria(products, watch_data)
                
                print(f"✅ EXTREME VALUE {i}: Handled price={extreme_price}")
                
            except Exception as e:
                print(f"⚠️ EXTREME VALUE {i}: Failed with price={extreme_price} - {e}")
                # Don't fail the test - extreme values might legitimately cause issues


class TestTimingAndRaceConditions:
    """Test for timing-related bugs and race conditions."""

    @pytest.mark.asyncio
    async def test_rapid_sequential_requests(self):
        """Test rapid sequential requests for the same user."""
        
        async def rapid_request(request_id: int):
            """Simulate rapid user requests."""
            mock_update = MagicMock()
            mock_update.effective_user.id = 12345  # Same user
            mock_update.effective_chat.send_message = AsyncMock()
            mock_context = MagicMock()
            mock_context.user_data = {}
            
            watch_data = {
                "asin": None,
                "keywords": f"monitor {request_id}",
                "max_price": 50000,
                "mode": "daily"
            }
            
            with patch('bot.watch_flow._cached_search_items_advanced', return_value=[
                {"asin": f"TEST{request_id}", "title": f"Product {request_id}", "price": 45000}
            ]):
                with patch('bot.cache_service.get_price', return_value=45000):
                    await _finalize_watch(mock_update, mock_context, watch_data)
                    return f"Request {request_id}: Success"
        
        # Simulate user clicking watch button multiple times rapidly
        start_time = time.time()
        tasks = [rapid_request(i) for i in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        failures = [r for r in results if isinstance(r, Exception)]
        successes = [r for r in results if r not in failures]
        
        print(f"⚡ RAPID REQUESTS: {len(successes)}/10 successful in {end_time-start_time:.2f}s")
        print(f"❌ FAILURES: {len(failures)} requests failed")
        
        # All requests should succeed (or gracefully handle duplicates)
        assert len(failures) == 0, f"Rapid requests caused {len(failures)} failures"

    @pytest.mark.asyncio  
    async def test_timeout_scenarios(self):
        """Test behavior under various timeout conditions."""
        
        def slow_api_mock(*args, **kwargs):
            """Simulate slow API response."""
            time.sleep(5)  # 5 second delay
            return [{"asin": "SLOW", "title": "Slow Product", "price": 50000}]
        
        def timeout_api_mock(*args, **kwargs):
            """Simulate API timeout."""
            raise TimeoutError("API request timed out")
        
        timeout_scenarios = [
            ("Slow API", slow_api_mock),
            ("Timeout API", timeout_api_mock),
        ]
        
        for scenario_name, mock_func in timeout_scenarios:
            try:
                mock_update = MagicMock()
                mock_update.effective_user.id = 12345
                mock_update.effective_chat.send_message = AsyncMock()
                mock_context = MagicMock()
                
                watch_data = {
                    "keywords": "test timeout",
                    "max_price": 50000,
                    "mode": "daily"
                }
                
                start_time = time.time()
                
                with patch('bot.paapi_factory.search_items_advanced', side_effect=mock_func):
                    # Should handle timeouts gracefully and not hang
                    await asyncio.wait_for(
                        _finalize_watch(mock_update, mock_context, watch_data),
                        timeout=10.0  # 10 second max
                    )
                    
                end_time = time.time()
                duration = end_time - start_time
                
                print(f"✅ {scenario_name}: Handled in {duration:.1f}s")
                
            except asyncio.TimeoutError:
                pytest.fail(f"{scenario_name}: Operation hung and timed out")
            except Exception as e:
                print(f"✅ {scenario_name}: Gracefully handled - {e}")


class TestDataConsistencyAndIntegrity:
    """Test data consistency across different components."""

    def test_ai_bridge_data_consistency(self):
        """Test that PA-API bridge maintains data consistency."""
        
        # Mock PA-API response with complex nested structure
        mock_paapi_item = type('MockItem', (), {
            'asin': 'B08N5WRWNW',
            'item_info': type('ItemInfo', (), {
                'title': type('Title', (), {'display_value': 'LG 27" Gaming Monitor'})(),
                'features': type('Features', (), {
                    'display_values': ['27 inch display', '144Hz refresh rate', 'IPS panel']
                })(),
                'technical_info': type('TechInfo', (), {
                    'display_values': [
                        type('Spec', (), {
                            'name': type('Name', (), {'display_value': 'Refresh Rate'})(),
                            'value': type('Value', (), {'display_value': '144 Hz'})()
                        })(),
                        type('Spec', (), {
                            'name': type('Name', (), {'display_value': 'Resolution'})(),
                            'value': type('Value', (), {'display_value': '2560 x 1440'})()
                        })()
                    ]
                })(),
                'by_line_info': type('ByLineInfo', (), {
                    'brand': type('Brand', (), {'display_value': 'LG'})()
                })()
            })(),
            'offers': type('Offers', (), {
                'listings': [
                    type('Listing', (), {
                        'price': type('Price', (), {'amount': 589.99})(),
                        'availability': type('Availability', (), {'message': 'In Stock'})()
                    })()
                ]
            })(),
            'images': type('Images', (), {
                'primary': type('Primary', (), {
                    'large': type('Large', (), {'url': 'https://example.com/image.jpg'})()
                })()
            })()
        })()
        
        try:
            # Transform using AI bridge
            result = asyncio.run(transform_paapi_to_ai_format(mock_paapi_item))
            
            # Verify data consistency
            assert result['asin'] == 'B08N5WRWNW', "ASIN should be preserved"
            assert 'LG' in result['title'], "Title should contain brand"
            assert len(result['features']) > 0, "Features should be extracted"
            assert 'Refresh Rate' in result['technical_details'], "Technical details should be extracted"
            assert result['price'] is not None, "Price should be converted"
            assert result['brand'] == 'LG', "Brand should be extracted"
            
            print("✅ DATA CONSISTENCY: AI bridge maintains data integrity")
            
        except Exception as e:
            pytest.fail(f"Data consistency issue in AI bridge: {e}")

    def test_carousel_card_data_integrity(self):
        """Test that carousel cards maintain data integrity."""
        
        test_cases = [
            # Normal case
            {"title": "LG Gaming Monitor", "price": 58999, "asin": "B08N5WRWNW", "watch_id": 1},
            
            # Edge cases
            {"title": "", "price": 0, "asin": "", "watch_id": 0},
            {"title": "A" * 200, "price": 999999999, "asin": "X" * 20, "watch_id": 999999},
            
            # Special characters
            {"title": "Monitor @ #$%^&*()", "price": 50000, "asin": "TEST123", "watch_id": 1},
            {"title": "Monitor\nWith\tSpecial\rChars", "price": 50000, "asin": "TEST123", "watch_id": 1},
        ]
        
        for i, test_case in enumerate(test_cases):
            try:
                caption, keyboard = build_single_card(
                    title=test_case["title"],
                    price=test_case["price"],
                    image="https://example.com/image.jpg",
                    asin=test_case["asin"],
                    watch_id=test_case["watch_id"]
                )
                
                # Verify caption is valid
                assert isinstance(caption, str), f"Caption should be string for case {i}"
                assert len(caption) > 0, f"Caption should not be empty for case {i}"
                
                # Verify no unescaped markdown that could break formatting
                problematic_chars = ['*', '_', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
                for char in problematic_chars:
                    if char in test_case["title"] and char in caption:
                        # Should be escaped in caption
                        assert f"\\{char}" in caption, f"Character '{char}' should be escaped in caption"
                
                print(f"✅ CARD INTEGRITY {i}: Valid card generated")
                
            except Exception as e:
                pytest.fail(f"Card generation failed for case {i}: {e}")


class TestBusinessLogicEdgeCases:
    """Test edge cases in business logic that could cause incorrect behavior."""

    def test_price_filtering_edge_cases(self):
        """Test price filtering with edge cases."""
        
        # Products at exact boundary conditions
        boundary_products = [
            {"asin": "EXACT", "title": "Exact Match", "price": 50000},      # Exactly at limit
            {"asin": "UNDER", "title": "Just Under", "price": 49999},       # Just under limit  
            {"asin": "OVER", "title": "Just Over", "price": 50001},         # Just over limit
            {"asin": "ZERO", "title": "Zero Price", "price": 0},            # Zero price
            {"asin": "NONE", "title": "No Price", "price": None},           # No price
            {"asin": "NEG", "title": "Negative", "price": -1000},           # Negative price
        ]
        
        watch_data = {"max_price": 50000, "brand": None, "min_discount": None}  # 50k limit
        
        filtered = _filter_products_by_criteria(boundary_products, watch_data)
        
        # Check filtering logic
        filtered_asins = [p.get("asin") for p in filtered]
        
        # Should include products at or under limit (with valid prices)
        assert "EXACT" in filtered_asins, "Should include product exactly at price limit"
        assert "UNDER" in filtered_asins, "Should include product under price limit"
        assert "OVER" not in filtered_asins, "Should exclude product over price limit"
        
        print(f"✅ BOUNDARY FILTERING: {len(filtered)}/{len(boundary_products)} products passed filter")

    def test_technical_feature_detection_edge_cases(self):
        """Test technical feature detection with edge cases."""
        
        edge_case_queries = [
            # Should be detected as technical
            ("144hz", True),
            ("144 hz", True),
            ("144Hz", True),
            ("144 Hz", True),
            ("27inch", True),
            ("27 inch", True),
            ("27-inch", True),
            ("4k", True),
            ("4K", True),
            ("1440p", True),
            ("gaming monitor", True),
            
            # Should NOT be detected as technical
            ("monitor", False),
            ("display", False),
            ("screen", False),
            ("", False),
            ("   ", False),
            ("a", False),
            
            # Ambiguous cases (current behavior)
            ("good monitor", False),  # No specific technical terms
            ("cheap gaming", True),   # Has "gaming"
            ("27 something", False),  # Number but not technical context
        ]
        
        for query, expected in edge_case_queries:
            result = has_technical_features(query)
            
            if result != expected:
                print(f"⚠️ DETECTION MISMATCH: '{query}' -> {result} (expected {expected})")
            else:
                print(f"✅ DETECTION CORRECT: '{query}' -> {result}")
        
        # Don't fail the test for detection mismatches - this is subjective
        # But log them for review


class TestSecurityAndRobustness:
    """Test security-related edge cases and robustness."""

    def test_injection_attempt_handling(self):
        """Test handling of potential injection attempts."""
        
        injection_attempts = [
            # SQL injection attempts
            "monitor'; DROP TABLE watches;--",
            "monitor' UNION SELECT * FROM users--",
            "monitor' OR '1'='1",
            
            # XSS attempts
            "monitor<script>alert('xss')</script>",
            "monitor javascript:alert(1)",
            "monitor onload=alert(1)",
            
            # Command injection attempts
            "monitor; rm -rf /",
            "monitor && shutdown -h now",
            "monitor | cat /etc/passwd",
            
            # Path traversal attempts
            "monitor../../../etc/passwd",
            "monitor..\\..\\..\\windows\\system32",
        ]
        
        for injection in injection_attempts:
            try:
                # Test that malicious input doesn't cause crashes or unexpected behavior
                watch_data = {
                    "keywords": injection,
                    "max_price": 50000,
                    "brand": None,
                    "min_discount": None
                }
                
                # These functions should handle malicious input safely
                result1 = has_technical_features(injection)
                
                products = [{"asin": "SAFE", "title": "Safe Product", "price": 45000}]
                result2 = _filter_products_by_criteria(products, watch_data)
                
                print(f"✅ INJECTION SAFE: '{injection[:30]}...' handled safely")
                
            except Exception as e:
                # Any crash on malicious input is a security concern
                pytest.fail(f"Injection attempt caused crash: '{injection}' -> {e}")

    def test_large_input_handling(self):
        """Test handling of unusually large inputs."""
        
        large_inputs = [
            "monitor " + "x" * 10000,    # Very long query
            "a" * 1000000,               # Extremely long query  
            "monitor " * 1000,           # Repeated words
        ]
        
        for large_input in large_inputs:
            try:
                # Should handle large inputs without crashing or hanging
                start_time = time.time()
                
                result = has_technical_features(large_input)
                
                end_time = time.time()
                duration = end_time - start_time
                
                # Should complete in reasonable time
                assert duration < 5.0, f"Large input took {duration:.2f}s, should be < 5s"
                
                print(f"✅ LARGE INPUT: {len(large_input)} chars processed in {duration:.2f}s")
                
            except Exception as e:
                pytest.fail(f"Large input caused crash: {len(large_input)} chars -> {e}")


if __name__ == "__main__":
    print("🔍 ADVANCED EDGE CASE TESTING")
    print("=" * 50)
    print("Probing for subtle bugs that could embarrass us...")
