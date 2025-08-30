"""Tests for dynamic brand discovery functionality."""

import pytest
from unittest.mock import AsyncMock, patch

from bot.watch_flow_backup import get_dynamic_brands


class TestDynamicBrands:
    """Test dynamic brand discovery."""

    @pytest.mark.asyncio
    async def test_dynamic_brands_with_paapi_success(self):
        """Test dynamic brand discovery when PA-API returns results."""
        # Mock PA-API search results
        mock_paapi_results = [
            {"title": "3M Super Polish Car Care Kit", "price": 50000},
            {"title": "Meguiar's Gold Class Car Wash", "price": 60000},
            {"title": "Chemical Guys VSS Scratch Remover", "price": 45000},
            {"title": "Turtle Wax Super Hard Shell Paste", "price": 40000},
        ]
        
        with patch('bot.watch_flow.search_products', return_value=mock_paapi_results):
            brands = await get_dynamic_brands("car polish")
            
        # Should extract real car care brands
        expected_brands = ["3m", "chemical", "meguiar's", "turtle"]
        assert len(brands) > 0
        assert any(brand in expected_brands for brand in brands)
        # Should not fall back to common electronics brands
        common_brands = ["samsung", "lg", "sony", "apple"]
        assert not any(brand in common_brands for brand in brands)

    @pytest.mark.asyncio
    async def test_dynamic_brands_with_scraper_fallback(self):
        """Test dynamic brand discovery when PA-API fails but scraper succeeds."""
        # Mock PA-API failure (empty results)
        # Mock scraper success
        mock_scraper_results = [
            {"title": "Himalaya Herbals Purifying Neem Face Wash", "price": 15000},
            {"title": "Cetaphil Gentle Skin Cleanser", "price": 25000},
            {"title": "Neutrogena Ultra Gentle Daily Cleanser", "price": 30000},
            {"title": "Plum Green Tea Renewed Clarity Night Gel", "price": 35000},
        ]
        
        with patch('bot.watch_flow.search_products', return_value=[]), \
             patch('bot.scraper.scrape_amazon_search', return_value=mock_scraper_results):
            brands = await get_dynamic_brands("facewash")
            
        # Should extract real skincare brands
        expected_brands = ["himalaya", "cetaphil", "neutrogena", "plum"]
        assert len(brands) > 0
        assert any(brand in expected_brands for brand in brands)
        # Should not fall back to common electronics brands
        common_brands = ["samsung", "lg", "sony", "apple"]
        assert not any(brand in common_brands for brand in brands)

    @pytest.mark.asyncio
    async def test_dynamic_brands_fallback_to_common(self):
        """Test dynamic brand discovery falls back to common brands when all sources fail."""
        # Mock both PA-API and scraper failure
        with patch('bot.watch_flow.search_products', return_value=[]), \
             patch('bot.scraper.scrape_amazon_search', return_value=[]):
            brands = await get_dynamic_brands("unknown product")
            
        # Should fall back to common electronics brands
        common_brands = ["samsung", "lg", "sony", "boat", "apple", "mi", "oneplus", "realme", "oppo"]
        assert len(brands) > 0
        assert all(brand in common_brands for brand in brands)

    @pytest.mark.asyncio
    async def test_brand_extraction_filters_quantities(self):
        """Test that brand extraction filters out quantities and measurements."""
        mock_results = [
            {"title": "250 ml Car Polish by 3M Premium Quality", "price": 50000},
            {"title": "1 L Meguiar's Gold Class 220 g Pack", "price": 60000},
            {"title": "500gm Turtle Wax IA260166334 Model", "price": 40000},
        ]
        
        with patch('bot.watch_flow.search_products', return_value=mock_results):
            brands = await get_dynamic_brands("car polish")
            
        # Should extract brand names, not quantities
        assert "3m" in brands or "3m premium" in brands
        assert "meguiar's" in brands
        assert "turtle" in brands or "turtle wax" in brands
        
        # Should not extract quantities or product codes
        unwanted = ["250", "ml", "l", "220", "g", "500gm", "ia260166334"]
        assert not any(unwanted_item in brands for unwanted_item in unwanted)

    @pytest.mark.asyncio 
    async def test_brand_extraction_different_patterns(self):
        """Test brand extraction with various title patterns."""
        mock_results = [
            {"title": "Samsung Galaxy S24 Ultra", "price": 120000},  # Brand at start
            {"title": "Phone Case (Apple iPhone 15)", "price": 2000},  # Brand in parentheses  
            {"title": "Car Polish by Meguiar's Premium", "price": 5000},  # Brand with "by"
            {"title": "3M - Super Polish Kit", "price": 4000},  # Brand with separator
            {"title": "Dr. Smith's Face Wash", "price": 1500},  # Brand with possessive
        ]
        
        with patch('bot.watch_flow.search_products', return_value=mock_results):
            brands = await get_dynamic_brands("mixed products")
            
        # Should extract brands from different patterns
        expected_brands = ["samsung", "apple", "meguiar's", "3m", "dr"]
        found_brands = [brand for brand in brands if brand in expected_brands]
        assert len(found_brands) >= 3  # Should find at least 3 different pattern matches

    @pytest.mark.asyncio
    async def test_max_brands_limit(self):
        """Test that brand discovery respects the max_brands parameter."""
        # Create many mock results to test limiting
        mock_results = [
            {"title": f"Brand{i} Product Name", "price": 10000} for i in range(20)
        ]
        
        with patch('bot.watch_flow.search_products', return_value=mock_results):
            brands = await get_dynamic_brands("test products", max_brands=5)
            
        # Should respect the limit
        assert len(brands) <= 5

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test that errors are handled gracefully."""
        # Mock an exception in search_products
        with patch('bot.watch_flow.search_products', side_effect=Exception("API Error")), \
             patch('bot.scraper.scrape_amazon_search', side_effect=Exception("Scraper Error")):
            brands = await get_dynamic_brands("car polish")
            
        # Should fall back to common brands on error
        common_brands = ["samsung", "lg", "sony", "boat", "apple", "mi", "oneplus", "realme", "oppo"]
        assert len(brands) > 0
        assert all(brand in common_brands for brand in brands)