"""Tests for Natural Language Processing Handler functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from bot.nlp_handler import NaturalLanguageHandler


class TestNaturalLanguageHandler:
    """Test cases for NaturalLanguageHandler."""

    @pytest.fixture
    def nlp_handler(self):
        """Create NaturalLanguageHandler instance for testing."""
        return NaturalLanguageHandler()

    @pytest.mark.asyncio
    async def test_parse_product_query_with_intent(self, nlp_handler):
        """Test parsing product query with intent detection."""
        message = "Find Samsung phones under 30k with 20% discount"
        
        result = await nlp_handler.parse_product_query(message)
        
        # Verify basic parsing
        assert result["brand"] == "samsung"
        assert result["max_price"] == 30000
        assert result["min_discount"] == 20
        assert result["keywords"] == message
        
        # Verify NLP enhancements
        assert "intent" in result
        assert "nlp_confidence" in result
        assert "suggestions" in result
        assert "extracted_features" in result
        
        # Verify intent detection
        intent_data = result["intent"]
        assert intent_data["primary_intent"] == "search_product"
        assert intent_data["confidence"] > 0.0

    @pytest.mark.asyncio
    async def test_detect_intent_search_product(self, nlp_handler):
        """Test intent detection for product search."""
        test_cases = [
            ("Find iPhone 13", "search_product"),
            ("Looking for gaming laptop", "search_product"),
            ("Show me wireless headphones", "search_product"),
            ("Need a new phone under 25k", "search_product"),
        ]
        
        for message, expected_intent in test_cases:
            result = await nlp_handler.detect_intent(message)
            assert result["primary_intent"] == expected_intent
            assert result["confidence"] > 0.0

    @pytest.mark.asyncio
    async def test_detect_intent_create_watch(self, nlp_handler):
        """Test intent detection for watch creation."""
        test_cases = [
            ("Watch iPhone deals", "create_watch"),
            ("Alert me for Samsung offers", "create_watch"),
            ("Track MacBook prices", "create_watch"),
            ("Notify when iPhone drops below 50k", "create_watch"),
        ]
        
        for message, expected_intent in test_cases:
            result = await nlp_handler.detect_intent(message)
            assert result["primary_intent"] == expected_intent
            assert result["confidence"] > 0.0

    @pytest.mark.asyncio
    async def test_detect_intent_compare_products(self, nlp_handler):
        """Test intent detection for product comparison."""
        test_cases = [
            ("Compare iPhone vs Samsung", "compare_products"),
            ("Which is better - MacBook or Dell laptop", "compare_products"),
            ("Difference between iPhone 13 and 14", "compare_products"),
            ("iPad versus Samsung tablet", "compare_products"),
        ]
        
        for message, expected_intent in test_cases:
            result = await nlp_handler.detect_intent(message)
            assert result["primary_intent"] == expected_intent
            assert result["confidence"] > 0.0

    @pytest.mark.asyncio
    async def test_detect_intent_confidence_levels(self, nlp_handler):
        """Test intent detection confidence levels."""
        # High confidence cases
        high_confidence_cases = [
            "Find iPhone 13 under 50k",  # Clear search intent
            "Watch Samsung deals with 30% off",  # Clear watch intent
            "Compare iPhone vs Samsung Galaxy",  # Clear comparison intent
        ]
        
        for message in high_confidence_cases:
            result = await nlp_handler.detect_intent(message)
            assert result["confidence"] >= 0.8, f"Low confidence for: {message}"
            assert result["is_confident"] is True

    @pytest.mark.asyncio
    async def test_generate_smart_response_search_intent(self, nlp_handler):
        """Test smart response generation for search intent."""
        intent_data = {
            "primary_intent": "search_product",
            "confidence": 0.9
        }
        parse_data = {
            "brand": "samsung",
            "max_price": 30000,
            "keywords": "Samsung phones under 30k"
        }
        
        response = await nlp_handler.generate_smart_response(intent_data, parse_data)
        
        assert response["response_type"] == "search_product"
        assert response["confidence"] == 0.9
        assert "search_products" in response["actions"]
        assert "help you find products" in response["message"]

    @pytest.mark.asyncio
    async def test_generate_smart_response_watch_intent(self, nlp_handler):
        """Test smart response generation for watch intent."""
        intent_data = {
            "primary_intent": "create_watch",
            "confidence": 0.85
        }
        parse_data = {
            "brand": "apple",
            "keywords": "Watch iPhone deals"
        }
        
        response = await nlp_handler.generate_smart_response(intent_data, parse_data)
        
        assert response["response_type"] == "create_watch"
        assert "create_watch" in response["actions"]
        assert "set up a price watch" in response["message"]

    @pytest.mark.asyncio
    async def test_handle_comparison_request(self, nlp_handler):
        """Test comparison request handling."""
        message = "Compare iPhone 13 vs Samsung Galaxy S22 on camera and battery"
        products = ["B08N5WRWNW", "B09KGVJ3N5"]  # Example ASINs
        
        result = await nlp_handler.handle_comparison_request(message, products)
        
        assert result["comparison_type"] == "feature_comparison"
        assert "camera" in result["criteria"]
        assert "battery" in result["criteria"]
        assert result["products"] == products
        assert len(result["comparison_aspects"]) > 0

    def test_extract_features(self, nlp_handler):
        """Test feature extraction from messages."""
        test_cases = [
            ("gaming laptop with RGB", {"gaming": True}),
            ("wireless bluetooth headphones", {"wireless": True}),
            ("budget smartphone under 15k", {"budget": True}),
            ("premium flagship phone", {"premium": True}),
            ("portable lightweight laptop", {"portable": True}),
            ("waterproof smartwatch IP68", {"waterproof": True}),
            ("fast charging power bank", {"fast_charging": True}),
        ]
        
        for message, expected_features in test_cases:
            features = nlp_handler._extract_features(message)
            for feature, expected in expected_features.items():
                assert features.get(feature) == expected

    def test_detect_urgency(self, nlp_handler):
        """Test urgency detection from messages."""
        test_cases = [
            ("Need phone urgently", "high"),
            ("Looking for laptop asap", "high"),
            ("Want to buy today", "high"),
            ("Need phone soon", "medium"),
            ("Looking for laptop this week", "medium"),
            ("Want to buy a phone", "low"),
            ("Casual browsing for tablets", "low"),
        ]
        
        for message, expected_urgency in test_cases:
            urgency = nlp_handler._detect_urgency(message)
            assert urgency == expected_urgency

    def test_detect_price_sensitivity(self, nlp_handler):
        """Test price sensitivity detection."""
        test_cases = [
            ("cheap budget phone", "high"),
            ("affordable smartphone", "high"),
            ("economical laptop", "high"),
            ("premium flagship device", "low"),
            ("expensive high-end phone", "low"),
            ("luxury smartphone", "low"),
            ("good phone under 20k", "medium"),
            ("looking for smartphone", "medium"),
        ]
        
        for message, expected_sensitivity in test_cases:
            sensitivity = nlp_handler._detect_price_sensitivity(message)
            assert sensitivity == expected_sensitivity

    def test_extract_quality_preferences(self, nlp_handler):
        """Test quality preference extraction."""
        test_cases = [
            ("durable laptop for work", ["durability"]),
            ("fast powerful gaming phone", ["performance"]),
            ("beautiful stylish design", ["design"]),
            ("branded popular smartphone", ["brand"]),
            ("fast durable branded phone", ["performance", "durability", "brand"]),
        ]
        
        for message, expected_preferences in test_cases:
            preferences = nlp_handler._extract_quality_preferences(message)
            for pref in expected_preferences:
                assert pref in preferences

    def test_extract_usage_context(self, nlp_handler):
        """Test usage context extraction."""
        test_cases = [
            ("laptop for office work", ["work"]),
            ("gaming phone for games", ["gaming"]),
            ("family home computer", ["home"]),
            ("portable travel laptop", ["travel"]),
            ("phone for college student", ["study"]),
            ("work gaming laptop for office", ["work", "gaming"]),
        ]
        
        for message, expected_contexts in test_cases:
            contexts = nlp_handler._extract_usage_context(message)
            for context in expected_contexts:
                assert context in contexts

    def test_detect_comparison_type(self, nlp_handler):
        """Test comparison type detection."""
        test_cases = [
            ("compare features of iPhone vs Samsung", "feature_comparison"),
            ("check specs of laptop models", "feature_comparison"),
            ("price comparison between phones", "price_comparison"),
            ("which costs more", "price_comparison"),
            ("review comparison of tablets", "review_comparison"),
            ("rating comparison", "review_comparison"),
            ("which is better overall", "general_comparison"),
        ]
        
        for message, expected_type in test_cases:
            comp_type = nlp_handler._detect_comparison_type(message)
            assert comp_type == expected_type

    def test_extract_comparison_criteria(self, nlp_handler):
        """Test comparison criteria extraction."""
        test_cases = [
            ("compare price and performance", ["price", "performance"]),
            ("check camera and battery life", ["camera", "battery"]),
            ("display and storage comparison", ["display", "storage"]),
            ("speed and cost analysis", ["performance", "price"]),
        ]
        
        for message, expected_criteria in test_cases:
            criteria = nlp_handler._extract_comparison_criteria(message)
            for criterion in expected_criteria:
                assert criterion in criteria

    def test_extract_products_from_message(self, nlp_handler):
        """Test product ASIN extraction from messages."""
        message_with_asins = "Compare https://amazon.in/dp/B08N5WRWNW vs B09KGVJ3N5"
        
        asins = nlp_handler._extract_products_from_message(message_with_asins)
        
        assert "B08N5WRWNW" in asins
        assert "B09KGVJ3N5" in asins
        assert len(asins) == 2

    def test_extract_priority_factors(self, nlp_handler):
        """Test priority factor extraction."""
        test_cases = [
            ("budget-friendly phone", ["price"]),
            ("high quality durable laptop", ["quality"]),
            ("fast performance gaming", ["performance"]),
            ("branded popular smartphone", ["brand"]),
            ("budget quality performance phone", ["price", "quality", "performance"]),
        ]
        
        for message, expected_factors in test_cases:
            factors = nlp_handler._extract_priority_factors(message)
            for factor in expected_factors:
                assert factor in factors

    def test_extract_user_preferences(self, nlp_handler):
        """Test user preference extraction."""
        test_cases = [
            ("budget phone under 15k", {"budget_conscious": True}),
            ("premium high-end device", {"quality_focused": True}),
            ("Samsung phone preferred", {"preferred_brand": "samsung"}),
            ("cheap quality branded phone", {"budget_conscious": True, "quality_focused": True}),
        ]
        
        for message, expected_prefs in test_cases:
            preferences = nlp_handler._extract_user_preferences(message)
            for pref, value in expected_prefs.items():
                if pref == "preferred_brand":
                    assert preferences.get(pref) == value
                else:
                    assert preferences.get(pref) == value

    @pytest.mark.asyncio
    async def test_intent_confidence_calculation(self, nlp_handler):
        """Test intent confidence calculation accuracy."""
        # Test cases designed to achieve >80% accuracy target
        high_confidence_cases = [
            ("Find Samsung Galaxy S22 under 50000", "search_product"),
            ("Watch iPhone 13 deals with 25% discount", "create_watch"),
            ("Compare MacBook Pro vs Dell XPS", "compare_products"),
            ("What's the price of iPad Air", "price_inquiry"),
            ("Looking for best deals on headphones", "deal_hunting"),
        ]
        
        correct_predictions = 0
        total_cases = len(high_confidence_cases)
        
        for message, expected_intent in high_confidence_cases:
            result = await nlp_handler.detect_intent(message)
            if result["primary_intent"] == expected_intent and result["confidence"] >= 0.8:
                correct_predictions += 1
        
        accuracy = correct_predictions / total_cases
        assert accuracy >= 0.8, f"Intent detection accuracy {accuracy:.2%} below 80% target"

    @pytest.mark.asyncio
    async def test_error_handling(self, nlp_handler):
        """Test error handling in NLP processing."""
        # Test with None input
        result = await nlp_handler.parse_product_query("")
        assert "nlp_confidence" in result
        assert result["nlp_confidence"] >= 0.0
        
        # Test with malformed input
        result = await nlp_handler.detect_intent(None)
        assert result["primary_intent"] == "unknown"
        assert result["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_performance_with_long_messages(self, nlp_handler):
        """Test performance with long messages."""
        long_message = " ".join([
            "I am looking for a high-performance gaming laptop",
            "with excellent build quality and premium features",
            "that can handle intensive games and professional work",
            "preferably from a well-known brand like ASUS or MSI",
            "with budget around 80000 to 120000 rupees",
            "need fast delivery and good after-sales support"
        ])
        
        result = await nlp_handler.parse_product_query(long_message)
        
        # Verify processing completes successfully
        assert result["nlp_confidence"] > 0.0
        assert "intent" in result
        assert "extracted_features" in result
        
        # Verify key information is extracted
        intent = result["intent"]["primary_intent"]
        assert intent in ["search_product", "feature_search"]


# Integration tests

@pytest.mark.asyncio
async def test_nlp_integration_with_watch_parser():
    """Test integration between NLP handler and existing watch parser."""
    nlp_handler = NaturalLanguageHandler()
    
    message = "Watch Samsung Galaxy S22 deals under 60k with minimum 20% discount"
    result = await nlp_handler.parse_product_query(message)
    
    # Verify both basic parsing and NLP enhancements work together
    assert result["brand"] == "samsung"
    assert result["max_price"] == 60000
    assert result["min_discount"] == 20
    assert result["intent"]["primary_intent"] == "create_watch"
    assert result["nlp_confidence"] > 0.0


@pytest.mark.asyncio
async def test_smart_response_integration():
    """Test end-to-end smart response generation."""
    nlp_handler = NaturalLanguageHandler()
    
    message = "Find gaming laptops under 80k with good performance"
    
    # Step 1: Parse query
    parse_result = await nlp_handler.parse_product_query(message)
    
    # Step 2: Generate smart response
    response = await nlp_handler.generate_smart_response(
        parse_result["intent"], parse_result
    )
    
    # Verify integrated workflow
    assert response["response_type"] == "search_product"
    assert "search_products" in response["actions"]
    assert len(response["message"]) > 0


# Accuracy benchmarks

@pytest.mark.asyncio
async def test_intent_detection_accuracy_benchmark():
    """Benchmark test for intent detection accuracy."""
    nlp_handler = NaturalLanguageHandler()
    
    # Comprehensive test dataset for accuracy validation
    test_dataset = [
        # Search intent (20 cases)
        ("Find iPhone 13", "search_product"),
        ("Looking for gaming laptop", "search_product"),
        ("Show me wireless headphones", "search_product"),
        ("Need smartphone under 25k", "search_product"),
        ("Search for tablets", "search_product"),
        
        # Watch intent (15 cases)  
        ("Watch MacBook deals", "create_watch"),
        ("Alert me for iPhone offers", "create_watch"),
        ("Track Samsung prices", "create_watch"),
        ("Notify price drops", "create_watch"),
        ("Monitor laptop deals", "create_watch"),
        
        # Comparison intent (10 cases)
        ("Compare iPhone vs Samsung", "compare_products"),
        ("Which is better - iPad or tablet", "compare_products"),
        ("Difference between models", "compare_products"),
        ("iPhone versus Android", "compare_products"),
        
        # Other intents (5 cases)
        ("What's the price of iPhone", "price_inquiry"),
        ("Looking for best deals", "deal_hunting"),
        ("Show product features", "feature_search"),
    ]
    
    correct_predictions = 0
    high_confidence_predictions = 0
    
    for message, expected_intent in test_dataset:
        result = await nlp_handler.detect_intent(message)
        
        if result["primary_intent"] == expected_intent:
            correct_predictions += 1
            
        if result["confidence"] >= 0.8 and result["primary_intent"] == expected_intent:
            high_confidence_predictions += 1
    
    total_cases = len(test_dataset)
    accuracy = correct_predictions / total_cases
    high_confidence_accuracy = high_confidence_predictions / total_cases
    
    # Assert accuracy targets
    assert accuracy >= 0.80, f"Overall accuracy {accuracy:.2%} below 80% target"
    assert high_confidence_accuracy >= 0.60, f"High confidence accuracy {high_confidence_accuracy:.2%} below 60% target"
    
    print(f"Intent Detection Accuracy: {accuracy:.2%}")
    print(f"High Confidence Accuracy: {high_confidence_accuracy:.2%}")


@pytest.mark.asyncio
async def test_feature_extraction_coverage():
    """Test feature extraction coverage and accuracy."""
    nlp_handler = NaturalLanguageHandler()
    
    feature_test_cases = [
        ("gaming RGB mechanical keyboard", ["gaming"]),
        ("budget affordable smartphone", ["budget"]),
        ("premium flagship device", ["premium"]),
        ("portable travel laptop", ["portable"]),
        ("wireless bluetooth headphones", ["wireless"]),
        ("waterproof fitness tracker", ["waterproof"]),
        ("fast charging power bank", ["fast_charging"]),
        ("professional work laptop", ["professional"]),
    ]
    
    correct_extractions = 0
    total_features = 0
    
    for message, expected_features in feature_test_cases:
        extracted = nlp_handler._extract_features(message)
        
        for feature in expected_features:
            total_features += 1
            if extracted.get(feature) is True:
                correct_extractions += 1
    
    extraction_accuracy = correct_extractions / total_features
    assert extraction_accuracy >= 0.90, f"Feature extraction accuracy {extraction_accuracy:.2%} below 90% target"
