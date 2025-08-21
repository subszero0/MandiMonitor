"""Tests for enhanced PA-API wrapper."""

from unittest.mock import AsyncMock, Mock, patch
import pytest

from bot.paapi_enhanced import (
    get_item_detailed, search_items_advanced, batch_get_items,
    get_browse_nodes_hierarchy, _extract_comprehensive_data
)
from bot.errors import QuotaExceededError


@pytest.fixture
def mock_api_item():
    """Create mock PA-API item response."""
    mock_item = Mock()
    mock_item.asin = "B08N5WRWNW"
    mock_item.title = "Test Product"
    
    # Mock item_info
    mock_item.item_info = Mock()
    mock_item.item_info.by_line_info = Mock()
    mock_item.item_info.by_line_info.brand = Mock()
    mock_item.item_info.by_line_info.brand.display_value = "Test Brand"
    mock_item.item_info.features = Mock()
    mock_item.item_info.features.display_values = ["Feature 1", "Feature 2"]
    
    # Mock offers
    mock_item.offers = Mock()
    mock_item.offers.listings = [Mock()]
    mock_item.offers.listings[0].price = Mock()
    mock_item.offers.listings[0].price.amount = 25.00
    mock_item.offers.listings[0].availability = Mock()
    mock_item.offers.listings[0].availability.type = "InStock"
    
    # Mock images
    mock_item.images = Mock()
    mock_item.images.primary = Mock()
    mock_item.images.primary.large = Mock()
    mock_item.images.primary.large.url = "https://example.com/image.jpg"
    
    # Mock customer reviews
    mock_item.customer_reviews = Mock()
    mock_item.customer_reviews.count = 150
    mock_item.customer_reviews.star_rating = Mock()
    mock_item.customer_reviews.star_rating.value = 4.3
    
    return mock_item


@pytest.mark.asyncio
async def test_get_item_detailed_success(mock_api_item):
    """Test successful detailed item fetch."""
    with patch('bot.paapi_enhanced.acquire_api_permission', new_callable=AsyncMock), \
         patch('bot.paapi_enhanced.asyncio.to_thread', new_callable=AsyncMock) as mock_thread:
        
        mock_thread.return_value = {
            "asin": "B08N5WRWNW",
            "title": "Test Product",
            "brand": "Test Brand",
            "offers": {"price": 2500},
            "images": {"large": "https://example.com/image.jpg"},
            "reviews": {"count": 150, "average_rating": 4.3}
        }
        
        result = await get_item_detailed("B08N5WRWNW")
        
        assert result["asin"] == "B08N5WRWNW"
        assert result["title"] == "Test Product"
        assert result["brand"] == "Test Brand"
        assert result["offers"]["price"] == 2500


@pytest.mark.asyncio
async def test_get_item_detailed_quota_exceeded():
    """Test quota exceeded error handling."""
    with patch('bot.paapi_enhanced.acquire_api_permission', new_callable=AsyncMock), \
         patch('bot.paapi_enhanced.asyncio.to_thread', new_callable=AsyncMock) as mock_thread:
        
        mock_thread.side_effect = Exception("503 Service Unavailable")
        
        with pytest.raises(QuotaExceededError):
            await get_item_detailed("B08N5WRWNW")


@pytest.mark.asyncio
async def test_search_items_advanced_success():
    """Test advanced search functionality."""
    with patch('bot.paapi_enhanced.acquire_api_permission', new_callable=AsyncMock), \
         patch('bot.paapi_enhanced.asyncio.to_thread', new_callable=AsyncMock) as mock_thread:
        
        mock_thread.return_value = [
            {
                "asin": "B08N5WRWNW",
                "title": "Gaming Laptop",
                "offers": {"price": 80000},
                "reviews": {"average_rating": 4.5}
            }
        ]
        
        results = await search_items_advanced(
            keywords="gaming laptop",
            max_price=10000000,  # ₹100,000 in paise
            min_reviews_rating=4.0
        )
        
        assert len(results) == 1
        assert results[0]["title"] == "Gaming Laptop"


@pytest.mark.asyncio
async def test_search_items_advanced_no_credentials():
    """Test search with no PA-API credentials."""
    with patch('bot.paapi_enhanced.settings') as mock_settings:
        mock_settings.PAAPI_ACCESS_KEY = None
        mock_settings.PAAPI_SECRET_KEY = None
        mock_settings.PAAPI_TAG = None
        
        results = await search_items_advanced(keywords="test")
        assert results == []


@pytest.mark.asyncio
async def test_batch_get_items_success():
    """Test batch item fetching."""
    with patch('bot.paapi_enhanced.acquire_api_permission', new_callable=AsyncMock), \
         patch('bot.paapi_enhanced.asyncio.to_thread', new_callable=AsyncMock) as mock_thread:
        
        mock_thread.return_value = {
            "B08N5WRWNW": {"asin": "B08N5WRWNW", "title": "Product 1"},
            "B08N5WRXXX": {"asin": "B08N5WRXXX", "title": "Product 2"}
        }
        
        results = await batch_get_items(["B08N5WRWNW", "B08N5WRXXX"])
        
        assert len(results) == 2
        assert "B08N5WRWNW" in results
        assert "B08N5WRXXX" in results


@pytest.mark.asyncio
async def test_batch_get_items_too_many():
    """Test batch request with too many ASINs."""
    asins = [f"B08N5WRW{i:02d}" for i in range(11)]  # 11 ASINs
    
    with pytest.raises(ValueError, match="maximum 10 ASINs"):
        await batch_get_items(asins)


