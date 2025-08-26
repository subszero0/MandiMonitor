"""
Tests for Multi-Card Selector (Phase 6).

These tests validate the intelligent multi-card selection logic, comparison table
generation, and smart defaults for the Phase 6 enhancement.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from bot.ai.multi_card_selector import MultiCardSelector


class TestMultiCardSelector:
    """Test the MultiCardSelector class for Phase 6."""

    @pytest.fixture
    def selector(self):
        """Create a MultiCardSelector instance for testing."""
        return MultiCardSelector()

    @pytest.fixture
    def sample_user_features(self):
        """Sample user features for testing."""
        return {
            "refresh_rate": "144",
            "size": "27",
            "resolution": "1440p",
            "curvature": "curved",
            "confidence": 0.8
        }

    @pytest.fixture
    def sample_scored_products(self):
        """Sample scored products for testing."""
        return [
            (
                {
                    "asin": "B08N5WRWNW",
                    "title": "ASUS TUF Gaming 27\" Curved Monitor 144Hz",
                    "price": 2500000,  # ₹25,000 in paise
                    "brand": "ASUS",
                    "image": "https://example.com/image1.jpg"
                },
                {
                    "score": 0.92,
                    "confidence": 0.88,
                    "rationale": "✓ refresh_rate=144Hz (exact), size=27″ (exact)",
                    "matched_features": ["refresh_rate", "size", "curvature"],
                    "mismatched_features": [],
                    "missing_features": ["resolution"],
                    "processing_time_ms": 15.2,
                    "feature_scores": {
                        "refresh_rate": {"score": 1.0, "user_value": "144", "product_value": "144"},
                        "size": {"score": 1.0, "user_value": "27", "product_value": "27"},
                        "curvature": {"score": 0.95, "user_value": "curved", "product_value": "curved"}
                    }
                }
            ),
            (
                {
                    "asin": "B09G9FPHY6",
                    "title": "LG UltraGear 27\" Gaming Monitor 165Hz",
                    "price": 3200000,  # ₹32,000 in paise
                    "brand": "LG",
                    "image": "https://example.com/image2.jpg"
                },
                {
                    "score": 0.89,
                    "confidence": 0.82,
                    "rationale": "✓ refresh_rate=165Hz (upgrade!), size=27″ (exact)",
                    "matched_features": ["refresh_rate", "size"],
                    "mismatched_features": ["curvature"],
                    "missing_features": ["resolution"],
                    "processing_time_ms": 12.8,
                    "feature_scores": {
                        "refresh_rate": {"score": 0.95, "user_value": "144", "product_value": "165"},
                        "size": {"score": 1.0, "user_value": "27", "product_value": "27"}
                    }
                }
            ),
            (
                {
                    "asin": "B09WPJNHKP",
                    "title": "Samsung Odyssey G5 27\" Curved 144Hz",
                    "price": 2200000,  # ₹22,000 in paise
                    "brand": "Samsung",
                    "image": "https://example.com/image3.jpg"
                },
                {
                    "score": 0.85,
                    "confidence": 0.75,
                    "rationale": "✓ refresh_rate=144Hz (exact), size=27″ (exact), curvature=curved (exact)",
                    "matched_features": ["refresh_rate", "size", "curvature"],
                    "mismatched_features": [],
                    "missing_features": ["resolution"],
                    "processing_time_ms": 18.1,
                    "feature_scores": {
                        "refresh_rate": {"score": 1.0, "user_value": "144", "product_value": "144"},
                        "size": {"score": 1.0, "user_value": "27", "product_value": "27"},
                        "curvature": {"score": 1.0, "user_value": "curved", "product_value": "curved"}
                    }
                }
            )
        ]

    @pytest.mark.asyncio
    async def test_single_card_high_confidence(self, selector, sample_scored_products, sample_user_features):
        """Test single card selection when AI confidence is high."""
        # Modify first product to have very high confidence
        sample_scored_products[0][1]["confidence"] = 0.95
        
        result = await selector.select_products_for_comparison(
            scored_products=sample_scored_products,
            user_features=sample_user_features,
            max_cards=3
        )
        
        assert result["presentation_mode"] == "single"
        assert len(result["products"]) == 1
        assert result["products"][0]["asin"] == "B08N5WRWNW"
        assert "High AI confidence" in result["selection_reason"]
        assert result["ai_metadata"]["selection_type"] == "single_card"

    @pytest.mark.asyncio
    async def test_multi_card_close_competition(self, selector, sample_scored_products, sample_user_features):
        """Test multi-card selection when products have close scores."""
        result = await selector.select_products_for_comparison(
            scored_products=sample_scored_products,
            user_features=sample_user_features,
            max_cards=3
        )
        
        assert result["presentation_mode"] in ["duo", "trio"]
        assert len(result["products"]) >= 2
        assert len(result["products"]) <= 3
        assert result["ai_metadata"]["selection_type"] == "multi_card"
        
        # Check that comparison table is generated
        comparison_table = result["comparison_table"]
        assert "key_differences" in comparison_table
        assert "strengths" in comparison_table
        assert "summary" in comparison_table

    @pytest.mark.asyncio
    async def test_price_diversity_triggers_multi_card(self, selector, sample_user_features):
        """Test that significant price differences trigger multi-card selection."""
        # Create products with significant price differences
        scored_products = [
            (
                {"asin": "B001", "price": 1500000, "brand": "Budget Brand"},  # ₹15,000
                {"score": 0.80, "confidence": 0.70, "matched_features": ["size"], "mismatched_features": [], "missing_features": []}
            ),
            (
                {"asin": "B002", "price": 4500000, "brand": "Premium Brand"},  # ₹45,000  
                {"score": 0.82, "confidence": 0.72, "matched_features": ["refresh_rate"], "mismatched_features": [], "missing_features": []}
            )
        ]
        
        result = await selector.select_products_for_comparison(
            scored_products=scored_products,
            user_features=sample_user_features,
            max_cards=3
        )
        
        # Should show multi-card due to price diversity
        assert result["presentation_mode"] == "duo"
        assert len(result["products"]) == 2

    def test_should_show_multiple_cards_logic(self, selector):
        """Test the logic for determining when to show multiple cards."""
        # Close scores should trigger multi-card
        close_scored_products = [
            ({"asin": "B001"}, {"score": 0.85, "matched_features": ["refresh_rate"]}),
            ({"asin": "B002"}, {"score": 0.82, "matched_features": ["size"]})
        ]
        assert selector._should_show_multiple_cards(close_scored_products) == True
        
        # Large score gap should not trigger multi-card
        gap_scored_products = [
            ({"asin": "B001"}, {"score": 0.90, "matched_features": ["refresh_rate"]}),
            ({"asin": "B002"}, {"score": 0.60, "matched_features": ["size"]})
        ]
        assert selector._should_show_multiple_cards(gap_scored_products) == False

    def test_products_have_different_strengths(self, selector):
        """Test detection of products with different strengths."""
        # Products excelling in different features
        diverse_products = [
            ({"asin": "B001"}, {"matched_features": ["refresh_rate", "size"]}),
            ({"asin": "B002"}, {"matched_features": ["resolution", "brand"]}),
            ({"asin": "B003"}, {"matched_features": ["curvature", "panel_type"]})
        ]
        
        assert selector._products_have_different_strengths(diverse_products) == True
        
        # Products with similar strengths
        similar_products = [
            ({"asin": "B001"}, {"matched_features": ["refresh_rate", "size"]}),
            ({"asin": "B002"}, {"matched_features": ["refresh_rate", "size"]})
        ]
        
        assert selector._products_have_different_strengths(similar_products) == False

    def test_price_ranges_offer_value_choice(self, selector):
        """Test detection of meaningful price ranges."""
        # Significant price difference (>25%)
        price_diverse_products = [
            ({"asin": "B001", "price": 2000000}, {}),  # ₹20,000
            ({"asin": "B002", "price": 3500000}, {})   # ₹35,000 (75% higher)
        ]
        
        assert selector._price_ranges_offer_value_choice(price_diverse_products) == True
        
        # Small price difference (<25%)
        price_similar_products = [
            ({"asin": "B001", "price": 2000000}, {}),  # ₹20,000
            ({"asin": "B002", "price": 2300000}, {})   # ₹23,000 (15% higher)
        ]
        
        assert selector._price_ranges_offer_value_choice(price_similar_products) == False

    @pytest.mark.asyncio
    async def test_comparison_table_generation(self, selector, sample_scored_products, sample_user_features):
        """Test comprehensive comparison table generation."""
        result = await selector.select_products_for_comparison(
            scored_products=sample_scored_products,
            user_features=sample_user_features,
            max_cards=3
        )
        
        comparison_table = result["comparison_table"]
        
        # Check basic structure
        assert "headers" in comparison_table
        assert "key_differences" in comparison_table
        assert "strengths" in comparison_table
        assert "trade_offs" in comparison_table
        assert "summary" in comparison_table
        
        # Check that key differences include expected features
        key_diffs = comparison_table["key_differences"]
        feature_names = [diff["feature"] for diff in key_diffs]
        
        # Should include price since products have different prices
        assert any("Price" in name for name in feature_names)
        
        # Should include brand since products have different brands
        assert any("Brand" in name for name in feature_names)

    def test_diverse_product_selection(self, selector, sample_scored_products, sample_user_features):
        """Test selection of diverse products."""
        selected = selector._select_diverse_products(
            scored_products=sample_scored_products,
            user_features=sample_user_features,
            max_cards=2
        )
        
        # Should select top product plus one diverse option
        assert len(selected) == 2
        assert selected[0][0]["asin"] == "B08N5WRWNW"  # Top choice
        
        # Second choice should be different brand/price
        second_product = selected[1][0]
        first_product = selected[0][0]
        assert second_product["brand"] != first_product["brand"]

    def test_product_strengths_identification(self, selector, sample_scored_products):
        """Test identification of product strengths."""
        strengths = selector._identify_product_strengths(sample_scored_products)
        
        # Should have strengths for each product
        assert len(strengths) == len(sample_scored_products)
        
        # Check that strengths are meaningful
        for i, product_strengths in strengths.items():
            assert isinstance(product_strengths, list)
            if product_strengths:
                # Should have specific strength descriptions
                assert any(isinstance(strength, str) and len(strength) > 5 for strength in product_strengths)

    @pytest.mark.asyncio
    async def test_empty_products_handling(self, selector, sample_user_features):
        """Test handling of empty product list."""
        result = await selector.select_products_for_comparison(
            scored_products=[],
            user_features=sample_user_features,
            max_cards=3
        )
        
        assert result["presentation_mode"] == "none"
        assert len(result["products"]) == 0
        assert result["ai_metadata"]["selection_type"] == "empty"

    @pytest.mark.asyncio
    async def test_single_product_handling(self, selector, sample_scored_products, sample_user_features):
        """Test handling of single product."""
        result = await selector.select_products_for_comparison(
            scored_products=sample_scored_products[:1],
            user_features=sample_user_features,
            max_cards=3
        )
        
        assert result["presentation_mode"] == "single"
        assert len(result["products"]) == 1
        assert "Only one viable product" in result["selection_reason"]

    def test_presentation_mode_determination(self, selector):
        """Test presentation mode determination based on card count."""
        assert selector._get_presentation_mode(1) == "single"
        assert selector._get_presentation_mode(2) == "duo"
        assert selector._get_presentation_mode(3) == "trio"
        assert selector._get_presentation_mode(4) == "multi"

    @pytest.mark.asyncio
    async def test_performance_requirements(self, selector, sample_scored_products, sample_user_features):
        """Test that multi-card selection meets performance requirements."""
        import time
        
        start_time = time.time()
        result = await selector.select_products_for_comparison(
            scored_products=sample_scored_products,
            user_features=sample_user_features,
            max_cards=3
        )
        processing_time = (time.time() - start_time) * 1000
        
        # Should complete within 200ms (Phase 6 requirement)
        assert processing_time < 200
        
        # Should track processing time
        assert "processing_time_ms" in result["ai_metadata"]
        assert result["ai_metadata"]["processing_time_ms"] >= 0  # Can be 0 for very fast operations


class TestMultiCardIntegration:
    """Integration tests for multi-card selector with other components."""

    @pytest.mark.asyncio
    async def test_integration_with_matching_engine(self):
        """Test integration with the FeatureMatchingEngine."""
        from bot.ai.matching_engine import FeatureMatchingEngine
        
        engine = FeatureMatchingEngine()
        
        # Sample user features and products
        user_features = {"refresh_rate": "144", "size": "27"}
        products = [
            {"asin": "B001", "title": "Gaming Monitor 144Hz 27 inch", "price": 25000},
            {"asin": "B002", "title": "Professional Monitor 165Hz 27 inch", "price": 35000},
            {"asin": "B003", "title": "Budget Monitor 120Hz 27 inch", "price": 15000}
        ]
        
        # Test the carousel selection method
        with patch('bot.ai.matching_engine.FeatureMatchingEngine._extract_product_features') as mock_extract:
            # Mock product feature extraction
            mock_extract.side_effect = [
                {"refresh_rate": "144", "size": "27", "brand": "ASUS"},
                {"refresh_rate": "165", "size": "27", "brand": "LG"},
                {"refresh_rate": "120", "size": "27", "brand": "Samsung"}
            ]
            
            result = await engine.select_products_for_carousel(
                user_features=user_features,
                products=products,
                category="gaming_monitor",
                max_cards=3
            )
            
            # Should return properly structured result
            assert "products" in result
            assert "comparison_table" in result
            assert "presentation_mode" in result
            assert "ai_metadata" in result

    def test_comparison_summary_generation(self):
        """Test generation of comparison summary text."""
        selector = MultiCardSelector()
        
        sample_products = [
            ({"asin": "B001", "price": 25000}, {"score": 0.9, "matched_features": ["refresh_rate"]}),
            ({"asin": "B002", "price": 35000}, {"score": 0.85, "matched_features": ["size"]})
        ]
        
        comparison = {
            "key_differences": [
                {"feature": "Price", "values": ["₹25,000", "₹35,000"]},
                {"feature": "Brand", "values": ["ASUS", "LG"]}
            ],
            "trade_offs": ["Higher price options offer better feature matches"]
        }
        
        summary = selector._create_comparison_summary(sample_products, comparison)
        
        assert "2 competitive options found" in summary
        assert "Price" in summary or "Brand" in summary
        assert isinstance(summary, str)
        assert len(summary) > 20  # Should be meaningful summary


class TestMultiCardPerformance:
    """Performance tests for multi-card selector."""

    @pytest.mark.asyncio
    async def test_large_product_set_performance(self):
        """Test performance with large product sets."""
        selector = MultiCardSelector()
        
        # Create large product set
        scored_products = []
        for i in range(30):  # 30 products
            product = {
                "asin": f"B{i:08d}",
                "title": f"Gaming Monitor {i} 144Hz",
                "price": 20000 + (i * 1000),
                "brand": f"Brand{i % 5}"
            }
            score_data = {
                "score": 0.8 - (i * 0.01),  # Decreasing scores
                "confidence": 0.7,
                "matched_features": ["refresh_rate"],
                "mismatched_features": [],
                "missing_features": []
            }
            scored_products.append((product, score_data))
        
        user_features = {"refresh_rate": "144", "size": "27"}
        
        import time
        start_time = time.time()
        
        result = await selector.select_products_for_comparison(
            scored_products=scored_products,
            user_features=user_features,
            max_cards=3
        )
        
        processing_time = (time.time() - start_time) * 1000
        
        # Should handle large sets efficiently
        assert processing_time < 100  # Should be well under 200ms requirement
        assert len(result["products"]) <= 3  # Should limit to max cards
        assert result["presentation_mode"] in ["single", "duo", "trio"]
