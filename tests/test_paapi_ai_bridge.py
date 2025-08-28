"""
Tests for PA-API AI Bridge functionality.

This module tests the Phase R1 implementation of the PA-API AI Bridge,
ensuring proper transformation of Amazon data to AI-compatible format
and integration with existing PA-API functionality.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from bot.paapi_ai_bridge import (
    transform_paapi_to_ai_format,
    extract_title,
    extract_features_list,
    extract_technical_info,
    extract_price,
    extract_image_url,
    extract_brand,
    extract_manufacturer,
    extract_rating_count,
    extract_average_rating,
    extract_availability,
    extract_product_info,
    extract_offers_info,
    search_products_with_ai_analysis,
    get_items_with_ai_analysis,
    PaapiAiPerformanceTracker,
    AI_SEARCH_RESOURCES,
    AI_GETITEMS_RESOURCES,
    DEFAULT_SEARCH_RESOURCES,
    DEFAULT_GETITEMS_RESOURCES
)


class TestPaapiItemTransformation:
    """Test PA-API response transformation to AI format."""

    def create_mock_paapi_item(self, **overrides) -> Mock:
        """Create a mock PA-API item for testing."""
        mock_item = Mock()
        mock_item.asin = overrides.get('asin', 'B08N5WRWNW')
        
        # Mock item_info
        mock_item.item_info = Mock()
        mock_item.item_info.title = Mock()
        mock_item.item_info.title.display_value = overrides.get('title', 'Test Gaming Monitor 144Hz')
        
        # Mock features
        mock_item.item_info.features = Mock()
        mock_item.item_info.features.display_values = overrides.get('features', [
            '144Hz refresh rate',
            '27-inch display',
            'IPS panel'
        ])
        
        # Mock technical info
        mock_item.item_info.technical_info = overrides.get('technical_info', None)
        
        # Mock by_line_info
        mock_item.item_info.by_line_info = Mock()
        mock_item.item_info.by_line_info.brand = Mock()
        mock_item.item_info.by_line_info.brand.display_value = overrides.get('brand', 'Samsung')
        mock_item.item_info.by_line_info.manufacturer = Mock()
        mock_item.item_info.by_line_info.manufacturer.display_value = overrides.get('manufacturer', 'Samsung Electronics')
        
        # Mock product_info
        mock_item.item_info.product_info = Mock()
        mock_item.item_info.product_info.color = Mock()
        mock_item.item_info.product_info.color.display_value = overrides.get('color', 'Black')
        
        # Mock offers
        mock_item.offers = Mock()
        mock_item.offers.listings = [Mock()]
        mock_item.offers.listings[0].price = Mock()
        mock_item.offers.listings[0].price.amount = overrides.get('price_amount', 299.99)
        mock_item.offers.listings[0].availability = Mock()
        mock_item.offers.listings[0].availability.message = overrides.get('availability', 'In Stock')
        
        # Mock images
        mock_item.images = Mock()
        mock_item.images.primary = Mock()
        mock_item.images.primary.large = Mock()
        mock_item.images.primary.large.url = overrides.get('image_url', 'https://example.com/image.jpg')
        
        # Mock customer reviews
        mock_item.customer_reviews = Mock()
        mock_item.customer_reviews.star_rating = Mock()
        mock_item.customer_reviews.star_rating.value = overrides.get('rating', 4.5)
        mock_item.customer_reviews.count = overrides.get('review_count', 1250)
        
        return mock_item

    @pytest.mark.asyncio
    async def test_transform_paapi_to_ai_format_basic(self):
        """Test basic transformation of PA-API item to AI format."""
        mock_item = self.create_mock_paapi_item(
            asin='B08N5WRWNW',
            title='Samsung 27" Gaming Monitor 144Hz',
            brand='Samsung',
            price_amount=25000.0,  # ₹250.00
            rating=4.5,
            review_count=1250
        )
        
        result = await transform_paapi_to_ai_format(mock_item)
        
        assert result['asin'] == 'B08N5WRWNW'
        assert result['title'] == 'Samsung 27" Gaming Monitor 144Hz'
        assert result['brand'] == 'Samsung'
        assert result['manufacturer'] == 'Samsung Electronics'
        assert result['price'] == 2500000  # Price in paise
        assert result['average_rating'] == 4.5
        assert result['rating_count'] == 1250
        assert result['availability'] == 'In Stock'
        assert len(result['features']) == 3
        assert 'ai_extraction_metadata' in result
        assert result['ai_extraction_metadata']['source'] == 'paapi_ai_bridge'

    @pytest.mark.asyncio
    async def test_transform_handles_missing_fields(self):
        """Test transformation handles missing fields gracefully."""
        mock_item = Mock()
        mock_item.asin = 'B08N5WRWNW'
        # Explicitly set missing attributes to None
        mock_item.item_info = None
        mock_item.offers = None
        mock_item.images = None
        mock_item.customer_reviews = None
        
        result = await transform_paapi_to_ai_format(mock_item)
        
        assert result['asin'] == 'B08N5WRWNW'
        assert result['title'] == ''
        assert result['features'] == []
        assert result['price'] is None
        assert result['brand'] is None
        assert 'ai_extraction_metadata' in result

    def test_extract_title_success(self):
        """Test successful title extraction."""
        mock_item = self.create_mock_paapi_item(title='Test Gaming Monitor')
        result = extract_title(mock_item)
        assert result == 'Test Gaming Monitor'

    def test_extract_title_missing(self):
        """Test title extraction with missing data."""
        mock_item = Mock()
        mock_item.item_info = None
        result = extract_title(mock_item)
        assert result == ''

    def test_extract_features_list_success(self):
        """Test successful features extraction."""
        mock_item = self.create_mock_paapi_item(features=[
            '144Hz refresh rate',
            '27-inch display',
            'IPS panel technology'
        ])
        result = extract_features_list(mock_item)
        assert len(result) == 3
        assert '144Hz refresh rate' in result
        assert '27-inch display' in result
        assert 'IPS panel technology' in result

    def test_extract_features_list_empty(self):
        """Test features extraction with empty list."""
        mock_item = self.create_mock_paapi_item(features=[])
        result = extract_features_list(mock_item)
        assert result == []

    def test_extract_technical_info_success(self):
        """Test technical info extraction with structured data."""
        mock_tech_info = Mock()
        
        # Create proper mock structure for technical info
        refresh_rate_item = Mock()
        refresh_rate_item.name = Mock()
        refresh_rate_item.name.display_value = 'Refresh Rate'
        refresh_rate_item.value = Mock()
        refresh_rate_item.value.display_value = '144 Hz'
        
        panel_type_item = Mock()
        panel_type_item.name = Mock()
        panel_type_item.name.display_value = 'Panel Type'
        panel_type_item.value = Mock()
        panel_type_item.value.display_value = 'IPS'
        
        mock_tech_info.display_values = [refresh_rate_item, panel_type_item]
        
        mock_item = self.create_mock_paapi_item(technical_info=mock_tech_info)
        result = extract_technical_info(mock_item)
        
        assert 'Refresh Rate' in result
        assert result['Refresh Rate'] == '144 Hz'
        assert 'Panel Type' in result
        assert result['Panel Type'] == 'IPS'

    def test_extract_price_success(self):
        """Test price extraction and conversion to paise."""
        mock_item = self.create_mock_paapi_item(price_amount=299.99)
        result = extract_price(mock_item)
        assert result == 29999  # ₹299.99 in paise

    def test_extract_price_missing(self):
        """Test price extraction with missing data."""
        mock_item = Mock()
        mock_item.offers = None
        result = extract_price(mock_item)
        assert result is None

    def test_extract_brand_success(self):
        """Test brand extraction."""
        mock_item = self.create_mock_paapi_item(brand='Samsung')
        result = extract_brand(mock_item)
        assert result == 'Samsung'

    def test_extract_manufacturer_success(self):
        """Test manufacturer extraction."""
        mock_item = self.create_mock_paapi_item(manufacturer='Samsung Electronics')
        result = extract_manufacturer(mock_item)
        assert result == 'Samsung Electronics'

    def test_extract_rating_count_success(self):
        """Test rating count extraction."""
        mock_item = self.create_mock_paapi_item(review_count=1250)
        result = extract_rating_count(mock_item)
        assert result == 1250

    def test_extract_average_rating_success(self):
        """Test average rating extraction."""
        mock_item = self.create_mock_paapi_item(rating=4.5)
        result = extract_average_rating(mock_item)
        assert result == 4.5

    def test_extract_availability_success(self):
        """Test availability extraction."""
        mock_item = self.create_mock_paapi_item(availability='In Stock')
        result = extract_availability(mock_item)
        assert result == 'In Stock'

    def test_extract_product_info_success(self):
        """Test product info extraction."""
        mock_item = self.create_mock_paapi_item(color='Black')
        result = extract_product_info(mock_item)
        assert 'color' in result
        assert result['color'] == 'Black'

    def test_extract_offers_info_success(self):
        """Test offers info extraction."""
        mock_item = self.create_mock_paapi_item()
        # Add delivery info
        mock_item.offers.listings[0].delivery_info = Mock()
        mock_item.offers.listings[0].delivery_info.is_prime_eligible = True
        mock_item.offers.listings[0].delivery_info.is_free_shipping_eligible = True
        
        result = extract_offers_info(mock_item)
        assert result['prime_eligible'] is True
        assert result['free_shipping'] is True


class TestResourceConfiguration:
    """Test resource configuration for AI analysis."""

    def test_ai_search_resources_contains_critical_fields(self):
        """Test that AI search resources include critical fields for AI analysis."""
        from paapi5_python_sdk.models.search_items_resource import SearchItemsResource
        
        critical_resources = [
            SearchItemsResource.ITEMINFO_FEATURES,
            SearchItemsResource.ITEMINFO_TECHNICALINFO,
            SearchItemsResource.ITEMINFO_TITLE,
            SearchItemsResource.OFFERS_LISTINGS_PRICE
        ]
        
        for resource in critical_resources:
            assert resource in AI_SEARCH_RESOURCES, f"Critical resource {resource} missing from AI_SEARCH_RESOURCES"

    def test_ai_getitems_resources_contains_critical_fields(self):
        """Test that AI GetItems resources include critical fields for AI analysis."""
        from paapi5_python_sdk.models.get_items_resource import GetItemsResource
        
        critical_resources = [
            GetItemsResource.ITEMINFO_FEATURES,
            GetItemsResource.ITEMINFO_TECHNICALINFO,
            GetItemsResource.ITEMINFO_TITLE,
            GetItemsResource.OFFERSV2_LISTINGS_PRICE
        ]
        
        for resource in critical_resources:
            assert resource in AI_GETITEMS_RESOURCES, f"Critical resource {resource} missing from AI_GETITEMS_RESOURCES"

    def test_default_resources_are_minimal(self):
        """Test that default resources contain minimal required fields."""
        assert len(DEFAULT_SEARCH_RESOURCES) <= len(AI_SEARCH_RESOURCES)
        assert len(DEFAULT_GETITEMS_RESOURCES) <= len(AI_GETITEMS_RESOURCES)


class TestAiSearchFunctionality:
    """Test AI-enhanced search functionality."""

    @pytest.mark.asyncio
    async def test_search_products_with_ai_analysis_success(self):
        """Test successful AI-enhanced search (mocked response handling)."""
        # For now, test with AI disabled to avoid PA-API dependencies
        result = await search_products_with_ai_analysis(
            keywords='gaming monitor 144hz',
            search_index='Electronics',
            item_count=5,
            enable_ai_analysis=False  # Test fallback mode
        )
        
        assert 'products' in result
        assert 'processing_time_ms' in result
        assert 'ai_analysis_enabled' in result
        assert result['ai_analysis_enabled'] is False
        assert 'metadata' in result
        assert result['metadata']['search_keywords'] == 'gaming monitor 144hz'

    @pytest.mark.asyncio
    async def test_search_products_handles_api_failure(self):
        """Test search handles failures gracefully."""
        # Test with empty keywords to simulate failure
        result = await search_products_with_ai_analysis(
            keywords='',
            enable_ai_analysis=False
        )
        
        assert 'products' in result
        assert result['products'] == []  # Should return empty list on error
        assert 'metadata' in result

    @pytest.mark.asyncio
    async def test_get_items_with_ai_analysis_success(self):
        """Test successful AI-enhanced GetItems."""
        # Test with AI disabled to avoid dependencies
        result = await get_items_with_ai_analysis(
            asins=['B08N5WRWNW'],
            enable_ai_analysis=False
        )
        
        # Should return dictionary structure
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_get_items_with_empty_asins(self):
        """Test GetItems with empty ASIN list."""
        result = await get_items_with_ai_analysis(asins=[])
        assert result == {}


class TestPerformanceTracking:
    """Test performance tracking functionality."""

    def test_performance_tracker_initialization(self):
        """Test performance tracker initializes correctly."""
        tracker = PaapiAiPerformanceTracker()
        metrics = tracker.get_metrics()
        
        assert metrics['total_searches'] == 0
        assert metrics['total_transformations'] == 0
        assert metrics['avg_search_time_ms'] == 0.0
        assert metrics['avg_transformation_time_ms'] == 0.0
        assert 'last_reset' in metrics

    def test_performance_tracker_record_search(self):
        """Test recording search performance metrics."""
        tracker = PaapiAiPerformanceTracker()
        
        # Record successful searches
        tracker.record_search(100.0, True)
        tracker.record_search(200.0, True)
        
        metrics = tracker.get_metrics()
        assert metrics['total_searches'] == 2
        assert metrics['avg_search_time_ms'] == 150.0  # Average of 100 and 200

    def test_performance_tracker_record_transformation(self):
        """Test recording transformation performance metrics."""
        tracker = PaapiAiPerformanceTracker()
        
        # Record successful transformations
        tracker.record_transformation(10.0, True)
        tracker.record_transformation(20.0, True)
        
        metrics = tracker.get_metrics()
        assert metrics['total_transformations'] == 2
        assert metrics['avg_transformation_time_ms'] == 15.0  # Average of 10 and 20

    def test_performance_tracker_reset(self):
        """Test resetting performance metrics."""
        tracker = PaapiAiPerformanceTracker()
        
        # Record some metrics
        tracker.record_search(100.0, True)
        tracker.record_transformation(10.0, True)
        
        # Reset and verify
        tracker.reset_metrics()
        metrics = tracker.get_metrics()
        
        assert metrics['total_searches'] == 0
        assert metrics['total_transformations'] == 0
        assert metrics['avg_search_time_ms'] == 0.0
        assert metrics['avg_transformation_time_ms'] == 0.0


class TestConfigurationAndFeatureFlags:
    """Test configuration and feature flag functionality."""

    @patch('bot.paapi_ai_bridge.settings')
    def test_is_ai_analysis_enabled_true(self, mock_settings):
        """Test AI analysis enabled flag returns True."""
        from bot.paapi_ai_bridge import is_ai_analysis_enabled
        mock_settings.ENABLE_AI_ANALYSIS = True
        assert is_ai_analysis_enabled() is True

    @patch('bot.paapi_ai_bridge.settings')
    def test_is_ai_analysis_enabled_false(self, mock_settings):
        """Test AI analysis enabled flag returns False."""
        from bot.paapi_ai_bridge import is_ai_analysis_enabled
        mock_settings.ENABLE_AI_ANALYSIS = False
        assert is_ai_analysis_enabled() is False

    @patch('bot.paapi_ai_bridge.settings')
    def test_should_use_enhanced_resources_true(self, mock_settings):
        """Test enhanced resources flag returns True."""
        from bot.paapi_ai_bridge import should_use_enhanced_resources
        mock_settings.ENABLE_ENHANCED_PAAPI = True
        assert should_use_enhanced_resources() is True


class TestErrorHandlingAndRobustness:
    """Test error handling and robustness of AI bridge."""

    @pytest.mark.asyncio
    async def test_transform_handles_malformed_item(self):
        """Test transformation handles malformed PA-API items."""
        # Create item with missing required attributes
        mock_item = Mock()
        mock_item.asin = 'B08N5WRWNW'
        # Set missing attributes to None to simulate malformed response
        mock_item.item_info = None
        mock_item.offers = None
        mock_item.images = None
        mock_item.customer_reviews = None
        
        result = await transform_paapi_to_ai_format(mock_item)
        
        # Should not crash and should provide safe defaults
        assert result['asin'] == 'B08N5WRWNW'
        assert result['title'] == ''
        assert result['features'] == []
        assert result['technical_details'] == {}
        assert 'ai_extraction_metadata' in result

    def test_extract_functions_handle_none_input(self):
        """Test extraction functions handle None input gracefully."""
        none_item = None
        
        assert extract_title(none_item) == ''
        assert extract_features_list(none_item) == []
        assert extract_technical_info(none_item) == {}
        assert extract_price(none_item) is None
        assert extract_brand(none_item) is None

    def test_extract_functions_handle_attribute_errors(self):
        """Test extraction functions handle AttributeError gracefully."""
        mock_item = Mock()
        # Remove all attributes to trigger AttributeError
        del mock_item.item_info
        del mock_item.offers
        del mock_item.images
        del mock_item.customer_reviews
        
        # These should not raise exceptions
        assert extract_title(mock_item) == ''
        assert extract_features_list(mock_item) == []
        assert extract_price(mock_item) is None
        assert extract_brand(mock_item) is None


if __name__ == '__main__':
    pytest.main([__file__])