@pytest.mark.asyncio
async def test_batch_get_items_empty():
    """Test batch request with empty ASIN list."""
    results = await batch_get_items([])
    assert results == {}


@pytest.mark.asyncio
async def test_get_browse_nodes_hierarchy_success():
    """Test browse node hierarchy retrieval."""
    with patch('bot.paapi_enhanced.acquire_api_permission', new_callable=AsyncMock), \
         patch('bot.paapi_enhanced.asyncio.to_thread', new_callable=AsyncMock) as mock_thread:
        
        mock_thread.return_value = {
            "id": 1951048031,
            "name": "Electronics",
            "children": [
                {"id": 1951049031, "name": "Computers & Accessories"}
            ],
            "ancestors": [],
            "sales_rank": 1
        }
        
        result = await get_browse_nodes_hierarchy(1951048031)
        
        assert result["id"] == 1951048031
        assert result["name"] == "Electronics"
        assert len(result["children"]) == 1


def test_extract_comprehensive_data(mock_api_item):
    """Test comprehensive data extraction from PA-API response."""
    data = _extract_comprehensive_data(mock_api_item)
    
    assert data["asin"] == "B08N5WRWNW"
    assert data["title"] == "Test Product"
    assert data["brand"] == "Test Brand"
    assert data["features"] == ["Feature 1", "Feature 2"]
    assert data["offers"]["price"] == 2500  # Converted to paise
    assert data["offers"]["availability_type"] == "InStock"
    assert data["images"]["large"] == "https://example.com/image.jpg"
    assert data["reviews"]["count"] == 150
    assert data["reviews"]["average_rating"] == 4.3


def test_extract_comprehensive_data_minimal():
    """Test data extraction with minimal PA-API response."""
    mock_item = Mock()
    mock_item.asin = "B08N5WRWNW"
    mock_item.title = "Test Product"
    
    data = _extract_comprehensive_data(mock_item)
    
    assert data["asin"] == "B08N5WRWNW"
    assert data["title"] == "Test Product"
    assert data["brand"] is None
    assert data["features"] == []
    assert data["offers"]["price"] is None


@pytest.mark.asyncio
async def test_priority_handling():
    """Test that priority is passed to rate limiter."""
    with patch('bot.paapi_enhanced.acquire_api_permission', new_callable=AsyncMock) as mock_acquire, \
         patch('bot.paapi_enhanced.asyncio.to_thread', new_callable=AsyncMock) as mock_thread:
        
        mock_thread.return_value = {"asin": "test", "title": "test"}
        
        await get_item_detailed("B08N5WRWNW", priority="high")
        
        mock_acquire.assert_called_once_with("high")


@pytest.mark.asyncio
async def test_resource_customization():
    """Test custom resource specification."""
    custom_resources = ["ItemInfo.Title", "Offers.Listings.Price"]
    
    with patch('bot.paapi_enhanced.acquire_api_permission', new_callable=AsyncMock), \
         patch('bot.paapi_enhanced.asyncio.to_thread', new_callable=AsyncMock) as mock_thread:
        
        mock_thread.return_value = {"asin": "test", "title": "test"}
        
        await get_item_detailed("B08N5WRWNW", resources=custom_resources)
        
        # Verify custom resources were passed
        mock_thread.assert_called_once()
        args = mock_thread.call_args[0]
        assert args[1] == custom_resources


@pytest.mark.asyncio
async def test_error_handling_network():
    """Test network error handling."""
    with patch('bot.paapi_enhanced.acquire_api_permission', new_callable=AsyncMock), \
         patch('bot.paapi_enhanced.asyncio.to_thread', new_callable=AsyncMock) as mock_thread:
        
        mock_thread.side_effect = Exception("Network error")
        
        with pytest.raises(Exception, match="Network error"):
            await get_item_detailed("B08N5WRWNW")


@pytest.mark.asyncio
async def test_search_filtering():
    """Test search result filtering."""
    with patch('bot.paapi_enhanced.acquire_api_permission', new_callable=AsyncMock), \
         patch('bot.paapi_enhanced.asyncio.to_thread', new_callable=AsyncMock) as mock_thread:
        
        # Mock returns products with different ratings
        mock_thread.return_value = [
            {"asin": "B08N5WRWNW", "reviews": {"average_rating": 4.5}},
            {"asin": "B08N5WRXXX", "reviews": {"average_rating": 3.5}},
            {"asin": "B08N5WRYYY", "reviews": {"average_rating": 4.8}}
        ]
        
        results = await search_items_advanced(
            keywords="test",
            min_reviews_rating=4.0
        )
        
        # Should filter out the 3.5 rating product
        assert len(results) == 2
        for result in results:
            assert result["reviews"]["average_rating"] >= 4.0


@pytest.mark.asyncio
async def test_integration_with_rate_limiter():
    """Test integration with rate limiter for multiple requests."""
    with patch('bot.paapi_enhanced.acquire_api_permission', new_callable=AsyncMock) as mock_acquire, \
         patch('bot.paapi_enhanced.asyncio.to_thread', new_callable=AsyncMock) as mock_thread:
        
        mock_thread.return_value = {"asin": "test", "title": "test"}
        
        # Make multiple requests
        await get_item_detailed("B08N5WRWNW")
        await get_item_detailed("B08N5WRXXX")
        await get_item_detailed("B08N5WRYYY")
        
        # Rate limiter should be called for each request
        assert mock_acquire.call_count == 3
