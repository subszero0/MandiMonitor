"""Tests for CategoryManager."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from bot.category_manager import CategoryManager


class TestCategoryManager:
    """Test CategoryManager functionality."""

    @pytest.fixture
    def category_manager(self):
        """Create CategoryManager instance."""
        return CategoryManager()

    @pytest.mark.asyncio
    async def test_build_category_tree(self, category_manager):
        """Test category tree building."""
        with patch('bot.category_manager.get_browse_nodes_hierarchy') as mock_get_nodes:
            mock_get_nodes.return_value = {
                "id": 1951048031,
                "name": "Electronics",
                "children": [{"id": 123, "name": "Mobiles"}],
                "ancestors": []
            }
            
            with patch('bot.category_manager.Session') as mock_session:
                mock_session.return_value.__enter__.return_value.get.return_value = None
                
                tree = await category_manager.build_category_tree()
                
                assert len(tree) > 0
                assert 1951048031 in tree
                assert tree[1951048031]["name"] == "Electronics"

    @pytest.mark.asyncio
    async def test_get_category_suggestions(self, category_manager):
        """Test category suggestion generation."""
        suggestions = await category_manager.get_category_suggestions("smartphone mobile phone")
        
        assert isinstance(suggestions, list)
        assert len(suggestions) <= 5
        
        if suggestions:
            suggestion = suggestions[0]
            assert "node_id" in suggestion
            assert "name" in suggestion
            assert "score" in suggestion

    @pytest.mark.asyncio
    async def test_keyword_category_matching(self, category_manager):
        """Test keyword-based category matching."""
        matches = await category_manager._keyword_category_matching("laptop computer")
        
        assert isinstance(matches, list)
        
        # Should match computers & accessories category
        computer_matches = [m for m in matches if "computer" in m["name"].lower()]
        assert len(computer_matches) > 0

    @pytest.mark.asyncio
    async def test_get_category_by_id(self, category_manager):
        """Test getting category by ID."""
        with patch('bot.category_manager.Session') as mock_session:
            mock_node = MagicMock()
            mock_node.id = 1951048031
            mock_node.name = "Electronics"
            mock_node.parent_id = None
            mock_node.sales_rank = None
            
            mock_session.return_value.__enter__.return_value.get.return_value = mock_node
            
            category = await category_manager.get_category_by_id(1951048031)
            
            assert category is not None
            assert category["id"] == 1951048031
            assert category["name"] == "Electronics"

    @pytest.mark.asyncio
    async def test_get_subcategories(self, category_manager):
        """Test getting subcategories."""
        with patch('bot.category_manager.Session') as mock_session:
            mock_subcategory = MagicMock()
            mock_subcategory.id = 123
            mock_subcategory.name = "Mobiles"
            mock_subcategory.parent_id = 1951048031
            mock_subcategory.sales_rank = None
            
            mock_session.return_value.__enter__.return_value.exec.return_value.all.return_value = [mock_subcategory]
            
            subcategories = await category_manager.get_subcategories(1951048031)
            
            assert isinstance(subcategories, list)
            assert len(subcategories) == 1
            assert subcategories[0]["name"] == "Mobiles"

    def test_indian_top_level_nodes(self, category_manager):
        """Test that Indian marketplace nodes are defined."""
        nodes = category_manager.INDIAN_TOP_LEVEL_NODES
        
        assert len(nodes) > 0
        assert 1951048031 in nodes  # Electronics
        assert 1951049031 in nodes  # Computers & Accessories
        assert nodes[1951048031] == "Electronics"
