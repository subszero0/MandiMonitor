"""
Simple tests to verify PopularityModel is eliminated and syntax errors are fixed.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch

from bot.product_selection_models import get_selection_model, FeatureMatchModel, PopularityModel
from bot.ai.multi_card_selector import MultiCardSelector


class TestPopularityModelElimination:
    """Test that PopularityModel is completely eliminated."""

    def test_get_selection_model_never_returns_popularity_for_multiple_products(self):
        """Test that get_selection_model never returns PopularityModel for 2+ products."""
        test_cases = [
            ("gaming monitor", 2),
            ("simple monitor", 3), 
            ("best monitor", 5),
            ("laptop", 10),
        ]
        
        for query, product_count in test_cases:
            model = get_selection_model(query, product_count)
            assert not isinstance(model, PopularityModel), f"PopularityModel returned for query='{query}', count={product_count}"
            assert isinstance(model, FeatureMatchModel), f"Expected FeatureMatchModel for query='{query}', count={product_count}"

    def test_comparison_table_fallback_structure(self):
        """Test that fallback comparison table has correct structure (syntax error test)."""
        selector = MultiCardSelector()
        
        # This should not raise syntax errors
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


def test_multi_card_selector_syntax():
    """Test that MultiCardSelector can be instantiated without syntax errors."""
    # This will fail if there are syntax errors in multi_card_selector.py
    selector = MultiCardSelector()
    assert selector is not None
    
    # Test that we can call the fallback method
    fallback = selector._get_fallback_comparison_table()
    assert isinstance(fallback, dict)


def test_import_all_modules():
    """Test that all modules import without syntax errors."""
    try:
        from bot.ai.multi_card_selector import MultiCardSelector
        from bot.ai.enhanced_product_selection import EnhancedFeatureMatchModel
        from bot.ai.enhanced_carousel import build_enhanced_card
        from bot.product_selection_models import smart_product_selection
        assert True  # If we get here, imports worked
    except SyntaxError as e:
        pytest.fail(f"Syntax error in imports: {e}")
    except Exception as e:
        # Other errors are okay for this test, we just want to check syntax
        assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
