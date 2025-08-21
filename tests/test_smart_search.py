"""Tests for SmartSearchEngine."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from bot.smart_search import SmartSearchEngine


class TestSmartSearchEngine:
    """Test SmartSearchEngine functionality."""

    @pytest.fixture
    def search_engine(self):
        """Create SmartSearchEngine instance."""
        return SmartSearchEngine()

    @pytest.mark.asyncio
    async def test_intelligent_search(self, search_engine):
        """Test intelligent search functionality."""
        with patch.object(search_engine, '_analyze_search_intent') as mock_intent:
            mock_intent.return_value = {
                "type": "general",
                "confidence": 0.7,
                "price_sensitive": False
            }
            
            with patch.object(search_engine.category_manager, 'get_category_suggestions') as mock_categories:
                mock_categories.return_value = [
                    {"node_id": 1951048031, "name": "Electronics", "score": 2}
                ]
                
                with patch('bot.smart_search.search_items_advanced') as mock_search:
                    mock_search.return_value = [
                        {
                            "asin": "B123456789",
                            "title": "Test Product",
                            "offers": {"price": 2500000},  # 25000 rs in paise
                            "reviews": {"average_rating": 4.2, "count": 150}
                        }
                    ]
                    
                    result = await search_engine.intelligent_search("smartphone")
                    
                    assert "query" in result
                    assert "intent" in result
                    assert "categories" in result
                    assert "results" in result
                    assert result["query"] == "smartphone"

    @pytest.mark.asyncio
    async def test_search_with_filters(self, search_engine):
        """Test filtered search functionality."""
        filters = {
            "price_range": {"min": 10000, "max": 50000},
            "brand": "Samsung",
            "min_rating": 4.0,
            "min_discount": 10
        }
        
        with patch('bot.smart_search.search_items_advanced') as mock_search:
            mock_search.return_value = [
                {
                    "asin": "B123456789",
                    "title": "Samsung Phone",
                    "brand": "Samsung",
                    "offers": {"price": 3000000, "savings_percentage": 15},
                    "reviews": {"average_rating": 4.3, "count": 200}
                }
            ]
            
            results = await search_engine.search_with_filters("smartphone", filters)
            
            assert isinstance(results, list)
            assert len(results) >= 0

    @pytest.mark.asyncio
    async def test_get_search_suggestions(self, search_engine):
        """Test search suggestions generation."""
        with patch.object(search_engine.category_manager, 'get_category_suggestions') as mock_categories:
            mock_categories.return_value = [
                {"node_id": 1951048031, "name": "Electronics", "score": 2}
            ]
            
            suggestions = await search_engine.get_search_suggestions("phone")
            
            assert isinstance(suggestions, list)
            assert len(suggestions) <= 8

    @pytest.mark.asyncio
    async def test_find_similar_products(self, search_engine):
        """Test finding similar products."""
        with patch('bot.smart_search.Session') as mock_session:
            mock_product = MagicMock()
            mock_product.brand = "Samsung"
            mock_session.return_value.__enter__.return_value.get.return_value = mock_product
            
            with patch.object(search_engine, '_find_by_brand') as mock_find_brand:
                mock_find_brand.return_value = [
                    {"asin": "B987654321", "title": "Similar Samsung Product"}
                ]
                
                similar = await search_engine.find_similar_products("B123456789")
                
                assert isinstance(similar, list)

    def test_analyze_search_intent(self, search_engine):
        """Test search intent analysis."""
        # Test deal hunting intent
        intent = search_engine._analyze_search_intent("cheap smartphone under 15000")
        assert intent["type"] == "deal_hunting"
        assert intent["price_sensitive"] is True
        
        # Test comparison intent
        intent = search_engine._analyze_search_intent("iPhone vs Samsung comparison")
        assert intent["type"] == "comparison"
        
        # Test brand-specific intent
        intent = search_engine._analyze_search_intent("Apple iPhone 15")
        assert intent["brand_specific"] is True
        
        # Test feature-focused intent
        intent = search_engine._analyze_search_intent("laptop with SSD and 16GB RAM")
        assert intent["type"] == "feature_search"
        assert intent["feature_focused"] is True

    def test_calculate_result_score(self, search_engine):
        """Test result scoring algorithm."""
        result = {
            "offers": {
                "price": 2500000,
                "savings_percentage": 20,
                "is_prime_eligible": True,
                "availability_type": "InStock"
            },
            "reviews": {
                "average_rating": 4.5,
                "count": 300
            },
            "brand": "Samsung"
        }
        
        intent = {"price_sensitive": True}
        user_context = {"preferred_brands": ["Samsung"]}
        
        score = search_engine._calculate_result_score(result, intent, user_context)
        
        assert 0 <= score <= 1
        assert score > 0.5  # Should be high due to good rating, discount, and brand match

    def test_get_common_completions(self, search_engine):
        """Test common search completions."""
        completions = search_engine._get_common_completions("phone")
        
        assert isinstance(completions, list)
        assert len(completions) <= 5
        
        # Should include relevant completions
        phone_completions = [c for c in completions if "phone" in c]
        assert len(phone_completions) > 0

    def test_apply_additional_filters(self, search_engine):
        """Test additional filtering."""
        results = [
            {
                "offers": {
                    "availability_type": "InStock",
                    "is_prime_eligible": True
                },
                "reviews": {"count": 150}
            },
            {
                "offers": {
                    "availability_type": "OutOfStock",
                    "is_prime_eligible": False
                },
                "reviews": {"count": 50}
            }
        ]
        
        filters = {
            "availability_filter": "in_stock",
            "min_reviews": 100
        }
        
        filtered = search_engine._apply_additional_filters(results, filters)
        
        assert len(filtered) == 1
        assert filtered[0]["offers"]["availability_type"] == "InStock"

    @pytest.mark.asyncio
    async def test_store_search_query(self, search_engine):
        """Test search query storage."""
        with patch('bot.smart_search.Session') as mock_session:
            mock_session_instance = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_session_instance
            
            await search_engine._store_search_query("test query", 123, 5)
            
            mock_session_instance.add.assert_called_once()
            mock_session_instance.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_history_suggestions(self, search_engine):
        """Test user history-based suggestions."""
        with patch('bot.smart_search.Session') as mock_session:
            mock_query = MagicMock()
            mock_query.query = "samsung smartphone"
            
            mock_session.return_value.__enter__.return_value.exec.return_value.all.return_value = [mock_query]
            
            suggestions = await search_engine._get_user_history_suggestions(123, "samsung")
            
            assert isinstance(suggestions, list)
            if suggestions:
                assert "samsung" in suggestions[0].lower()

    def test_build_search_parameters(self, search_engine):
        """Test search parameter building."""
        intent = {
            "type": "deal_hunting",
            "price_sensitive": True
        }
        
        categories = [
            {"node_id": 1951048031, "name": "Electronics"}
        ]
        
        params = search_engine._build_search_parameters("smartphone", intent, categories)
        
        assert "keywords" in params
        assert params["keywords"] == "smartphone"
        assert "browse_node_id" in params
        assert params["browse_node_id"] == 1951048031
        
        # Deal hunting should add discount requirement
        if intent["type"] == "deal_hunting":
            assert "min_savings_percent" in params
