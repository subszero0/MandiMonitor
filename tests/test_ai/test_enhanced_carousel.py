"""
Tests for Enhanced Carousel Builder (Phase 6).

These tests validate the enhanced carousel building functions for multi-card
selection with comparison features, AI insights, and intelligent highlighting.
"""

import pytest
from bot.ai.enhanced_carousel import (
    build_product_carousel,
    build_enhanced_card,
    build_comparison_summary_card,
    build_ai_selection_message,
    format_comparison_table_text,
    get_carousel_analytics_metadata,
    _get_product_highlights
)


class TestEnhancedCarousel:
    """Test the enhanced carousel building functions."""

    @pytest.fixture
    def sample_products(self):
        """Sample products for testing."""
        return [
            {
                "asin": "B08N5WRWNW",
                "title": "ASUS TUF Gaming 27\" Curved Monitor 144Hz",
                "price": 2500000,  # ₹25,000 in paise
                "brand": "ASUS",
                "image": "https://example.com/image1.jpg"
            },
            {
                "asin": "B09G9FPHY6", 
                "title": "LG UltraGear 27\" Gaming Monitor 165Hz",
                "price": 3200000,  # ₹32,000 in paise
                "brand": "LG",
                "image": "https://example.com/image2.jpg"
            },
            {
                "asin": "B09WPJNHKP",
                "title": "Samsung Odyssey G5 27\" Curved 144Hz",
                "price": 2200000,  # ₹22,000 in paise
                "brand": "Samsung", 
                "image": "https://example.com/image3.jpg"
            }
        ]

    @pytest.fixture
    def sample_comparison_table(self):
        """Sample comparison table for testing."""
        return {
            "headers": ["Feature", "Option 1", "Option 2", "Option 3"],
            "key_differences": [
                {
                    "feature": "Refresh Rate",
                    "values": ["144Hz", "165Hz", "144Hz"],
                    "user_preference": "144Hz",
                    "highlight_best": 0
                },
                {
                    "feature": "Price",
                    "values": ["₹25,000", "₹32,000", "₹22,000"],
                    "user_preference": "Not specified", 
                    "highlight_best": 2
                },
                {
                    "feature": "Brand",
                    "values": ["ASUS", "LG", "Samsung"],
                    "user_preference": "Not specified",
                    "highlight_best": -1
                }
            ],
            "strengths": {
                0: ["Exact refresh rate match", "High overall match"],
                1: ["Premium features"],
                2: ["Budget-friendly", "Exact refresh rate match"]
            },
            "trade_offs": [
                "Higher price options offer better feature matches"
            ],
            "summary": "3 competitive options found • Key differences: Refresh Rate, Price"
        }

    def test_build_enhanced_card_single(self, sample_products, sample_comparison_table):
        """Test building enhanced card for single product."""
        product = sample_products[0]
        
        caption, keyboard = build_enhanced_card(
            product=product,
            position=1,
            total_cards=1,
            comparison_table=sample_comparison_table,
            watch_id=12345
        )
        
        # Should show as single best match
        assert "🎯 **AI Best Match**" in caption
        assert "ASUS TUF Gaming" in caption
        assert "₹25,000" in caption
        assert "🛒 CREATE WATCH" in keyboard.inline_keyboard[0][0].text
        assert "click:12345:B08N5WRWNW" in keyboard.inline_keyboard[0][0].callback_data

    def test_build_enhanced_card_multi(self, sample_products, sample_comparison_table):
        """Test building enhanced card for multi-card scenario."""
        product = sample_products[0]
        
        caption, keyboard = build_enhanced_card(
            product=product,
            position=1,
            total_cards=3,
            comparison_table=sample_comparison_table,
            watch_id=12345
        )
        
        # Should show position indicator
        assert "🥇 **Option 1**" in caption
        assert "ASUS TUF Gaming" in caption
        assert "₹25,000" in caption
        
        # Should show strengths
        assert "✨ **Best for**:" in caption
        assert "Exact refresh rate match" in caption
        
        # Should show feature highlights
        assert "🔍 **Key Specs**:" in caption
        
        # Button should indicate position
        assert "🛒 CREATE WATCH (1)" in keyboard.inline_keyboard[0][0].text

    def test_build_enhanced_card_price_formatting(self, sample_comparison_table):
        """Test price formatting in enhanced cards."""
        # Test high price (in paise)
        high_price_product = {
            "asin": "B001",
            "title": "Expensive Monitor",
            "price": 5000000,  # ₹50,000 in paise
            "brand": "Premium"
        }
        
        caption, _ = build_enhanced_card(
            product=high_price_product,
            position=1,
            total_cards=1,
            comparison_table=sample_comparison_table,
            watch_id=123
        )
        
        assert "₹50,000" in caption
        
        # Test low price (already in rupees)
        low_price_product = {
            "asin": "B002",
            "title": "Budget Monitor", 
            "price": 15000,  # ₹15,000 already in rupees
            "brand": "Budget"
        }
        
        caption, _ = build_enhanced_card(
            product=low_price_product,
            position=1,
            total_cards=1,
            comparison_table=sample_comparison_table,
            watch_id=123
        )
        
        assert "₹15,000" in caption

    def test_build_comparison_summary_card(self, sample_comparison_table):
        """Test building comparison summary card."""
        card = build_comparison_summary_card(
            comparison_table=sample_comparison_table,
            selection_reason="Close competition between top choices",
            product_count=3
        )
        
        assert card["type"] == "summary_card"
        assert card["keyboard"] is None
        
        caption = card["caption"]
        assert "🤖 **AI Smart Comparison**" in caption
        assert "Why these 3 options?" in caption
        assert "Close competition between top choices" in caption
        assert "⚖️ **Trade-offs to Consider**:" in caption
        # Check for gaming-related content (refresh rate mentioned as gaming performance)
        assert ("Gaming Performance" in caption) or ("Hz" in caption)
        assert "Price" in caption or "₹" in caption
        assert "💡 **Specific Recommendations**:" in caption

    def test_build_product_carousel_single(self, sample_products, sample_comparison_table):
        """Test building carousel for single product."""
        cards = build_product_carousel(
            products=sample_products[:1],
            comparison_table=sample_comparison_table,
            selection_reason="High AI confidence - clear best choice",
            watch_id=12345
        )
        
        # Should have only one card (no summary for single product)
        assert len(cards) == 1
        assert cards[0]["type"] == "product_card"
        assert cards[0]["asin"] == "B08N5WRWNW"

    def test_build_product_carousel_multi(self, sample_products, sample_comparison_table):
        """Test building carousel for multiple products."""
        cards = build_product_carousel(
            products=sample_products,
            comparison_table=sample_comparison_table,
            selection_reason="Multiple competitive options",
            watch_id=12345
        )
        
        # Should have product cards + summary card
        assert len(cards) == 4  # 3 products + 1 summary
        
        # Check product cards
        for i in range(3):
            assert cards[i]["type"] == "product_card"
            assert cards[i]["asin"] == sample_products[i]["asin"]
        
        # Check summary card
        assert cards[3]["type"] == "summary_card"
        assert "AI Smart Comparison" in cards[3]["caption"]

    def test_get_product_highlights(self, sample_comparison_table):
        """Test getting product highlights from comparison table."""
        # Test product that has best values
        highlights = _get_product_highlights(
            product={"asin": "B001"},
            product_index=0,  # First product
            comparison_table=sample_comparison_table
        )
        
        assert len(highlights) <= 3  # Should limit to top 3
        
        # Should highlight features where this product is best
        highlight_text = " ".join(highlights)
        assert "144Hz" in highlight_text and "⭐" in highlight_text  # Best refresh rate match
        
        # Test product without best values
        highlights = _get_product_highlights(
            product={"asin": "B002"},
            product_index=1,  # Second product
            comparison_table=sample_comparison_table
        )
        
        # Should still show features but without star
        assert len(highlights) >= 1
        highlight_text = " ".join(highlights)
        assert "165Hz" in highlight_text  # Should show its refresh rate

    def test_build_ai_selection_message_single(self):
        """Test AI selection message for single product."""
        message = build_ai_selection_message(
            presentation_mode="single",
            selection_reason="High AI confidence (92%) - clear best choice",
            product_count=1,
            user_query="gaming monitor 144hz curved"
        )
        
        assert "🎯 **AI Found Your Perfect Match!**" in message
        assert "gaming monitor 144hz curved" in message
        assert "High AI confidence" in message
        assert "Here's your best option:" in message

    def test_build_ai_selection_message_multi(self):
        """Test AI selection message for multiple products."""
        # Test duo
        message = build_ai_selection_message(
            presentation_mode="duo",
            selection_reason="Close competition - different strengths",
            product_count=2,
            user_query="gaming monitor 27 inch"
        )
        
        assert "🤖 **AI Found Two Great Options!**" in message
        assert "gaming monitor 27 inch" in message
        assert "Close competition" in message
        assert "Choose the option that best fits" in message
        
        # Test trio
        message = build_ai_selection_message(
            presentation_mode="trio",
            selection_reason="Multiple competitive choices",
            product_count=3,
            user_query="curved monitor"
        )
        
        assert "🤖 **AI Found Three Competitive Choices!**" in message

    def test_format_comparison_table_text(self, sample_comparison_table):
        """Test formatting comparison table as text."""
        text = format_comparison_table_text(sample_comparison_table)
        
        assert "📊 **Feature Comparison**" in text
        assert "**Refresh Rate**" in text
        assert "1. 144Hz ⭐" in text  # Best option marked
        assert "2. 165Hz" in text
        assert "3. 144Hz" in text
        assert "**Price**" in text
        assert "3. ₹22,000 ⭐" in text  # Cheapest marked as best

    def test_format_comparison_table_text_empty(self):
        """Test formatting empty comparison table."""
        text = format_comparison_table_text({})
        assert "No comparison data available" in text
        
        text = format_comparison_table_text({"key_differences": []})
        assert "No comparison data available" in text

    def test_get_carousel_analytics_metadata(self):
        """Test generation of carousel analytics metadata."""
        metadata = get_carousel_analytics_metadata(
            presentation_mode="trio",
            product_count=3,
            selection_criteria="ai_multi_card",
            processing_time_ms=45.2
        )
        
        assert metadata["carousel_type"] == "enhanced_ai_carousel"
        assert metadata["presentation_mode"] == "trio"
        assert metadata["product_count"] == 3
        assert metadata["selection_criteria"] == "ai_multi_card"
        assert metadata["processing_time_ms"] == 45.2
        assert metadata["multi_card_experience"] == True
        
        # Should include feature list
        features = metadata["features_enabled"]
        assert "ai_insights" in features
        assert "comparison_table" in features
        assert "product_highlights" in features
        assert "strengths_analysis" in features

    def test_get_carousel_analytics_metadata_single(self):
        """Test analytics metadata for single card."""
        metadata = get_carousel_analytics_metadata(
            presentation_mode="single",
            product_count=1,
            selection_criteria="high_confidence",
            processing_time_ms=12.5
        )
        
        assert metadata["multi_card_experience"] == False
        assert metadata["product_count"] == 1


