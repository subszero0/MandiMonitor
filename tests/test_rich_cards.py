"""Tests for Rich Cards Builder functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from bot.rich_cards import RichCardBuilder, CarouselBuilder


class TestRichCardBuilder:
    """Test cases for RichCardBuilder."""

    @pytest.fixture
    def rich_card_builder(self):
        """Create RichCardBuilder instance for testing."""
        return RichCardBuilder()

    @pytest.fixture
    def mock_product(self):
        """Mock Product data for testing."""
        product = MagicMock()
        product.asin = "B0TEST123"
        product.title = "Test Product Title"
        product.brand = "TestBrand"
        product.large_image = "https://example.com/large.jpg"
        product.medium_image = "https://example.com/medium.jpg"
        product.small_image = "https://example.com/small.jpg"
        product.features_list = ["Feature 1", "Feature 2", "Feature 3"]
        return product

    @pytest.fixture
    def mock_offers(self):
        """Mock ProductOffers data for testing."""
        offers = MagicMock()
        offers.asin = "B0TEST123"
        offers.price = 2500000  # ₹25,000 in paise
        offers.list_price = 3000000  # ₹30,000 in paise
        offers.availability_type = "InStock"
        offers.is_prime_eligible = True
        offers.is_amazon_fulfilled = True
        offers.max_order_quantity = 5
        offers.savings_percentage = 16.67
        offers.savings_amount = 500000
        return offers

    @pytest.fixture
    def mock_reviews(self):
        """Mock CustomerReviews data for testing."""
        reviews = MagicMock()
        reviews.asin = "B0TEST123"
        reviews.average_rating = 4.5
        reviews.review_count = 1250
        return reviews

    @pytest.mark.asyncio
    async def test_build_comprehensive_card_success(
        self, rich_card_builder, mock_product, mock_offers, mock_reviews
    ):
        """Test successful comprehensive card building."""
        with patch("bot.rich_cards.Session") as mock_session:
            # Setup mock session
            mock_session_instance = mock_session.return_value.__enter__.return_value
            mock_session_instance.get.side_effect = [mock_product, mock_reviews]
            mock_session_instance.exec.return_value.first.return_value = mock_offers

            # Mock market intelligence
            with patch.object(rich_card_builder.market_intel, 'calculate_deal_quality') as mock_deal_quality:
                mock_deal_quality.return_value = {
                    "score": 85.0,
                    "quality": "excellent",
                    "factors": {"price_score": 90, "review_score": 85}
                }

                result = await rich_card_builder.build_comprehensive_card("B0TEST123")

                # Verify result structure
                assert result["enhanced"] is True
                assert result["deal_quality"] == 85.0
                assert "caption" in result
                assert "keyboard" in result
                assert "image" in result
                assert result["product_data"]["asin"] == "B0TEST123"

                # Verify caption contains key information
                caption = result["caption"]
                assert "Test Product Title" in caption
                assert "TestBrand" in caption
                assert "₹25,000.00" in caption
                assert "Deal Quality: 85/100" in caption

    @pytest.mark.asyncio
    async def test_build_comprehensive_card_fallback(self, rich_card_builder):
        """Test fallback when product data is not available."""
        with patch("bot.rich_cards.Session") as mock_session:
            # Setup mock session to return None (no product found)
            mock_session_instance = mock_session.return_value.__enter__.return_value
            mock_session_instance.get.return_value = None

            result = await rich_card_builder.build_comprehensive_card("B0TEST123")

            # Verify fallback behavior
            assert result["enhanced"] is False
            assert result["fallback"] is True
            assert "caption" in result
            assert "keyboard" in result

    @pytest.mark.asyncio
    async def test_build_comparison_carousel(self, rich_card_builder):
        """Test building comparison carousel."""
        with patch.object(rich_card_builder, 'build_comprehensive_card') as mock_build:
            # Mock return values for different products
            mock_build.side_effect = [
                {"enhanced": True, "deal_quality": 85, "product_data": {"asin": "B0TEST123"}},
                {"enhanced": True, "deal_quality": 75, "product_data": {"asin": "B0TEST456"}},
                {"enhanced": True, "deal_quality": 90, "product_data": {"asin": "B0TEST789"}},
            ]

            products = ["B0TEST123", "B0TEST456", "B0TEST789"]
            result = await rich_card_builder.build_comparison_carousel(products)

            # Verify carousel is sorted by deal quality (highest first)
            assert len(result) == 3
            assert result[0]["deal_quality"] == 90  # B0TEST789
            assert result[1]["deal_quality"] == 85  # B0TEST123
            assert result[2]["deal_quality"] == 75  # B0TEST456

    @pytest.mark.asyncio
    async def test_build_enhanced_deal_card(
        self, rich_card_builder, mock_product, mock_offers, mock_reviews
    ):
        """Test building enhanced deal card."""
        with patch("bot.rich_cards.Session") as mock_session:
            mock_session_instance = mock_session.return_value.__enter__.return_value
            mock_session_instance.get.side_effect = [mock_product, mock_reviews]
            mock_session_instance.exec.return_value.first.return_value = mock_offers

            with patch.object(rich_card_builder.market_intel, 'calculate_deal_quality') as mock_deal_quality:
                mock_deal_quality.return_value = {
                    "score": 92.0,
                    "quality": "exceptional",
                    "factors": {"price_score": 95, "review_score": 90}
                }

                result = await rich_card_builder.build_enhanced_deal_card(
                    "B0TEST123", 2500000, watch_id=123, urgency="high"
                )

                # Verify deal card properties
                assert result["enhanced"] is True
                assert result["deal_type"] == "enhanced"
                assert result["urgency"] == "high"
                assert result["deal_quality"] == 92.0

                # Verify caption contains deal-specific content
                caption = result["caption"]
                assert "EXCEPTIONAL DEAL!" in caption or "EXCELLENT DEAL!" in caption
                assert "Deal Score: 92/100" in caption

    @pytest.mark.asyncio
    async def test_build_enhanced_caption(self, rich_card_builder, mock_product, mock_offers, mock_reviews):
        """Test building enhanced caption."""
        deal_quality = {
            "score": 88.0,
            "quality": "excellent",
            "factors": {"price_score": 90, "review_score": 85}
        }

        caption = await rich_card_builder._build_enhanced_caption(
            mock_product, mock_offers, mock_reviews, deal_quality
        )

        # Verify caption content
        assert "Test Product Title" in caption
        assert "TestBrand" in caption
        assert "₹25,000.00" in caption
        assert "₹30,000.00" in caption  # List price
        assert "Deal Quality: 88/100" in caption
        assert "4.5/5" in caption
        assert "1,250 reviews" in caption
        assert "In Stock" in caption
        assert "Prime Eligible" in caption

    @pytest.mark.asyncio
    async def test_build_enhanced_keyboard_search_context(self, rich_card_builder, mock_product):
        """Test building enhanced keyboard for search context."""
        keyboard = await rich_card_builder._build_enhanced_keyboard(
            "B0TEST123", mock_product, "search", None
        )

        # Verify keyboard structure
        assert len(keyboard.inline_keyboard) >= 3  # At least 3 rows of buttons
        
        # Check for expected buttons
        all_buttons = []
        for row in keyboard.inline_keyboard:
            for button in row:
                all_buttons.append(button.text)
        
        assert any("BUY NOW" in btn or "View Product" in btn for btn in all_buttons)
        assert any("Create Watch" in btn for btn in all_buttons)
        assert any("Price History" in btn for btn in all_buttons)

    @pytest.mark.asyncio
    async def test_build_deal_caption_exceptional_quality(
        self, rich_card_builder, mock_product, mock_offers, mock_reviews
    ):
        """Test deal caption for exceptional quality deals."""
        deal_quality = {"score": 95.0, "quality": "exceptional"}
        
        caption = await rich_card_builder._build_deal_caption(
            mock_product, mock_offers, mock_reviews, deal_quality, 2500000, "critical"
        )

        # Verify exceptional deal formatting
        assert "EXCEPTIONAL DEAL!" in caption
        assert "Deal Score: 95/100" in caption
        assert "LIMITED TIME - ACT FAST!" in caption


class TestCarouselBuilder:
    """Test cases for CarouselBuilder."""

    @pytest.fixture
    def carousel_builder(self):
        """Create CarouselBuilder instance for testing."""
        return CarouselBuilder()

    @pytest.mark.asyncio
    async def test_build_search_results_carousel(self, carousel_builder):
        """Test building search results carousel."""
        with patch.object(carousel_builder.rich_card_builder, 'build_comparison_carousel') as mock_build:
            mock_build.return_value = [
                {"enhanced": True, "deal_quality": 85, "product_data": {"asin": "B0TEST123"}},
                {"enhanced": True, "deal_quality": 75, "product_data": {"asin": "B0TEST456"}},
            ]

            result = await carousel_builder.build_search_results_carousel(
                ["B0TEST123", "B0TEST456"], "test query"
            )

            # Verify carousel structure
            assert result["total_products"] == 2
            assert result["has_enhanced"] is True
            assert result["query"] == "test query"
            assert "Search Results (2 products)" in result["header"]
            assert "Enhanced Cards: 2/2" in result["header"]

    @pytest.mark.asyncio
    async def test_build_search_results_carousel_no_results(self, carousel_builder):
        """Test search results carousel with no results."""
        with patch.object(carousel_builder.rich_card_builder, 'build_comparison_carousel') as mock_build:
            mock_build.return_value = []

            result = await carousel_builder.build_search_results_carousel([], "empty query")

            # Verify empty results handling
            assert result["total_products"] == 0
            assert result["has_enhanced"] is False
            assert "No results found" in result["header"]

    @pytest.mark.asyncio
    async def test_build_deals_carousel(self, carousel_builder):
        """Test building deals carousel."""
        deals_data = [
            {"asin": "B0TEST123", "current_price": 2500000, "urgency": "high", "watch_id": 1},
            {"asin": "B0TEST456", "current_price": 1500000, "urgency": "medium", "watch_id": 2},
        ]

        with patch.object(carousel_builder.rich_card_builder, 'build_enhanced_deal_card') as mock_build:
            mock_build.side_effect = [
                {"enhanced": True, "deal_quality": 88, "urgency": "high"},
                {"enhanced": True, "deal_quality": 76, "urgency": "medium"},
            ]

            result = await carousel_builder.build_deals_carousel(deals_data)

            # Verify deals carousel
            assert result["total_deals"] == 2
            assert result["average_quality"] == 82.0  # (88 + 76) / 2
            assert "Deal Alerts (2 deals)" in result["header"]

    @pytest.mark.asyncio
    async def test_build_watch_summary_carousel(self, carousel_builder):
        """Test building watch summary carousel."""
        result = await carousel_builder.build_watch_summary_carousel(12345)

        # Verify basic structure (placeholder implementation)
        assert "Your Watches" in result["header"]
        assert result["total_watches"] == 0  # Placeholder returns empty
        assert result["active_watches"] == 0


# Integration tests

@pytest.mark.asyncio
async def test_rich_cards_integration_with_market_intelligence():
    """Test integration between rich cards and market intelligence."""
    rich_card_builder = RichCardBuilder()
    
    with patch("bot.rich_cards.Session"), \
         patch.object(rich_card_builder.market_intel, 'calculate_deal_quality') as mock_deal_quality:
        
        mock_deal_quality.return_value = {
            "score": 85.0,
            "quality": "excellent",
            "factors": {
                "price_score": 90,
                "review_score": 85,
                "availability_score": 80,
                "discount_score": 85,
                "brand_score": 75
            },
            "recommendations": ["Excellent deal - consider buying immediately"]
        }

        # Verify market intelligence is called during card building
        await rich_card_builder.build_comprehensive_card("B0TEST123")
        mock_deal_quality.assert_called_once()


@pytest.mark.asyncio 
async def test_error_handling_in_rich_cards():
    """Test error handling in rich card building."""
    rich_card_builder = RichCardBuilder()
    
    with patch("bot.rich_cards.Session") as mock_session:
        # Simulate database error
        mock_session.side_effect = Exception("Database connection error")
        
        result = await rich_card_builder.build_comprehensive_card("B0TEST123")
        
        # Verify graceful error handling
        assert result["enhanced"] is False
        assert "error" in result or "fallback" in result


# Performance tests

@pytest.mark.asyncio
async def test_comparison_carousel_performance():
    """Test performance with multiple products."""
    carousel_builder = CarouselBuilder()
    
    # Test with 10 products (maximum expected)
    products = [f"B0TEST{i:03d}" for i in range(10)]
    
    with patch.object(carousel_builder.rich_card_builder, 'build_comparison_carousel') as mock_build:
        mock_build.return_value = [{"enhanced": True, "deal_quality": 80} for _ in range(10)]
        
        result = await carousel_builder.build_search_results_carousel(products, "performance test")
        
        # Verify all products are processed
        assert result["total_products"] == 10
        assert result["has_enhanced"] is True
