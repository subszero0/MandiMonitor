"""Tests for Revenue Optimization Engine."""

import asyncio
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from bot.revenue_optimization import (
    RevenueOptimizer, 
    ConversionEvent, 
    ABTestVariant
)


class TestRevenueOptimizer:
    """Test cases for RevenueOptimizer class."""

    @pytest.fixture
    def revenue_optimizer(self):
        """Create RevenueOptimizer instance for testing."""
        return RevenueOptimizer()

    @pytest.fixture
    def sample_product_data(self):
        """Sample product data for testing."""
        return {
            "asin": "B0TEST123",
            "title": "Test Product",
            "price": 12345,  # ₹123.45 in paise
            "discount_percent": 25,
            "rating": 4.2,
            "category": "Electronics",
            "image": "https://example.com/image.jpg"
        }

    @pytest.fixture
    def sample_user_context(self):
        """Sample user context for testing."""
        return {
            "user_id": 12345,
            "session_id": "test_session_123",
            "segment": "regular_user",
            "source": "search"
        }

    @pytest.mark.asyncio
    async def test_optimize_affiliate_links_basic(
        self, 
        revenue_optimizer, 
        sample_product_data, 
        sample_user_context
    ):
        """Test basic affiliate link optimization."""
        result = await revenue_optimizer.optimize_affiliate_links(
            sample_product_data, sample_user_context
        )
        
        assert "url" in result
        assert "button_text" in result
        assert "urgency_message" in result
        assert "variant" in result
        assert "tracking_params" in result
        assert "optimization_score" in result
        
        # URL should contain the ASIN
        assert sample_product_data["asin"] in result["url"]
        
        # Should have a valid variant
        assert result["variant"] in [v.value for v in ABTestVariant]
        
        # Optimization score should be between 0 and 1
        assert 0.0 <= result["optimization_score"] <= 1.0

    @pytest.mark.asyncio
    async def test_optimize_affiliate_links_high_value_user(
        self, 
        revenue_optimizer, 
        sample_product_data
    ):
        """Test optimization for high-value user segment."""
        user_context = {
            "user_id": 12345,
            "segment": "high_value",
            "source": "deals"
        }
        
        result = await revenue_optimizer.optimize_affiliate_links(
            sample_product_data, user_context
        )
        
        # High-value users should get higher optimization scores
        assert result["optimization_score"] > 0.5

    @pytest.mark.asyncio
    async def test_optimize_affiliate_links_error_handling(
        self, 
        revenue_optimizer
    ):
        """Test error handling in affiliate link optimization."""
        # Test with invalid product data
        invalid_product = {"invalid": "data"}
        user_context = {"user_id": 123}
        
        result = await revenue_optimizer.optimize_affiliate_links(
            invalid_product, user_context
        )
        
        # Should fallback gracefully
        assert "url" in result
        assert "button_text" in result
        assert result["variant"] == ABTestVariant.CONTROL.value

    @pytest.mark.asyncio
    @patch('bot.revenue_optimization.engine')
    async def test_track_conversion_funnel(
        self, 
        mock_engine, 
        revenue_optimizer
    ):
        """Test conversion funnel tracking."""
        # Mock database session
        mock_session = MagicMock()
        mock_engine.return_value.__enter__.return_value = mock_session
        
        # Mock query results - need to match the actual order in track_conversion_funnel
        # Order: recent_searches, recent_clicks, recent_watches
        mock_session.exec.return_value.one_or_none.side_effect = [5, 3, 2]  # searches, clicks, watches
        
        # Mock the helper methods
        with patch.object(revenue_optimizer, '_calculate_revenue_potential') as mock_revenue_potential:
            with patch.object(revenue_optimizer, '_determine_user_segment') as mock_user_segment:
                with patch.object(revenue_optimizer, '_identify_optimization_opportunities') as mock_opportunities:
                    
                    mock_revenue_potential.return_value = {"estimated_daily_revenue": 1.5}
                    mock_user_segment.return_value = "regular_user"
                    mock_opportunities.return_value = ["test opportunity"]
                    
                    result = await revenue_optimizer.track_conversion_funnel(
                        user_id=123, 
                        event=ConversionEvent.LINK_CLICKED
                    )
        
        assert "user_id" in result
        assert "events" in result
        assert "conversion_rates" in result
        assert "revenue_potential" in result
        assert "user_segment" in result
        
        # Check conversion rates calculation
        assert "search_to_click" in result["conversion_rates"]
        assert "watch_to_click" in result["conversion_rates"]

    @pytest.mark.asyncio
    @patch('bot.revenue_optimization.engine')
    async def test_analyze_revenue_performance(
        self, 
        mock_engine, 
        revenue_optimizer
    ):
        """Test revenue performance analysis."""
        # Mock database session
        mock_session = MagicMock()
        mock_engine.return_value.__enter__.return_value = mock_session
        
        # Mock query results for metrics
        mock_session.exec.return_value.one_or_none.side_effect = [100, 50, 200]  # clicks, users, searches
        
        result = await revenue_optimizer.analyze_revenue_performance("30d")
        
        assert "period" in result
        assert "overall_metrics" in result
        assert "ab_test_performance" in result
        assert "optimization_recommendations" in result
        
        # Check overall metrics
        metrics = result["overall_metrics"]
        assert "total_clicks" in metrics
        assert "total_users" in metrics
        assert "estimated_revenue" in metrics

    def test_get_user_variant_consistency(self, revenue_optimizer):
        """Test that user variant assignment is consistent."""
        user_id = 12345
        
        # Should return the same variant for the same user
        variant1 = revenue_optimizer._get_user_variant(user_id)
        variant2 = revenue_optimizer._get_user_variant(user_id)
        
        assert variant1 == variant2
        
        # Different users should potentially get different variants
        variant3 = revenue_optimizer._get_user_variant(54321)
        # Note: We can't guarantee different variants due to hash distribution

    def test_get_user_variant_none_user(self, revenue_optimizer):
        """Test variant assignment for None user."""
        variant = revenue_optimizer._get_user_variant(None)
        assert variant == ABTestVariant.CONTROL

    @pytest.mark.asyncio
    async def test_build_tracking_params(self, revenue_optimizer, sample_product_data, sample_user_context):
        """Test tracking parameters building."""
        variant = ABTestVariant.VARIANT_A
        
        result = await revenue_optimizer._build_tracking_params(
            sample_product_data, sample_user_context, variant
        )
        
        assert "asin" in result
        assert "user_id" in result
        assert "variant" in result
        assert "timestamp" in result
        assert result["asin"] == sample_product_data["asin"]
        assert result["user_id"] == sample_user_context["user_id"]
        assert result["variant"] == variant.value

    @pytest.mark.asyncio
    async def test_calculate_optimization_score_factors(
        self, 
        revenue_optimizer, 
        sample_user_context
    ):
        """Test optimization score calculation with different factors."""
        # High discount product
        high_discount_product = {
            "asin": "B0TEST123",
            "discount_percent": 30,
            "rating": 4.5
        }
        
        score = await revenue_optimizer._calculate_optimization_score(
            high_discount_product, sample_user_context, ABTestVariant.CONTROL
        )
        
        # Should be higher than base score due to high discount and rating
        assert score > 0.5

    @pytest.mark.asyncio
    @patch('bot.revenue_optimization.engine')
    async def test_determine_user_segment(
        self, 
        mock_engine, 
        revenue_optimizer
    ):
        """Test user segment determination."""
        # Mock database session
        mock_session = MagicMock()
        mock_engine.return_value.__enter__.return_value = mock_session
        
        # Mock high-activity user - reset the side_effect for each test
        mock_session.exec.return_value.one_or_none.side_effect = [12, 8]  # clicks, watches
        
        segment = await revenue_optimizer._determine_user_segment(123)
        assert segment == "high_value"
        
        # Reset mock for second test
        mock_session.reset_mock()
        mock_session.exec.return_value.one_or_none.side_effect = [6, 3]  # clicks, watches
        
        segment = await revenue_optimizer._determine_user_segment(456)  # Different user ID
        assert segment == "frequent_buyer"

    @pytest.mark.asyncio
    async def test_identify_optimization_opportunities(self, revenue_optimizer):
        """Test optimization opportunity identification."""
        # High searches, no watches
        opportunities = await revenue_optimizer._identify_optimization_opportunities(
            user_id=123, searches=10, watches=0, clicks=0
        )
        
        assert len(opportunities) > 0
        assert any("watch creation" in opp.lower() for opp in opportunities)
        
        # High watches, no clicks
        opportunities = await revenue_optimizer._identify_optimization_opportunities(
            user_id=123, searches=5, watches=5, clicks=0
        )
        
        assert any("deal presentation" in opp.lower() for opp in opportunities)

    @pytest.mark.asyncio
    async def test_calculate_revenue_potential(self, revenue_optimizer):
        """Test revenue potential calculation."""
        result = await revenue_optimizer._calculate_revenue_potential(
            recent_clicks=10, recent_searches=50
        )
        
        assert "estimated_daily_revenue" in result
        assert "conversion_rate" in result
        assert "revenue_category" in result
        
        # Check conversion rate calculation
        assert result["conversion_rate"] == 0.2  # 10/50
        
        # Check revenue category
        assert result["revenue_category"] in ["high", "medium", "low"]

    @pytest.mark.asyncio
    async def test_record_conversion_event(self, revenue_optimizer):
        """Test conversion event recording."""
        user_id = 123
        event = ConversionEvent.SEARCH
        event_data = {"query": "test product"}
        
        # Should not raise any exceptions
        await revenue_optimizer._record_conversion_event(user_id, event, event_data)
        
        # Check that event was recorded in funnel
        assert revenue_optimizer.conversion_funnel[user_id][event.value] > 0

    @pytest.mark.asyncio
    async def test_add_optimization_params(self, revenue_optimizer, sample_user_context):
        """Test optimization parameter addition to URLs."""
        base_url = "https://www.amazon.in/dp/B0TEST123?tag=test-21"
        variant = ABTestVariant.VARIANT_B
        
        result = await revenue_optimizer._add_optimization_params(
            base_url, sample_user_context, variant
        )
        
        assert variant.value in result
        assert "ts=" in result  # timestamp
        
        # Test URL without existing query params
        base_url_no_params = "https://www.amazon.in/dp/B0TEST123"
        result = await revenue_optimizer._add_optimization_params(
            base_url_no_params, sample_user_context, variant
        )
        
        assert "?" in result
        assert variant.value in result


