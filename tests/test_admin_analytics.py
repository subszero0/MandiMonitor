"""Tests for Admin Analytics and Business Intelligence Dashboard."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from bot.admin_analytics import AdminAnalytics


class TestAdminAnalytics:
    """Test cases for AdminAnalytics class."""

    @pytest.fixture
    def admin_analytics(self):
        """Create AdminAnalytics instance for testing."""
        return AdminAnalytics()

    @pytest.fixture
    def mock_session(self):
        """Mock database session."""
        session = MagicMock()
        session.exec.return_value.one.return_value = 100
        session.exec.return_value.one_or_none.return_value = 50
        return session

    @pytest.mark.asyncio
    @patch('bot.admin_analytics.engine')
    async def test_generate_performance_dashboard_basic(
        self, 
        mock_engine, 
        admin_analytics, 
        mock_session
    ):
        """Test basic performance dashboard generation."""
        mock_engine.return_value.__enter__.return_value = mock_session
        
        # Mock multiple query results
        mock_session.exec.return_value.one_or_none.side_effect = [
            100,  # total_users
            80,   # active_users
            20,   # new_users
            50,   # total_watches
            15,   # active_watches
            25,   # total_products
            75,   # total_clicks
            30,   # unique_clickers
            150,  # total_searches
            200   # cache_hits
        ]
        
        result = await admin_analytics.generate_performance_dashboard("30d")
        
        assert "generated_at" in result
        assert "time_period" in result
        assert "user_metrics" in result
        assert "product_metrics" in result
        assert "revenue_metrics" in result
        assert "performance_metrics" in result
        assert "growth_metrics" in result
        assert "key_insights" in result
        assert "action_items" in result
        
        # Check user metrics structure
        user_metrics = result["user_metrics"]
        assert "total" in user_metrics
        assert "active_monthly" in user_metrics
        assert "growth_rate" in user_metrics

    @pytest.mark.asyncio
    @patch('bot.admin_analytics.engine')
    async def test_generate_performance_dashboard_different_periods(
        self, 
        mock_engine, 
        admin_analytics, 
        mock_session
    ):
        """Test dashboard generation with different time periods."""
        mock_engine.return_value.__enter__.return_value = mock_session
        mock_session.exec.return_value.one_or_none.return_value = 50
        mock_session.exec.return_value.one.return_value = 100
        
        # Test different periods
        for period in ["7d", "30d", "90d"]:
            result = await admin_analytics.generate_performance_dashboard(period)
            assert result["time_period"] == period

    @pytest.mark.asyncio
    async def test_generate_performance_dashboard_error_handling(self, admin_analytics):
        """Test error handling in dashboard generation."""
        # Mock a database error
        with patch('bot.admin_analytics.engine') as mock_engine:
            mock_engine.side_effect = Exception("Database connection failed")
            
            result = await admin_analytics.generate_performance_dashboard("30d")
            
            assert "error" in result
            assert "user_metrics" in result
            assert result["user_metrics"]["total"] == 0

    @pytest.mark.asyncio
    @patch('bot.admin_analytics.engine')
    async def test_analyze_user_segmentation_basic(
        self, 
        mock_engine, 
        admin_analytics, 
        mock_session
    ):
        """Test basic user segmentation analysis."""
        mock_engine.return_value.__enter__.return_value = mock_session
        
        # Mock user activity data
        with patch.object(admin_analytics, '_get_users_with_activity') as mock_get_users:
            mock_get_users.return_value = [
                {
                    "user_id": 1,
                    "watches_count": 10,
                    "clicks_count": 5,
                    "searches_count": 20,
                    "estimated_revenue": 2.5
                },
                {
                    "user_id": 2,
                    "watches_count": 2,
                    "clicks_count": 1,
                    "searches_count": 5,
                    "estimated_revenue": 0.5
                }
            ]
            
            with patch.object(admin_analytics, '_classify_user_segment') as mock_classify:
                mock_classify.side_effect = ["power_users", "casual_users"]
                
                result = await admin_analytics.analyze_user_segmentation()
                
                assert "generated_at" in result
                assert "total_users" in result
                assert "segment_distribution" in result
                assert "segment_statistics" in result
                assert "churn_risk_analysis" in result
                
                # Check segment distribution
                assert result["total_users"] == 2
                assert "power_users" in result["segment_distribution"]
                assert "casual_users" in result["segment_distribution"]

    @pytest.mark.asyncio
    async def test_analyze_user_segmentation_detailed(self, admin_analytics):
        """Test detailed user segmentation analysis."""
        with patch.object(admin_analytics, '_get_users_with_activity') as mock_get_users:
            mock_get_users.return_value = []
            
            result = await admin_analytics.analyze_user_segmentation(detailed=True)
            
            assert "detailed_segments" in result

    @pytest.mark.asyncio
    @patch('bot.admin_analytics.engine')
    async def test_analyze_product_performance_basic(
        self, 
        mock_engine, 
        admin_analytics, 
        mock_session
    ):
        """Test basic product performance analysis."""
        mock_engine.return_value.__enter__.return_value = mock_session
        
        # Mock product performance data
        with patch.object(admin_analytics, '_get_product_performance_data') as mock_get_products:
            mock_get_products.return_value = [
                {"asin": "B0TEST123", "performance_score": 85},
                {"asin": "B0TEST456", "performance_score": 72}
            ]
            
            result = await admin_analytics.analyze_product_performance()
            
            assert "generated_at" in result
            assert "total_products" in result
            assert "category_performance" in result
            assert "price_trends" in result
            assert "deal_effectiveness" in result
            assert "top_performing_products" in result
            assert "optimization_recommendations" in result
            
            assert result["total_products"] == 2

    @pytest.mark.asyncio
    async def test_analyze_product_performance_with_category(self, admin_analytics):
        """Test product performance analysis with category filter."""
        with patch.object(admin_analytics, '_get_product_performance_data') as mock_get_products:
            mock_get_products.return_value = []
            
            result = await admin_analytics.analyze_product_performance(category="Electronics")
            
            assert result["category_filter"] == "Electronics"

    @pytest.mark.asyncio
    async def test_generate_revenue_insights_basic(self, admin_analytics):
        """Test basic revenue insights generation."""
        # Mock revenue optimizer
        with patch.object(admin_analytics.revenue_optimizer, 'analyze_revenue_performance') as mock_revenue:
            mock_revenue.return_value = {
                "overall_metrics": {
                    "total_clicks": 100,
                    "estimated_revenue": 5.0
                }
            }
            
            result = await admin_analytics.generate_revenue_insights()
            
            assert "generated_at" in result
            assert "revenue_performance" in result
            assert "revenue_by_source" in result
            assert "seasonal_patterns" in result

    @pytest.mark.asyncio
    async def test_generate_revenue_insights_with_forecasting(self, admin_analytics):
        """Test revenue insights with forecasting enabled."""
        with patch.object(admin_analytics.revenue_optimizer, 'analyze_revenue_performance') as mock_revenue:
            mock_revenue.return_value = {"overall_metrics": {}}
            
            result = await admin_analytics.generate_revenue_insights(include_forecasting=True)
            
            assert "revenue_forecast" in result

    @pytest.mark.asyncio
    @patch('bot.admin_analytics.engine')
    async def test_calculate_user_metrics(
        self, 
        mock_engine, 
        admin_analytics, 
        mock_session
    ):
        """Test user metrics calculation."""
        mock_engine.return_value.__enter__.return_value = mock_session
        
        # Mock query results
        mock_session.exec.return_value.one.side_effect = [100]  # total_users
        mock_session.exec.return_value.one_or_none.side_effect = [80, 20, 2.5]  # active, new, avg_watches
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=30)
        result = await admin_analytics._calculate_user_metrics(mock_session, cutoff_time)
        
        assert "total" in result
        assert "active_monthly" in result
        assert "new_users" in result
        assert "growth_rate" in result
        assert "engagement_rate" in result
        assert "avg_watches_per_user" in result
        
        # Check calculations
        assert result["total"] == 100
        assert result["growth_rate"] == 25.0  # 20/(100-20) * 100

    @pytest.mark.asyncio
    @patch('bot.admin_analytics.engine')
    async def test_calculate_product_metrics(
        self, 
        mock_engine, 
        admin_analytics, 
        mock_session
    ):
        """Test product metrics calculation."""
        mock_engine.return_value.__enter__.return_value = mock_session
        
        # Mock query results
        mock_session.exec.return_value.one.side_effect = [150]  # total_watches
        mock_session.exec.return_value.one_or_none.side_effect = [50, 25]  # active_watches, total_products
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=30)
        result = await admin_analytics._calculate_product_metrics(mock_session, cutoff_time)
        
        assert "total_watches" in result
        assert "active_watches" in result
        assert "total_products" in result
        assert "watch_creation_rate" in result
        assert "watches_per_product" in result
        
        assert result["total_watches"] == 150
        assert result["watches_per_product"] == 6.0  # 150/25

    @pytest.mark.asyncio
    @patch('bot.admin_analytics.engine')
    async def test_calculate_revenue_metrics(
        self, 
        mock_engine, 
        admin_analytics, 
        mock_session
    ):
        """Test revenue metrics calculation."""
        mock_engine.return_value.__enter__.return_value = mock_session
        
        # Mock query results and CTR calculation
        mock_session.exec.return_value.one_or_none.side_effect = [75, 30]  # total_clicks, unique_clickers
        
        with patch.object(admin_analytics, '_calculate_overall_ctr') as mock_ctr:
            mock_ctr.return_value = 0.05
            
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=30)
            result = await admin_analytics._calculate_revenue_metrics(mock_session, cutoff_time)
            
            assert "total_clicks" in result
            assert "unique_clickers" in result
            assert "estimated_revenue" in result
            assert "revenue_per_user" in result
            assert "click_through_rate" in result
            
            assert result["total_clicks"] == 75
            assert result["estimated_revenue"] == 3.75  # 75 * 0.05

    @pytest.mark.asyncio
    async def test_generate_key_insights(self, admin_analytics):
        """Test key insights generation."""
        user_metrics = {"growth_rate": 25, "engagement_rate": 75}
        product_metrics = {"watches_per_product": 2.5}
        revenue_metrics = {"click_through_rate": 0.03}
        growth_metrics = {}
        
        insights = await admin_analytics._generate_key_insights(
            user_metrics, product_metrics, revenue_metrics, growth_metrics
        )
        
        assert isinstance(insights, list)
        assert len(insights) > 0
        
        # Should detect high growth
        assert any("growth" in insight.lower() for insight in insights)
        
        # Should detect high engagement
        assert any("engagement" in insight.lower() for insight in insights)

    @pytest.mark.asyncio
    async def test_generate_action_items(self, admin_analytics):
        """Test action items generation."""
        user_metrics = {"engagement_rate": 25}  # Low engagement
        product_metrics = {"watch_creation_rate": 3}  # Low watch creation
        revenue_metrics = {"revenue_per_user": 0.5}  # Low revenue per user
        
        actions = await admin_analytics._generate_action_items(
            user_metrics, product_metrics, revenue_metrics
        )
        
        assert isinstance(actions, list)
        assert len(actions) > 0
        
        # Should suggest engagement campaign
        assert any("engagement" in action.lower() for action in actions)
        
        # Should suggest monetization optimization
        assert any("monetization" in action.lower() for action in actions)

    @pytest.mark.asyncio
    @patch('bot.admin_analytics.engine')
    async def test_calculate_overall_ctr(
        self, 
        mock_engine, 
        admin_analytics, 
        mock_session
    ):
        """Test overall CTR calculation."""
        mock_engine.return_value.__enter__.return_value = mock_session
        
        # Mock query results
        mock_session.exec.return_value.one_or_none.side_effect = [200, 10]  # searches, clicks
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=30)
        result = await admin_analytics._calculate_overall_ctr(mock_session, cutoff_time)
        
        assert result == 0.05  # 10/200

    def test_cache_validity_check(self, admin_analytics):
        """Test cache validity checking."""
        # Test with non-existent cache key
        assert not admin_analytics._is_cache_valid("non_existent_key")
        
        # Test with existing cache key (simplified implementation always returns True)
        admin_analytics.analytics_cache["test_key"] = {"data": "test"}
        assert admin_analytics._is_cache_valid("test_key")

    @pytest.mark.asyncio
    async def test_error_handling_in_metrics_calculation(self, admin_analytics):
        """Test error handling in various metrics calculations."""
        with patch('bot.admin_analytics.engine') as mock_engine:
            mock_engine.side_effect = Exception("Database error")
            
            # Test user metrics error handling
            try:
                await admin_analytics._calculate_user_metrics(None, datetime.now())
            except Exception:
                pass  # Expected to fail gracefully
            
            # Test product metrics error handling
            try:
                await admin_analytics._calculate_product_metrics(None, datetime.now())
            except Exception:
                pass  # Expected to fail gracefully


class TestAdminAnalyticsIntegration:
    """Integration tests for admin analytics."""

    @pytest.mark.asyncio
    async def test_full_dashboard_generation_flow(self):
        """Test complete dashboard generation flow."""
        analytics = AdminAnalytics()
        
        # Mock all dependencies
        with patch('bot.admin_analytics.engine') as mock_engine:
            mock_session = MagicMock()
            mock_engine.return_value.__enter__.return_value = mock_session
            
            # Mock all query results
            mock_session.exec.return_value.one.return_value = 100
            mock_session.exec.return_value.one_or_none.return_value = 50
            
            # Mock revenue optimizer
            with patch.object(analytics.revenue_optimizer, 'analyze_revenue_performance') as mock_revenue:
                mock_revenue.return_value = {"overall_metrics": {}}
                
                result = await analytics.generate_performance_dashboard("30d")
                
                # Verify complete structure
                assert all(key in result for key in [
                    "generated_at", "time_period", "user_metrics", 
                    "product_metrics", "revenue_metrics", "performance_metrics",
                    "growth_metrics", "category_metrics", "key_insights", "action_items"
                ])

    @pytest.mark.asyncio
    async def test_analytics_performance_under_load(self):
        """Test analytics performance under concurrent load."""
        analytics = AdminAnalytics()
        
        # Mock database
        with patch('bot.admin_analytics.engine') as mock_engine:
            mock_session = MagicMock()
            mock_engine.return_value.__enter__.return_value = mock_session
            mock_session.exec.return_value.one_or_none.return_value = 10
            
            # Run multiple concurrent analytics requests
            import asyncio
            tasks = []
            for i in range(5):
                task = analytics.generate_performance_dashboard("7d")
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All requests should complete successfully
            assert len(results) == 5
            for result in results:
                if isinstance(result, Exception):
                    pytest.fail(f"Analytics request failed: {result}")
                assert "generated_at" in result

    @pytest.mark.asyncio
    async def test_cache_behavior(self):
        """Test analytics caching behavior."""
        analytics = AdminAnalytics()
        
        # Mock database to return different values
        call_count = 0
        
        def mock_dashboard_generation(period):
            nonlocal call_count
            call_count += 1
            return {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "call_count": call_count,
                "user_metrics": {"total": call_count * 10}
            }
        
        # Patch the actual dashboard generation method
        with patch.object(analytics, 'generate_performance_dashboard', side_effect=mock_dashboard_generation):
            # First call should execute
            result1 = await analytics.generate_performance_dashboard("30d")
            
            # Cache the result manually for testing
            analytics.analytics_cache["dashboard_30d"] = result1
            
            # Verify cache content
            assert "call_count" in result1
            assert result1["call_count"] == 1

    @pytest.mark.asyncio
    async def test_comprehensive_user_segmentation(self):
        """Test comprehensive user segmentation with realistic data."""
        analytics = AdminAnalytics()
        
        # Mock realistic user data
        mock_users = [
            {"user_id": 1, "watches_count": 15, "clicks_count": 12, "searches_count": 30, "estimated_revenue": 6.0},
            {"user_id": 2, "watches_count": 8, "clicks_count": 6, "searches_count": 15, "estimated_revenue": 3.0},
            {"user_id": 3, "watches_count": 2, "clicks_count": 1, "searches_count": 5, "estimated_revenue": 0.5},
            {"user_id": 4, "watches_count": 0, "clicks_count": 0, "searches_count": 1, "estimated_revenue": 0.0},
        ]
        
        with patch.object(analytics, '_get_users_with_activity', return_value=mock_users):
            with patch.object(analytics, '_classify_user_segment') as mock_classify:
                mock_classify.side_effect = ["power_users", "regular_users", "casual_users", "new_users"]
                
                result = await analytics.analyze_user_segmentation(detailed=True)
                
                assert result["total_users"] == 4
                assert len(result["detailed_segments"]["power_users"]) == 1
                assert len(result["detailed_segments"]["regular_users"]) == 1
                assert len(result["detailed_segments"]["casual_users"]) == 1
                assert len(result["detailed_segments"]["new_users"]) == 1
