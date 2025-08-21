"""Tests for Smart Alert Engine."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from bot.smart_alerts import SmartAlertEngine, UserPreferenceManager
from bot.enhanced_models import DealAlert, Product, ProductOffers
from bot.models import Watch, User


class TestSmartAlertEngine:
    """Test Smart Alert Engine functionality."""

    @pytest.fixture
    def smart_alerts(self):
        """Create SmartAlertEngine instance."""
        return SmartAlertEngine()

    @pytest.fixture
    def sample_watch(self):
        """Create sample watch."""
        return Watch(
            id=1,
            user_id=123,
            asin="B0TEST123",
            keywords="test product",
            max_price=15000,
            min_discount=10,
            mode="daily"
        )

    @pytest.fixture
    def sample_current_data(self):
        """Create sample current product data."""
        return {
            "title": "Amazing Test Product - Best Quality",
            "price": 12000,  # ₹120.00
            "list_price": 15000,  # ₹150.00
            "savings_percentage": 20,
            "image": "https://example.com/image.jpg",
            "availability": "InStock"
        }

    @pytest.fixture
    def sample_deal_quality(self):
        """Create sample deal quality data."""
        return {
            "score": 85.0,
            "quality": "excellent",
            "factors": {
                "price_score": 90.0,
                "review_score": 85.0,
                "availability_score": 95.0,
                "discount_score": 70.0,
                "brand_score": 80.0
            },
            "recommendations": ["Excellent deal - consider buying immediately"]
        }

    @pytest.mark.asyncio
    async def test_generate_enhanced_deal_alert_premium(
        self, smart_alerts, sample_watch, sample_current_data, sample_deal_quality
    ):
        """Test enhanced deal alert generation for premium deals."""
        with patch.object(smart_alerts.market_intel, 'calculate_deal_quality', 
                         return_value=sample_deal_quality):
            with patch.object(smart_alerts, '_calculate_urgency', return_value="high"):
                with patch.object(smart_alerts, '_get_price_context', 
                                return_value={"price_level": "historical_low"}):
                    with patch.object(smart_alerts, '_store_deal_alert'):
                        
                        result = await smart_alerts.generate_enhanced_deal_alert(
                            sample_watch, sample_current_data
                        )
                        
                        assert "error" not in result
                        assert result["quality_score"] == 85.0
                        assert result["quality_category"] == "excellent"
                        assert result["urgency"] == "high"
                        assert "caption" in result
                        assert "keyboard" in result
                        assert "🔥 **PREMIUM DEAL ALERT!** 🔥" in result["caption"]

    @pytest.mark.asyncio
    async def test_generate_enhanced_deal_alert_good(
        self, smart_alerts, sample_watch, sample_current_data
    ):
        """Test enhanced deal alert generation for good deals."""
        good_quality = {
            "score": 70.0,
            "quality": "good",
            "factors": {},
            "recommendations": ["Good deal - worth considering"]
        }
        
        with patch.object(smart_alerts.market_intel, 'calculate_deal_quality', 
                         return_value=good_quality):
            with patch.object(smart_alerts, '_calculate_urgency', return_value="medium"):
                with patch.object(smart_alerts, '_get_price_context', 
                                return_value={"price_level": "below_average"}):
                    with patch.object(smart_alerts, '_store_deal_alert'):
                        
                        result = await smart_alerts.generate_enhanced_deal_alert(
                            sample_watch, sample_current_data
                        )
                        
                        assert result["quality_score"] == 70.0
                        assert result["quality_category"] == "good"
                        assert "✨ **GOOD DEAL ALERT** ✨" in result["caption"]

    @pytest.mark.asyncio
    async def test_generate_enhanced_deal_alert_standard(
        self, smart_alerts, sample_watch, sample_current_data
    ):
        """Test enhanced deal alert generation for standard deals."""
        standard_quality = {
            "score": 45.0,
            "quality": "average",
            "factors": {},
            "recommendations": ["Average deal"]
        }
        
        with patch.object(smart_alerts.market_intel, 'calculate_deal_quality', 
                         return_value=standard_quality):
            with patch.object(smart_alerts, '_calculate_urgency', return_value="low"):
                with patch.object(smart_alerts, '_get_price_context', 
                                return_value={"price_level": "average"}):
                    with patch.object(smart_alerts, '_store_deal_alert'):
                        with patch('bot.smart_alerts.build_single_card', 
                                 return_value=("Test caption", Mock())):
                            
                            result = await smart_alerts.generate_enhanced_deal_alert(
                                sample_watch, sample_current_data
                            )
                            
                            assert result["quality_score"] == 45.0
                            assert result["quality_category"] == "average"
                            assert "Deal Quality: 45/100" in result["caption"]

    @pytest.mark.asyncio
    async def test_generate_enhanced_deal_alert_fallback(
        self, smart_alerts, sample_watch, sample_current_data
    ):
        """Test fallback when enhanced alert generation fails."""
        with patch.object(smart_alerts.market_intel, 'calculate_deal_quality', 
                         side_effect=Exception("API Error")):
            with patch('bot.smart_alerts.build_single_card', 
                     return_value=("Fallback caption", Mock())):
                
                result = await smart_alerts.generate_enhanced_deal_alert(
                    sample_watch, sample_current_data
                )
                
                assert result["fallback"] is True
                assert result["quality_score"] == 50.0

    @pytest.mark.asyncio
    async def test_calculate_urgency_critical(self, smart_alerts, sample_watch, sample_current_data):
        """Test urgency calculation for critical deals."""
        deal_quality = {"score": 95.0}
        
        with patch('bot.smart_alerts.Session') as mock_session:
            # Mock recent price history showing price drop
            mock_session.return_value.__enter__.return_value.exec.return_value.all.return_value = [
                Mock(current_price=15000)  # Previous price much higher
            ]
            
            # Add stock urgency
            current_data = {**sample_current_data, "availability": "low stock"}
            
            result = await smart_alerts._calculate_urgency(
                deal_quality, current_data, sample_watch
            )
            
            assert result == "critical"

    @pytest.mark.asyncio
    async def test_calculate_urgency_high(self, smart_alerts, sample_watch, sample_current_data):
        """Test urgency calculation for high priority deals."""
        deal_quality = {"score": 85.0}
        
        with patch('bot.smart_alerts.Session') as mock_session:
            mock_session.return_value.__enter__.return_value.exec.return_value.all.return_value = []
            
            result = await smart_alerts._calculate_urgency(
                deal_quality, sample_current_data, sample_watch
            )
            
            assert result == "high"

    @pytest.mark.asyncio
    async def test_get_price_context_historical_low(self, smart_alerts):
        """Test price context for historical low."""
        trends = {
            "price_metrics": {
                "min_price": 12000,
                "max_price": 18000,
                "average_price": 15000,
                "volatility_percentage": 5.0
            },
            "trend_analysis": {
                "direction": "decreasing"
            }
        }
        
        with patch.object(smart_alerts.market_intel, 'analyze_price_trends', 
                         return_value=trends):
            
            result = await smart_alerts._get_price_context("B0TEST123", 12100)
            
            assert result["price_level"] == "historical_low"
            assert result["trend"] == "decreasing"

    @pytest.mark.asyncio
    async def test_get_price_context_no_history(self, smart_alerts):
        """Test price context with no history."""
        with patch.object(smart_alerts.market_intel, 'analyze_price_trends', 
                         return_value={"error": "No data"}):
            
            result = await smart_alerts._get_price_context("B0NODATA", 12000)
            
            assert result["context"] == "No price history available"

    @pytest.mark.asyncio
    async def test_send_comparison_alert(self, smart_alerts):
        """Test sending comparison alert with alternatives."""
        alternatives = [
            {
                "asin": "B0ALT001",
                "title": "Alternative Product 1",
                "price": 10000,
                "savings_percentage": 25,
                "rating": 4.5,
                "review_count": 200
            },
            {
                "asin": "B0ALT002", 
                "title": "Alternative Product 2",
                "price": 11000,
                "savings_percentage": 15,
                "rating": 4.2,
                "review_count": 150
            }
        ]
        
        with patch.object(smart_alerts.bot, 'send_message', new_callable=AsyncMock) as mock_send:
            result = await smart_alerts.send_comparison_alert(123, "B0TEST123", alternatives)
            
            assert result is True
            mock_send.assert_called_once()
            
            # Check message content
            call_args = mock_send.call_args
            assert "Better Deal Found!" in call_args[1]["text"]
            assert "Alternative Product 1" in call_args[1]["text"]

    @pytest.mark.asyncio
    async def test_send_comparison_alert_no_alternatives(self, smart_alerts):
        """Test comparison alert with no alternatives."""
        result = await smart_alerts.send_comparison_alert(123, "B0TEST123", [])
        
        assert result is False

    @pytest.mark.asyncio
    async def test_send_price_drop_prediction_alert_high_confidence(self, smart_alerts):
        """Test price drop prediction alert with high confidence."""
        prediction_data = {
            "confidence": 0.85,
            "predicted_price": 10000,
            "current_price": 12000
        }
        
        with patch.object(smart_alerts.bot, 'send_message', new_callable=AsyncMock) as mock_send:
            result = await smart_alerts.send_price_drop_prediction_alert(
                123, "B0TEST123", prediction_data
            )
            
            assert result is True
            mock_send.assert_called_once()
            
            # Check message content
            call_args = mock_send.call_args
            assert "Price Drop Predicted!" in call_args[1]["text"]
            assert "High confidence" in call_args[1]["text"]

    @pytest.mark.asyncio
    async def test_send_price_drop_prediction_alert_low_confidence(self, smart_alerts):
        """Test price drop prediction alert with low confidence."""
        prediction_data = {
            "confidence": 0.5,  # Below threshold
            "predicted_price": 10000,
            "current_price": 12000
        }
        
        result = await smart_alerts.send_price_drop_prediction_alert(
            123, "B0TEST123", prediction_data
        )
        
        assert result is False  # Should not send due to low confidence

    @pytest.mark.asyncio
    async def test_store_deal_alert(self, smart_alerts, sample_watch, sample_current_data):
        """Test storing deal alert in database."""
        deal_quality = {"score": 80.0}
        
        with patch('bot.smart_alerts.Session') as mock_session:
            mock_session_instance = mock_session.return_value.__enter__.return_value
            
            await smart_alerts._store_deal_alert(sample_watch, sample_current_data, deal_quality)
            
            # Verify DealAlert was added
            mock_session_instance.add.assert_called_once()
            mock_session_instance.commit.assert_called_once()
            
            # Check the alert data
            added_alert = mock_session_instance.add.call_args[0][0]
            assert isinstance(added_alert, DealAlert)
            assert added_alert.watch_id == sample_watch.id
            assert added_alert.asin == sample_watch.asin
            assert added_alert.current_price == sample_current_data["price"]

    @pytest.mark.asyncio
    async def test_build_premium_deal_card(self, smart_alerts, sample_watch, sample_current_data):
        """Test building premium deal card."""
        deal_quality = {"score": 90.0, "quality": "excellent"}
        urgency = "critical"
        price_context = {"price_level": "historical_low", "trend": "decreasing"}
        
        caption, keyboard = await smart_alerts._build_premium_deal_card(
            sample_watch, sample_current_data, deal_quality, urgency, price_context
        )
        
        assert "🔥 **PREMIUM DEAL ALERT!** 🔥" in caption
        assert "Historical Low Price!" in caption
        assert "LIMITED TIME - ACT NOW!" in caption
        assert keyboard is not None

    @pytest.mark.asyncio 
    async def test_build_good_deal_card(self, smart_alerts, sample_watch, sample_current_data):
        """Test building good deal card."""
        deal_quality = {"score": 75.0, "quality": "good"}
        urgency = "medium"
        price_context = {"price_level": "below_average"}
        
        caption, keyboard = await smart_alerts._build_good_deal_card(
            sample_watch, sample_current_data, deal_quality, urgency, price_context
        )
        
        assert "✨ **GOOD DEAL ALERT** ✨" in caption
        assert "Deal Quality: 75/100" in caption
        assert keyboard is not None

    @pytest.mark.asyncio
    async def test_market_insight_notifications(self, smart_alerts):
        """Test market insight notification generation."""
        # Test weekly roundup
        result = await smart_alerts.generate_market_insight_notification(
            123, "weekly_roundup", {}
        )
        assert result["type"] == "weekly_roundup"
        assert "Weekly Market Roundup" in result["caption"]
        
        # Test seasonal opportunity
        result = await smart_alerts.generate_market_insight_notification(
            123, "seasonal_opportunity", {}
        )
        assert result["type"] == "seasonal_opportunity"
        
        # Test unknown type
        result = await smart_alerts.generate_market_insight_notification(
            123, "unknown_type", {}
        )
        assert "error" in result


class TestUserPreferenceManager:
    """Test User Preference Manager functionality."""

    @pytest.fixture
    def pref_manager(self):
        """Create UserPreferenceManager instance."""
        return UserPreferenceManager()

    @pytest.mark.asyncio
    async def test_get_user_preferences_default(self, pref_manager):
        """Test getting default user preferences."""
        prefs = await pref_manager.get_user_preferences(123)
        
        assert prefs["notification_frequency"] == "normal"
        assert prefs["deal_quality_threshold"] == 70
        assert "deal_alerts" in prefs["enabled_notification_types"]

    @pytest.mark.asyncio
    async def test_update_user_preferences(self, pref_manager):
        """Test updating user preferences."""
        new_prefs = {
            "notification_frequency": "high",
            "deal_quality_threshold": 80
        }
        
        result = await pref_manager.update_user_preferences(123, new_prefs)
        
        assert result is True

    @pytest.mark.asyncio
    async def test_should_send_notification_enabled(self, pref_manager):
        """Test notification permission for enabled type."""
        with patch.object(pref_manager, 'get_user_preferences', 
                         return_value={"enabled_notification_types": ["deal_alerts"]}):
            
            result = await pref_manager.should_send_notification(123, "deal_alerts")
            
            assert result is True

    @pytest.mark.asyncio
    async def test_should_send_notification_disabled(self, pref_manager):
        """Test notification permission for disabled type."""
        with patch.object(pref_manager, 'get_user_preferences', 
                         return_value={"enabled_notification_types": ["weekly_roundup"]}):
            
            result = await pref_manager.should_send_notification(123, "deal_alerts")
            
            assert result is False

    @pytest.mark.asyncio
    async def test_should_send_notification_quiet_hours(self, pref_manager):
        """Test notification permission during quiet hours."""
        quiet_time = datetime.utcnow().replace(hour=2, minute=0, second=0, microsecond=0)  # 2 AM
        
        with patch.object(pref_manager, 'get_user_preferences', 
                         return_value={
                             "enabled_notification_types": ["deal_alerts"],
                             "quiet_hours": {"start": 22, "end": 8}
                         }):
            
            result = await pref_manager.should_send_notification(
                123, "deal_alerts", quiet_time
            )
            
            assert result is False

    @pytest.mark.asyncio
    async def test_should_send_notification_active_hours(self, pref_manager):
        """Test notification permission during active hours."""
        active_time = datetime.utcnow().replace(hour=14, minute=0, second=0, microsecond=0)  # 2 PM
        
        with patch.object(pref_manager, 'get_user_preferences', 
                         return_value={
                             "enabled_notification_types": ["deal_alerts"],
                             "quiet_hours": {"start": 22, "end": 8}
                         }):
            
            result = await pref_manager.should_send_notification(
                123, "deal_alerts", active_time
            )
            
            assert result is True


class TestSmartAlertsIntegration:
    """Integration tests for Smart Alert Engine."""

    @pytest.mark.asyncio
    async def test_full_alert_pipeline(self):
        """Test complete alert generation pipeline."""
        smart_alerts = SmartAlertEngine()
        
        # Mock all dependencies
        watch = Watch(id=1, user_id=123, asin="B0TEST123", keywords="test", mode="daily")
        current_data = {
            "title": "Test Product",
            "price": 10000,
            "image": "test.jpg"
        }
        
        # Mock market intelligence
        deal_quality = {
            "score": 88.0,
            "quality": "excellent",
            "factors": {},
            "recommendations": ["Great deal!"]
        }
        
        with patch.object(smart_alerts.market_intel, 'calculate_deal_quality', 
                         return_value=deal_quality):
            with patch.object(smart_alerts, '_calculate_urgency', return_value="high"):
                with patch.object(smart_alerts, '_get_price_context', 
                                return_value={"price_level": "below_average"}):
                    with patch.object(smart_alerts, '_store_deal_alert'):
                        
                        result = await smart_alerts.generate_enhanced_deal_alert(
                            watch, current_data
                        )
                        
                        # Verify complete pipeline
                        assert "error" not in result
                        assert result["quality_score"] == 88.0
                        assert result["urgency"] == "high"
                        assert "caption" in result
                        assert "keyboard" in result
                        assert "🔥 **PREMIUM DEAL ALERT!** 🔥" in result["caption"]

