"""
Tests to verify PopularityModel is completely eliminated and multi-card functionality works.

This test suite specifically validates:
1. PopularityModel is never used in any scenario
2. FeatureMatchModel is forced for all queries with 2+ products
3. Multi-card functionality works correctly
4. Syntax errors are resolved and AI system functions properly
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from bot.product_selection_models import (
    get_selection_model,
    smart_product_selection,
    FeatureMatchModel,
    PopularityModel,
    RandomSelectionModel
)
from bot.ai.multi_card_selector import MultiCardSelector
from bot.ai.enhanced_product_selection import EnhancedFeatureMatchModel


class TestPopularityModelElimination:
    """Test that PopularityModel is completely eliminated from the system."""

    def test_get_selection_model_never_returns_popularity(self):
        """Test that get_selection_model never returns PopularityModel."""
        test_cases = [
            # (query, product_count)
            ("gaming monitor", 2),
            ("simple monitor", 3),
            ("best monitor", 5),
            ("laptop", 10),
            ("headphones", 15),
            ("phone", 25),
            ("", 2),  # Empty query
            ("a", 2),  # Single character
        ]
        
        for query, product_count in test_cases:
            model = get_selection_model(query, product_count)
            assert not isinstance(model, PopularityModel), f"PopularityModel returned for query='{query}', count={product_count}"
            assert isinstance(model, FeatureMatchModel), f"Expected FeatureMatchModel for query='{query}', count={product_count}"

    def test_single_product_uses_random_not_popularity(self):
        """Test that single product scenarios use RandomSelectionModel, not PopularityModel."""
        model = get_selection_model("any query", 1)
        assert isinstance(model, RandomSelectionModel)
        assert not isinstance(model, PopularityModel)

    @pytest.mark.asyncio
    async def test_smart_product_selection_no_popularity_fallback(self):
        """Test that smart_product_selection never falls back to PopularityModel."""
        products = [
            {"asin": "B001", "title": "Product A", "rating_count": 100, "average_rating": 4.0},
            {"asin": "B002", "title": "Product B", "rating_count": 200, "average_rating": 4.2}
        ]
        
        # Mock FeatureMatchModel to fail, should skip PopularityModel entirely
        with patch('bot.product_selection_models.FeatureMatchModel') as MockFeature:
            mock_feature_instance = Mock()
            mock_feature_instance.select_product = AsyncMock(side_effect=Exception("AI failed"))
            MockFeature.return_value = mock_feature_instance
            
            # Mock PopularityModel to ensure it's never called
            with patch('bot.product_selection_models.PopularityModel') as MockPop:
                mock_pop_instance = Mock()
                mock_pop_instance.select_product = AsyncMock(return_value={"asin": "B999", "should_not_appear": True})
                MockPop.return_value = mock_pop_instance
                
                result = await smart_product_selection(products, "gaming monitor")
                
                # PopularityModel should never be called
                MockPop.assert_not_called()
                mock_pop_instance.select_product.assert_not_called()
                
                # Should fall back to RandomSelectionModel
                assert result is not None
                assert result["asin"] in ["B001", "B002"]
                assert "should_not_appear" not in result

    @pytest.mark.asyncio
    async def test_all_scenarios_avoid_popularity_model(self):
        """Test various scenarios to ensure PopularityModel is never used."""
        products = [
            {"asin": "B001", "title": "Product A", "rating_count": 100, "average_rating": 4.0},
            {"asin": "B002", "title": "Product B", "rating_count": 200, "average_rating": 4.2}
        ]
        
        queries = [
            "gaming monitor 144hz",
            "laptop for programming", 
            "best headphones",
            "monitor",
            "cheap laptop",
            "",  # Empty query
        ]
        
        for query in queries:
            # Mock PopularityModel to detect if it's ever called
            with patch('bot.product_selection_models.PopularityModel') as MockPop:
                mock_pop_instance = Mock()
                mock_pop_instance.select_product = AsyncMock(return_value={"should_not_appear": True})
                MockPop.return_value = mock_pop_instance
                
                result = await smart_product_selection(products, query)
                
                # PopularityModel should never be instantiated or called
                MockPop.assert_not_called()
                mock_pop_instance.select_product.assert_not_called()
                
                assert result is not None
                assert "should_not_appear" not in result


class TestMultiCardFunctionality:
    """Test that multi-card functionality works correctly."""

    @pytest.fixture
    def sample_products(self):
        """Sample products for multi-card testing."""
        return [
            {
                "asin": "B08N5WRWNW",
                "title": "ASUS TUF Gaming 27\" Curved Monitor 144Hz",
                "price": 2500000,  # ₹25,000 in paise
                "brand": "ASUS"
            },
            {
                "asin": "B09G9FPHY6", 
                "title": "LG UltraGear 27\" Gaming Monitor 165Hz",
                "price": 3200000,  # ₹32,000 in paise
                "brand": "LG"
            },
            {
                "asin": "B09WPJNHKP",
                "title": "Samsung Odyssey G5 27\" Curved 144Hz",
                "price": 2200000,  # ₹22,000 in paise
                "brand": "Samsung"
            }
        ]

    @pytest.mark.asyncio
    async def test_multi_card_selector_syntax_fixed(self, sample_products):
        """Test that MultiCardSelector works without syntax errors."""
        selector = MultiCardSelector()
        
        # Create scored products tuple format
        scored_products = [
            (sample_products[0], {"score": 0.92, "confidence": 0.88, "matched_features": ["refresh_rate"]}),
            (sample_products[1], {"score": 0.89, "confidence": 0.82, "matched_features": ["refresh_rate"]}),
            (sample_products[2], {"score": 0.85, "confidence": 0.75, "matched_features": ["refresh_rate"]})
        ]
        
        user_features = {"refresh_rate": "144", "size": "27"}
        
        # This should not raise syntax errors
        result = await selector.select_products_for_comparison(
            scored_products=scored_products,
            user_features=user_features,
            max_cards=3
        )
        
        assert result is not None
        assert "products" in result
        assert "comparison_table" in result
        assert "presentation_mode" in result

    @pytest.mark.asyncio
    async def test_comparison_table_generation_robust(self, sample_products):
        """Test that comparison table generation is robust and returns proper dict."""
        selector = MultiCardSelector()
        
        scored_products = [
            (sample_products[0], {"score": 0.92, "matched_features": ["refresh_rate"]}),
            (sample_products[1], {"score": 0.89, "matched_features": ["refresh_rate"]})
        ]
        
        user_features = {"refresh_rate": "144"}
        
        result = await selector.select_products_for_comparison(
            scored_products=scored_products,
            user_features=user_features,
            max_cards=2
        )
        
        comparison_table = result["comparison_table"]
        
        # Verify comparison_table is a dict with required structure
        assert isinstance(comparison_table, dict)
        assert "headers" in comparison_table
        assert "key_differences" in comparison_table
        assert "strengths" in comparison_table
        assert "trade_offs" in comparison_table
        assert "summary" in comparison_table
        
        # Verify each field has correct type
        assert isinstance(comparison_table["headers"], list)
        assert isinstance(comparison_table["key_differences"], list)
        assert isinstance(comparison_table["strengths"], dict)
        assert isinstance(comparison_table["trade_offs"], list)
        assert isinstance(comparison_table["summary"], str)

    @pytest.mark.asyncio
    async def test_enhanced_feature_match_model_validation(self, sample_products):
        """Test that EnhancedFeatureMatchModel validates data properly."""
        model = EnhancedFeatureMatchModel()
        
        # Mock MultiCardSelector to return proper structure
        with patch.object(model, '_initialize_components') as mock_init:
            # Mock components
            mock_feature_extractor = Mock()
            mock_matching_engine = Mock()
            mock_carousel_selector = Mock()
            
            # Mock feature extraction
            mock_feature_extractor.extract_features.return_value = {
                "refresh_rate": "144",
                "size": "27",
                "confidence": 0.8
            }
            
            # Mock scoring
            scored_products = [
                (sample_products[0], {"score": 0.92, "confidence": 0.88}),
                (sample_products[1], {"score": 0.89, "confidence": 0.82})
            ]
            mock_matching_engine.score_products = AsyncMock(return_value=scored_products)
            
            # Mock carousel selection with proper structure
            mock_carousel_selector.select_products_for_comparison = AsyncMock(return_value={
                "products": sample_products[:2],
                "comparison_table": {
                    "headers": ["Feature", "Option 1", "Option 2"],
                    "key_differences": [],
                    "strengths": {},
                    "trade_offs": [],
                    "summary": "Test summary"
                },
                "presentation_mode": "duo",
                "selection_reason": "Test reason",
                "ai_metadata": {"selection_type": "multi_card"}
            })
            
            model._feature_extractor = mock_feature_extractor
            model._matching_engine = mock_matching_engine
            model._carousel_selector = mock_carousel_selector
            
            result = await model.select_product(
                products=sample_products,
                user_query="gaming monitor 144hz",
                user_preferences={}
            )
            
            # Should return multi-card result
            assert result is not None
            assert result["selection_type"] == "multi_card"
            assert len(result["products"]) == 2
            assert isinstance(result["comparison_table"], dict)
            assert result["metadata"]["validation_passed"] is True

    def test_comparison_table_fallback_structure(self):
        """Test that fallback comparison table has correct structure."""
        selector = MultiCardSelector()
        
        fallback_table = selector._get_fallback_comparison_table()
        
        # Verify structure
        assert isinstance(fallback_table, dict)
        assert "headers" in fallback_table
        assert "key_differences" in fallback_table
        assert "strengths" in fallback_table
        assert "trade_offs" in fallback_table
        assert "summary" in fallback_table
        
        # Verify types
        assert isinstance(fallback_table["headers"], list)
        assert isinstance(fallback_table["key_differences"], list)
        assert isinstance(fallback_table["strengths"], dict)
        assert isinstance(fallback_table["trade_offs"], list)
        assert isinstance(fallback_table["summary"], str)


class TestSystemIntegration:
    """Test system integration scenarios."""

    @pytest.mark.asyncio
    async def test_full_pipeline_no_popularity_model(self):
        """Test full pipeline from product selection to multi-card without PopularityModel."""
        products = [
            {"asin": "B001", "title": "Gaming Monitor 144Hz", "price": 25000},
            {"asin": "B002", "title": "Office Monitor 75Hz", "price": 15000},
            {"asin": "B003", "title": "Professional Monitor 165Hz", "price": 35000}
        ]
        
        # Mock to ensure PopularityModel is never used
        with patch('bot.product_selection_models.PopularityModel') as MockPop:
            mock_pop = Mock()
            MockPop.return_value = mock_pop
            
            result = await smart_product_selection(products, "gaming monitor 144hz")
            
            # PopularityModel should never be instantiated
            MockPop.assert_not_called()
            
            # Should get a valid result
            assert result is not None
            assert result["asin"] in ["B001", "B002", "B003"]

    @pytest.mark.asyncio 
    async def test_error_scenarios_skip_popularity_model(self):
        """Test that error scenarios properly skip PopularityModel."""
        products = [
            {"asin": "B001", "title": "Product A"},
            {"asin": "B002", "title": "Product B"}
        ]
        
        # Mock FeatureMatchModel to fail
        with patch('bot.product_selection_models.FeatureMatchModel') as MockFeature:
            mock_feature = Mock()
            mock_feature.select_product = AsyncMock(side_effect=Exception("Feature match failed"))
            MockFeature.return_value = mock_feature
            
            # Mock PopularityModel to ensure it's not called
            with patch('bot.product_selection_models.PopularityModel') as MockPop:
                mock_pop = Mock()
                MockPop.return_value = mock_pop
                
                result = await smart_product_selection(products, "test query")
                
                # PopularityModel should be completely skipped
                MockPop.assert_not_called()
                
                # Should fall back to RandomSelectionModel
                assert result is not None

    def test_default_model_name_not_popularity(self):
        """Test that default model names are not PopularityModel."""
        # This test ensures that any default model name references are updated
        from bot.watch_flow import send_single_card_experience
        import inspect
        
        # Check the source code of send_single_card_experience for default model name
        source = inspect.getsource(send_single_card_experience)
        
        # Should not have PopularityModel as default
        assert "PopularityModel" not in source or "EnhancedFeatureMatchModel" in source


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "--tb=short"])
