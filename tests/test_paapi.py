"""Tests for Amazon PA-API wrapper."""

import pytest
from unittest.mock import AsyncMock, patch

from bot.paapi_wrapper import get_item, search_products
from bot.errors import QuotaExceededError


@pytest.mark.asyncio
async def test_get_item_success():
    """Test successful PA-API item fetching."""
    mock_item_data = {
        "price": 12300,  # 123.00 rupees in paise
        "title": "Test Product",
        "image": "https://example.com/image.jpg",
    }

    with patch("bot.paapi_wrapper._sync_get_item", return_value=mock_item_data):
        result = await get_item("B0ABC123")
        assert result == mock_item_data


@pytest.mark.asyncio
async def test_get_item_quota_exceeded():
    """Test PA-API quota exceeded error handling."""
    with patch(
        "bot.paapi_wrapper._sync_get_item",
        side_effect=Exception("503 Service Unavailable")
    ):
        with pytest.raises(QuotaExceededError):
            await get_item("B0ABC123")


@pytest.mark.asyncio
async def test_search_products_success():
    """Test successful PA-API product search."""
    mock_products = [
        {
            "asin": "B0ABC123",
            "title": "Test Product 1",
            "price": 12300,
            "image": "https://example.com/image1.jpg",
        },
        {
            "asin": "B0DEF456",
            "title": "Test Product 2", 
            "price": 15600,
            "image": "https://example.com/image2.jpg",
        }
    ]

    with patch("bot.paapi_wrapper._sync_search_products", return_value=mock_products):
        results = await search_products("test query")
        assert len(results) == 2
        assert results[0]["asin"] == "B0ABC123"
        assert results[1]["title"] == "Test Product 2"


@pytest.mark.asyncio
async def test_search_products_no_credentials():
    """Test PA-API search when credentials are not configured."""
    with patch("bot.paapi_wrapper.settings") as mock_settings:
        mock_settings.PAAPI_ACCESS_KEY = None
        mock_settings.PAAPI_SECRET_KEY = None
        mock_settings.PAAPI_TAG = None
        
        results = await search_products("test query")
        assert results == []


@pytest.mark.asyncio  
async def test_search_products_quota_exceeded():
    """Test PA-API search quota exceeded error handling."""
    with patch(
        "bot.paapi_wrapper._sync_search_products",
        side_effect=Exception("503 Service Unavailable")
    ):
        with pytest.raises(QuotaExceededError):
            await search_products("test query")


@pytest.mark.asyncio
async def test_search_products_error_fallback():
    """Test PA-API search error returns empty list."""
    with patch(
        "bot.paapi_wrapper._sync_search_products",
        side_effect=Exception("Generic error")
    ):
        results = await search_products("test query")
        assert results == []



