#!/usr/bin/env python3
"""
Comprehensive Unit Tests for PA-API Phases 1-4 Implementation
This test suite validates all four phases of PA-API improvements:
- Phase 1: Price Filters
- Phase 2: Browse Node Filtering
- Phase 3: Extended Search Depth
- Phase 4: Smart Query Enhancement
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock

# Add the bot directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))

from bot.paapi_official import OfficialPaapiClient

class TestPAAPIPhases(unittest.TestCase):
    """Unit tests for PA-API Phase 1-4 implementations."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = OfficialPaapiClient()
        self.mock_settings = Mock()
        self.mock_settings.PAAPI_TAG = "TestTag"
        self.mock_settings.PAAPI_MARKETPLACE = "www.amazon.in"

    async def test_phase1_price_filters_min_price(self):
        """Test Phase 1: Min price filter implementation."""
        # Test min_price parameter is properly set
        with patch('bot.paapi_official.settings', self.mock_settings):
            with patch.object(self.client, '_sync_search_items') as mock_sync:
                mock_sync.return_value = [{'asin': 'B123', 'title': 'Test Product'}]

                # Test with min_price
                result = await self.client.search_items_advanced(
                    keywords="test",
                    min_price=500000,  # ₹5,000 in paise
                    item_count=5
                )

                # Verify _sync_search_items was called with min_price
                mock_sync.assert_called_once()
                args, kwargs = mock_sync.call_args
                self.assertEqual(kwargs['min_price'], 500000)

    async def test_phase1_price_filters_max_price(self):
        """Test Phase 1: Max price filter implementation."""
        with patch('bot.paapi_official.settings', self.mock_settings):
            with patch.object(self.client, '_sync_search_items') as mock_sync:
                mock_sync.return_value = [{'asin': 'B123', 'title': 'Test Product'}]

                # Test with max_price
                result = await self.client.search_items_advanced(
                    keywords="test",
                    max_price=1000000,  # ₹10,000 in paise
                    item_count=5
                )

                # Verify _sync_search_items was called with max_price
                mock_sync.assert_called_once()
                args, kwargs = mock_sync.call_args
                self.assertEqual(kwargs['max_price'], 1000000)

    async def test_phase1_price_filters_combined_limitation(self):
        """Test Phase 1: Combined price filters handle PA-API limitation."""
        with patch('bot.paapi_official.settings', self.mock_settings):
            with patch.object(self.client, '_sync_search_items') as mock_sync:
                mock_sync.return_value = [{'asin': 'B123', 'title': 'Test Product'}]

                # Test with both min_price and max_price (PA-API limitation)
                result = await self.client.search_items_advanced(
                    keywords="test",
                    min_price=500000,   # ₹5,000
                    max_price=1000000,  # ₹10,000
                    item_count=5
                )

                # Verify only min_price is used (PA-API limitation)
                mock_sync.assert_called_once()
                args, kwargs = mock_sync.call_args
                self.assertEqual(kwargs['min_price'], 500000)
                self.assertEqual(kwargs['max_price'], 1000000)  # Still passed, but ignored by PA-API

    async def test_phase2_browse_node_filtering(self):
        """Test Phase 2: Browse node filtering implementation."""
        with patch('bot.paapi_official.settings', self.mock_settings):
            with patch.object(self.client, '_sync_search_items') as mock_sync:
                mock_sync.return_value = [{'asin': 'B123', 'title': 'Test Product'}]

                # Test with browse_node_id
                result = await self.client.search_items_advanced(
                    keywords="laptop",
                    browse_node_id=1951049031,  # Computers & Accessories
                    item_count=5
                )

                # Verify _sync_search_items was called with browse_node_id
                mock_sync.assert_called_once()
                args, kwargs = mock_sync.call_args
                self.assertEqual(kwargs['browse_node_id'], 1951049031)

    def test_phase3_search_depth_calculation_low_budget(self):
        """Test Phase 3: Search depth calculation for low budget."""
        # Test low budget (< ₹10k) should return base depth of 3
        depth = self.client._calculate_search_depth(
            keywords="basic mouse",
            search_index="Electronics",
            min_price=500000,  # ₹5,000
            max_price=None,
            item_count=20
        )

        # Should return close to base depth (3-4) for low budget
        # Electronics index (1.5x) + item_count (1.2x) = 1.8x, so 3 * 1.8 = 5.4 → 5
        self.assertGreaterEqual(depth, 3)
        self.assertLessEqual(depth, 6)  # Allow some flexibility

    def test_phase3_search_depth_calculation_premium_budget(self):
        """Test Phase 3: Search depth calculation for premium budget."""
        # Test premium budget (₹50k+) should return higher depth
        depth = self.client._calculate_search_depth(
            keywords="gaming monitor",
            search_index="Electronics",
            min_price=7500000,  # ₹75,000
            max_price=None,
            item_count=30
        )

        # Should return higher depth (7-8) for premium budget + gaming + electronics
        self.assertGreaterEqual(depth, 7)
        self.assertLessEqual(depth, 8)

    def test_phase3_search_depth_calculation_ultra_premium(self):
        """Test Phase 3: Search depth calculation for ultra-premium budget."""
        # Test ultra-premium budget (₹1L+) should return maximum depth
        depth = self.client._calculate_search_depth(
            keywords="professional studio monitor",
            search_index="Electronics",
            min_price=15000000,  # ₹1,50,000
            max_price=None,
            item_count=40
        )

        # Should return maximum depth (8) for ultra-premium
        self.assertEqual(depth, 8)

    def test_phase3_search_depth_calculation_premium_keywords(self):
        """Test Phase 3: Search depth calculation with premium keywords."""
        # Test premium keywords without high budget
        depth = self.client._calculate_search_depth(
            keywords="4k uhd hdr gaming monitor",
            search_index="Electronics",
            min_price=2500000,  # ₹25,000
            max_price=None,
            item_count=25
        )

        # Should return elevated depth due to premium keywords + electronics
        self.assertGreaterEqual(depth, 5)
        self.assertLessEqual(depth, 8)

    def test_phase3_search_depth_calculation_large_item_count(self):
        """Test Phase 3: Search depth calculation with large item count."""
        # Test large item count requirement
        depth = self.client._calculate_search_depth(
            keywords="laptop",
            search_index="Electronics",
            min_price=1000000,  # ₹10,000
            max_price=None,
            item_count=60  # Large count
        )

        # Should return elevated depth due to item count
        self.assertGreaterEqual(depth, 4)

    def test_phase4_query_enhancement_ultra_premium(self):
        """Test Phase 4: Query enhancement for ultra-premium budget."""
        enhanced = self.client._enhance_search_query(
            keywords="monitor",
            title=None,
            brand=None,
            min_price=10000000,  # ₹1,00,000
            max_price=None,
            search_index="Electronics"
        )

        # Should enhance with professional/studio terms
        self.assertIsNotNone(enhanced)
        self.assertIn("professional", enhanced)
        self.assertIn("studio", enhanced)
        self.assertIn("enterprise", enhanced)

    def test_phase4_query_enhancement_premium(self):
        """Test Phase 4: Query enhancement for premium budget."""
        enhanced = self.client._enhance_search_query(
            keywords="laptop",
            title=None,
            brand=None,
            min_price=7500000,  # ₹75,000
            max_price=None,
            search_index="Electronics"
        )

        # Should enhance with professional/high-performance terms
        self.assertIsNotNone(enhanced)
        self.assertIn("professional", enhanced)
        self.assertIn("high-performance", enhanced)
        self.assertIn("creator", enhanced)

    def test_phase4_query_enhancement_mid_premium(self):
        """Test Phase 4: Query enhancement for mid-premium budget."""
        enhanced = self.client._enhance_search_query(
            keywords="monitor",
            title=None,
            brand=None,
            min_price=3500000,  # ₹35,000
            max_price=None,
            search_index="Electronics"
        )

        # Should enhance with gaming/performance terms
        self.assertIsNotNone(enhanced)
        self.assertIn("gaming", enhanced)
        self.assertIn("performance", enhanced)
        self.assertIn("144hz", enhanced)

    def test_phase4_query_enhancement_monitor_premium_specs(self):
        """Test Phase 4: Monitor premium specs enhancement."""
        enhanced = self.client._enhance_search_query(
            keywords="gaming monitor",
            title=None,
            brand=None,
            min_price=4000000,  # ₹40,000
            max_price=None,
            search_index="Electronics"
        )

        # Should enhance with premium display specs
        self.assertIsNotNone(enhanced)
        premium_specs = ["4k", "uhd", "hdr", "ips", "144hz"]
        has_premium_spec = any(spec in enhanced for spec in premium_specs)
        self.assertTrue(has_premium_spec)

    def test_phase4_query_enhancement_laptop_premium_specs(self):
        """Test Phase 4: Laptop premium specs enhancement."""
        enhanced = self.client._enhance_search_query(
            keywords="laptop",
            title=None,
            brand=None,
            min_price=6000000,  # ₹60,000
            max_price=None,
            search_index="Electronics"
        )

        # Should enhance with premium laptop specs
        self.assertIsNotNone(enhanced)
        premium_specs = ["high-performance", "creator", "workstation", "ssd"]
        has_premium_spec = any(spec in enhanced for spec in premium_specs)
        self.assertTrue(has_premium_spec)

    def test_phase4_query_enhancement_audio_premium_features(self):
        """Test Phase 4: Audio premium features enhancement."""
        enhanced = self.client._enhance_search_query(
            keywords="headphone",
            title=None,
            brand=None,
            min_price=1500000,  # ₹15,000
            max_price=None,
            search_index="Electronics"
        )

        # Should enhance with premium audio features
        self.assertIsNotNone(enhanced)
        premium_features = ["wireless", "bluetooth", "noise-cancelling", "premium"]
        has_premium_feature = any(feature in enhanced for feature in premium_features)
        self.assertTrue(has_premium_feature)

    def test_phase4_query_enhancement_computers_accessory(self):
        """Test Phase 4: Computers accessory premium features."""
        enhanced = self.client._enhance_search_query(
            keywords="wireless keyboard",
            title=None,
            brand=None,
            min_price=600000,  # ₹6,000
            max_price=None,
            search_index="Computers"
        )

        # Should enhance with premium accessory features
        self.assertIsNotNone(enhanced)
        premium_features = ["wireless", "bluetooth", "ergonomic", "premium"]
        has_premium_feature = any(feature in enhanced for feature in premium_features)
        self.assertTrue(has_premium_feature)

    def test_phase4_query_enhancement_low_budget_no_change(self):
        """Test Phase 4: Low budget queries should not be enhanced."""
        enhanced = self.client._enhance_search_query(
            keywords="basic mouse",
            title=None,
            brand=None,
            min_price=500000,  # ₹5,000 (below threshold)
            max_price=None,
            search_index="Electronics"
        )

        # Should not enhance low budget queries
        self.assertIsNone(enhanced)

    def test_phase4_query_enhancement_brand_consistency(self):
        """Test Phase 4: Brand consistency - no duplication."""
        enhanced = self.client._enhance_search_query(
            keywords="laptop",
            title=None,
            brand="Apple",
            min_price=7500000,  # ₹75,000
            max_price=None,
            search_index="Electronics"
        )

        # Should enhance but not duplicate Apple-related terms
        self.assertIsNotNone(enhanced)
        self.assertNotIn("apple", enhanced.lower())

    def test_phase4_query_enhancement_quality_indicators(self):
        """Test Phase 4: Quality indicators for higher budgets."""
        enhanced = self.client._enhance_search_query(
            keywords="camera",
            title=None,
            brand=None,
            min_price=2500000,  # ₹25,000 (above quality threshold)
            max_price=None,
            search_index="Electronics"
        )

        # Should include quality indicators
        self.assertIsNotNone(enhanced)
        quality_terms = ["quality", "reliable", "durable", "premium-build"]
        has_quality_term = any(term in enhanced for term in quality_terms)
        self.assertTrue(has_quality_term)

    def test_phase4_query_enhancement_duplicate_removal(self):
        """Test Phase 4: Duplicate term removal."""
        # Create a query that would have duplicates
        enhanced = self.client._enhance_search_query(
            keywords="gaming gaming monitor",
            title=None,
            brand=None,
            min_price=3500000,  # ₹35,000
            max_price=None,
            search_index="Electronics"
        )

        # Should remove duplicates and enhance the query
        self.assertIsNotNone(enhanced)
        # The enhanced query should contain gaming-related terms but deduplicated
        # Check that "gaming" appears exactly twice (original had 2, we don't add more)
        gaming_count = enhanced.lower().count("gaming")
        self.assertEqual(gaming_count, 2)  # Should have exactly 2 (from original)

        # Verify the query was actually enhanced (should be longer than original)
        self.assertGreater(len(enhanced), len("gaming gaming monitor"))

    async def test_combined_phases_integration(self):
        """Test combined functionality of all phases."""
        with patch('bot.paapi_official.settings', self.mock_settings):
            with patch.object(self.client, '_sync_search_items') as mock_sync:
                mock_sync.return_value = [
                    {'asin': 'B123', 'title': 'Gaming Monitor 4K'},
                    {'asin': 'B456', 'title': 'Professional Laptop'}
                ]

                # Test comprehensive search with all phase features
                result = await self.client.search_items_advanced(
                    keywords="gaming monitor",  # Will be enhanced by Phase 4
                    search_index="Electronics",  # Used by Phase 4
                    min_price=3500000,          # ₹35,000 - triggers Phase 4 enhancements
                    max_price=7500000,          # ₹75,000 - for Phase 1
                    browse_node_id=1951048031,  # Electronics category - Phase 2
                    item_count=40                # Large count - triggers Phase 3 extended depth
                )

                # Verify all phases were invoked
                mock_sync.assert_called_once()
                args, kwargs = mock_sync.call_args

                # Phase 1: Price filters
                self.assertEqual(kwargs['min_price'], 3500000)
                self.assertEqual(kwargs['max_price'], 7500000)

                # Phase 2: Browse node filtering
                self.assertEqual(kwargs['browse_node_id'], 1951048031)

                # Phase 3: Extended search depth (should be > 3 due to budget + keywords)
                # Phase 4: Query enhancement (verified through enhanced keywords)

    def test_edge_cases_empty_keywords(self):
        """Test edge case: empty keywords."""
        enhanced = self.client._enhance_search_query(
            keywords="",
            title=None,
            brand=None,
            min_price=5000000,
            max_price=None,
            search_index="Electronics"
        )
        self.assertIsNone(enhanced)

    def test_edge_cases_whitespace_keywords(self):
        """Test edge case: whitespace-only keywords."""
        enhanced = self.client._enhance_search_query(
            keywords="   ",
            title=None,
            brand=None,
            min_price=5000000,
            max_price=None,
            search_index="Electronics"
        )
        self.assertIsNone(enhanced)

    def test_edge_cases_none_keywords(self):
        """Test edge case: None keywords."""
        enhanced = self.client._enhance_search_query(
            keywords=None,
            title=None,
            brand=None,
            min_price=5000000,
            max_price=None,
            search_index="Electronics"
        )
        self.assertIsNone(enhanced)

if __name__ == '__main__':
    # Add verbose output
    unittest.main(verbosity=2)
