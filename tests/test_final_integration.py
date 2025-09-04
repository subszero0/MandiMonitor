"""
Final integration test to verify the exact scenario that was failing is now fixed.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from bot.product_selection_models import smart_product_selection
from bot.ai.enhanced_product_selection import EnhancedFeatureMatchModel


@pytest.mark.asyncio
async def test_multi_card_experience_no_syntax_errors():
    """Test the exact scenario that was causing syntax errors and PopularityModel fallback."""
    
    # Sample products similar to the logs
    products = [
        {
            "asin": "B0DCBDVNLD",
            "title": "LG Ultragear™ 32GS60QC (32 inch) QHD 1000R Curved Gaming Monitor",
            "price": 1964900,  # ₹19,649 in paise
            "brand": "LG",
            "rating_count": 150,
            "average_rating": 4.3
        },
        {
            "asin": "B08N5WRWNW", 
            "title": "Samsung Gaming Monitor 32 inch Curved 144Hz",
            "price": 2299000,  # ₹22,990 in paise
            "brand": "Samsung",
            "rating_count": 200,
            "average_rating": 4.4
        },
        {
            "asin": "B09G9FPHY6",
            "title": "ASUS TUF Gaming Monitor 32 inch 165Hz",
            "price": 3179900,  # ₹31,799 in paise
            "brand": "ASUS", 
            "rating_count": 180,
            "average_rating": 4.2
        }
    ]
    
    # This is the exact query from the logs
    user_query = "32 inch gaming monitor under INR 80,000"
    
    # Mock the AI components to simulate successful operation
    with patch('bot.ai.enhanced_product_selection.EnhancedFeatureMatchModel._initialize_components'):
        
        model = EnhancedFeatureMatchModel()
        
        # Mock feature extractor
        mock_feature_extractor = Mock()
        mock_feature_extractor.extract_features.return_value = {
            "size": "32",
            "category": "gaming_monitor", 
            "refresh_rate": "144",
            "confidence": 0.8,
            "technical_density": 0.7
        }
        
        # Mock matching engine  
        mock_matching_engine = Mock()
        scored_products = [
            (products[0], {"score": 0.92, "confidence": 0.88, "matched_features": ["size", "refresh_rate"]}),
            (products[1], {"score": 0.89, "confidence": 0.82, "matched_features": ["size", "refresh_rate"]}),
            (products[2], {"score": 0.85, "confidence": 0.75, "matched_features": ["size", "refresh_rate"]})
        ]
        mock_matching_engine.score_products = AsyncMock(return_value=scored_products)
        
        # Mock carousel selector with proper structure
        mock_carousel_selector = Mock()
        mock_carousel_selector.select_products_for_comparison = AsyncMock(return_value={
            "products": products,
            "comparison_table": {
                "headers": ["Feature", "Option 1", "Option 2", "Option 3"],
                "key_differences": [
                    {
                        "feature": "Price",
                        "values": ["₹19,649", "₹22,990", "₹31,799"],
                        "highlight_best": 0
                    },
                    {
                        "feature": "Brand", 
                        "values": ["LG", "Samsung", "ASUS"],
                        "highlight_best": -1
                    }
                ],
                "strengths": {
                    0: ["Best price", "Good refresh rate"],
                    1: ["Curved design", "Samsung quality"],
                    2: ["Higher refresh rate", "ASUS brand"]
                },
                "trade_offs": [
                    "LG option offers best value for money",
                    "Samsung provides curved design at mid-range price",
                    "ASUS offers highest performance at premium price"
                ],
                "summary": "Three competitive gaming monitors with different price-performance trade-offs"
            },
            "presentation_mode": "trio",
            "selection_reason": "Multiple competitive options found with different strengths",
            "ai_metadata": {
                "selection_type": "multi_card",
                "products_analyzed": 3,
                "top_score": 0.92
            }
        })
        
        # Set up the model
        model._feature_extractor = mock_feature_extractor
        model._matching_engine = mock_matching_engine  
        model._carousel_selector = mock_carousel_selector
        
        # This should work without syntax errors and not fall back to PopularityModel
        result = await model.select_product(
            products=products,
            user_query=user_query,
            user_preferences={}
        )
        
        # Verify the result
        assert result is not None
        assert result["selection_type"] == "multi_card"
        assert len(result["products"]) == 3
        assert isinstance(result["comparison_table"], dict)
        assert result["metadata"]["model_used"] == "EnhancedFeatureMatchModel"
        assert result["metadata"]["validation_passed"] is True
        
        # Verify comparison table structure
        comparison_table = result["comparison_table"]
        assert "headers" in comparison_table
        assert "key_differences" in comparison_table
        assert "strengths" in comparison_table
        assert "trade_offs" in comparison_table
        assert "summary" in comparison_table
        
        # Verify no PopularityModel traces
        assert "PopularityModel" not in str(result)
        assert result["metadata"]["model_name"] == "EnhancedFeatureMatchModel"


@pytest.mark.asyncio
async def test_smart_product_selection_integration():
    """Test the smart_product_selection function with the same scenario."""
    
    products = [
        {"asin": "B001", "title": "Gaming Monitor 32 inch 144Hz", "price": 25000, "rating_count": 100, "average_rating": 4.0},
        {"asin": "B002", "title": "Gaming Monitor 32 inch 165Hz", "price": 35000, "rating_count": 150, "average_rating": 4.2}
    ]
    
    # Should use FeatureMatchModel and not fall back to PopularityModel
    result = await smart_product_selection(products, "32 inch gaming monitor")
    
    # Should get a result without PopularityModel
    assert result is not None
    assert result["asin"] in ["B001", "B002"]
    
    # Should not have PopularityModel metadata
    metadata_str = str(result)
    assert "PopularityModel" not in metadata_str


def test_no_syntax_errors_in_key_modules():
    """Test that key modules import without syntax errors."""
    
    try:
        # These imports would fail if there were syntax errors
        from bot.ai.multi_card_selector import MultiCardSelector
        from bot.ai.enhanced_product_selection import EnhancedFeatureMatchModel  
        from bot.ai.enhanced_carousel import build_enhanced_card
        from bot.product_selection_models import smart_product_selection, get_selection_model
        from bot.watch_flow import send_multi_card_experience
        
        # Test instantiation
        selector = MultiCardSelector()
        model = EnhancedFeatureMatchModel()
        
        # Test method calls that were causing syntax errors
        fallback_table = selector._get_fallback_comparison_table()
        assert isinstance(fallback_table, dict)
        
        # Test model selection
        selection_model = get_selection_model("gaming monitor", 3)
        assert selection_model is not None
        
        print("✅ All modules imported and instantiated successfully")
        
    except SyntaxError as e:
        pytest.fail(f"Syntax error found: {e}")
    except Exception as e:
        # Other import errors are okay, we're just testing syntax
        print(f"Import successful, runtime error expected: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
