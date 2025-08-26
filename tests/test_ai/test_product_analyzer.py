"""
Unit tests for ProductFeatureAnalyzer - Phase 2 Implementation.

Tests cover the Phase 2 Definition of Done criteria:
- Extract features from 90% of gaming monitor products
- Field precedence: TechnicalInfo > Specifications > Features > Title
- Confidence scoring accurately reflects extraction reliability
- Feature analysis completes in <200ms per product
- Integration tests with real PA-API responses
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, patch

from bot.ai.product_analyzer import ProductFeatureAnalyzer


class TestProductFeatureAnalyzer:
    """Test suite for ProductFeatureAnalyzer."""
    
    @pytest.fixture
    def analyzer(self):
        """Create a ProductFeatureAnalyzer instance for testing."""
        return ProductFeatureAnalyzer()
    
    @pytest.fixture
    def sample_product_data(self):
        """Sample product data mimicking PA-API response structure."""
        return {
            "asin": "B08N5WRWNW",
            "title": "Samsung 27-Inch CRG5 Curved Gaming Monitor (LC27RG50FQNXZA) – 144Hz Refresh Rate, FHD 1920x1080p, Radeon FreeSync, Black",
            "brand": "Samsung",
            "manufacturer": "Samsung",
            "features": [
                "27-inch curved VA gaming monitor with 1500R curvature",
                "144Hz refresh rate with 4ms (GTG) response time",
                "Full HD 1920x1080 resolution with 16:9 aspect ratio",
                "AMD Radeon FreeSync for seamless gameplay",
                "Multiple connectivity options: HDMI 1.4 x2, DisplayPort"
            ],
            "technical_details": {
                "screen_size": "27 inches",
                "refresh_rate": "144 Hz",
                "resolution": "1920x1080",
                "panel_type": "VA",
                "curvature": "1500R"
            },
            "offers": {"price": 1899900},  # Price in paise
        }
    
    @pytest.fixture  
    def minimal_product_data(self):
        """Minimal product data with only title information."""
        return {
            "asin": "B07DL6L8QX",
            "title": "LG UltraGear 24GN600-B 24 Inch Full HD (1920 x 1080) IPS Gaming Monitor with 144Hz, 1ms Motion Blur Reduction, FreeSync Premium, 99% sRGB, HDR 10, Tilt/Height/Pivot Adjustable Stand, HDMI x2, DP",
            "features": [],
            "technical_details": {}
        }

    @pytest.mark.asyncio
    async def test_comprehensive_feature_extraction(self, analyzer, sample_product_data):
        """Test extraction of all key gaming monitor features from comprehensive data."""
        result = await analyzer.analyze_product_features(sample_product_data)
        
        # Verify all expected features are extracted
        expected_features = ["refresh_rate", "size", "resolution", "curvature", "panel_type"]
        for feature in expected_features:
            assert feature in result, f"Missing feature: {feature}"
            assert "value" in result[feature], f"Missing value for feature: {feature}"
            assert "confidence" in result[feature], f"Missing confidence for feature: {feature}"
            assert "source" in result[feature], f"Missing source for feature: {feature}"
        
        # Verify specific extracted values
        assert result["refresh_rate"]["value"] == "144"
        assert result["size"]["value"] == "27"
        assert result["resolution"]["value"] == "1080p"  # Normalized from 1920x1080
        assert result["curvature"]["value"] == "curved"  # Inferred from curvature data
        assert result["panel_type"]["value"] == "va"
        
        # Verify overall confidence is reasonable
        assert result["overall_confidence"] > 0.7, f"Low overall confidence: {result['overall_confidence']}"
        
        # Verify metadata
        assert "extraction_metadata" in result
        assert result["extraction_metadata"]["asin"] == "B08N5WRWNW"
        # May extract additional features like brand, so check minimum
        assert result["extraction_metadata"]["features_extracted"] >= len(expected_features)

    @pytest.mark.asyncio
    async def test_field_precedence_technical_info_wins(self, analyzer):
        """Test that technical_info has precedence over features and title."""
        conflicting_product_data = {
            "asin": "TEST123",
            "title": "LG 32 inch 60Hz Monitor",  # Conflicting information
            "features": ["27-inch display", "120Hz refresh rate"],  # Different info
            "technical_details": {
                "screen_size": "24 inches",  # This should win
                "refresh_rate": "144 Hz"     # This should win
            }
        }
        
        result = await analyzer.analyze_product_features(conflicting_product_data)
        
        # Technical details should win due to field precedence
        assert result["refresh_rate"]["value"] == "144"
        assert result["refresh_rate"]["source"] == "technical_info"
        assert result["size"]["value"] == "24"
        assert result["size"]["source"] == "technical_info"
        
        # Confidence should be high for technical_info sources
        assert result["refresh_rate"]["confidence"] > 0.9
        assert result["size"]["confidence"] > 0.9

    @pytest.mark.asyncio
    async def test_field_precedence_features_over_title(self, analyzer):
        """Test that features have precedence over title when technical_info is missing."""
        product_data = {
            "asin": "TEST456", 
            "title": "Samsung 32 inch 60Hz Monitor",  # Lower priority
            "features": ["27-inch curved display", "144Hz refresh rate"],  # Should win
            "technical_details": {}  # Empty, so features should win
        }
        
        result = await analyzer.analyze_product_features(product_data)
        
        # Features should win over title
        assert result["refresh_rate"]["value"] == "144"
        assert result["refresh_rate"]["source"] == "features"
        assert result["size"]["value"] == "27"
        assert result["size"]["source"] == "features"
        
        # Confidence should be moderate for features sources
        assert 0.8 <= result["refresh_rate"]["confidence"] <= 0.9
        assert 0.7 <= result["size"]["confidence"] <= 0.9

    @pytest.mark.asyncio 
    async def test_title_only_fallback(self, analyzer, minimal_product_data):
        """Test extraction from title when structured data is unavailable."""
        result = await analyzer.analyze_product_features(minimal_product_data)
        
        # Should extract basic features from title
        expected_from_title = ["size", "resolution", "refresh_rate", "panel_type"]
        extracted_features = [key for key in expected_from_title if key in result]
        
        assert len(extracted_features) >= 3, "Should extract at least 3 features from title"
        
        # All extracted features should have title as source
        for feature in extracted_features:
            if feature in result:
                assert result[feature]["source"] == "title"
                # Title-based confidence should be lower but still reasonable
                assert 0.4 < result[feature]["confidence"] < 0.8

    @pytest.mark.asyncio
    async def test_confidence_scoring_accuracy(self, analyzer, sample_product_data):
        """Test that confidence scoring accurately reflects data source reliability."""
        result = await analyzer.analyze_product_features(sample_product_data)
        
        # Features from technical_info should have highest confidence
        technical_features = [
            f for f, data in result.items() 
            if isinstance(data, dict) and data.get("source") == "technical_info"
        ]
        
        if technical_features:
            technical_confidence = sum(
                result[f]["confidence"] for f in technical_features
            ) / len(technical_features)
            assert technical_confidence > 0.9, "Technical info should have high confidence"
        
        # Features from features should have medium confidence
        feature_features = [
            f for f, data in result.items()
            if isinstance(data, dict) and data.get("source") == "features"
        ]
        
        if feature_features:
            features_confidence = sum(
                result[f]["confidence"] for f in feature_features
            ) / len(feature_features)
            assert 0.7 < features_confidence < 0.9, "Features should have medium confidence"

    @pytest.mark.asyncio
    async def test_feature_normalization(self, analyzer):
        """Test normalization of different feature value formats."""
        test_cases = [
            # Refresh rate normalization
            {
                "technical_details": {"refresh_rate": "144Hz"},
                "expected": {"refresh_rate": "144"}
            },
            {
                "features": ["144 fps gaming"],
                "expected": {"refresh_rate": "144"}
            },
            
            # Size normalization with unit conversion
            {
                "technical_details": {"screen_size": "68.6 cm"},
                "expected": {"size": "27"}  # 68.6 cm ≈ 27 inches
            },
            {
                "features": ["27 inch display"],
                "expected": {"size": "27"}
            },
            
            # Resolution normalization
            {
                "technical_details": {"resolution": "3840x2160"},
                "expected": {"resolution": "4k"}
            },
            {
                "features": ["QHD 1440p resolution"],
                "expected": {"resolution": "1440p"}
            },
            {
                "title": "Full HD 1080p Monitor",
                "expected": {"resolution": "1080p"}
            }
        ]
        
        for case in test_cases:
            product_data = {"asin": "TEST", **case}
            result = await analyzer.analyze_product_features(product_data)
            
            for expected_feature, expected_value in case["expected"].items():
                assert expected_feature in result, f"Missing {expected_feature} for case: {case}"
                assert result[expected_feature]["value"] == expected_value, \
                    f"Wrong {expected_feature} value: expected {expected_value}, got {result[expected_feature]['value']}"

    @pytest.mark.asyncio
    async def test_feature_validation(self, analyzer):
        """Test validation of extracted feature values against known ranges."""
        invalid_data = {
            "asin": "INVALID",
            "features": [
                "5000Hz refresh rate",   # Invalid: too high
                "5 inch monitor",        # Invalid: too small
                "85 inch gaming monitor" # Invalid: too large for gaming
            ]
        }
        
        result = await analyzer.analyze_product_features(invalid_data)
        
        # Invalid values should be filtered out
        if "refresh_rate" in result:
            rate = int(result["refresh_rate"]["value"])
            assert 30 <= rate <= 480, "Refresh rate should be within valid range"
        
        if "size" in result:
            size = float(result["size"]["value"])
            assert 10.0 <= size <= 65.0, "Size should be within valid range"

    @pytest.mark.asyncio
    async def test_performance_requirements(self, analyzer, sample_product_data):
        """Test that feature analysis completes within performance requirements."""
        # Test individual product analysis (should be <200ms)
        start_time = time.time()
        result = await analyzer.analyze_product_features(sample_product_data)
        analysis_time = (time.time() - start_time) * 1000  # Convert to ms
        
        assert analysis_time < 200, f"Analysis too slow: {analysis_time:.1f}ms (should be <200ms)"
        assert result is not None, "Analysis should return valid result"
        
        # Test batch processing performance
        batch_products = [sample_product_data] * 10  # 10 identical products
        start_time = time.time()
        
        tasks = [analyzer.analyze_product_features(product) for product in batch_products]
        results = await asyncio.gather(*tasks)
        
        batch_time = (time.time() - start_time) * 1000
        avg_time_per_product = batch_time / len(batch_products)
        
        assert avg_time_per_product < 200, f"Batch avg too slow: {avg_time_per_product:.1f}ms"
        assert len(results) == 10, "All products should be processed"
        assert all(r is not None for r in results), "All results should be valid"

    @pytest.mark.asyncio
    async def test_empty_and_invalid_data_handling(self, analyzer):
        """Test graceful handling of empty or invalid product data."""
        test_cases = [
            {},  # Empty dict
            {"asin": "EMPTY"},  # Only ASIN
            {"asin": "NULL", "title": None, "features": None},  # Null values
            {"asin": "MALFORMED", "technical_details": "invalid json"},  # Malformed data
        ]
        
        for case in test_cases:
            result = await analyzer.analyze_product_features(case)
            
            # Should not crash and return valid structure
            assert isinstance(result, dict), "Should return dict even for invalid input"
            assert "overall_confidence" in result, "Should include overall confidence"
            assert "extraction_metadata" in result, "Should include metadata"
            
            # Confidence should be low for empty/invalid data
            if len(result) <= 2:  # Only metadata fields
                assert result["overall_confidence"] < 0.3, "Should have low confidence for empty data"

    @pytest.mark.asyncio
    async def test_brand_extraction_accuracy(self, analyzer):
        """Test accurate brand extraction from various sources."""
        brand_test_cases = [
            {
                "brand": "Samsung",
                "title": "Samsung Monitor",
                "expected": "samsung"
            },
            {
                "manufacturer": "LG Electronics",
                "title": "LG UltraGear Gaming Monitor", 
                "expected": "lg"
            },
            {
                "title": "ASUS ROG Swift Gaming Monitor",
                "features": ["ASUS design"],
                "expected": "asus"
            }
        ]
        
        for case in brand_test_cases:
            product_data = {"asin": "BRAND_TEST", **case}
            result = await analyzer.analyze_product_features(product_data)
            
            if "brand" in result:
                assert result["brand"]["value"] == case["expected"], \
                    f"Wrong brand extracted: expected {case['expected']}, got {result['brand']['value']}"

    @pytest.mark.asyncio
    async def test_overall_confidence_calculation(self, analyzer):
        """Test overall confidence calculation logic."""
        # High confidence scenario: mostly technical_info
        high_confidence_data = {
            "asin": "HIGH_CONF",
            "technical_details": {
                "screen_size": "27 inches",
                "refresh_rate": "144 Hz",
                "resolution": "1920x1080"
            }
        }
        
        result_high = await analyzer.analyze_product_features(high_confidence_data)
        
        # Low confidence scenario: title only
        low_confidence_data = {
            "asin": "LOW_CONF", 
            "title": "Some monitor with unclear specs"
        }
        
        result_low = await analyzer.analyze_product_features(low_confidence_data)
        
        # High confidence should be significantly higher
        assert result_high["overall_confidence"] > result_low["overall_confidence"] + 0.2, \
            "Technical info should yield higher confidence than title-only"


class TestProductAnalyzerIntegration:
    """Integration tests for ProductFeatureAnalyzer with PA-API-like data."""
    
    @pytest.fixture
    def analyzer(self):
        return ProductFeatureAnalyzer()
    
    @pytest.mark.asyncio
    async def test_paapi_response_structure_compatibility(self, analyzer):
        """Test compatibility with actual PA-API response structure."""
        # Simulate actual PA-API response structure from paapi_official.py
        paapi_response = {
            "asin": "B08N5WRWNW",
            "title": "Samsung 27-Inch CRG5 Curved Gaming Monitor - 144Hz, FHD, Black",
            "brand": "Samsung",
            "manufacturer": "Samsung",
            "features": [
                "27-inch curved VA gaming monitor with 1500R curvature for immersive gaming",
                "144Hz refresh rate and 4ms response time eliminate lag and motion blur",
                "Full HD 1920x1080 resolution delivers crisp, detailed images"
            ],
            "technical_details": {},  # Often empty in real responses
            "offers": {
                "price": 1899900,
                "availability": "In Stock"
            },
            "reviews": {
                "rating": 4.3,
                "count": 1247
            }
        }
        
        result = await analyzer.analyze_product_features(paapi_response)
        
        # Should extract key features even from features list
        assert "refresh_rate" in result
        assert "size" in result
        assert result["refresh_rate"]["value"] == "144"
        assert result["size"]["value"] == "27"
        
        # Should handle missing technical_details gracefully
        assert result["overall_confidence"] > 0.5, "Should maintain reasonable confidence"

    @pytest.mark.asyncio
    async def test_golden_asin_dataset_processing(self, analyzer):
        """Test processing of golden ASIN dataset for regression testing."""
        # Golden ASIN dataset with known specifications
        golden_asins = [
            {
                "asin": "B08N5WRWNW", 
                "title": "Samsung 27-Inch CRG5 Curved Gaming Monitor - 144Hz Refresh Rate, FHD 1920x1080p",
                "features": ["27-inch curved display", "144Hz refresh rate", "1920x1080 resolution"],
                "verified_specs": {"refresh_rate": "144", "size": "27", "resolution": "1080p", "curvature": "curved"}
            },
            {
                "asin": "B07DL6L8QX",
                "title": "LG UltraGear 24GN600-B 24 Inch Full HD IPS Gaming Monitor with 144Hz",
                "features": ["24-inch IPS display", "144Hz refresh rate", "Full HD resolution"],
                "verified_specs": {"refresh_rate": "144", "size": "24", "resolution": "1080p", "panel_type": "ips"}
            }
        ]
        
        accuracy_scores = []
        
        for golden_asin in golden_asins:
            result = await analyzer.analyze_product_features(golden_asin)
            verified_specs = golden_asin["verified_specs"]
            
            # Calculate accuracy for this ASIN
            correct_extractions = 0
            total_verifiable = len(verified_specs)
            
            for feature, expected_value in verified_specs.items():
                if feature in result and result[feature]["value"] == expected_value:
                    correct_extractions += 1
            
            accuracy = correct_extractions / total_verifiable if total_verifiable > 0 else 0
            accuracy_scores.append(accuracy)
            
            # Each ASIN should have >80% accuracy
            assert accuracy >= 0.8, f"Low accuracy for {golden_asin['asin']}: {accuracy:.2%}"
        
        # Overall accuracy should be >90%
        overall_accuracy = sum(accuracy_scores) / len(accuracy_scores)
        assert overall_accuracy >= 0.9, f"Overall accuracy too low: {overall_accuracy:.2%}"


# Performance benchmarking (run separately if needed)
class TestProductAnalyzerPerformance:
    """Performance tests for ProductFeatureAnalyzer."""
    
    @pytest.fixture
    def analyzer(self):
        return ProductFeatureAnalyzer()
    
    @pytest.mark.asyncio
    async def test_concurrent_analysis_performance(self, analyzer):
        """Test concurrent analysis of multiple products."""
        sample_products = [
            {
                "asin": f"TEST{i}",
                "title": f"Gaming Monitor {i} 27-inch 144Hz QHD",
                "features": [f"27-inch display {i}", "144Hz refresh rate", "QHD resolution"]
            }
            for i in range(20)  # 20 concurrent analyses
        ]
        
        start_time = time.time()
        
        # Run concurrent analysis
        tasks = [analyzer.analyze_product_features(product) for product in sample_products]
        results = await asyncio.gather(*tasks)
        
        total_time = (time.time() - start_time) * 1000
        avg_time = total_time / len(sample_products)
        
        assert avg_time < 200, f"Concurrent avg time too slow: {avg_time:.1f}ms"
        assert len(results) == 20, "All analyses should complete"
        assert all(r["overall_confidence"] > 0 for r in results), "All should have valid confidence"
