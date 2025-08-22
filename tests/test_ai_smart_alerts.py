"""Tests for AI-enhanced smart alerts functionality."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timedelta

from bot.smart_alerts import SmartAlertEngine
from bot.models import User, Watch, Price, Click
from bot.enhanced_models import Product, ProductOffers, CustomerReviews, PriceHistory, SearchQuery, DealAlert


class TestAISmartAlerts:
    """Test cases for AI-enhanced smart alerts functionality."""

    @pytest.fixture
    def mock_smart_alerts(self):
        """Mock smart alerts engine for testing."""
        with patch('bot.smart_alerts.Bot') as mock_bot:
            engine = SmartAlertEngine()
            engine.bot = mock_bot
            return engine

    @pytest.fixture
    def sample_watch(self):
        """Sample watch for testing."""
        return Watch(
            id=1,
            user_id=1,
            asin="B001",
            keywords="gaming laptop",
            brand="ASUS",
            max_price=100000,
            mode="daily"
        )

    @pytest.fixture
    def sample_product_data(self):
        """Sample product data for testing."""
        return {
            "asin": "B001",
            "title": "ASUS Gaming Laptop ROG Strix",
            "price": 85000,  # ₹850 in paise
            "image": "https://example.com/laptop.jpg",
            "brand": "ASUS",
            "discount": 15,
            "list_price": 100000
        }

    @pytest.fixture
    def sample_deal_quality(self):
        """Sample deal quality data for testing."""
        return {
            "score": 85,
            "quality": "excellent",
            "factors": {
                "discount": 15,
                "price_trend": "favorable",
                "availability": "in_stock"
            },
            "recommendations": ["Buy now", "Limited time offer"]
        }

    @pytest.fixture
    def sample_ai_prediction(self):
        """Sample AI prediction data for testing."""
        return {
            "success_probability": 0.85,
            "confidence": "high",
            "historical_metrics": {
                "avg_price": 95000,
                "min_price": 80000,
                "recent_trend": "stable"
            },
            "recommendation": "Excellent deal - highly recommended!",
            "optimal_price_range": {
                "excellent_deal": "₹800.00 - ₹880.00",
                "good_deal": "₹880.00 - ₹950.00"
            }
        }

    @pytest.mark.asyncio
    async def test_generate_enhanced_deal_alert(self, mock_smart_alerts, sample_watch, sample_product_data):
        """Test enhanced deal alert generation with AI predictions."""
        with patch.object(mock_smart_alerts.market_intel, 'calculate_deal_quality') as mock_deal_quality:
            mock_deal_quality.return_value = {
                "score": 85,
                "quality": "excellent",
                "factors": {"discount": 15}
            }
            
            with patch('bot.smart_alerts.predictive_engine') as mock_ai:
                mock_ai.predict_deal_success.return_value = {
                    "success_probability": 0.9,
                    "confidence": "high"
                }
                
                with patch.object(mock_smart_alerts, '_calculate_urgency_with_ai') as mock_urgency:
                    mock_urgency.return_value = "high"
                    
                    with patch.object(mock_smart_alerts, '_get_price_context') as mock_context:
                        mock_context.return_value = {"trend": "favorable"}
                        
                        with patch.object(mock_smart_alerts, '_build_premium_deal_card') as mock_card:
                            mock_card.return_value = ("Test caption", None)
                            
                            with patch.object(mock_smart_alerts, '_store_deal_alert') as mock_store:
                                mock_store.return_value = None
                                
                                result = await mock_smart_alerts.generate_enhanced_deal_alert(
                                    sample_watch, sample_product_data
                                )
                                
                                assert isinstance(result, dict)
                                assert "ai_prediction" in result
                                assert "quality_score" in result
                                assert "urgency" in result
                                assert result["quality_score"] == 85
                                assert result["urgency"] == "high"

    @pytest.mark.asyncio
    async def test_generate_smart_inventory_alert_success(self, mock_smart_alerts):
        """Test successful smart inventory alert generation."""
        with patch('bot.smart_alerts.predictive_engine') as mock_ai:
            mock_ai.predict_inventory_alerts.return_value = {
                "stockout_probability": 0.7,
                "urgency_level": "high",
                "days_until_stockout": 3,
                "recommendation": "Alert users soon"
            }
            
            with patch('bot.smart_alerts.Session') as mock_session:
                mock_product = Product(
                    asin="B001",
                    title="Test Product",
                    brand="TestBrand"
                )
                mock_session.return_value.__enter__.return_value.get.return_value = mock_product
                
                with patch.object(mock_smart_alerts, '_build_inventory_alert_message') as mock_build:
                    mock_build.return_value = {
                        "caption": "Test alert",
                        "keyboard": None,
                        "urgency": "high"
                    }
                    
                    result = await mock_smart_alerts.generate_smart_inventory_alert("B001")
                    
                    assert result["status"] == "success"
                    assert result["urgency"] == "high"
                    assert result["should_send"] is True  # High urgency should trigger send

    @pytest.mark.asyncio
    async def test_generate_smart_inventory_alert_insufficient_data(self, mock_smart_alerts):
        """Test smart inventory alert with insufficient data."""
        with patch('bot.smart_alerts.predictive_engine') as mock_ai:
            mock_ai.predict_inventory_alerts.return_value = {
                "prediction": "insufficient_data",
                "confidence": "low"
            }
            
            result = await mock_smart_alerts.generate_smart_inventory_alert("B001")
            
            assert result["status"] == "insufficient_data"
            assert "Not enough data" in result["message"]

    @pytest.mark.asyncio
    async def test_generate_smart_inventory_alert_product_not_found(self, mock_smart_alerts):
        """Test smart inventory alert when product not found."""
        with patch('bot.smart_alerts.predictive_engine') as mock_ai:
            mock_ai.predict_inventory_alerts.return_value = {
                "stockout_probability": 0.5,
                "urgency_level": "medium"
            }
            
            with patch('bot.smart_alerts.Session') as mock_session:
                mock_session.return_value.__enter__.return_value.get.return_value = None
                
                result = await mock_smart_alerts.generate_smart_inventory_alert("B001")
                
                assert result["status"] == "product_not_found"
                assert "Product not found" in result["message"]

    @pytest.mark.asyncio
    async def test_generate_personalized_recommendations_success(self, mock_smart_alerts):
        """Test successful personalized recommendations generation."""
        with patch('bot.smart_alerts.predictive_engine') as mock_ai:
            mock_ai.predict_user_interests.return_value = [
                {
                    "asin": "B001",
                    "title": "Gaming Laptop",
                    "brand": "ASUS",
                    "category": "Electronics",
                    "confidence_score": 0.85,
                    "predicted_interest_level": "high",
                    "explanation": "Based on your gaming preferences",
                    "source": "ai_prediction"
                },
                {
                    "asin": "B002",
                    "title": "Wireless Mouse",
                    "brand": "Logitech",
                    "category": "Electronics", 
                    "confidence_score": 0.7,
                    "predicted_interest_level": "medium",
                    "explanation": "Complements your setup",
                    "source": "collaborative_filtering"
                }
            ]
            
            with patch.object(mock_smart_alerts, '_format_recommendation_for_display') as mock_format:
                mock_format.side_effect = lambda x: x  # Return as-is
                
                with patch.object(mock_smart_alerts, '_build_recommendations_message') as mock_build:
                    mock_build.return_value = {
                        "caption": "AI Recommendations",
                        "keyboard": None
                    }
                    
                    result = await mock_smart_alerts.generate_personalized_recommendations(1)
                    
                    assert result["status"] == "success"
                    assert result["count"] == 2
                    assert len(result["recommendations"]) == 2

    @pytest.mark.asyncio
    async def test_generate_personalized_recommendations_no_data(self, mock_smart_alerts):
        """Test personalized recommendations with no data."""
        with patch('bot.smart_alerts.predictive_engine') as mock_ai:
            mock_ai.predict_user_interests.return_value = []
            
            result = await mock_smart_alerts.generate_personalized_recommendations(1)
            
            assert result["status"] == "no_recommendations"
            assert "No recommendations available" in result["message"]

    @pytest.mark.asyncio
    async def test_calculate_urgency_with_ai_high_success(self, mock_smart_alerts, sample_watch, sample_product_data):
        """Test urgency calculation with high AI success probability."""
        deal_quality = {"score": 70}
        deal_prediction = {"success_probability": 0.9}
        
        with patch.object(mock_smart_alerts, '_calculate_urgency') as mock_base_urgency:
            mock_base_urgency.return_value = "medium"
            
            urgency = await mock_smart_alerts._calculate_urgency_with_ai(
                deal_quality, deal_prediction, sample_product_data, sample_watch
            )
            
            assert urgency == "high"  # Should be upgraded from medium to high

    @pytest.mark.asyncio
    async def test_calculate_urgency_with_ai_low_success(self, mock_smart_alerts, sample_watch, sample_product_data):
        """Test urgency calculation with low AI success probability."""
        deal_quality = {"score": 70}
        deal_prediction = {"success_probability": 0.2}
        
        with patch.object(mock_smart_alerts, '_calculate_urgency') as mock_base_urgency:
            mock_base_urgency.return_value = "high"
            
            urgency = await mock_smart_alerts._calculate_urgency_with_ai(
                deal_quality, deal_prediction, sample_product_data, sample_watch
            )
            
            assert urgency == "medium"  # Should be downgraded from high to medium

    @pytest.mark.asyncio
    async def test_build_inventory_alert_message(self, mock_smart_alerts):
        """Test building inventory alert message."""
        mock_product = Product(
            asin="B001",
            title="Gaming Laptop",
            brand="ASUS"
        )
        
        inventory_prediction = {
            "stockout_probability": 0.8,
            "days_until_stockout": 2,
            "recommendation": "Alert users immediately"
        }
        
        result = await mock_smart_alerts._build_inventory_alert_message(
            mock_product, inventory_prediction, "critical"
        )
        
        assert "caption" in result
        assert "keyboard" in result
        assert "urgency" in result
        assert "🔥" in result["caption"]  # Critical emoji
        assert "Gaming Laptop" in result["caption"]
        assert "80.0%" in result["caption"]  # Stockout probability

    def test_format_recommendation_for_display(self, mock_smart_alerts):
        """Test formatting recommendation for display."""
        recommendation = {
            "asin": "B001",
            "title": "Gaming Laptop",
            "brand": "ASUS",
            "category": "Electronics",
            "confidence_score": 0.85,
            "predicted_interest_level": "high",
            "explanation": "Based on your preferences",
            "source": "ai_prediction"
        }
        
        result = mock_smart_alerts._format_recommendation_for_display(recommendation)
        
        assert result["asin"] == "B001"
        assert result["title"] == "Gaming Laptop"
        assert result["confidence"] == 0.85
        assert result["interest_level"] == "high"

    @pytest.mark.asyncio
    async def test_build_recommendations_message(self, mock_smart_alerts):
        """Test building recommendations message."""
        recommendations = [
            {
                "asin": "B001",
                "title": "Gaming Laptop ASUS ROG Strix with amazing performance",
                "brand": "ASUS",
                "category": "Electronics",
                "confidence": 0.9,
                "explanation": "Perfect for gaming enthusiasts based on your history"
            },
            {
                "asin": "B002", 
                "title": "Gaming Mouse",
                "brand": "Logitech",
                "category": "Electronics",
                "confidence": 0.7,
                "explanation": "Complements your setup"
            }
        ]
        
        result = await mock_smart_alerts._build_recommendations_message(recommendations)
        
        assert "caption" in result
        assert "keyboard" in result
        assert "AI-Powered Recommendations" in result["caption"]
        assert "🔥" in result["caption"]  # High confidence emoji for first rec
        assert "Gaming Laptop" in result["caption"]

    @pytest.mark.asyncio
    async def test_build_recommendations_message_empty(self, mock_smart_alerts):
        """Test building recommendations message with empty list."""
        result = await mock_smart_alerts._build_recommendations_message([])
        
        assert result["caption"] == "No recommendations available"
        assert result["keyboard"] is None

    @pytest.mark.asyncio
    async def test_error_handling_inventory_alert(self, mock_smart_alerts):
        """Test error handling in inventory alert generation."""
        with patch('bot.smart_alerts.predictive_engine') as mock_ai:
            mock_ai.predict_inventory_alerts.side_effect = Exception("AI error")
            
            result = await mock_smart_alerts.generate_smart_inventory_alert("B001")
            
            assert result["status"] == "error"
            assert "AI error" in result["message"]

    @pytest.mark.asyncio
    async def test_error_handling_personalized_recommendations(self, mock_smart_alerts):
        """Test error handling in personalized recommendations."""
        with patch('bot.smart_alerts.predictive_engine') as mock_ai:
            mock_ai.predict_user_interests.side_effect = Exception("Recommendation error")
            
            result = await mock_smart_alerts.generate_personalized_recommendations(1)
            
            assert result["status"] == "error"
            assert "Recommendation error" in result["message"]

    @pytest.mark.asyncio
    async def test_enhanced_deal_alert_fallback(self, mock_smart_alerts, sample_watch, sample_product_data):
        """Test enhanced deal alert fallback on error."""
        with patch.object(mock_smart_alerts.market_intel, 'calculate_deal_quality') as mock_deal_quality:
            mock_deal_quality.side_effect = Exception("Market intel error")
            
            with patch.object(mock_smart_alerts, '_generate_fallback_alert') as mock_fallback:
                mock_fallback.return_value = {
                    "caption": "Fallback alert",
                    "keyboard": None,
                    "quality_score": 50
                }
                
                result = await mock_smart_alerts.generate_enhanced_deal_alert(
                    sample_watch, sample_product_data
                )
                
                assert result["quality_score"] == 50
                mock_fallback.assert_called_once()


@pytest.mark.integration
class TestAISmartAlertsIntegration:
    """Integration tests for AI-enhanced smart alerts."""
    
    @pytest.mark.asyncio
    async def test_full_alert_pipeline_with_ai(self):
        """Test complete alert pipeline with AI enhancements."""
        # This would test the full pipeline with real database and AI
        # For now, we'll skip this as it requires full system setup
        pass

    @pytest.mark.asyncio 
    async def test_ai_model_integration(self):
        """Test integration between smart alerts and AI models."""
        # This would test real AI model integration
        # For now, we'll skip this as it requires trained models
        pass
