"""Tests for Market Intelligence System."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from bot.market_intelligence import MarketIntelligence
from bot.enhanced_models import Product, ProductOffers, CustomerReviews, PriceHistory
from bot.models import Price


class TestMarketIntelligence:
    """Test Market Intelligence functionality."""

    @pytest.fixture
    def market_intel(self):
        """Create MarketIntelligence instance."""
        return MarketIntelligence()

    @pytest.fixture
    def sample_price_history(self):
        """Create sample price history data."""
        base_time = datetime.utcnow() - timedelta(days=30)
        history = []
        
        for i in range(30):
            history.append(PriceHistory(
                id=i,
                asin="B0TEST123",
                price=10000 + (i % 10) * 500,  # Varying prices
                timestamp=base_time + timedelta(days=i)
            ))
        
        return history

    @pytest.fixture
    def sample_product(self):
        """Create sample product data."""
        return Product(
            asin="B0TEST123",
            title="Test Product",
            brand="TestBrand",
            last_updated=datetime.utcnow()
        )

    @pytest.fixture
    def sample_offer(self):
        """Create sample product offer."""
        return ProductOffers(
            id=1,
            asin="B0TEST123",
            price=9500,
            list_price=12000,
            savings_percentage=20,
            availability_type="InStock",
            is_prime_eligible=True,
            is_amazon_fulfilled=True
        )

    @pytest.fixture
    def sample_reviews(self):
        """Create sample customer reviews."""
        return CustomerReviews(
            asin="B0TEST123",
            review_count=150,
            average_rating=4.3
        )

    @pytest.mark.asyncio
    async def test_analyze_price_trends_enhanced_history(
        self, market_intel, sample_price_history
    ):
        """Test price trend analysis with enhanced history."""
        with patch('bot.market_intelligence.Session') as mock_session:
            mock_session.return_value.__enter__.return_value.exec.return_value.all.return_value = sample_price_history
            
            result = await market_intel.analyze_price_trends("B0TEST123", "1month")
            
            assert "error" not in result
            assert result["asin"] == "B0TEST123"
            assert result["timeframe"] == "1month"
            assert result["data_points"] == 30
            assert "price_metrics" in result
            assert "trend_analysis" in result

    @pytest.mark.asyncio
    async def test_analyze_price_trends_no_history(self, market_intel):
        """Test price trend analysis with no history."""
        with patch('bot.market_intelligence.Session') as mock_session:
            mock_session.return_value.__enter__.return_value.exec.return_value.all.return_value = []
            
            result = await market_intel.analyze_price_trends("B0NOHISTORY", "1month")
            
            assert "error" in result
            assert result["error"] == "No price history available"

    @pytest.mark.asyncio
    async def test_calculate_deal_quality_comprehensive(
        self, market_intel, sample_product, sample_offer, sample_reviews, sample_price_history
    ):
        """Test comprehensive deal quality calculation."""
        with patch('bot.market_intelligence.Session') as mock_session:
            mock_session_instance = mock_session.return_value.__enter__.return_value
            
            # Mock database queries
            mock_session_instance.get.side_effect = lambda model, asin: {
                Product: sample_product,
                CustomerReviews: sample_reviews
            }.get(model)
            
            mock_session_instance.exec.return_value.first.return_value = sample_offer
            
            # Mock price history
            market_intel._get_price_history = AsyncMock(return_value=sample_price_history)
            
            result = await market_intel.calculate_deal_quality("B0TEST123", 9500)
            
            assert "error" not in result
            assert "score" in result
            assert 0 <= result["score"] <= 100
            assert "quality" in result
            assert "factors" in result
            assert "recommendations" in result

    @pytest.mark.asyncio
    async def test_calculate_deal_quality_no_data(self, market_intel):
        """Test deal quality calculation with no data."""
        with patch('bot.market_intelligence.Session') as mock_session:
            mock_session_instance = mock_session.return_value.__enter__.return_value
            mock_session_instance.get.return_value = None
            mock_session_instance.exec.return_value.first.return_value = None
            
            market_intel._get_price_history = AsyncMock(return_value=[])
            
            result = await market_intel.calculate_deal_quality("B0NODATA", 10000)
            
            assert result["score"] == 50.0
            assert result["reason"] == "No historical data available"

    @pytest.mark.asyncio
    async def test_predict_price_movement(self, market_intel, sample_price_history):
        """Test price movement prediction."""
        with patch('bot.market_intelligence.Session') as mock_session:
            mock_session.return_value.__enter__.return_value.exec.return_value.all.return_value = sample_price_history
            
            result = await market_intel.predict_price_movement("B0TEST123", 30)
            
            assert "error" not in result
            assert "predicted_price" in result
            assert "confidence" in result
            assert "price_range" in result
            assert 0 <= result["confidence"] <= 1

    @pytest.mark.asyncio
    async def test_predict_price_movement_insufficient_data(self, market_intel):
        """Test price prediction with insufficient data."""
        with patch('bot.market_intelligence.Session') as mock_session:
            # Return very few data points
            mock_session.return_value.__enter__.return_value.exec.return_value.all.return_value = []
            
            result = await market_intel.predict_price_movement("B0NODATA", 30)
            
            assert "error" in result
            assert "Insufficient historical data" in result["error"]

    @pytest.mark.asyncio
    async def test_generate_market_report(self, market_intel):
        """Test market report generation."""
        with patch('bot.market_intelligence.Session') as mock_session:
            # Mock category products
            market_intel._get_category_products = AsyncMock(return_value=["B0TEST123", "B0TEST456"])
            market_intel._analyze_market_trends = AsyncMock(return_value={"trend": "stable"})
            market_intel._find_best_deals = AsyncMock(return_value=[])
            market_intel._analyze_market_volatility = AsyncMock(return_value={"volatility": "low"})
            market_intel._generate_category_insights = AsyncMock(return_value={"insights": "stable"})
            market_intel._generate_market_recommendations = AsyncMock(return_value=["Market stable"])
            
            result = await market_intel.generate_market_report(category_id=123, timeframe="1week")
            
            assert "error" not in result
            assert "report_generated" in result
            assert "market_trends" in result
            assert "best_deals" in result

    def test_calculate_trend_direction_increasing(self, market_intel):
        """Test trend direction calculation for increasing prices."""
        prices = [1000, 1050, 1100, 1150, 1200]  # Increasing trend
        timestamps = [datetime.utcnow() - timedelta(days=i) for i in range(5, 0, -1)]
        
        import asyncio
        result = asyncio.run(market_intel._calculate_trend_direction(prices, timestamps))
        
        assert result["direction"] == "increasing"
        assert result["strength"] > 0

    def test_calculate_trend_direction_decreasing(self, market_intel):
        """Test trend direction calculation for decreasing prices."""
        prices = [1200, 1150, 1100, 1050, 1000]  # Decreasing trend
        timestamps = [datetime.utcnow() - timedelta(days=i) for i in range(5, 0, -1)]
        
        import asyncio
        result = asyncio.run(market_intel._calculate_trend_direction(prices, timestamps))
        
        assert result["direction"] == "decreasing"
        assert result["strength"] > 0

    def test_calculate_price_percentiles(self, market_intel):
        """Test price percentile calculations."""
        prices = [1000, 1100, 1200, 1300, 1400, 1500]
        current_price = 1200
        
        import asyncio
        result = asyncio.run(market_intel._calculate_price_percentiles(prices, current_price))
        
        assert "current_percentile" in result
        assert "p25" in result
        assert "p50_median" in result
        assert "p75" in result
        assert "is_good_deal" in result

    def test_detect_seasonal_patterns_insufficient_data(self, market_intel):
        """Test seasonal pattern detection with insufficient data."""
        short_history = [
            PriceHistory(
                id=1, asin="B0TEST123", price=1000, 
                timestamp=datetime.utcnow() - timedelta(days=1)
            )
        ]
        
        import asyncio
        result = asyncio.run(market_intel._detect_seasonal_patterns(short_history))
        
        assert result["pattern"] == "insufficient_data"

    def test_calculate_drop_probability(self, market_intel):
        """Test drop probability calculation."""
        prices = [1000, 950, 1050, 980, 1020, 970, 1030, 960, 1010, 950]
        
        import asyncio
        result = asyncio.run(market_intel._calculate_drop_probability(prices))
        
        assert 0 <= result <= 1

    @pytest.mark.asyncio
    async def test_calculate_price_factor(self, market_intel):
        """Test price factor calculation for deal quality."""
        # Mock price history with current price being low
        price_history = [
            Mock(price=1000), Mock(price=1100), Mock(price=1200), Mock(price=900)  # Current: 900
        ]
        
        result = await market_intel._calculate_price_factor(900, price_history)
        
        # 900 is lower than most prices, should get high score
        assert result > 70.0

    @pytest.mark.asyncio
    async def test_calculate_review_factor(self, market_intel, sample_reviews):
        """Test review factor calculation."""
        with patch('bot.market_intelligence.Session') as mock_session:
            mock_session.return_value.__enter__.return_value.get.return_value = sample_reviews
            
            result = await market_intel._calculate_review_factor(
                mock_session.return_value.__enter__.return_value, "B0TEST123"
            )
            
            # Good rating (4.3/5) with decent review count (150) should score well
            assert result > 80.0

    @pytest.mark.asyncio
    async def test_calculate_availability_factor(self, market_intel, sample_offer):
        """Test availability factor calculation."""
        result = await market_intel._calculate_availability_factor(sample_offer)
        
        # InStock + Prime + Amazon fulfilled should score high
        assert result > 90.0

    @pytest.mark.asyncio
    async def test_calculate_discount_factor(self, market_intel, sample_offer):
        """Test discount factor calculation."""
        result = await market_intel._calculate_discount_factor(sample_offer)
        
        # 20% discount should get moderate score
        assert 50.0 <= result <= 80.0

    @pytest.mark.asyncio
    async def test_calculate_brand_factor_premium_brand(self, market_intel):
        """Test brand factor for premium brand."""
        product = Product(asin="B0TEST123", title="Test", brand="Apple")
        
        result = await market_intel._calculate_brand_factor(product)
        
        # Apple is premium brand, should score high
        assert result == 90.0

    @pytest.mark.asyncio
    async def test_calculate_brand_factor_unknown_brand(self, market_intel):
        """Test brand factor for unknown brand."""
        product = Product(asin="B0TEST123", title="Test", brand="UnknownBrand")
        
        result = await market_intel._calculate_brand_factor(product)
        
        # Unknown brand should get moderate score
        assert result == 55.0

    @pytest.mark.asyncio
    async def test_generate_deal_recommendation(self, market_intel):
        """Test deal recommendation generation."""
        result = await market_intel._generate_deal_recommendation(
            current_price=1000,
            min_price=800,
            max_price=1500,
            avg_price=1200,
            drop_probability=0.3
        )
        
        assert "recommendation" in result
        assert "action" in result
        assert "reasoning" in result

    @pytest.mark.asyncio
    async def test_error_handling(self, market_intel):
        """Test error handling in market intelligence."""
        with patch('bot.market_intelligence.Session', side_effect=Exception("Database error")):
            result = await market_intel.analyze_price_trends("B0ERROR", "1month")
            
            assert "error" in result
            assert "Database error" in result["error"]


class TestMarketIntelligenceIntegration:
    """Integration tests for Market Intelligence."""

    @pytest.mark.asyncio
    async def test_full_analysis_pipeline(self):
        """Test complete analysis pipeline."""
        market_intel = MarketIntelligence()
        
        # Mock all dependencies
        with patch('bot.market_intelligence.Session') as mock_session:
            # Mock comprehensive data
            mock_session_instance = mock_session.return_value.__enter__.return_value
            
            # Mock price history
            price_history = [
                PriceHistory(id=i, asin="B0TEST123", price=1000 + i*10, 
                           timestamp=datetime.utcnow() - timedelta(days=30-i))
                for i in range(30)
            ]
            mock_session_instance.exec.return_value.all.return_value = price_history
            
            # Mock product and offers
            product = Product(asin="B0TEST123", title="Test Product", brand="TestBrand")
            offer = ProductOffers(
                id=1, asin="B0TEST123", price=1200, list_price=1500,
                savings_percentage=20, availability_type="InStock"
            )
            reviews = CustomerReviews(asin="B0TEST123", review_count=100, average_rating=4.5)
            
            mock_session_instance.get.side_effect = lambda model, asin: {
                Product: product,
                CustomerReviews: reviews
            }.get(model)
            
            mock_session_instance.exec.return_value.first.return_value = offer
            
            # Test trend analysis
            trends = await market_intel.analyze_price_trends("B0TEST123", "1month")
            assert "error" not in trends
            assert trends["data_points"] == 30
            
            # Test deal quality
            quality = await market_intel.calculate_deal_quality("B0TEST123", 1200)
            assert "error" not in quality
            assert 0 <= quality["score"] <= 100
            
            # Test price prediction
            prediction = await market_intel.predict_price_movement("B0TEST123", 30)
            assert "error" not in prediction
            assert "predicted_price" in prediction

