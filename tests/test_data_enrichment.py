"""Tests for data enrichment service."""

from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from bot.data_enrichment import ProductEnrichmentService
from bot.enhanced_models import Product, ProductOffers, CustomerReviews, PriceHistory
from bot.models import Price


@pytest.fixture
def test_engine():
    """Create test database engine."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def test_session(test_engine):
    """Create test database session."""
    with Session(test_engine) as session:
        yield session


@pytest.fixture
def enrichment_service():
    """Create enrichment service for testing."""
    return ProductEnrichmentService()


@pytest.fixture
def mock_product_data():
    """Mock comprehensive product data."""
    return {
        "asin": "B08N5WRWNW",
        "title": "Test Gaming Laptop",
        "brand": "Test Brand",
        "manufacturer": "Test Corp",
        "product_group": "Electronics",
        "features": ["Gaming", "RGB Keyboard", "Fast SSD"],
        "color": "Black",
        "size": "15.6 inch",
        "images": {
            "small": "https://example.com/small.jpg",
            "medium": "https://example.com/medium.jpg",
            "large": "https://example.com/large.jpg",
            "variants": ["https://example.com/var1.jpg"]
        },
        "offers": {
            "price": 80000,  # ₹800 in paise
            "list_price": 100000,
            "savings_amount": 20000,
            "savings_percentage": 20,
            "availability_type": "InStock",
            "condition": "New",
            "is_prime_eligible": True,
            "is_amazon_fulfilled": True,
            "merchant_name": "Amazon",
            "promotions": [
                {"type": "discount", "display_name": "20% off"}
            ]
        },
        "reviews": {
            "count": 250,
            "average_rating": 4.4
        },
        "browse_nodes": [
            {"id": 1951048031, "name": "Electronics", "sales_rank": 5}
        ]
    }


@pytest.mark.asyncio
async def test_enrich_product_data_success(enrichment_service, test_session, mock_product_data):
    """Test successful product enrichment."""
    with patch('bot.data_enrichment.get_item_detailed', new_callable=AsyncMock) as mock_get_item, \
         patch('bot.data_enrichment.engine', test_session.bind):
        
        mock_get_item.return_value = mock_product_data
        
        result = await enrichment_service.enrich_product_data("B08N5WRWNW")
        
        assert result is True
        mock_get_item.assert_called_once()


@pytest.mark.asyncio
async def test_enrich_product_data_quota_exceeded(enrichment_service):
    """Test quota exceeded handling."""
    from bot.errors import QuotaExceededError
    
    with patch('bot.data_enrichment.get_item_detailed', new_callable=AsyncMock) as mock_get_item:
        mock_get_item.side_effect = QuotaExceededError("Quota exceeded")
        
        result = await enrichment_service.enrich_product_data("B08N5WRWNW")
        
        assert result is False


@pytest.mark.asyncio
async def test_store_enriched_data(enrichment_service, test_session, mock_product_data):
    """Test storing enriched data in database."""
    with patch('bot.data_enrichment.engine', test_session.bind):
        await enrichment_service._store_enriched_data("B08N5WRWNW", mock_product_data)
        
        # Verify Product record
        product = test_session.get(Product, "B08N5WRWNW")
        assert product is not None
        assert product.title == "Test Gaming Laptop"
        assert product.brand == "Test Brand"
        assert product.features_list == ["Gaming", "RGB Keyboard", "Fast SSD"]
        
        # Verify ProductOffers record
        offers = test_session.query(ProductOffers).filter_by(asin="B08N5WRWNW").first()
        assert offers is not None
        assert offers.price == 80000
        assert offers.savings_percentage == 20
        assert offers.is_prime_eligible is True
        
        # Verify CustomerReviews record
        reviews = test_session.get(CustomerReviews, "B08N5WRWNW")
        assert reviews is not None
        assert reviews.review_count == 250
        assert reviews.average_rating == 4.4
        
        # Verify PriceHistory record
        price_history = test_session.query(PriceHistory).filter_by(asin="B08N5WRWNW").first()
        assert price_history is not None
        assert price_history.price == 80000


@pytest.mark.asyncio
async def test_calculate_deal_quality_score(enrichment_service, test_session):
    """Test deal quality scoring algorithm."""
    with patch('bot.data_enrichment.engine', test_session.bind):
        # Create test data
        product = Product(asin="B08N5WRWNW", title="Test Product")
        test_session.add(product)
        
        offer = ProductOffers(
            asin="B08N5WRWNW",
            price=2000,
            list_price=2500,
            savings_percentage=20,
            availability_type="InStock",
            is_prime_eligible=True,
            is_amazon_fulfilled=True
        )
        test_session.add(offer)
        
        reviews = CustomerReviews(
            asin="B08N5WRWNW",
            review_count=100,
            average_rating=4.5
        )
        test_session.add(reviews)
        
        # Add price history
        for i in range(10):
            price_history = PriceHistory(
                asin="B08N5WRWNW",
                price=2000 + (i * 100),  # Prices from 2000 to 2900
                timestamp=datetime.utcnow() - timedelta(days=i)
            )
            test_session.add(price_history)
        
        test_session.commit()
        
        score = await enrichment_service.calculate_deal_quality_score("B08N5WRWNW")
        
        # Should be a good score due to good price, reviews, and availability
        assert 70.0 <= score <= 100.0


@pytest.mark.asyncio
async def test_detect_price_patterns(enrichment_service, test_session):
    """Test price pattern detection."""
    with patch('bot.data_enrichment.engine', test_session.bind):
        # Create test price history with trend
        product = Product(asin="B08N5WRWNW", title="Test Product")
        test_session.add(product)
        
        # Create descending price trend
        prices = [3000, 2900, 2800, 2700, 2600, 2500, 2400, 2300, 2200, 2100]
        for i, price in enumerate(prices):
            price_history = PriceHistory(
                asin="B08N5WRWNW",
                price=price,
                timestamp=datetime.utcnow() - timedelta(days=len(prices) - i)
            )
            test_session.add(price_history)
        
        test_session.commit()
        
        patterns = await enrichment_service.detect_price_patterns("B08N5WRWNW")
        
        assert "error" not in patterns
        assert patterns["current_price"] == 2100
        assert patterns["min_price"] == 2100
        assert patterns["max_price"] == 3000
        assert patterns["trend"] == "decreasing"
        assert patterns["data_points"] == 10


@pytest.mark.asyncio
async def test_price_score_calculation(enrichment_service, test_session):
    """Test price score calculation."""
    with patch('bot.data_enrichment.engine', test_session.bind):
        # Create price history
        prices = [2000, 2100, 2200, 2300, 2400, 2500]
        for price in prices:
            price_history = PriceHistory(
                asin="B08N5WRWNW",
                price=price,
                timestamp=datetime.utcnow() - timedelta(days=1)
            )
            test_session.add(price_history)
        
        test_session.commit()
        
        # Current price is lowest, should get high score
        score = await enrichment_service._calculate_price_score(test_session, "B08N5WRWNW", 1900)
        assert score > 80.0
        
        # Current price is highest, should get low score
        score = await enrichment_service._calculate_price_score(test_session, "B08N5WRWNW", 2600)
        assert score < 20.0


@pytest.mark.asyncio
async def test_review_score_calculation(enrichment_service, test_session):
    """Test review score calculation."""
    with patch('bot.data_enrichment.engine', test_session.bind):
        # High rating, many reviews
        reviews = CustomerReviews(
            asin="B08N5WRWNW",
            review_count=1500,
            average_rating=4.8
        )
        test_session.add(reviews)
        test_session.commit()
        
        score = await enrichment_service._calculate_review_score(test_session, "B08N5WRWNW")
        assert score > 90.0  # Should be high due to excellent rating and high count


@pytest.mark.asyncio
async def test_availability_score_calculation(enrichment_service):
    """Test availability score calculation."""
    # In stock, Prime eligible, Amazon fulfilled
    offer = ProductOffers(
        asin="B08N5WRWNW",
        price=2000,
        availability_type="InStock",
        is_prime_eligible=True,
        is_amazon_fulfilled=True
    )
    
    score = await enrichment_service._calculate_availability_score(offer)
    assert score > 100.0  # Should exceed 100 due to bonuses
    
    # Out of stock
    offer.availability_type = "OutOfStock"
    score = await enrichment_service._calculate_availability_score(offer)
    assert score == 0.0


@pytest.mark.asyncio
async def test_discount_score_calculation(enrichment_service):
    """Test discount score calculation."""
    offer = ProductOffers(asin="B08N5WRWNW", price=2000)
    
    # High discount
    offer.savings_percentage = 60
    score = await enrichment_service._calculate_discount_score(offer)
    assert score == 100.0
    
    # Medium discount
    offer.savings_percentage = 25
    score = await enrichment_service._calculate_discount_score(offer)
    assert score == 60.0
    
    # No discount
    offer.savings_percentage = None
    score = await enrichment_service._calculate_discount_score(offer)
    assert score == 0.0


@pytest.mark.asyncio
async def test_drop_probability_calculation(enrichment_service):
    """Test price drop probability calculation."""
    # Prices that show pattern of drops from similar levels
    prices = [2000, 1900, 2000, 1950, 2000, 1850, 2000]
    
    probability = await enrichment_service._calculate_drop_probability(prices)
    
    # Should show high probability since price tends to drop from 2000 level
    assert 0.5 < probability <= 1.0


@pytest.mark.asyncio
async def test_insufficient_data_handling(enrichment_service, test_session):
    """Test handling of insufficient data scenarios."""
    with patch('bot.data_enrichment.engine', test_session.bind):
        # No product data
        score = await enrichment_service.calculate_deal_quality_score("NONEXISTENT")
        assert score == 0.0
        
        # No price history
        patterns = await enrichment_service.detect_price_patterns("NONEXISTENT")
        assert "error" in patterns


@pytest.mark.asyncio
async def test_error_handling(enrichment_service):
    """Test error handling in enrichment service."""
    with patch('bot.data_enrichment.get_item_detailed', new_callable=AsyncMock) as mock_get_item:
        mock_get_item.side_effect = Exception("Network error")
        
        result = await enrichment_service.enrich_product_data("B08N5WRWNW")
        assert result is False


@pytest.mark.asyncio
async def test_update_existing_product(enrichment_service, test_session, mock_product_data):
    """Test updating existing product data."""
    with patch('bot.data_enrichment.engine', test_session.bind):
        # Create existing product
        existing_product = Product(
            asin="B08N5WRWNW",
            title="Old Title",
            brand="Old Brand"
        )
        test_session.add(existing_product)
        test_session.commit()
        
        # Store updated data
        await enrichment_service._store_enriched_data("B08N5WRWNW", mock_product_data)
        
        # Verify update
        updated_product = test_session.get(Product, "B08N5WRWNW")
        assert updated_product.title == "Test Gaming Laptop"
        assert updated_product.brand == "Test Brand"


@pytest.mark.asyncio
async def test_priority_scheduling(enrichment_service):
    """Test priority-based scheduling."""
    with patch('bot.data_enrichment.get_item_detailed', new_callable=AsyncMock) as mock_get_item:
        mock_get_item.return_value = {"asin": "test", "title": "test"}
        
        await enrichment_service.enrich_product_data("B08N5WRWNW", priority="high")
        
        # Verify priority was passed
        args = mock_get_item.call_args
        assert args[1]["priority"] == "high"  # Second positional arg should be priority
