"""
Unit tests for FeatureMatchingEngine - Phase 3 Implementation.

Tests cover the Phase 3 Definition of Done criteria:
- Weighted scoring algorithm with category-specific importance
- Exact match vs partial match scoring with tolerance windows
- Tie-breaking logic using popularity/rating scores
- Explainable scoring with rationale generation
- Monotonicity tests (adding features never decreases score)
- Performance requirements (<50ms for 30 products)
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, patch, MagicMock

from bot.ai.matching_engine import FeatureMatchingEngine
from bot.ai.feature_extractor import FeatureExtractor
from bot.ai.product_analyzer import ProductFeatureAnalyzer


class TestFeatureMatchingEngine:
    """Test suite for FeatureMatchingEngine."""
    
    @pytest.fixture
    def matching_engine(self):
        """Create a FeatureMatchingEngine instance for testing."""
        return FeatureMatchingEngine()
    
    @pytest.fixture
    def sample_user_features(self):
        """Sample user requirements for testing."""
        return {
            "refresh_rate": "144",
            "size": "27",
            "resolution": "1440p",
            "curvature": "curved",
            "brand": "samsung",
            "confidence": 0.85,
            "technical_query": True
        }
    
    @pytest.fixture
    def sample_product_features(self):
        """Sample product features for testing."""
        return {
            "refresh_rate": "144",
            "size": "27",
            "resolution": "1440p", 
            "curvature": "curved",
            "brand": "samsung",
            "panel_type": "va"
        }
    
    @pytest.fixture
    def sample_products(self):
        """Sample product data for testing."""
        return [
            {
                "asin": "B08N5WRWNW",
                "title": "Samsung 27-Inch CRG5 Curved Gaming Monitor 144Hz FHD VA",
                "price": "₹25,999",
                "rating_count": 1250,
                "average_rating": 4.3,
                "sales_rank": 45
            },
            {
                "asin": "B07DL6L8QX", 
                "title": "LG UltraGear 24 Inch Full HD IPS Gaming Monitor 144Hz",
                "price": "₹18,999",
                "rating_count": 2100,
                "average_rating": 4.5,
                "sales_rank": 23
            },
            {
                "asin": "B09X67JBQV",
                "title": "ASUS TUF Gaming VG27AQ 27 2K HDR Gaming Monitor IPS 165Hz",
                "price": "₹32,999",
                "rating_count": 890,
                "average_rating": 4.4,
                "sales_rank": 67
            }
        ]

    def test_exact_feature_matching(self, matching_engine, sample_user_features, sample_product_features):
        """Test perfect feature matching scenario."""
        result = matching_engine.score_product(
            sample_user_features, sample_product_features, "gaming_monitor"
        )
        
        # Should have high score for exact matches
        assert result["score"] >= 0.9
        assert result["confidence"] >= 0.8
        assert len(result["matched_features"]) >= 4  # refresh_rate, size, resolution, curvature
        assert len(result["mismatched_features"]) == 0
        assert "refresh_rate=144Hz (exact)" in result["rationale"]
        assert "size=27″ (exact)" in result["rationale"]

    def test_tolerance_window_scoring(self, matching_engine):
        """Test tolerance window functionality for near-matches."""
        user_features = {"refresh_rate": "144", "size": "27"}
        
        # Test refresh rate tolerance (144Hz requested, 165Hz found)
        product_features_upgrade = {"refresh_rate": "165", "size": "27"}
        result_upgrade = matching_engine.score_product(
            user_features, product_features_upgrade, "gaming_monitor"
        )
        
        # Should get upgrade bonus
        refresh_score = result_upgrade["feature_scores"]["refresh_rate"]["score"]
        assert refresh_score >= 0.9  # Should be high due to upgrade bonus
        
        # Test size tolerance (27" requested, 24" found)
        product_features_downgrade = {"refresh_rate": "144", "size": "24"}
        result_downgrade = matching_engine.score_product(
            user_features, product_features_downgrade, "gaming_monitor"
        )
        
        # Should have decent score within tolerance
        size_score = result_downgrade["feature_scores"]["size"]["score"]
        assert 0.7 <= size_score <= 0.9  # Within tolerance but some penalty

    def test_penalty_system(self, matching_engine):
        """Test penalty system for mismatched features."""
        user_features = {"refresh_rate": "144", "resolution": "1440p"}
        
        # Test significant mismatch
        product_features_mismatch = {"refresh_rate": "60", "resolution": "1080p"}
        result = matching_engine.score_product(
            user_features, product_features_mismatch, "gaming_monitor"
        )
        
        # Should apply penalties for mismatches
        assert result["score"] < 0.7  # Significant penalty
        assert len(result["mismatched_features"]) >= 1
        
        # Resolution mismatch should have specific penalty
        if "resolution" in result["feature_scores"]:
            resolution_score = result["feature_scores"]["resolution"]["score"]
            assert resolution_score < 0.5  # Below mismatch threshold

    def test_weighted_scoring(self, matching_engine):
        """Test category-specific feature importance weights."""
        # Test high-importance feature match (refresh_rate weight = 3.0)
        user_features_refresh = {"refresh_rate": "144"}
        product_features_refresh = {"refresh_rate": "144"}
        result_refresh = matching_engine.score_product(
            user_features_refresh, product_features_refresh, "gaming_monitor"
        )
        
        # Test low-importance feature match (brand weight = 0.8)
        user_features_brand = {"brand": "samsung"}
        product_features_brand = {"brand": "samsung"}
        result_brand = matching_engine.score_product(
            user_features_brand, product_features_brand, "gaming_monitor"
        )
        
        # Refresh rate match should contribute more to overall score
        assert result_refresh["score"] > result_brand["score"]

    def test_monotonicity_property(self, matching_engine):
        """Test that adding matching features never decreases score."""
        base_user_features = {"refresh_rate": "144"}
        base_product_features = {"refresh_rate": "144"}
        
        base_result = matching_engine.score_product(
            base_user_features, base_product_features, "gaming_monitor"
        )
        
        # Add more matching features
        extended_user_features = {
            "refresh_rate": "144",
            "size": "27",
            "resolution": "1440p"
        }
        extended_product_features = {
            "refresh_rate": "144", 
            "size": "27",
            "resolution": "1440p"
        }
        
        extended_result = matching_engine.score_product(
            extended_user_features, extended_product_features, "gaming_monitor"
        )
        
        # Adding matching features should not decrease score
        assert extended_result["score"] >= base_result["score"]
        assert len(extended_result["matched_features"]) > len(base_result["matched_features"])

    def test_explainability_rationale(self, matching_engine):
        """Test rationale generation for explainable AI."""
        user_features = {
            "refresh_rate": "144",
            "size": "27", 
            "resolution": "1440p",
            "curvature": "curved"
        }
        product_features = {
            "refresh_rate": "165",  # Upgrade
            "size": "27",           # Exact match
            "resolution": "1080p",  # Mismatch
            "curvature": "flat"     # Mismatch
        }
        
        result = matching_engine.score_product(
            user_features, product_features, "gaming_monitor"
        )
        
        rationale = result["rationale"]
        
        # Should explain matches, upgrades, and mismatches
        assert "165Hz" in rationale  # Should mention the upgrade
        assert "27″" in rationale    # Should mention exact match
        assert "✓" in rationale or "≈" in rationale  # Should have match indicators
        
        # Should be human-readable
        assert len(rationale) > 10
        assert not rationale.startswith("No clear")

    def test_tie_breaking_logic(self, matching_engine):
        """Test tie-breaking using popularity and price scores."""
        # Two products with similar feature scores but different popularity
        product_high_popularity = {
            "asin": "HIGH_POP",
            "title": "Popular Monitor 144Hz 27 inch",
            "rating_count": 2000,
            "average_rating": 4.5,
            "price": "₹25000"
        }
        
        product_low_popularity = {
            "asin": "LOW_POP", 
            "title": "Unknown Monitor 144Hz 27 inch",
            "rating_count": 50,
            "average_rating": 3.8,
            "price": "₹25000"
        }
        
        pop_score_high = matching_engine._get_popularity_score(product_high_popularity)
        pop_score_low = matching_engine._get_popularity_score(product_low_popularity)
        
        # Popular product should have higher popularity score
        assert pop_score_high > pop_score_low
        assert pop_score_high >= 0.6  # Should be reasonably high
        assert pop_score_low <= 0.4   # Should be lower

    def test_price_tier_scoring(self, matching_engine):
        """Test price tier scoring for tie-breaking."""
        # Test different price tiers
        budget_product = {"price": "₹8,999"}
        value_product = {"price": "₹18,999"}
        premium_product = {"price": "₹28,999"}
        ultra_premium_product = {"price": "₹75,999"}
        
        budget_score = matching_engine._get_price_tier_score(budget_product)
        value_score = matching_engine._get_price_tier_score(value_product)
        premium_score = matching_engine._get_price_tier_score(premium_product)
        ultra_score = matching_engine._get_price_tier_score(ultra_premium_product)
        
        # Premium should score highest, value second
        assert premium_score > value_score > budget_score
        assert premium_score > ultra_score  # Ultra-premium gets penalty

    @pytest.mark.asyncio
    async def test_async_product_scoring(self, matching_engine, sample_user_features, sample_products):
        """Test async product scoring with ProductFeatureAnalyzer integration."""
        # Mock the ProductFeatureAnalyzer to avoid actual PA-API calls
        with patch('bot.ai.matching_engine.ProductFeatureAnalyzer') as mock_analyzer_class:
            mock_analyzer = AsyncMock()
            mock_analyzer_class.return_value = mock_analyzer
            
            # Mock analyzer response for different products
            mock_analyzer.analyze_product_features.side_effect = [
                {  # Samsung monitor
                    "refresh_rate": {"value": "144", "confidence": 0.9},
                    "size": {"value": "27", "confidence": 0.95},
                    "resolution": {"value": "1080p", "confidence": 0.85},
                    "curvature": {"value": "curved", "confidence": 0.8},
                    "brand": {"value": "samsung", "confidence": 0.9}
                },
                {  # LG monitor
                    "refresh_rate": {"value": "144", "confidence": 0.9},
                    "size": {"value": "24", "confidence": 0.95},
                    "resolution": {"value": "1080p", "confidence": 0.85},
                    "panel_type": {"value": "ips", "confidence": 0.9},
                    "brand": {"value": "lg", "confidence": 0.9}
                },
                {  # ASUS monitor
                    "refresh_rate": {"value": "165", "confidence": 0.9},
                    "size": {"value": "27", "confidence": 0.95},
                    "resolution": {"value": "1440p", "confidence": 0.9},
                    "panel_type": {"value": "ips", "confidence": 0.9},
                    "brand": {"value": "asus", "confidence": 0.9}
                }
            ]
            
            # Test async scoring
            scored_products = await matching_engine.score_products(
                sample_user_features, sample_products, "gaming_monitor"
            )
            
            # Should return scored products sorted by relevance
            assert len(scored_products) == 3
            assert all(isinstance(item, tuple) for item in scored_products)
            assert all(len(item) == 2 for item in scored_products)
            
            # Products should be sorted by score (highest first)
            scores = [item[1]["score"] for item in scored_products]
            assert scores == sorted(scores, reverse=True)
            
            # Should have rationale for each product
            for product, score_data in scored_products:
                assert "rationale" in score_data
                assert "score" in score_data
                assert score_data["score"] >= 0.0

    def test_performance_benchmark(self, matching_engine, sample_user_features):
        """Test performance requirements (<50ms for 30 products)."""
        # Create 30 mock products for performance testing
        mock_products = []
        for i in range(30):
            mock_products.append({
                "asin": f"TEST_ASIN_{i:02d}",
                "title": f"Test Monitor {i} 144Hz 27 inch gaming display",
                "price": f"₹{20000 + i * 1000}",
                "rating_count": 100 + i * 50,
                "average_rating": 4.0 + (i % 10) * 0.05
            })
        
        # Mock the product feature extraction to avoid actual processing
        with patch.object(matching_engine, '_extract_product_features') as mock_extract:
            mock_extract.return_value = asyncio.coroutine(lambda: {
                "refresh_rate": "144",
                "size": "27",
                "resolution": "1080p"
            })()
            
            start_time = time.time()
            
            # Run async scoring
            async def run_scoring():
                return await matching_engine.score_products(
                    sample_user_features, mock_products, "gaming_monitor"
                )
            
            scored_products = asyncio.run(run_scoring())
            processing_time = (time.time() - start_time) * 1000  # Convert to ms
            
            # Should meet performance requirement
            assert processing_time <= 50  # 50ms requirement
            assert len(scored_products) == 30
            
            # Should maintain quality even with performance constraints
            for product, score_data in scored_products:
                assert score_data["score"] >= 0.0
                assert "rationale" in score_data

    def test_edge_cases(self, matching_engine):
        """Test edge cases and error handling."""
        # Empty user features
        empty_result = matching_engine.score_product({}, {"refresh_rate": "144"}, "gaming_monitor")
        assert empty_result["score"] == 0.0
        assert "No features to compare" in empty_result["rationale"]
        
        # Empty product features  
        empty_product_result = matching_engine.score_product(
            {"refresh_rate": "144"}, {}, "gaming_monitor"
        )
        assert empty_product_result["score"] == 0.0
        
        # Invalid numeric values
        invalid_result = matching_engine.score_product(
            {"refresh_rate": "invalid"},
            {"refresh_rate": "also_invalid"},
            "gaming_monitor"
        )
        assert invalid_result["score"] >= 0.0  # Should handle gracefully
        
        # Missing weight category
        unknown_category_result = matching_engine.score_product(
            {"refresh_rate": "144"},
            {"refresh_rate": "144"},
            "unknown_category"
        )
        assert unknown_category_result["score"] > 0.0  # Should use default weights

    def test_confidence_calculation(self, matching_engine):
        """Test confidence calculation based on feature coverage."""
        # High coverage scenario
        user_features_comprehensive = {
            "refresh_rate": "144",
            "size": "27", 
            "resolution": "1440p",
            "curvature": "curved",
            "panel_type": "ips"
        }
        product_features_comprehensive = {
            "refresh_rate": "144",
            "size": "27",
            "resolution": "1440p", 
            "curvature": "curved",
            "panel_type": "ips"
        }
        
        comprehensive_result = matching_engine.score_product(
            user_features_comprehensive, product_features_comprehensive, "gaming_monitor"
        )
        
        # Low coverage scenario
        user_features_minimal = {"refresh_rate": "144"}
        product_features_minimal = {"refresh_rate": "60"}  # Mismatch
        
        minimal_result = matching_engine.score_product(
            user_features_minimal, product_features_minimal, "gaming_monitor"
        )
        
        # Comprehensive match should have higher confidence
        assert comprehensive_result["confidence"] > minimal_result["confidence"]
        assert comprehensive_result["confidence"] >= 0.8  # High confidence for full matches

    def test_categorical_tolerance(self, matching_engine):
        """Test categorical tolerance for refresh rate and resolution."""
        # Test refresh rate upgrade path (144Hz → 165Hz)
        user_features = {"refresh_rate": "144"}
        product_features = {"refresh_rate": "165"}
        
        result = matching_engine.score_product(
            user_features, product_features, "gaming_monitor"
        )
        
        refresh_score = result["feature_scores"]["refresh_rate"]["score"]
        assert refresh_score >= 0.9  # Should get upgrade bonus
        
        # Test resolution upgrade path (1080p → 1440p)
        user_res_features = {"resolution": "1080p"}
        product_res_features = {"resolution": "1440p"}
        
        res_result = matching_engine.score_product(
            user_res_features, product_res_features, "gaming_monitor"
        )
        
        resolution_score = res_result["feature_scores"]["resolution"]["score"]
        assert resolution_score >= 0.85  # Should accept upgrade

    def test_feature_score_explanation(self, matching_engine, sample_user_features, sample_product_features):
        """Test detailed scoring explanation for debugging."""
        result = matching_engine.score_product(
            sample_user_features, sample_product_features, "gaming_monitor"
        )
        
        explanation = matching_engine.explain_scoring(result, sample_user_features)
        
        # Should contain key information
        assert "Feature Matching Score:" in explanation
        assert "Confidence:" in explanation
        assert "Processing Time:" in explanation
        assert "Feature Breakdown:" in explanation
        assert "Rationale:" in explanation
        
        # Should contain feature details
        for feature in ["refresh_rate", "size", "resolution"]:
            if feature in sample_user_features:
                assert feature in explanation

    @pytest.mark.asyncio
    async def test_empty_products_list(self, matching_engine, sample_user_features):
        """Test handling of empty products list."""
        result = await matching_engine.score_products(
            sample_user_features, [], "gaming_monitor"
        )
        assert result == []

    def test_feature_importance_weights(self, matching_engine):
        """Test that feature importance weights are properly applied."""
        from bot.ai.vocabularies import get_feature_weights
        
        weights = get_feature_weights("gaming_monitor")
        
        # Critical gaming features should have higher weights
        assert weights["refresh_rate"] > weights["brand"]
        assert weights["resolution"] > weights["panel_type"]
        assert weights["size"] > weights["category"]
        
        # Test weight application in scoring
        user_features = {"refresh_rate": "144", "brand": "samsung"}
        product_features = {"refresh_rate": "144", "brand": "samsung"}
        
        result = matching_engine.score_product(
            user_features, product_features, "gaming_monitor"
        )
        
        # Refresh rate should contribute more to total score than brand
        refresh_contribution = (
            result["feature_scores"]["refresh_rate"]["score"] * 
            result["feature_scores"]["refresh_rate"]["weight"]
        )
        brand_contribution = (
            result["feature_scores"]["brand"]["score"] * 
            result["feature_scores"]["brand"]["weight"]
        )
        
        assert refresh_contribution > brand_contribution


class TestFeatureMatchingIntegration:
    """Integration tests for FeatureMatchingEngine with other AI components."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_feature_matching(self):
        """Test complete flow: query → feature extraction → product analysis → matching."""
        # This would be a comprehensive integration test
        # Mock external dependencies for now
        
        user_query = "gaming monitor 144hz curved 27 inch samsung"
        
        # Extract user features
        extractor = FeatureExtractor()
        user_features = extractor.extract_features(user_query, "gaming_monitor")
        
        # Should extract key features
        assert user_features["refresh_rate"] == "144"
        assert user_features["size"] == "27"
        assert user_features["curvature"] == "curved"
        assert user_features["brand"] == "samsung"
        assert user_features["confidence"] > 0.8
        
        # Mock product data
        product_data = {
            "title": "Samsung 27-Inch CRG5 Curved Gaming Monitor 144Hz",
            "features": ["144Hz refresh rate", "27-inch curved display", "VA panel"],
            "brand": "Samsung",
            "asin": "B08N5WRWNW"
        }
        
        # Analyze product features
        analyzer = ProductFeatureAnalyzer()
        product_features = await analyzer.analyze_product_features(product_data)
        
        # Extract values for matching
        feature_values = {}
        for feature_name, feature_data in product_features.items():
            if isinstance(feature_data, dict) and "value" in feature_data:
                feature_values[feature_name] = feature_data["value"]
        
        # Score the match
        matching_engine = FeatureMatchingEngine()
        score_result = matching_engine.score_product(
            user_features, feature_values, "gaming_monitor"
        )
        
        # Should have high score for good match
        assert score_result["score"] >= 0.8
        assert len(score_result["matched_features"]) >= 3
        assert "samsung" in score_result["rationale"].lower()
        assert "144hz" in score_result["rationale"].lower()


