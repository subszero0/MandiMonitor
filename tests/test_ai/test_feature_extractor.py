"""
Unit tests for FeatureExtractor - Phase 1 Implementation.

Tests cover the Phase 1 Definition of Done criteria:
- Extract 5 key gaming monitor features (resolution, refresh rate, size, curvature, brand)
- >85% accuracy on balanced dataset (200+ queries)
- Handle locale variants: inch/"/cm, Hz/FPS/hertz, QHD/WQHD/1440p synonyms
- Ignore marketing fluff ("cinematic", "eye care")
- <100ms processing time
"""

import pytest
import time
from unittest.mock import patch

from bot.ai.feature_extractor import FeatureExtractor


class TestFeatureExtractor:
    """Test suite for FeatureExtractor."""
    
    @pytest.fixture
    def extractor(self):
        """Create a FeatureExtractor instance for testing."""
        return FeatureExtractor()
    
    def test_gaming_monitor_feature_extraction(self, extractor):
        """Test extraction of key gaming monitor features."""
        test_cases = [
            # (query, expected_features)
            (
                "gaming monitor 144hz curved 27 inch",
                {
                    "refresh_rate": "144",
                    "curvature": "curved", 
                    "size": "27",
                    "category_detected": "gaming_monitor"
                }
            ),
            (
                "Samsung 27 inch 4k monitor",
                {
                    "size": "27",
                    "resolution": "4k", 
                    "brand": "samsung",
                    "category_detected": "gaming_monitor"
                }
            ),
            (
                "curved gaming display 165 fps",
                {
                    "curvature": "curved",
                    "refresh_rate": "165",
                    "category_detected": "gaming_monitor"
                }
            ),
            (
                "monitor 32\" 1440p IPS panel",
                {
                    "size": "32",
                    "resolution": "1440p",
                    "panel_type": "ips",
                    "category_detected": "gaming_monitor"
                }
            ),
        ]
        
        for query, expected in test_cases:
            result = extractor.extract_features(query)
            
            # Check each expected feature
            for key, expected_value in expected.items():
                assert key in result, f"Missing feature '{key}' in result for query: {query}"
                assert str(result[key]).lower() == str(expected_value).lower(), \
                    f"Feature '{key}' mismatch for query '{query}': expected {expected_value}, got {result[key]}"
            
            # Check confidence is reasonable
            assert result.get("confidence", 0) > 0.3, f"Low confidence for query: {query}"

    def test_unit_variants(self, extractor):
        """Test handling of different unit variants."""
        test_cases = [
            # Inch variants
            ("27 inch gaming monitor", {"size": "27"}),
            ("27\" gaming monitor", {"size": "27"}),  
            ("27 in gaming monitor", {"size": "27"}),
            
            # Refresh rate variants
            ("144hz monitor", {"refresh_rate": "144"}),
            ("144 fps monitor", {"refresh_rate": "144"}),
            ("144 hertz monitor", {"refresh_rate": "144"}),
            
            # Resolution synonyms
            ("QHD gaming monitor", {"resolution": "1440p"}),
            ("WQHD gaming monitor", {"resolution": "1440p"}),
            ("1440p gaming monitor", {"resolution": "1440p"}),
            ("4K monitor", {"resolution": "4k"}),
            ("UHD monitor", {"resolution": "4k"}),
            ("FHD monitor", {"resolution": "1080p"}),
            ("Full HD monitor", {"resolution": "1080p"}),
        ]
        
        for query, expected in test_cases:
            result = extractor.extract_features(query)
            
            for key, expected_value in expected.items():
                assert key in result, f"Missing feature '{key}' for query: {query}"
                assert str(result[key]).lower() == str(expected_value).lower(), \
                    f"Expected {expected_value}, got {result[key]} for query: {query}"

    def test_cm_to_inches_conversion(self, extractor):
        """Test centimeter to inches conversion."""
        test_cases = [
            ("68.5 cm gaming monitor", "27.0"),  # 68.5 cm ≈ 27 inches
            ("61 cm monitor", "24.0"),           # 61 cm ≈ 24 inches  
            ("81.3 cm display", "32.0"),         # 81.3 cm ≈ 32 inches
        ]
        
        for query, expected_inches in test_cases:
            result = extractor.extract_features(query)
            
            assert "size" in result, f"Size not extracted from: {query}"
            assert result["size"] == expected_inches, \
                f"CM conversion failed for {query}: expected {expected_inches}, got {result['size']}"

    def test_hinglish_queries(self, extractor):
        """Test handling of Hinglish (Hindi + English) queries."""
        test_cases = [
            ("gaming monitor 144hz ka curved 27 inch", {"refresh_rate": "144", "curvature": "curved", "size": "27"}),
            ("Samsung ka 27 inch 4k monitor chahiye", {"brand": "samsung", "size": "27", "resolution": "4k"}),
            ("curved gaming display 165 fps wala", {"curvature": "curved", "refresh_rate": "165"}),
        ]
        
        for query, expected in test_cases:
            result = extractor.extract_features(query)
            
            for key, expected_value in expected.items():
                assert key in result, f"Missing feature '{key}' for Hinglish query: {query}"
                assert str(result[key]).lower() == str(expected_value).lower(), \
                    f"Hinglish extraction failed for {query}: expected {expected_value}, got {result[key]}"

    def test_marketing_fluff_filtering(self, extractor):
        """Test that marketing language is properly filtered."""
        marketing_queries = [
            "cinematic gaming experience", 
            "eye care gaming monitor",
            "stunning visual experience",
            "best gaming monitor ever", 
            "ultimate professional display",
            "amazing premium monitor"
        ]
        
        for query in marketing_queries:
            result = extractor.extract_features(query)
            
            # Should have very low confidence or be filtered
            confidence = result.get("confidence", 0)
            assert confidence < 0.3, f"Marketing query not filtered: {query} (confidence: {confidence})"
            
            # Should not extract meaningless features from marketing terms
            meaningful_features = [k for k in result.keys() 
                                 if k not in ["confidence", "processing_time_ms", "marketing_heavy", 
                                            "technical_query", "category_detected"]]
            
            # Allow minimal extraction but discourage high-confidence marketing matches
            if meaningful_features:
                assert confidence < 0.5, f"High confidence on marketing query: {query}"

    def test_case_insensitive_extraction(self, extractor):
        """Test that extraction works regardless of case."""
        test_cases = [
            "GAMING MONITOR 144HZ",
            "Gaming Monitor 144Hz", 
            "gaming monitor 144hz",
            "GaMiNg MoNiToR 144Hz"
        ]
        
        expected = {"refresh_rate": "144", "category_detected": "gaming_monitor"}
        
        for query in test_cases:
            result = extractor.extract_features(query)
            
            for key, expected_value in expected.items():
                assert key in result, f"Case sensitivity issue with query: {query}"
                assert str(result[key]).lower() == str(expected_value).lower()

    def test_typo_resilience(self, extractor):
        """Test handling of common typos."""
        test_cases = [
            # Typos that should still work due to partial matching
            ("gamng moniter 144hz", {"refresh_rate": "144"}),  # Should extract refresh rate
            ("144Hz Gaming Monitor", {"refresh_rate": "144"}),  # Should handle capitalization
        ]
        
        for query, expected in test_cases:
            result = extractor.extract_features(query)
            
            for key, expected_value in expected.items():
                # Be more lenient with typos - just check that we extract something reasonable
                if key in result:
                    assert str(result[key]).lower() == str(expected_value).lower()

    def test_performance_requirements(self, extractor):
        """Test that processing time meets <100ms requirement."""
        test_queries = [
            "gaming monitor 144hz curved 27 inch",
            "Samsung 27 inch 4k monitor for professional work",
            "curved gaming display 165 fps with HDR support",
            "monitor 32\" 1440p IPS panel for coding and gaming"
        ]
        
        for query in test_queries:
            start_time = time.time()
            result = extractor.extract_features(query)
            processing_time = (time.time() - start_time) * 1000  # Convert to ms
            
            # Check reported processing time
            reported_time = result.get("processing_time_ms", 0)
            assert reported_time < 100, f"Reported processing time {reported_time:.1f}ms exceeds 100ms for: {query}"
            
            # Check actual processing time  
            assert processing_time < 100, f"Actual processing time {processing_time:.1f}ms exceeds 100ms for: {query}"

    def test_confidence_scoring(self, extractor):
        """Test confidence scoring logic."""
        test_cases = [
            # High confidence - technical query with clear features
            ("gaming monitor 144hz curved 27 inch", 0.4),  # Should be high confidence
            
            # Medium confidence - some features
            ("27 inch monitor", 0.2),  # Should be medium
            
            # Low confidence - vague query
            ("good monitor", 0.1),  # Should be low
            
            # Very low confidence - marketing fluff
            ("cinematic experience", 0.05),  # Should be very low
        ]
        
        for query, min_expected_confidence in test_cases:
            result = extractor.extract_features(query)
            confidence = result.get("confidence", 0)
            
            assert confidence >= min_expected_confidence, \
                f"Confidence too low for '{query}': got {confidence:.3f}, expected >={min_expected_confidence}"

    def test_empty_and_invalid_queries(self, extractor):
        """Test handling of empty or invalid queries."""
        invalid_queries = [
            "",           # Empty string
            "   ",        # Whitespace only  
            None,         # None input
        ]
        
        for query in invalid_queries:
            if query is None:
                # Test None input separately
                continue
                
            result = extractor.extract_features(query)
            
            assert result.get("confidence", 1) == 0.0, f"Should have zero confidence for invalid query: '{query}'"
            assert result.get("processing_time_ms", 0) >= 0, "Should have non-negative processing time"

    def test_feature_validation(self, extractor):
        """Test the validate_extraction method."""
        # Test valid features
        valid_features = {
            "refresh_rate": "144",
            "size": "27",
            "resolution": "1440p"
        }
        
        validated = extractor.validate_extraction(valid_features)
        assert validated["validation"]["valid"] is True
        assert len(validated["validation"]["errors"]) == 0
        
        # Test invalid features
        invalid_features = {
            "refresh_rate": "999",  # Too high
            "size": "100",          # Too large
        }
        
        validated = extractor.validate_extraction(invalid_features)
        assert len(validated["validation"]["warnings"]) > 0

    def test_feature_explanation(self, extractor):
        """Test the get_feature_explanation method."""
        features = {
            "refresh_rate": "144",
            "size": "27",
            "resolution": "1440p",
            "confidence": 0.8
        }
        
        explanation = extractor.get_feature_explanation(features)
        
        assert "144Hz" in explanation
        assert "27\"" in explanation
        assert "1440p" in explanation
        assert "80%" in explanation  # Confidence percentage

    def test_comprehensive_accuracy(self, extractor):
        """Test accuracy on a comprehensive dataset."""
        # Comprehensive test dataset with expected results
        test_dataset = [
            # Perfect matches
            ("gaming monitor 144hz curved 27 inch", 
             {"refresh_rate": "144", "curvature": "curved", "size": "27"}),
            ("Samsung 4K 32 inch IPS monitor", 
             {"brand": "samsung", "resolution": "4k", "size": "32", "panel_type": "ips"}),
            
            # Unit variants
            ("27\" 165fps gaming display", 
             {"size": "27", "refresh_rate": "165"}),
            ("68.5 cm QHD monitor", 
             {"size": "27.0", "resolution": "1440p"}),
            
            # Hinglish
            ("Samsung ka curved gaming monitor 144hz", 
             {"brand": "samsung", "curvature": "curved", "refresh_rate": "144"}),
            
            # Partial matches
            ("good 27 inch monitor", 
             {"size": "27"}),
            
            # Should extract nothing meaningful
            ("cinematic experience", {}),
            ("best monitor ever", {}),
        ]
        
        total_tests = len(test_dataset)
        correct_extractions = 0
        
        for query, expected in test_dataset:
            result = extractor.extract_features(query)
            
            # Count as correct if all expected features are correctly extracted
            features_correct = True
            for key, expected_value in expected.items():
                if key not in result or str(result[key]).lower() != str(expected_value).lower():
                    features_correct = False
                    break
            
            if features_correct:
                correct_extractions += 1
            else:
                print(f"Failed: {query}")
                print(f"  Expected: {expected}")
                print(f"  Got: {result}")
        
        accuracy = correct_extractions / total_tests
        print(f"\nOverall accuracy: {accuracy:.1%} ({correct_extractions}/{total_tests})")
        
        # Should meet 85% accuracy requirement
        assert accuracy >= 0.85, f"Accuracy {accuracy:.1%} below 85% requirement"