class TestCarouselEdgeCases:
    """Test edge cases for carousel building."""

    def test_empty_products_list(self):
        """Test handling empty products list."""
        cards = build_product_carousel(
            products=[],
            comparison_table={},
            selection_reason="No products found",
            watch_id=123
        )
        
        assert cards == []

    def test_missing_product_data(self):
        """Test handling products with missing data."""
        incomplete_product = {
            "asin": "B123",
            # Missing title, price, brand, image
        }
        
        caption, keyboard = build_enhanced_card(
            product=incomplete_product,
            position=1,
            total_cards=1,
            comparison_table={"strengths": {}},
            watch_id=123
        )
        
        assert "Unknown Product" in caption
        assert "Price updating..." in caption
        assert "B123" in keyboard.inline_keyboard[0][0].callback_data

    def test_invalid_comparison_table(self):
        """Test handling invalid comparison table data."""
        # Empty comparison table
        card = build_comparison_summary_card(
            comparison_table={},
            selection_reason="Test reason",
            product_count=2
        )
        
        assert "AI Smart Comparison" in card["caption"]
        assert "Test reason" in card["caption"]
        
        # Comparison table with missing fields
        incomplete_table = {
            "key_differences": [],  # Empty differences
            "trade_offs": []  # Empty trade-offs
        }
        
        card = build_comparison_summary_card(
            comparison_table=incomplete_table,
            selection_reason="Another test",
            product_count=1
        )
        
        assert "Another test" in card["caption"]

    def test_large_product_count(self):
        """Test handling large number of products."""
        # Create many products
        products = []
        for i in range(10):
            products.append({
                "asin": f"B{i:03d}",
                "title": f"Monitor {i}",
                "price": 20000 + i * 1000,
                "brand": f"Brand{i}"
            })
        
        comparison_table = {
            "strengths": {i: [f"Feature {i}"] for i in range(10)},
            "key_differences": [],
            "trade_offs": []
        }
        
        cards = build_product_carousel(
            products=products,
            comparison_table=comparison_table,
            selection_reason="Many options available",
            watch_id=123
        )
        
        # Should handle all products + summary
        assert len(cards) == 11  # 10 products + 1 summary
        
        # All should be valid cards
        for i, card in enumerate(cards[:-1]):  # Exclude summary
            assert card["type"] == "product_card"
            assert card["asin"] == f"B{i:03d}"


