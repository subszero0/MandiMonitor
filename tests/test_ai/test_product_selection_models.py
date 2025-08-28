"""
Tests for Phase 4: Product Selection Models

This test suite validates the AI-powered product selection models including:
- FeatureMatchModel with AI scoring and fallbacks
- PopularityModel for ratings-based selection
- RandomSelectionModel for final fallback
- Model selection logic and fallback chains
- Performance monitoring integration
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from bot.product_selection_models import (
    FeatureMatchModel,
    PopularityModel, 
    RandomSelectionModel,
    get_selection_model,
    smart_product_selection,
    has_technical_features
)


class TestFeatureMatchModel:
    """Test the AI-powered FeatureMatchModel."""

    @pytest.fixture
    def feature_match_model(self):
        """Create a FeatureMatchModel instance."""
        return FeatureMatchModel()

    @pytest.fixture
    def sample_products(self):
        """Sample products for testing."""
        return [
            {
                "asin": "B08N5WRWNW",
                "title": "Samsung 27 Inch Curved Gaming Monitor 144Hz",
                "price": 25000,
                "rating_count": 150,
                "average_rating": 4.3
            },
            {
                "asin": "B09G9FPHY6", 
                "title": "LG 24 Inch IPS Monitor 75Hz",
                "price": 15000,
                "rating_count": 89,
                "average_rating": 4.1
            },
            {
                "asin": "B09WPJNHKP",
                "title": "ASUS TUF Gaming 27 Inch 165Hz Curved",
                "price": 28000,
                "rating_count": 203,
                "average_rating": 4.5
            }
        ]

    @pytest.mark.asyncio
    async def test_feature_match_model_initialization(self, feature_match_model):
        """Test FeatureMatchModel initializes correctly."""
        assert feature_match_model.model_name == "FeatureMatchModel"
        assert feature_match_model.version == "1.0.0"
        assert feature_match_model._feature_extractor is None
        assert feature_match_model._matching_engine is None

    @pytest.mark.asyncio
    async def test_feature_match_with_technical_query(self, feature_match_model, sample_products):
        """Test FeatureMatchModel with a technical query."""
        technical_query = "gaming monitor 144hz curved 27 inch"
        
        # Mock the AI components
        with patch.object(feature_match_model, '_initialize_ai_components') as mock_init:
            mock_feature_extractor = Mock()
            mock_matching_engine = Mock()
            
            # Mock feature extraction
            mock_feature_extractor.extract_features.return_value = {
                "refresh_rate": "144",
                "size": "27", 
                "curvature": "curved",
                "confidence": 0.9,
                "technical_density": 0.8
            }
            
            # Mock scoring
            mock_matching_engine.score_products = AsyncMock(return_value=[
                (sample_products[0], {
                    "score": 0.95,
                    "rationale": "✓ refresh_rate=144Hz (exact), size=27″ (exact), curvature=curved",
                    "confidence": 0.9,
                    "matched_features": ["refresh_rate", "size", "curvature"],
                    "processing_time_ms": 15.2
                })
            ])
            
            feature_match_model._feature_extractor = mock_feature_extractor
            feature_match_model._matching_engine = mock_matching_engine
            
            result = await feature_match_model.select_product(sample_products, technical_query)
            
            assert result is not None
            assert result["asin"] == "B08N5WRWNW"
            assert "_ai_metadata" in result
            assert result["_ai_metadata"]["ai_selection"] is True
            assert result["_ai_metadata"]["ai_score"] == 0.95
            assert result["_ai_metadata"]["model_name"] == "FeatureMatchModel"

    @pytest.mark.asyncio
    async def test_feature_match_with_non_technical_query(self, feature_match_model, sample_products):
        """Test FeatureMatchModel falls back for non-technical queries."""
        non_technical_query = "good monitor"
        
        with patch.object(feature_match_model, '_initialize_ai_components'):
            mock_feature_extractor = Mock()
            mock_feature_extractor.extract_features.return_value = {
                "confidence": 0.2,  # Low confidence
                "technical_density": 0.1  # Low technical density
            }
            
            feature_match_model._feature_extractor = mock_feature_extractor
            
            result = await feature_match_model.select_product(sample_products, non_technical_query)
            
            # Should return None to trigger fallback
            assert result is None

    @pytest.mark.asyncio
    async def test_feature_match_empty_products(self, feature_match_model):
        """Test FeatureMatchModel with empty product list."""
        result = await feature_match_model.select_product([], "gaming monitor 144hz")
        assert result is None

    @pytest.mark.asyncio
    async def test_feature_match_empty_query(self, feature_match_model, sample_products):
        """Test FeatureMatchModel with empty query."""
        result = await feature_match_model.select_product(sample_products, "")
        
        # Should return first product for empty query
        assert result == sample_products[0]

    def test_has_technical_features_classifier(self, feature_match_model):
        """Test the technical features classifier."""
        # Mock AI components to test classifier
        feature_match_model._feature_extractor = Mock()
        feature_match_model._matching_engine = Mock()
        
        # High confidence technical query
        assert feature_match_model._has_technical_features({
            "refresh_rate": "144",
            "confidence": 0.8,
            "technical_density": 0.7
        }) is True
        
        # Low confidence non-technical query
        assert feature_match_model._has_technical_features({
            "confidence": 0.2,
            "technical_density": 0.1
        }) is False
        
        # Medium confidence with technical density should trigger AI (reverted logic)
        assert feature_match_model._has_technical_features({
            "confidence": 0.6,
            "technical_density": 0.5
        }) is True
        
        # Medium confidence with actual technical features should definitely be True
        assert feature_match_model._has_technical_features({
            "confidence": 0.6,
            "technical_density": 0.5,
            "refresh_rate": "144"
        }) is True
        
        # Empty features
        assert feature_match_model._has_technical_features({}) is False


class TestPopularityModel:
    """Test the PopularityModel."""

    @pytest.fixture
    def popularity_model(self):
        """Create a PopularityModel instance."""
        return PopularityModel()

    @pytest.fixture
    def sample_products_with_ratings(self):
        """Sample products with different popularity metrics."""
        return [
            {
                "asin": "B001",
                "title": "Product A",
                "rating_count": 50,
                "average_rating": 3.5,
                "sales_rank": 1000
            },
            {
                "asin": "B002",
                "title": "Product B", 
                "rating_count": 500,
                "average_rating": 4.5,
                "sales_rank": 100
            },
            {
                "asin": "B003",
                "title": "Product C",
                "rating_count": 1000,
                "average_rating": 4.2,
                "sales_rank": 50
            }
        ]

    @pytest.mark.asyncio
    async def test_popularity_model_selection(self, popularity_model, sample_products_with_ratings):
        """Test PopularityModel selects most popular product."""
        result = await popularity_model.select_product(
            sample_products_with_ratings, 
            "any query"
        )
        
        assert result is not None
        assert "_popularity_metadata" in result
        assert result["_popularity_metadata"]["popularity_selection"] is True
        assert result["_popularity_metadata"]["model_name"] == "PopularityModel"
        
        # Should select product with best combined popularity score
        # Product B or C should be selected (both have high ratings and good rank)
        assert result["asin"] in ["B002", "B003"]

    @pytest.mark.asyncio
    async def test_popularity_model_empty_products(self, popularity_model):
        """Test PopularityModel with empty product list."""
        result = await popularity_model.select_product([], "any query")
        assert result is None

    def test_popularity_score_calculation(self, popularity_model):
        """Test popularity score calculation logic."""
        # High popularity product
        high_pop_product = {
            "rating_count": 1000,
            "average_rating": 4.5,
            "sales_rank": 10
        }
        high_score = popularity_model._calculate_popularity_score(high_pop_product)
        
        # Low popularity product
        low_pop_product = {
            "rating_count": 5,
            "average_rating": 3.0,
            "sales_rank": 50000
        }
        low_score = popularity_model._calculate_popularity_score(low_pop_product)
        
        assert high_score > low_score
        assert 0 <= high_score <= 1
        assert 0 <= low_score <= 1


class TestRandomSelectionModel:
    """Test the RandomSelectionModel."""

    @pytest.fixture
    def random_model(self):
        """Create a RandomSelectionModel instance."""
        return RandomSelectionModel()

    @pytest.fixture
    def sample_products_basic(self):
        """Basic sample products for random selection."""
        return [
            {"asin": "B001", "title": "Product A", "average_rating": 4.0, "rating_count": 100},
            {"asin": "B002", "title": "Product B", "average_rating": 3.0, "rating_count": 10},
            {"asin": "B003", "title": "Product C", "average_rating": 4.5, "rating_count": 200}
        ]

    @pytest.mark.asyncio
    async def test_random_selection(self, random_model, sample_products_basic):
        """Test RandomSelectionModel returns a valid product."""
        result = await random_model.select_product(sample_products_basic, "any query")
        
        assert result is not None
        assert result["asin"] in ["B001", "B002", "B003"]
        assert "_random_metadata" in result
        assert result["_random_metadata"]["random_selection"] is True
        assert result["_random_metadata"]["model_name"] == "RandomSelectionModel"

    @pytest.mark.asyncio
    async def test_random_selection_empty_products(self, random_model):
        """Test RandomSelectionModel with empty product list."""
        result = await random_model.select_product([], "any query")
        assert result is None

    def test_random_selection_weighting(self, random_model):
        """Test random selection uses basic weighting."""
        # High quality product should get higher weight
        high_quality = {"average_rating": 4.5, "rating_count": 500}
        high_weight = random_model._calculate_basic_weight(high_quality)
        
        # Low quality product should get lower weight  
        low_quality = {"average_rating": 2.5, "rating_count": 1}
        low_weight = random_model._calculate_basic_weight(low_quality)
        
        assert high_weight > low_weight


class TestModelSelectionLogic:
    """Test the model selection logic and integration."""

    def test_get_selection_model_logic(self):
        """Test model selection based on query and product count."""
        # Complex query with many products should use FeatureMatchModel
        model = get_selection_model("gaming monitor 144hz curved 27 inch", 10)
        assert isinstance(model, FeatureMatchModel)
        
        # Simple query with moderate products should use PopularityModel
        model = get_selection_model("monitor", 5)
        assert isinstance(model, PopularityModel)
        
        # Few products should use RandomSelectionModel
        model = get_selection_model("any query", 2)
        assert isinstance(model, RandomSelectionModel)

    @pytest.mark.asyncio
    async def test_smart_product_selection_fallback_chain(self):
        """Test the complete fallback chain works correctly."""
        products = [
            {"asin": "B001", "title": "Product A", "rating_count": 100, "average_rating": 4.0}
        ]
        
        # Test with technical query that should try AI first
        with patch('bot.product_selection_models.FeatureMatchModel') as MockAI:
            # Mock AI model to fail
            mock_ai_instance = Mock()
            mock_ai_instance.select_product = AsyncMock(return_value=None)
            MockAI.return_value = mock_ai_instance
            
            result = await smart_product_selection(products, "gaming monitor 144hz")
            
            # Should fallback and return a result
            assert result is not None
            assert result["asin"] == "B001"

    @pytest.mark.asyncio
    async def test_smart_product_selection_empty_products(self):
        """Test smart_product_selection with empty product list."""
        result = await smart_product_selection([], "any query")
        assert result is None

    def test_has_technical_features_global_function(self):
        """Test the global has_technical_features function."""
        # Technical queries
        assert has_technical_features("gaming monitor 144hz") is True
        assert has_technical_features("27 inch curved display") is True
        assert has_technical_features("4k monitor") is True
        assert has_technical_features("monitor 1440p ips") is True
        
        # Non-technical queries
        assert has_technical_features("good monitor") is False
        assert has_technical_features("monitor") is False
        assert has_technical_features("") is False
        assert has_technical_features("best budget option") is False


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    @pytest.mark.asyncio
    async def test_gaming_monitor_selection_scenario(self):
        """Test a realistic gaming monitor selection scenario."""
        gaming_products = [
            {
                "asin": "B08N5WRWNW",
                "title": "Samsung Odyssey G5 27-Inch Curved Gaming Monitor, 1440P, 144Hz",
                "price": 25000,
                "rating_count": 2547,
                "average_rating": 4.3
            },
            {
                "asin": "B09G9FPHY6",
                "title": "LG 24GN600-B 24-Inch Ultragear Gaming Monitor 144Hz 1ms IPS",
                "price": 18000,
                "rating_count": 1823,
                "average_rating": 4.4
            },
            # Add more products to trigger AI model (need >=5 products)
            {
                "asin": "B09C001",
                "title": "ASUS Gaming Monitor 144Hz",
                "price": 22000,
                "rating_count": 1200,
                "average_rating": 4.2
            },
            {
                "asin": "B09C002", 
                "title": "Dell Gaming Monitor 165Hz",
                "price": 24000,
                "rating_count": 800,
                "average_rating": 4.1
            },
            {
                "asin": "B09C003",
                "title": "MSI Gaming Monitor 144Hz Curved",
                "price": 26000,
                "rating_count": 900,
                "average_rating": 4.4
            }
        ]
        
        technical_query = "gaming monitor 144hz 27 inch curved"
        
        # This should use FeatureMatchModel with 5+ products and complex query
        with patch('bot.product_selection_models.FeatureMatchModel.select_product') as mock_select:
            # Mock AI selection
            expected_result = gaming_products[0].copy()
            expected_result["_ai_metadata"] = {
                "ai_selection": True,
                "ai_score": 0.92,
                "ai_confidence": 0.85,
                "matched_features": ["refresh_rate", "size", "curvature"]
            }
            mock_select.return_value = expected_result
            
            result = await smart_product_selection(gaming_products, technical_query)
            
            assert result is not None
            assert result["asin"] == "B08N5WRWNW"
            assert "_ai_metadata" in result
            mock_select.assert_called_once()

    @pytest.mark.asyncio
    async def test_simple_monitor_selection_scenario(self):
        """Test a simple monitor selection that should use PopularityModel."""
        basic_products = [
            {
                "asin": "B001",
                "title": "Basic Monitor 1080p",
                "rating_count": 50,
                "average_rating": 3.8
            },
            {
                "asin": "B002", 
                "title": "Popular Monitor",
                "rating_count": 500,
                "average_rating": 4.5
            },
            # Add third product to trigger PopularityModel (need >=3 products)
            {
                "asin": "B003",
                "title": "Another Monitor",
                "rating_count": 100,
                "average_rating": 4.0
            }
        ]
        
        simple_query = "monitor"
        
        # Should use PopularityModel for simple queries with 3+ products
        result = await smart_product_selection(basic_products, simple_query)
        
        assert result is not None
        # Should select the more popular product (B002 has highest rating count and rating)
        assert result["asin"] == "B002"
        assert "_popularity_metadata" in result

    @pytest.mark.asyncio  
    async def test_error_handling_and_fallbacks(self):
        """Test error handling and ultimate fallback behavior."""
        products = [{"asin": "B001", "title": "Test Product"}]
        
        # Mock all models to fail
        with patch('bot.product_selection_models.FeatureMatchModel') as MockAI, \
             patch('bot.product_selection_models.PopularityModel') as MockPop, \
             patch('bot.product_selection_models.RandomSelectionModel') as MockRand:
            
            MockAI.return_value.select_product = AsyncMock(side_effect=Exception("AI failed"))
            MockPop.return_value.select_product = AsyncMock(side_effect=Exception("Popularity failed"))
            MockRand.return_value.select_product = AsyncMock(side_effect=Exception("Random failed"))
            
            result = await smart_product_selection(products, "test query")
            
            # Should fall back to ultimate fallback (first product)
            assert result is not None
            assert result["asin"] == "B001"
            assert "_fallback_metadata" in result
            assert result["_fallback_metadata"]["fallback_selection"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