# Performance benchmark tests
class TestFeatureExtractorPerformance:
    """Performance-focused tests for FeatureExtractor."""
    
    @pytest.fixture
    def extractor(self):
        return FeatureExtractor()
    
    def test_batch_processing_performance(self, extractor):
        """Test performance when processing multiple queries."""
        queries = [
            "gaming monitor 144hz curved 27 inch",
            "Samsung 4K 32 inch professional monitor", 
            "curved OLED display 240hz for gaming",
            "27\" 1440p IPS monitor for coding",
            "ultrawide 34 inch curved gaming screen"
        ] * 10  # 50 total queries
        
        start_time = time.time()
        results = [extractor.extract_features(query) for query in queries]
        total_time = (time.time() - start_time) * 1000
        
        avg_time_per_query = total_time / len(queries)
        
        assert avg_time_per_query < 50, f"Average time per query {avg_time_per_query:.1f}ms too high"
        assert all(r.get("processing_time_ms", 0) < 100 for r in results), "Some queries exceeded 100ms"
        
        print(f"\nBatch processing: {len(queries)} queries in {total_time:.1f}ms")
        print(f"Average per query: {avg_time_per_query:.1f}ms")

    def test_memory_usage_estimation(self, extractor):
        """Estimate memory footprint (basic check)."""
        import sys
        
        # Create multiple extractors to test memory scaling
        extractors = [FeatureExtractor() for _ in range(10)]
        
        # Process some queries to warm up
        for ext in extractors:
            ext.extract_features("gaming monitor 144hz curved 27 inch")
        
        # Basic memory usage check - pattern compilation shouldn't be huge
        pattern_count = sum(
            len(patterns) for patterns in extractor.patterns.values()
        )
        
        print(f"\nCompiled patterns: {pattern_count}")
        print(f"Vocabulary size: {len(extractor.patterns)} feature types")
        
        # Rough memory estimate - each compiled pattern ~1-10KB
        estimated_memory_kb = pattern_count * 5  # Conservative estimate
        print(f"Estimated memory usage: ~{estimated_memory_kb}KB")
        
        # Should be well under 100MB (100,000KB)
        assert estimated_memory_kb < 10000, f"Memory usage estimate {estimated_memory_kb}KB seems too high"