class TestCarouselPerformance:
    """Performance tests for carousel building."""

    def test_carousel_build_performance(self):
        """Test carousel building performance."""
        import time
        
        # Create moderate-sized dataset
        products = []
        for i in range(5):
            products.append({
                "asin": f"B{i:08d}",
                "title": f"Gaming Monitor {i} 144Hz 27 inch",
                "price": 20000 + i * 5000,
                "brand": f"Brand{i}",
                "image": f"https://example.com/image{i}.jpg"
            })
        
        comparison_table = {
            "strengths": {i: [f"Strength {i}", f"Feature {i}"] for i in range(5)},
            "key_differences": [
                {
                    "feature": "Price",
                    "values": [f"₹{20000 + i * 5000:,}" for i in range(5)],
                    "highlight_best": 0
                },
                {
                    "feature": "Brand", 
                    "values": [f"Brand{i}" for i in range(5)],
                    "highlight_best": -1
                }
            ],
            "trade_offs": ["Price vs features trade-off"],
            "summary": "5 competitive options"
        }
        
        start_time = time.time()
        
        cards = build_product_carousel(
            products=products,
            comparison_table=comparison_table,
            selection_reason="Performance test",
            watch_id=123
        )
        
        processing_time = (time.time() - start_time) * 1000
        
        # Should complete quickly (well under 200ms requirement)
        assert processing_time < 50  # Very fast for carousel building
        assert len(cards) == 6  # 5 products + 1 summary
        
        # All cards should be properly formatted
        for card in cards[:-1]:  # Exclude summary
            assert len(card["caption"]) > 50  # Should have substantial content
            assert card["asin"].startswith("B")

    def test_large_comparison_table_performance(self):
        """Test performance with large comparison tables."""
        import time
        
        # Create large comparison table
        comparison_table = {
            "strengths": {i: [f"Strength {j}" for j in range(5)] for i in range(10)},
            "key_differences": [
                {
                    "feature": f"Feature {i}",
                    "values": [f"Value {j}" for j in range(10)],
                    "highlight_best": i % 10
                }
                for i in range(20)  # Many features
            ],
            "trade_offs": [f"Trade-off {i}" for i in range(10)],
            "summary": "Complex comparison"
        }
        
        start_time = time.time()
        
        card = build_comparison_summary_card(
            comparison_table=comparison_table,
            selection_reason="Large table test",
            product_count=10
        )
        
        processing_time = (time.time() - start_time) * 1000
        
        # Should handle large tables efficiently
        assert processing_time < 20
        assert "AI Smart Comparison" in card["caption"]
        assert len(card["caption"]) > 100  # Should have substantial content
