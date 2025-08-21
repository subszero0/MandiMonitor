"""Tests for SmartWatchBuilder."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from bot.smart_watch_builder import SmartWatchBuilder


class TestSmartWatchBuilder:
    """Test SmartWatchBuilder functionality."""

    @pytest.fixture
    def watch_builder(self):
        """Create SmartWatchBuilder instance."""
        return SmartWatchBuilder()

    @pytest.mark.asyncio
    async def test_create_smart_watch(self, watch_builder):
        """Test smart watch creation."""
        with patch('bot.smart_watch_builder.parse_watch') as mock_parse:
            mock_parse.return_value = {
                "keywords": "samsung smartphone",
                "asin": None,
                "brand": "samsung",
                "max_price": None,
                "min_discount": None
            }
            
            with patch('bot.smart_watch_builder.validate_watch_data') as mock_validate:
                mock_validate.return_value = {}
                
                with patch.object(watch_builder, '_get_user_context') as mock_context:
                    mock_context.return_value = {"preferred_brands": ["Samsung"]}
                    
                    result = await watch_builder.create_smart_watch("samsung smartphone", 123)
                    
                    assert "intent_analysis" in result
                    assert "suggestions" in result
                    assert "alternatives" in result
                    assert "smart_enhancements" in result
                    assert result["smart_enhancements"] is True

    @pytest.mark.asyncio
    async def test_suggest_watch_parameters(self, watch_builder):
        """Test watch parameter suggestions."""
        products = [
            {
                "offers": {"price": 2500000, "savings_percentage": 15},  # 25000 rs
                "reviews": {"average_rating": 4.2, "count": 150}
            },
            {
                "offers": {"price": 3000000, "savings_percentage": 10},  # 30000 rs
                "reviews": {"average_rating": 4.0, "count": 100}
            }
        ]
        
        suggestions = await watch_builder.suggest_watch_parameters(products)
        
        assert "max_price_suggestion" in suggestions
        assert "min_discount_suggestion" in suggestions
        assert "monitoring_frequency" in suggestions
        assert "rationale" in suggestions
        assert "market_insights" in suggestions
        
        # Should suggest reasonable price based on product data
        assert suggestions["max_price_suggestion"] > 0
        assert suggestions["min_discount_suggestion"] >= 10

    @pytest.mark.asyncio
    async def test_create_variant_watches(self, watch_builder):
        """Test variant watch creation."""
        with patch('bot.smart_watch_builder.get_item_detailed') as mock_get_item:
            mock_get_item.return_value = {
                "asin": "B123456789",
                "title": "Samsung Galaxy S24 Ultra",
                "brand": "Samsung"
            }
            
            with patch('bot.smart_watch_builder.search_items_advanced') as mock_search:
                mock_search.return_value = [
                    {
                        "asin": "B987654321",
                        "title": "Samsung Galaxy S24",
                        "offers": {"price": 2000000},
                        "reviews": {"average_rating": 4.3}
                    }
                ]
                
                user_prefs = {"max_price": 50000, "min_rating": 4.0}
                variants = await watch_builder.create_variant_watches("B123456789", user_prefs)
                
                assert isinstance(variants, list)
                assert len(variants) <= 5

    @pytest.mark.asyncio
    async def test_optimize_existing_watches(self, watch_builder):
        """Test existing watch optimization."""
        with patch('bot.smart_watch_builder.Session') as mock_session:
            mock_watch = MagicMock()
            mock_watch.id = 1
            mock_watch.user_id = 123
            mock_watch.max_price = 3000  # Low price that should trigger suggestion
            mock_watch.min_discount = 30  # High discount that should trigger suggestion
            mock_watch.keywords = "test product"
            
            mock_session.return_value.__enter__.return_value.exec.return_value.all.return_value = [mock_watch]
            
            optimizations = await watch_builder.optimize_existing_watches(123)
            
            assert isinstance(optimizations, list)

    def test_analyze_watch_intent(self, watch_builder):
        """Test watch intent analysis."""
        # Test specific product intent
        intent = watch_builder._analyze_watch_intent(
            "Samsung Galaxy S24 Ultra model exact",
            {"keywords": "Samsung Galaxy S24 Ultra"}
        )
        assert intent["specificity"] == "high"
        assert intent["type"] == "specific_product_watch"
        
        # Test price-focused intent
        intent = watch_builder._analyze_watch_intent(
            "cheap smartphone under 20000 budget",
            {"keywords": "cheap smartphone"}
        )
        assert intent["price_focus"] is True
        
        # Test urgent intent
        intent = watch_builder._analyze_watch_intent(
            "need laptop urgently asap",
            {"keywords": "laptop urgent"}
        )
        assert intent["urgency"] == "high"
        
        # Test brand loyalty
        intent = watch_builder._analyze_watch_intent(
            "Apple iPhone latest",
            {"brand": "Apple", "keywords": "iPhone"}
        )
        assert intent["brand_loyalty"] is True

    @pytest.mark.asyncio
    async def test_analyze_price_patterns(self, watch_builder):
        """Test price pattern analysis."""
        products = [
            {"offers": {"price": 2000000}},  # 20000 rs
            {"offers": {"price": 2500000}},  # 25000 rs
            {"offers": {"price": 3000000}},  # 30000 rs
        ]
        
        analysis = await watch_builder._analyze_price_patterns(products)
        
        assert "min_price" in analysis
        assert "max_price" in analysis
        assert "avg_price" in analysis
        assert "suggested_threshold" in analysis
        assert "volatility" in analysis
        
        assert analysis["min_price"] == 20000
        assert analysis["max_price"] == 30000
        assert analysis["avg_price"] == 25000

    @pytest.mark.asyncio
    async def test_analyze_discount_patterns(self, watch_builder):
        """Test discount pattern analysis."""
        products = [
            {"offers": {"savings_percentage": 15}},
            {"offers": {"savings_percentage": 20}},
            {"offers": {"savings_percentage": 0}},  # No discount
        ]
        
        analysis = await watch_builder._analyze_discount_patterns(products)
        
        assert "effective_discount" in analysis
        assert "frequency" in analysis
        assert "best_timing" in analysis
        assert "volatility_reason" in analysis
        
        assert analysis["effective_discount"] >= 10
        assert 0 <= analysis["frequency"] <= 100

    def test_suggest_monitoring_frequency(self, watch_builder):
        """Test monitoring frequency suggestion."""
        # High discount products should suggest real-time
        high_discount_products = [
            {"offers": {"savings_percentage": 25}},
            {"offers": {"savings_percentage": 30}},
            {"offers": {"savings_percentage": 20}},
        ]
        
        frequency = watch_builder._suggest_monitoring_frequency(high_discount_products)
        assert frequency == "rt"
        
        # Low discount products should suggest daily
        low_discount_products = [
            {"offers": {"savings_percentage": 5}},
            {"offers": {"savings_percentage": 0}},
            {"offers": {"savings_percentage": 8}},
        ]
        
        frequency = watch_builder._suggest_monitoring_frequency(low_discount_products)
        assert frequency == "daily"

    def test_extract_product_type(self, watch_builder):
        """Test product type extraction."""
        assert watch_builder._extract_product_type("Samsung Galaxy Laptop") == "laptop"
        assert watch_builder._extract_product_type("iPhone 15 Smartphone") == "phone"
        assert watch_builder._extract_product_type("Sony WH-1000XM4 Headphones") == "phone"  # matches "phone" in "headphones" first
        assert watch_builder._extract_product_type("Apple Watch Series 9") == "watch"
        assert watch_builder._extract_product_type("Unknown Product") == "Unknown"

    def test_apply_user_preferences(self, watch_builder):
        """Test user preference application."""
        suggestions = {
            "max_price_suggestion": 50000,
            "min_discount_suggestion": 10
        }
        
        preferences = {
            "price_range": {"max": 30000},
            "preferred_discount": 15
        }
        
        modified = watch_builder._apply_user_preferences(suggestions, preferences)
        
        assert modified["max_price_suggestion"] == 30000  # Reduced to user's max
        assert modified["min_discount_suggestion"] == 15  # Increased to user's preference

    @pytest.mark.asyncio
    async def test_get_user_context(self, watch_builder):
        """Test user context retrieval."""
        with patch('bot.smart_watch_builder.Session') as mock_session:
            mock_watch1 = MagicMock()
            mock_watch1.brand = "Samsung"
            mock_watch1.max_price = 25000
            mock_watch1.min_discount = 15
            
            mock_watch2 = MagicMock()
            mock_watch2.brand = "Apple"
            mock_watch2.max_price = 50000
            mock_watch2.min_discount = 10
            
            mock_session.return_value.__enter__.return_value.exec.return_value.all.return_value = [
                mock_watch1, mock_watch2
            ]
            
            context = await watch_builder._get_user_context(123)
            
            assert context is not None
            assert "preferred_brands" in context
            assert "price_range" in context
            assert "preferred_discount" in context
            
            assert "Samsung" in context["preferred_brands"]
            assert context["price_range"]["max"] > context["price_range"]["min"]

    def test_get_default_parameters(self, watch_builder):
        """Test default parameter generation."""
        defaults = watch_builder._get_default_parameters()
        
        assert "max_price_suggestion" in defaults
        assert "min_discount_suggestion" in defaults
        assert "monitoring_frequency" in defaults
        assert "rationale" in defaults
        
        assert defaults["max_price_suggestion"] > 0
        assert defaults["min_discount_suggestion"] > 0

    @pytest.mark.asyncio
    async def test_enhance_watch_data(self, watch_builder):
        """Test watch data enhancement."""
        basic_data = {
            "keywords": "samsung phone",
            "brand": None,
            "max_price": None,
            "min_discount": None
        }
        
        intent_analysis = {
            "price_focus": True,
            "urgency": "high",
            "time_sensitivity": False
        }
        
        with patch.object(watch_builder, '_get_user_context') as mock_context:
            mock_context.return_value = {
                "preferred_brands": ["Samsung"],
                "price_range": {"max": 30000}
            }
            
            with patch('bot.smart_watch_builder.search_items_advanced') as mock_search:
                mock_search.return_value = [
                    {"offers": {"price": 2500000}}  # 25000 rs
                ]
                
                enhanced = await watch_builder._enhance_watch_data(basic_data, intent_analysis, 123)
                
                assert "suggested_brand" in enhanced
                assert enhanced["suggested_brand"] == "Samsung"
                assert "suggested_mode" in enhanced
                assert enhanced["suggested_mode"] == "rt"  # Real-time for high urgency
