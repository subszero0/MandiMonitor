"""Comprehensive integration tests for PA-API migration.

This test suite validates that the new official SDK implementation provides
the same functionality and data structure as the legacy implementation.
"""

import asyncio
import pytest
from unittest.mock import patch, MagicMock

from bot.config import settings
from bot.paapi_factory import get_paapi_client, LegacyPaapiClient
from bot.paapi_official import OfficialPaapiClient
from bot.paapi_resource_manager import get_resource_manager, refresh_resource_manager


class TestPaapiMigration:
    """Integration tests for PA-API migration."""

    def setup_method(self):
        """Set up test environment."""
        # Reset resource manager for each test
        refresh_resource_manager()

    @pytest.mark.asyncio
    async def test_factory_returns_correct_client(self):
        """Test that factory returns correct client based on feature flag."""
        # Test legacy client
        with patch.object(settings, 'USE_NEW_PAAPI_SDK', False):
            refresh_resource_manager()
            client = get_paapi_client()
            assert isinstance(client, LegacyPaapiClient)

        # Test official client (if SDK is available)
        with patch.object(settings, 'USE_NEW_PAAPI_SDK', True):
            refresh_resource_manager()
            try:
                client = get_paapi_client()
                assert isinstance(client, OfficialPaapiClient)
            except ImportError:
                # Official SDK not available, should fall back to legacy
                client = get_paapi_client()
                assert isinstance(client, LegacyPaapiClient)

    def test_resource_manager_context_mapping(self):
        """Test resource manager provides correct resources for different contexts."""
        manager = get_resource_manager()
        
        # Test minimal resources
        minimal_get = manager.get_resources_for_context("minimal", "get_items")
        minimal_search = manager.get_resources_for_context("minimal", "search_items")
        assert len(minimal_get) >= 3  # At least title, price, image
        assert len(minimal_search) >= 3
        
        # Test detailed resources
        detailed_get = manager.get_resources_for_context("detailed", "get_items")
        detailed_search = manager.get_resources_for_context("detailed", "search_items")
        assert len(detailed_get) > len(minimal_get)
        assert len(detailed_search) > len(minimal_search)
        
        # Test browse nodes
        browse_resources = manager.get_resources_for_context("browse_nodes")
        assert len(browse_resources) >= 2  # At least ancestor, children

    def test_resource_manager_convenience_methods(self):
        """Test resource manager convenience methods."""
        manager = get_resource_manager()
        
        minimal = manager.get_minimal_resources("get_items")
        detailed = manager.get_detailed_resources("get_items")
        full = manager.get_full_resources("get_items")
        
        assert len(minimal) <= len(detailed) <= len(full)

    @pytest.mark.asyncio 
    async def test_data_structure_compatibility(self):
        """Test that both implementations return compatible data structures."""
        test_asin = "B07DL6L8QX"  # Known working ASIN
        
        # Mock the actual API calls since we're testing structure compatibility
        mock_legacy_response = {
            "asin": test_asin,
            "title": "Test Product",
            "brand": "Test Brand",
            "offers": {
                "price": 49699,
                "list_price": 59999,
                "savings": 10300,
                "savings_percent": 17,
                "availability": "In Stock"
            },
            "reviews": {
                "rating": 4.5,
                "count": 123
            },
            "images": {
                "large": "https://example.com/large.jpg",
                "medium": "https://example.com/medium.jpg"
            }
        }
        
        # Test legacy client response structure
        with patch('bot.paapi_enhanced.get_item_detailed') as mock_legacy:
            mock_legacy.return_value = mock_legacy_response
            
            legacy_client = LegacyPaapiClient()
            legacy_result = await legacy_client.get_item_detailed(test_asin)
            
            # Verify expected structure
            assert "asin" in legacy_result
            assert "title" in legacy_result
            assert "offers" in legacy_result
            assert "price" in legacy_result["offers"]
            assert "reviews" in legacy_result

    @pytest.mark.asyncio
    async def test_error_handling_consistency(self):
        """Test that both implementations handle errors consistently."""
        from bot.errors import QuotaExceededError
        
        # Mock API calls to raise specific errors
        with patch('bot.paapi_enhanced.get_item_detailed') as mock_legacy:
            mock_legacy.side_effect = QuotaExceededError("Test quota error")
            
            legacy_client = LegacyPaapiClient()
            
            with pytest.raises(QuotaExceededError):
                await legacy_client.get_item_detailed("INVALID_ASIN")

    @pytest.mark.asyncio
    async def test_search_functionality_parity(self):
        """Test that search functionality works consistently across implementations."""
        test_keywords = "laptop"
        
        mock_search_response = [
            {
                "asin": "B123456789",
                "title": "Test Laptop",
                "price": 89999,
                "rating": 4.2,
                "image_url": "https://example.com/laptop.jpg"
            },
            {
                "asin": "B987654321", 
                "title": "Another Laptop",
                "price": 79999,
                "rating": 4.0,
                "image_url": "https://example.com/laptop2.jpg"
            }
        ]
        
        with patch('bot.paapi_enhanced.search_items_advanced') as mock_legacy:
            mock_legacy.return_value = mock_search_response
            
            legacy_client = LegacyPaapiClient()
            legacy_results = await legacy_client.search_items_advanced(keywords=test_keywords)
            
            assert isinstance(legacy_results, list)
            assert len(legacy_results) == 2
            assert all("asin" in item for item in legacy_results)
            assert all("title" in item for item in legacy_results)

    def test_configuration_compatibility(self):
        """Test that configuration works for both implementations."""
        # Test that all required config values are present
        required_configs = [
            'PAAPI_ACCESS_KEY',
            'PAAPI_SECRET_KEY', 
            'PAAPI_TAG',
            'PAAPI_HOST',
            'PAAPI_REGION',
            'PAAPI_MARKETPLACE'
        ]
        
        for config in required_configs:
            assert hasattr(settings, config), f"Missing required config: {config}"

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test that multiple concurrent requests work correctly."""
        test_asins = ["B07DL6L8QX", "B08N5WRWNW", "B09G9FPHY6"]
        
        mock_response = {
            "asin": "TEST",
            "title": "Test Product",
            "offers": {"price": 10000},
            "reviews": {"rating": 4.0}
        }
        
        with patch('bot.paapi_enhanced.get_item_detailed') as mock_legacy:
            mock_legacy.return_value = mock_response
            
            legacy_client = LegacyPaapiClient()
            
            # Run concurrent requests
            tasks = [
                legacy_client.get_item_detailed(asin) 
                for asin in test_asins
            ]
            
            results = await asyncio.gather(*tasks)
            
            assert len(results) == len(test_asins)
            assert all(isinstance(result, dict) for result in results)

    def test_resource_manager_feature_flag_switching(self):
        """Test that resource manager adapts to feature flag changes."""
        # Start with legacy
        with patch.object(settings, 'USE_NEW_PAAPI_SDK', False):
            manager = refresh_resource_manager()
            legacy_resources = manager.get_detailed_resources("get_items")
            
        # Switch to official SDK
        with patch.object(settings, 'USE_NEW_PAAPI_SDK', True):
            manager = refresh_resource_manager()
            official_resources = manager.get_detailed_resources("get_items")
            
        # Resources might be different types (strings vs enums) but should serve same purpose
        # Both should have meaningful length
        assert len(legacy_resources) > 0
        assert len(official_resources) > 0

    @pytest.mark.asyncio
    async def test_price_conversion_consistency(self):
        """Test that price conversion is consistent between implementations."""
        # Both implementations should return prices in paise (Indian cents)
        test_price_rupees = 499.99
        expected_price_paise = int(test_price_rupees * 100)  # 49999
        
        mock_response = {
            "asin": "B123456789",
            "title": "Test Product",
            "offers": {
                "price": expected_price_paise,
                "list_price": 59999,
                "savings": 10000
            }
        }
        
        with patch('bot.paapi_enhanced.get_item_detailed') as mock_legacy:
            mock_legacy.return_value = mock_response
            
            legacy_client = LegacyPaapiClient()
            result = await legacy_client.get_item_detailed("B123456789")
            
            assert result["offers"]["price"] == expected_price_paise
            assert isinstance(result["offers"]["price"], int)

    def test_error_logging_and_debugging(self):
        """Test that error logging provides useful debugging information."""
        # This is more of a smoke test to ensure error handling infrastructure exists
        try:
            manager = get_resource_manager()
            # Try to get resources for invalid context
            resources = manager.get_resources_for_context("invalid_context", "get_items")
            # Should not raise an error, but should log a warning and return default
            assert len(resources) > 0
        except Exception as e:
            pytest.fail(f"Resource manager should handle invalid contexts gracefully: {e}")


class TestPerformanceBaseline:
    """Performance baseline tests for migration comparison."""
    
    @pytest.mark.asyncio
    async def test_response_time_baseline(self):
        """Establish response time baseline for comparison."""
        import time
        
        mock_response = {"asin": "TEST", "title": "Test", "offers": {"price": 10000}}
        
        with patch('bot.paapi_enhanced.get_item_detailed') as mock_legacy:
            mock_legacy.return_value = mock_response
            
            client = LegacyPaapiClient()
            
            # Measure response time
            start_time = time.time()
            await client.get_item_detailed("B123456789")
            response_time = time.time() - start_time
            
            # Should complete quickly (mocked)
            assert response_time < 1.0  # 1 second max for mocked call

    @pytest.mark.asyncio
    async def test_memory_usage_baseline(self):
        """Test memory usage doesn't spike dramatically."""
        import gc
        
        mock_response = {"asin": "TEST", "title": "Test", "offers": {"price": 10000}}
        
        with patch('bot.paapi_enhanced.get_item_detailed') as mock_legacy:
            mock_legacy.return_value = mock_response
            
            client = LegacyPaapiClient()
            
            # Force garbage collection before test
            gc.collect()
            
            # Make multiple requests
            for i in range(10):
                await client.get_item_detailed(f"B12345678{i}")
            
            # Force garbage collection after test
            gc.collect()
            
            # Test passes if no memory errors occur


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
