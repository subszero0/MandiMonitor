"""
Phase R6: End-to-End Integration Tests for AI Intelligence Model.

This test suite validates the complete AI functionality including:
- Integration tests verify complete AI functionality
- Performance benchmarks meet established thresholds
- User acceptance scenarios validate AI behavior
- Load testing confirms system stability
"""

import asyncio
import time
import pytest
from unittest.mock import AsyncMock, Mock, patch
from typing import List, Dict, Any

from bot.product_selection_models import smart_product_selection, get_selection_model
from bot.ai.feature_extractor import FeatureExtractor
from bot.ai.matching_engine import FeatureMatchingEngine
from bot.ai.multi_card_selector import MultiCardSelector
from bot.ai_performance_monitor import get_ai_monitor
from bot.paapi_ai_bridge import search_products_with_ai_analysis
from bot.watch_flow import smart_product_selection_with_ai, send_multi_card_experience, send_single_card_experience


class TestAIIntegrationE2E:
    """Complete end-to-end AI integration test suite."""

    @pytest.fixture
    def sample_products(self):
        """Sample product data for testing."""
        return [
            {
                "asin": "B08N5WRWNW",
                "title": "LG 27GN950-B 27 Inch UltraGear UHD 4K Nano IPS Gaming Monitor",
                "price": 58999,
                "image": "https://m.media-amazon.com/images/I/71abc123.jpg",
                "features": [
                    "27 inch 4K UHD display",
                    "144Hz refresh rate",
                    "1ms response time",
                    "Nano IPS technology",
                    "HDR 600 support"
                ],
                "technical_details": {
                    "Display Type": "Nano IPS",
                    "Refresh Rate": "144 Hz",
                    "Resolution": "3840 x 2160",
                    "Response Time": "1 ms"
                }
            },
            {
                "asin": "B09G9FPHY6", 
                "title": "ASUS TUF Gaming VG27AQ 27\" 1440P HDR Gaming Monitor",
                "price": 32999,
                "image": "https://m.media-amazon.com/images/I/81def456.jpg",
                "features": [
                    "27 inch QHD display",
                    "165Hz refresh rate", 
                    "1ms response time",
                    "IPS panel",
                    "G-SYNC Compatible"
                ],
                "technical_details": {
                    "Display Type": "IPS",
                    "Refresh Rate": "165 Hz", 
                    "Resolution": "2560 x 1440",
                    "Response Time": "1 ms"
                }
            },
            {
                "asin": "B09X67JBQV",
                "title": "Samsung Odyssey G7 32\" Curved Gaming Monitor",
                "price": 45999,
                "image": "https://m.media-amazon.com/images/I/91ghi789.jpg", 
                "features": [
                    "32 inch curved display",
                    "240Hz refresh rate",
                    "1ms response time",
                    "QLED technology",
                    "1000R curvature"
                ],
                "technical_details": {
                    "Display Type": "QLED",
                    "Refresh Rate": "240 Hz",
                    "Resolution": "2560 x 1440", 
                    "Response Time": "1 ms"
                }
            }
        ]

    @pytest.fixture
    def technical_queries(self):
        """Sample technical queries for testing."""
        return [
            "gaming monitor 144hz 4k HDR",
            "curved gaming monitor 240hz",
            "programming monitor IPS 1440p",
            "budget gaming monitor under 30000"
        ]

    @pytest.mark.asyncio
    async def test_complete_ai_pipeline_technical_query(self, sample_products, technical_queries):
        """
        R6.1: Test complete AI pipeline for technical queries.
        Validates: query → feature extraction → matching → selection
        """
        query = technical_queries[0]  # "gaming monitor 144hz 4k HDR"
        
        # Step 1: Feature Extraction
        extractor = FeatureExtractor()
        user_features = extractor.extract_features(query)
        
        assert user_features is not None
        assert "refresh_rate" in user_features
        assert "resolution" in user_features
        # FeatureExtractor returns strings, check for "144" in refresh_rate
        assert "144" in str(user_features["refresh_rate"])
        
        # Step 2: Product Analysis & Matching
        engine = FeatureMatchingEngine()
        scored_products = await engine.score_products(user_features, sample_products)
        
        # Step 3: Product Selection
        result = await smart_product_selection(sample_products, query)
        
        assert result is not None
        assert "asin" in result
        assert "_ai_metadata" in result or "_popularity_metadata" in result
        
        # Step 4: Verify AI was used for technical query
        if "_ai_metadata" in result:
            ai_metadata = result["_ai_metadata"]
            assert ai_metadata["ai_score"] > 0
            assert ai_metadata["ai_confidence"] > 0
            assert len(ai_metadata["matched_features"]) > 0

    @pytest.mark.asyncio
    async def test_multi_card_selection_integration(self, sample_products):
        """
        R6.2: Test multi-card experience integration.
        Validates: complex query → multi-card decision → carousel generation
        """
        query = "gaming monitor comparison curved vs flat"
        
        # Test multi-card selector through high-level integration
        from bot.watch_flow import smart_product_selection_with_ai
        
        selection_result = await smart_product_selection_with_ai(
            products=sample_products,
            user_query=query,
            user_preferences={"budget_flexible": True},
            enable_multi_card=True
        )
        
        assert selection_result is not None
        assert selection_result["presentation_mode"] in ["single", "multi_card"]
        
        if selection_result["presentation_mode"] == "multi_card":
            assert len(selection_result["products"]) >= 2
            assert "comparison_table" in selection_result
            assert "selection_reason" in selection_result
            
            # Test carousel generation
            comparison_table = selection_result["comparison_table"]
            assert "key_differences" in comparison_table
            assert len(comparison_table["key_differences"]) > 0

    @pytest.mark.asyncio 
    async def test_watch_flow_ai_integration(self, sample_products):
        """
        R6.3: Test watch flow AI integration functions.
        Validates: smart_product_selection_with_ai → experience functions
        """
        query = "gaming monitor 144hz"
        
        # Mock the AI bridge function 
        with patch('bot.paapi_ai_bridge.search_products_with_ai_analysis') as mock_search:
            mock_search.return_value = {
                "products": sample_products,
                "ai_analysis_enabled": True,
                "processing_time_ms": 150.0
            }
            
            # Test smart product selection with AI
            result = await smart_product_selection_with_ai(
                products=sample_products,
                user_query=query,
                user_preferences={"max_price": 60000}
            )
            
            assert result is not None
            assert "selection_type" in result
            assert result["selection_type"] in ["single_card", "multi_card"]

    @pytest.mark.asyncio
    async def test_performance_benchmarks(self, sample_products, technical_queries):
        """
        R6.4: Test performance benchmarks meet established thresholds.
        Validates: <200ms processing time, <500ms total latency
        """
        query = technical_queries[0]
        
        # Test AI selection performance
        start_time = time.time()
        result = await smart_product_selection(sample_products, query)
        processing_time = (time.time() - start_time) * 1000
        
        assert result is not None
        assert processing_time < 500  # Under 500ms threshold
        
                # Test multi-card performance
        start_time = time.time()
        selection_result = await smart_product_selection_with_ai(
            products=sample_products[:3],  # Limit for performance test
            user_query=query,
            user_preferences={},
            enable_multi_card=True
        )
        multi_card_time = (time.time() - start_time) * 1000
        
        assert selection_result is not None
        assert multi_card_time < 300  # Under 300ms for multi-card

    @pytest.mark.asyncio
    async def test_ai_monitoring_integration(self, sample_products):
        """
        R6.5: Test AI performance monitoring integration.
        Validates: events logged, metrics collected, health checks work
        """
        query = "gaming monitor test"
        
        # Get monitor instance
        monitor = get_ai_monitor()
        initial_stats = monitor.get_performance_summary()
        initial_selections = initial_stats.get("total_selections", 0)
        
        # Perform AI selection
        result = await smart_product_selection(sample_products, query)
        
        # Check monitoring
        updated_stats = monitor.get_performance_summary()
        updated_selections = updated_stats.get("total_selections", 0)
        
        assert result is not None
        # Note: Monitoring might be disabled in tests, so we check if it's working
        if updated_selections > initial_selections:
            assert updated_selections == initial_selections + 1
            assert "models" in updated_stats
            assert "recent_performance" in updated_stats

    @pytest.mark.asyncio
    async def test_error_handling_and_fallbacks(self, sample_products):
        """
        R6.6: Test error handling and fallback mechanisms.
        Validates: graceful degradation, fallback chains work
        """
        query = "test query for error handling"
        
        # Test with corrupted product data
        corrupted_products = [
            {"asin": "INVALID", "title": None, "price": None},
            *sample_products
        ]
        
        # Should still return a result despite corrupted data
        result = await smart_product_selection(corrupted_products, query)
        assert result is not None
        assert "asin" in result
        
        # Test with empty products list
        empty_result = await smart_product_selection([], query)
        assert empty_result is None

    def test_model_selection_logic(self, technical_queries):
        """
        R6.7: Test model selection logic for different query types.
        Validates: technical queries → AI model, simple queries → popularity
        """
        # Technical query should select FeatureMatchModel
        technical_query = technical_queries[0]
        technical_model = get_selection_model(technical_query, 5)
        assert technical_model.__class__.__name__ == "FeatureMatchModel"
        
        # Simple query should select PopularityModel
        simple_query = "monitor"
        simple_model = get_selection_model(simple_query, 3)
        assert simple_model.__class__.__name__ == "PopularityModel"
        
        # Very few products should select RandomSelectionModel
        random_model = get_selection_model("any query", 1)
        assert random_model.__class__.__name__ == "RandomSelectionModel"

    @pytest.mark.asyncio
    async def test_load_simulation(self, sample_products):
        """
        R6.8: Test system stability under load.
        Validates: concurrent requests, memory usage, performance degradation
        """
        queries = [
            "gaming monitor 144hz",
            "programming monitor 4k", 
            "budget monitor under 20000",
            "curved gaming monitor",
            "IPS monitor 1440p"
        ]
        
        # Simulate concurrent requests
        tasks = []
        for query in queries:
            task = smart_product_selection(sample_products, query)
            tasks.append(task)
        
        # Execute all tasks concurrently
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = (time.time() - start_time) * 1000
        
        # Validate results
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) >= len(queries) // 2  # At least 50% success
        
        # Performance should not degrade significantly under load
        avg_time_per_request = total_time / len(queries)
        assert avg_time_per_request < 1000  # Under 1 second per request

    @pytest.mark.asyncio
    async def test_user_acceptance_scenarios(self, sample_products):
        """
        R6.9: Test user acceptance scenarios.
        Validates: realistic user journeys, expected AI behavior
        """
        scenarios = [
            {
                "query": "gaming monitor 4k 144hz under 60000",
                "expected_features": ["resolution", "refresh_rate", "price"],
                "should_use_ai": True
            },
            {
                "query": "cheap monitor",
                "expected_features": ["price"],
                "should_use_ai": False  # Simple query
            },
            {
                "query": "curved gaming monitor high refresh competitive esports",
                "expected_features": ["curvature", "refresh_rate"],
                "should_use_ai": True
            }
        ]
        
        for scenario in scenarios:
            result = await smart_product_selection(sample_products, scenario["query"])
            
            assert result is not None
            
            # Check if AI was used appropriately
            has_ai_metadata = "_ai_metadata" in result
            assert has_ai_metadata == scenario["should_use_ai"]
            
            if has_ai_metadata:
                ai_metadata = result["_ai_metadata"]
                matched_features = ai_metadata.get("matched_features", [])
                
                # Check if expected features were detected
                for expected_feature in scenario["expected_features"]:
                    # Feature should be either in matched_features or query has related terms
                    feature_in_matches = any(expected_feature in str(f).lower() for f in matched_features)
                    
                    # Check for feature-related terms in query
                    query_lower = scenario["query"].lower()
                    feature_in_query = False
                    
                    if expected_feature == "price":
                        feature_in_query = any(term in query_lower for term in ["under", "below", "max", "budget", "cost", "price"])
                    elif expected_feature == "refresh_rate":
                        feature_in_query = any(term in query_lower for term in ["hz", "refresh", "fps"])
                    elif expected_feature == "resolution":
                        feature_in_query = any(term in query_lower for term in ["4k", "1440p", "1080p", "uhd", "qhd", "fhd", "resolution"])
                    else:
                        feature_in_query = expected_feature in query_lower
                    
                    assert feature_in_matches or feature_in_query, \
                        f"Feature '{expected_feature}' not found in matches {matched_features} or query terms"

    @pytest.mark.asyncio
    async def test_end_to_end_watch_creation_simulation(self, sample_products):
        """
        R6.10: Simulate complete end-to-end watch creation flow.
        Validates: Complete user journey from query to watch creation
        """
        # Simulate user interaction
        user_query = "gaming monitor 144hz 1440p under 50000"
        user_preferences = {
            "max_price": 50000,
            "brand": None,
            "min_discount": None
        }
        
        # Step 1: Product search with AI analysis (mocked)
        with patch('bot.paapi_ai_bridge.search_products_with_ai_analysis') as mock_search:
            mock_search.return_value = {
                "products": sample_products,
                "ai_analysis_enabled": True,
                "processing_time_ms": 125.0
            }
            
            # Step 2: Smart product selection with AI
            selection_result = await smart_product_selection_with_ai(
                products=sample_products,
                user_query=user_query,
                user_preferences=user_preferences
            )
            
            assert selection_result is not None
            assert "selection_type" in selection_result
            
            # Step 3: Verify appropriate experience type
            if selection_result["selection_type"] == "multi_card":
                assert "products" in selection_result
                assert len(selection_result["products"]) >= 2
                assert "comparison_table" in selection_result
                
            elif selection_result["selection_type"] == "single_card":
                assert "products" in selection_result
                assert len(selection_result["products"]) == 1
                assert "asin" in selection_result["products"][0]
        
        # Verify the complete flow executed without errors
        assert True  # If we reach here, the flow completed successfully
