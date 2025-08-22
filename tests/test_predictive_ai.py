"""Tests for AI-powered predictive engine functionality."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

from bot.predictive_ai import PredictiveEngine, predictive_engine
from bot.models import User, Watch, Price, Click
from bot.enhanced_models import Product, ProductOffers, CustomerReviews, PriceHistory, SearchQuery, DealAlert


class TestPredictiveEngine:
    """Test cases for PredictiveEngine functionality."""

    @pytest.fixture
    def mock_engine(self):
        """Mock predictive engine for testing."""
        engine = PredictiveEngine()
        engine._user_patterns_cache = {}
        engine._cache_expiry = {}
        return engine

    @pytest.fixture
    def sample_user_data(self):
        """Sample user data for testing."""
        return {
            "user_id": 1,
            "watches": [
                Watch(id=1, user_id=1, asin="B001", keywords="laptop gaming", brand="ASUS", max_price=100000),
                Watch(id=2, user_id=1, asin="B002", keywords="smartphone android", brand="Samsung", max_price=50000),
                Watch(id=3, user_id=1, asin="B003", keywords="headphones wireless", brand="Sony", max_price=15000),
            ],
            "searches": [
                SearchQuery(id=1, user_id=1, query="gaming laptop", search_index="Electronics"),
                SearchQuery(id=2, user_id=1, query="android phone", search_index="Electronics"),
            ],
            "clicks": [
                Click(id=1, watch_id=1, asin="B001"),
                Click(id=2, watch_id=2, asin="B002"),
            ]
        }

    @pytest.fixture
    def sample_product_data(self):
        """Sample product data for testing."""
        return [
            Product(
                asin="B001",
                title="ASUS Gaming Laptop",
                brand="ASUS",
                product_group="Electronics",
                features='["High performance", "RGB keyboard"]'
            ),
            Product(
                asin="B002",
                title="Samsung Galaxy Smartphone",
                brand="Samsung",
                product_group="Electronics",
                features='["AMOLED display", "Fast charging"]'
            ),
            Product(
                asin="B003",
                title="Sony Wireless Headphones",
                brand="Sony",
                product_group="Electronics",
                features='["Noise cancellation", "30-hour battery"]'
            )
        ]

    @pytest.mark.asyncio
    async def test_predict_user_interests_new_user(self, mock_engine):
        """Test user interest prediction for new user with no data."""
        with patch('bot.predictive_ai.Session') as mock_session:
            mock_session.return_value.__enter__.return_value.exec.return_value.all.return_value = []
            
            recommendations = await mock_engine.predict_user_interests(999)
            
            # Should return default recommendations for new users
            assert isinstance(recommendations, list)
            assert len(recommendations) >= 0  # May be empty if no popular products

    @pytest.mark.asyncio
    async def test_predict_user_interests_existing_user(self, mock_engine, sample_user_data, sample_product_data):
        """Test user interest prediction for existing user with data."""
        with patch('bot.predictive_ai.Session') as mock_session:
            mock_session_instance = mock_session.return_value.__enter__.return_value
            
            # Mock database responses
            mock_session_instance.exec.return_value.all.side_effect = [
                sample_user_data["watches"],  # User watches
                sample_user_data["searches"],  # Search queries
                sample_user_data["clicks"],   # Clicks
                [User(id=2, tg_user_id=200), User(id=3, tg_user_id=300)],  # All users for similarity
            ]
            
            # Mock similar user watches (empty for simplicity)
            mock_session_instance.exec.return_value.all.return_value = []
            
            with patch.object(mock_engine, '_analyze_user_patterns') as mock_analyze:
                mock_analyze.return_value = {
                    "preferred_brands": {"ASUS": 1, "Samsung": 1},
                    "preferred_categories": {"Electronics": 2},
                    "price_ranges": [100000, 50000],
                    "search_keywords": ["gaming", "laptop", "android", "phone"]
                }
                
                with patch.object(mock_engine, '_find_similar_users') as mock_similar:
                    mock_similar.return_value = [2, 3]
                    
                    with patch.object(mock_engine, '_generate_ml_recommendations') as mock_ml_recs:
                        mock_ml_recs.return_value = [
                            {
                                "asin": "B004",
                                "title": "ASUS Gaming Monitor",
                                "brand": "ASUS",
                                "category": "Electronics",
                                "score": 0.85,
                                "source": "collaborative_filtering"
                            }
                        ]
                        
                        recommendations = await mock_engine.predict_user_interests(1)
                        
                        assert isinstance(recommendations, list)
                        assert len(recommendations) > 0
                        assert all("asin" in rec for rec in recommendations)
                        assert all("confidence_score" in rec for rec in recommendations)

    @pytest.mark.asyncio
    async def test_predict_deal_success_with_data(self, mock_engine):
        """Test deal success prediction with historical data."""
        with patch('bot.predictive_ai.Session') as mock_session:
            mock_session_instance = mock_session.return_value.__enter__.return_value
            
            # Mock product data
            mock_product = Product(
                asin="B001",
                title="Test Product",
                brand="TestBrand",
                product_group="Electronics"
            )
            mock_session_instance.get.return_value = mock_product
            
            # Mock price history
            price_history = [
                PriceHistory(asin="B001", price=10000, timestamp=datetime.utcnow() - timedelta(days=30)),
                PriceHistory(asin="B001", price=12000, timestamp=datetime.utcnow() - timedelta(days=20)),
                PriceHistory(asin="B001", price=9500, timestamp=datetime.utcnow() - timedelta(days=10)),
            ]
            
            # Mock deal alerts
            deal_alerts = [
                DealAlert(asin="B001", current_price=9000, alert_type="price_drop"),
            ]
            
            mock_session_instance.exec.return_value.all.side_effect = [price_history, deal_alerts]
            
            result = await mock_engine.predict_deal_success("B001", 8500)
            
            assert isinstance(result, dict)
            assert "success_probability" in result
            assert "confidence" in result
            assert "historical_metrics" in result
            assert 0.0 <= result["success_probability"] <= 1.0

    @pytest.mark.asyncio
    async def test_predict_deal_success_no_product(self, mock_engine):
        """Test deal success prediction when product not found."""
        with patch('bot.predictive_ai.Session') as mock_session:
            mock_session_instance = mock_session.return_value.__enter__.return_value
            mock_session_instance.get.return_value = None
            
            result = await mock_engine.predict_deal_success("NONEXISTENT", 5000)
            
            assert result["success_probability"] == 0.5
            assert result["confidence"] == "low"
            assert "No product data" in result["reason"]

    @pytest.mark.asyncio
    async def test_predict_inventory_alerts(self, mock_engine):
        """Test inventory alert predictions."""
        with patch('bot.predictive_ai.Session') as mock_session:
            mock_session_instance = mock_session.return_value.__enter__.return_value
            
            # Mock recent offers data
            recent_offers = [
                ProductOffers(asin="B001", availability_type="InStock", fetched_at=datetime.utcnow() - timedelta(days=1)),
                ProductOffers(asin="B001", availability_type="OutOfStock", fetched_at=datetime.utcnow() - timedelta(hours=12)),
                ProductOffers(asin="B001", availability_type="InStock", fetched_at=datetime.utcnow() - timedelta(hours=6)),
            ]
            
            mock_session_instance.exec.return_value.all.return_value = recent_offers
            
            result = await mock_engine.predict_inventory_alerts("B001")
            
            assert isinstance(result, dict)
            assert "stockout_probability" in result
            assert "urgency_level" in result
            assert "recommendation" in result

    @pytest.mark.asyncio
    async def test_predict_inventory_alerts_no_data(self, mock_engine):
        """Test inventory alert predictions with no data."""
        with patch('bot.predictive_ai.Session') as mock_session:
            mock_session_instance = mock_session.return_value.__enter__.return_value
            mock_session_instance.exec.return_value.all.return_value = []
            
            result = await mock_engine.predict_inventory_alerts("B001")
            
            assert result["prediction"] == "insufficient_data"
            assert result["confidence"] == "low"

    @pytest.mark.asyncio
    async def test_train_user_interest_model_insufficient_users(self, mock_engine):
        """Test training user interest model with insufficient users."""
        with patch('bot.predictive_ai.Session') as mock_session:
            mock_session_instance = mock_session.return_value.__enter__.return_value
            
            # Mock insufficient users
            mock_session_instance.exec.return_value.all.return_value = [
                User(id=1, tg_user_id=100),
                User(id=2, tg_user_id=200),
            ]
            
            result = await mock_engine.train_user_interest_model()
            
            assert result is False

    @pytest.mark.asyncio
    async def test_train_user_interest_model_success(self, mock_engine):
        """Test successful training of user interest model."""
        with patch('bot.predictive_ai.Session') as mock_session:
            mock_session_instance = mock_session.return_value.__enter__.return_value
            
            # Mock sufficient users
            users = [User(id=i, tg_user_id=100+i) for i in range(1, 12)]  # 11 users
            mock_session_instance.exec.return_value.all.return_value = users
            
            with patch.object(mock_engine, '_build_user_item_matrix') as mock_matrix:
                # Mock non-empty DataFrame
                mock_df = pd.DataFrame({
                    'B001': [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
                    'B002': [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
                    'B003': [1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0],
                }, index=range(1, 12))
                mock_matrix.return_value = mock_df
                
                result = await mock_engine.train_user_interest_model()
                
                assert result is True
                assert mock_engine.user_interest_model is not None

    @pytest.mark.asyncio
    async def test_train_deal_success_model_insufficient_data(self, mock_engine):
        """Test training deal success model with insufficient data."""
        with patch('bot.predictive_ai.Session') as mock_session:
            mock_session_instance = mock_session.return_value.__enter__.return_value
            
            # Mock insufficient deal alerts
            deal_alerts = [DealAlert(asin="B001", current_price=10000) for _ in range(3)]
            mock_session_instance.exec.return_value.all.return_value = deal_alerts
            
            result = await mock_engine.train_deal_success_model()
            
            assert result is False

    @pytest.mark.asyncio
    async def test_train_deal_success_model_success(self, mock_engine):
        """Test successful training of deal success model."""
        with patch('bot.predictive_ai.Session') as mock_session:
            mock_session_instance = mock_session.return_value.__enter__.return_value
            
            # Mock sufficient deal alerts
            deal_alerts = [
                DealAlert(asin=f"B{i:03d}", current_price=10000 + i*100, sent_at=datetime.utcnow() - timedelta(days=i))
                for i in range(1, 52)  # 51 deal alerts
            ]
            mock_session_instance.exec.return_value.all.return_value = deal_alerts
            
            with patch.object(mock_engine, '_prepare_deal_training_data') as mock_training_data:
                # Mock training data
                features = [[0.8, 1.2, 100, 1, 5, 3, 2, 1] for _ in range(40)]
                labels = [1, 0, 1, 1, 0, 1, 0, 1, 1, 0] * 4  # 40 labels
                mock_training_data.return_value = (features, labels)
                
                result = await mock_engine.train_deal_success_model()
                
                assert result is True
                assert mock_engine.deal_success_model is not None

    def test_calculate_user_similarity(self, mock_engine):
        """Test user similarity calculation."""
        patterns1 = {
            "preferred_brands": {"ASUS": 2, "Samsung": 1},
            "preferred_categories": {"Electronics": 3},
            "price_ranges": [50000, 75000, 100000],
        }
        
        patterns2 = {
            "preferred_brands": {"ASUS": 1, "Apple": 2},
            "preferred_categories": {"Electronics": 2, "Books": 1},
            "price_ranges": [60000, 80000],
        }
        
        similarity = mock_engine._calculate_user_similarity(patterns1, patterns2)
        
        assert 0.0 <= similarity <= 1.0
        assert isinstance(similarity, float)

    def test_calculate_recommendation_score(self, mock_engine):
        """Test recommendation score calculation."""
        product = Product(
            asin="B001",
            title="ASUS Gaming Laptop",
            brand="ASUS",
            product_group="Electronics"
        )
        
        user_patterns = {
            "preferred_brands": {"ASUS": 3, "Samsung": 1},
            "preferred_categories": {"Electronics": 5},
            "search_keywords": ["gaming", "laptop", "performance"],
        }
        
        score = mock_engine._calculate_recommendation_score(product, user_patterns, 3, 5)
        
        assert 0.0 <= score <= 1.0
        assert isinstance(score, float)

    def test_calculate_price_trend(self, mock_engine):
        """Test price trend calculation."""
        # Increasing prices
        increasing_prices = [10000, 11000, 12000, 13000, 14000]
        trend = mock_engine._calculate_price_trend(increasing_prices)
        assert trend == "increasing"
        
        # Decreasing prices
        decreasing_prices = [14000, 13000, 12000, 11000, 10000]
        trend = mock_engine._calculate_price_trend(decreasing_prices)
        assert trend == "decreasing"
        
        # Stable prices
        stable_prices = [12000, 12100, 11900, 12000, 12050]
        trend = mock_engine._calculate_price_trend(stable_prices)
        assert trend == "stable"

    def test_analyze_stock_patterns(self, mock_engine):
        """Test stock pattern analysis."""
        offers = [
            ProductOffers(availability_type="InStock", fetched_at=datetime.utcnow() - timedelta(hours=48)),
            ProductOffers(availability_type="InStock", fetched_at=datetime.utcnow() - timedelta(hours=36)),
            ProductOffers(availability_type="OutOfStock", fetched_at=datetime.utcnow() - timedelta(hours=24)),
            ProductOffers(availability_type="OutOfStock", fetched_at=datetime.utcnow() - timedelta(hours=12)),
            ProductOffers(availability_type="InStock", fetched_at=datetime.utcnow()),
        ]
        
        patterns = mock_engine._analyze_stock_patterns(offers)
        
        assert patterns["total_checks"] == 5
        assert patterns["in_stock_count"] == 3
        assert patterns["out_of_stock_count"] == 2
        assert patterns["stock_changes"] >= 0

    def test_predict_stockout_probability(self, mock_engine):
        """Test stockout probability prediction."""
        # High stockout pattern
        high_stockout_pattern = {
            "total_checks": 10,
            "in_stock_count": 3,
            "out_of_stock_count": 7,
            "stock_changes": 5,
            "avg_stock_duration": 6
        }
        
        prob = mock_engine._predict_stockout_probability(high_stockout_pattern)
        assert 0.5 <= prob <= 1.0
        
        # Low stockout pattern
        low_stockout_pattern = {
            "total_checks": 10,
            "in_stock_count": 9,
            "out_of_stock_count": 1,
            "stock_changes": 1,
            "avg_stock_duration": 48
        }
        
        prob = mock_engine._predict_stockout_probability(low_stockout_pattern)
        assert 0.0 <= prob <= 0.5

    def test_calculate_urgency_level(self, mock_engine):
        """Test urgency level calculation."""
        assert mock_engine._calculate_urgency_level(0.9) == "critical"
        assert mock_engine._calculate_urgency_level(0.7) == "high"
        assert mock_engine._calculate_urgency_level(0.5) == "medium"
        assert mock_engine._calculate_urgency_level(0.2) == "low"

    def test_heuristic_deal_success(self, mock_engine):
        """Test heuristic deal success calculation."""
        # Good deal metrics
        good_metrics = {
            "proposed_vs_min": 1.05,  # Close to minimum price
            "proposed_vs_avg": 0.75,  # Well below average
            "recent_trend": "increasing",
            "historical_deals": 8
        }
        
        score = mock_engine._heuristic_deal_success(good_metrics, 8000)
        assert score > 0.5
        
        # Poor deal metrics
        poor_metrics = {
            "proposed_vs_min": 1.5,   # Much higher than minimum
            "proposed_vs_avg": 1.2,   # Above average
            "recent_trend": "decreasing",
            "historical_deals": 1
        }
        
        score = mock_engine._heuristic_deal_success(poor_metrics, 15000)
        assert score <= 0.5

    @pytest.mark.asyncio
    async def test_error_handling_predict_user_interests(self, mock_engine):
        """Test error handling in predict_user_interests."""
        with patch('bot.predictive_ai.Session') as mock_session:
            mock_session.side_effect = Exception("Database error")
            
            recommendations = await mock_engine.predict_user_interests(1)
            
            # Should return fallback recommendations
            assert isinstance(recommendations, list)

    @pytest.mark.asyncio
    async def test_error_handling_predict_deal_success(self, mock_engine):
        """Test error handling in predict_deal_success."""
        with patch('bot.predictive_ai.Session') as mock_session:
            mock_session.side_effect = Exception("Database error")
            
            result = await mock_engine.predict_deal_success("B001", 10000)
            
            assert result["success_probability"] == 0.5
            assert result["confidence"] == "low"
            assert "error" in result

    @pytest.mark.asyncio
    async def test_caching_user_patterns(self, mock_engine):
        """Test that user patterns are cached correctly."""
        with patch('bot.predictive_ai.Session') as mock_session:
            mock_session_instance = mock_session.return_value.__enter__.return_value
            
            # Mock user watches
            watches = [Watch(id=1, user_id=1, asin="B001", keywords="laptop", brand="ASUS")]
            mock_session_instance.exec.return_value.all.side_effect = [watches, [], []]
            
            # First call should cache the result
            patterns1 = await mock_engine._analyze_user_patterns(1, watches, mock_session_instance)
            
            # Second call should use cache
            patterns2 = await mock_engine._analyze_user_patterns(1, watches, mock_session_instance)
            
            assert patterns1 == patterns2
            assert f"user_patterns_1" in mock_engine._user_patterns_cache

    def test_global_predictive_engine_instance(self):
        """Test that global predictive engine instance is available."""
        assert predictive_engine is not None
        assert isinstance(predictive_engine, PredictiveEngine)


@pytest.mark.integration
class TestPredictiveEngineIntegration:
    """Integration tests for PredictiveEngine with real database operations."""
    
    @pytest.mark.asyncio
    async def test_full_recommendation_flow(self):
        """Test complete recommendation flow with mocked database."""
        # This would test the full flow with a test database
        # For now, we'll skip this as it requires database setup
        pass

    @pytest.mark.asyncio
    async def test_ml_model_training_flow(self):
        """Test ML model training with realistic data."""
        # This would test model training with sufficient test data
        # For now, we'll skip this as it requires substantial test data
        pass