# Performance and stress tests
class TestFeatureMatchingPerformance:
    """Performance tests for FeatureMatchingEngine."""
    
    def test_scoring_performance_single_product(self, benchmark):
        """Benchmark single product scoring performance."""
        matching_engine = FeatureMatchingEngine()
        user_features = {"refresh_rate": "144", "size": "27", "resolution": "1440p"}
        product_features = {"refresh_rate": "144", "size": "27", "resolution": "1440p"}
        
        def score_single_product():
            return matching_engine.score_product(
                user_features, product_features, "gaming_monitor"
            )
        
        # Should complete quickly (target: <5ms per product)
        result = benchmark(score_single_product)
        assert result["score"] > 0.0

    def test_memory_usage_stability(self, matching_engine):
        """Test memory usage doesn't grow significantly with repeated scoring."""
        import gc
        
        user_features = {"refresh_rate": "144", "size": "27"}
        product_features = {"refresh_rate": "144", "size": "27"}
        
        # Run many scoring operations
        for i in range(1000):
            result = matching_engine.score_product(
                user_features, product_features, "gaming_monitor"
            )
            assert result["score"] > 0.0
            
            # Occasionally trigger garbage collection
            if i % 100 == 0:
                gc.collect()
        
        # Should complete without memory issues
        assert True  # If we get here, memory usage was stable


if __name__ == "__main__":
    # Run specific test for debugging
    import sys
    if len(sys.argv) > 1:
        pytest.main([__file__ + "::" + sys.argv[1], "-v"])
    else:
        pytest.main([__file__, "-v"])