class TestIntegrationRevenueOptimization:
    """Integration tests for revenue optimization."""

    @pytest.mark.asyncio
    @patch('bot.revenue_optimization.build_affiliate_url')
    async def test_full_optimization_flow(self, mock_build_affiliate):
        """Test complete optimization flow from product to optimized result."""
        mock_build_affiliate.return_value = "https://www.amazon.in/dp/B0TEST123?tag=test-21"
        
        optimizer = RevenueOptimizer()
        
        product_data = {
            "asin": "B0TEST123",
            "title": "Test Product",
            "price": 12345,
            "discount_percent": 20,
            "rating": 4.0
        }
        
        user_context = {
            "user_id": 12345,
            "session_id": "test_session",
            "source": "search"
        }
        
        # Optimize affiliate links
        result = await optimizer.optimize_affiliate_links(product_data, user_context)
        
        # Track conversion event
        await optimizer.track_conversion_funnel(
            user_context["user_id"], 
            ConversionEvent.LINK_CLICKED,
            {"asin": product_data["asin"]}
        )
        
        # Verify optimization result
        assert result["url"] != mock_build_affiliate.return_value  # Should be enhanced
        assert "variant=" in result["url"]
        assert result["tracking_params"]["asin"] == product_data["asin"]

    @pytest.mark.asyncio
    async def test_performance_under_load(self):
        """Test revenue optimizer performance under load."""
        optimizer = RevenueOptimizer()
        
        product_data = {
            "asin": "B0TEST123",
            "title": "Test Product",
            "price": 12345
        }
        
        # Simulate multiple concurrent optimization requests
        tasks = []
        for i in range(10):
            user_context = {"user_id": i, "source": "test"}
            task = optimizer.optimize_affiliate_links(product_data, user_context)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # All requests should complete successfully
        assert len(results) == 10
        for result in results:
            assert "url" in result
            assert "variant" in result

    @pytest.mark.asyncio
    async def test_ab_test_variant_distribution(self):
        """Test that A/B test variants are reasonably distributed."""
        optimizer = RevenueOptimizer()
        
        # Get variants for many users
        variants = []
        for user_id in range(1000):
            variant = optimizer._get_user_variant(user_id)
            variants.append(variant)
        
        # Count variant distribution
        from collections import Counter
        variant_counts = Counter(variants)
        
        # Each variant should have some representation (within reason)
        for variant in ABTestVariant:
            assert variant_counts[variant] > 100  # At least 10% of users
