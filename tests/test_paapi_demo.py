#!/usr/bin/env python3
"""
PA-API Manager Demo Tests: Zero-Tolerance Validation

This module contains manager-level demo tests that validate:
- Complete end-to-end user scenarios
- Zero-tolerance for failures or errors
- Production-ready user experience
- Stakeholder presentation scenarios
- Real-world usage patterns
- Embarrassment-free demonstrations

Based on Testing Philosophy: Manager Demo Tests level
"""

import asyncio
import time
from typing import List, Dict, Any, Optional
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import logging

# Configure logging for demo tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from bot.paapi_official import OfficialPaapiClient
from bot.paapi_ai_bridge import PaapiAiBridge
from bot.config import settings

class DemoScenario:
    """Represents a complete demo scenario with validation."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.steps = []
        self.validations = []

    def add_step(self, name: str, action, *args, **kwargs):
        """Add a step to the demo scenario."""
        self.steps.append({
            "name": name,
            "action": action,
            "args": args,
            "kwargs": kwargs
        })

    def add_validation(self, name: str, validator_func):
        """Add a validation to the demo scenario."""
        self.validations.append({
            "name": name,
            "validator": validator_func
        })

class TestPAAPIManagerDemoSuite:
    """Manager-level demo test suite with zero-tolerance validation."""

    def setup_method(self):
        """Set up demo environment."""
        self.client = OfficialPaapiClient()
        self.ai_bridge = PaapiAiBridge()
        self.demo_start_time = time.time()

    def teardown_method(self):
        """Clean up after demo tests."""
        demo_duration = time.time() - self.demo_start_time
        logger.info(".2f"
    def _create_demo_scenarios(self) -> List[DemoScenario]:
        """Create comprehensive demo scenarios."""
        scenarios = []

        # Demo Scenario 1: Budget Shopping Journey
        budget_demo = DemoScenario(
            "Budget Shopping Demo",
            "Complete journey for a budget-conscious shopper"
        )

        budget_demo.add_step(
            "Search budget laptop",
            self.client.search_items_advanced,
            keywords="budget laptop under 30000",
            search_index="Electronics",
            max_price=3000000,  # ₹30,000
            item_count=15
        )

        budget_demo.add_step(
            "AI analysis for budget",
            self.ai_bridge.search_products_with_ai_analysis,
            query="budget laptop for office work",
            search_results=[],  # Will be filled from previous step
            user_budget=30000,
            user_requirements="good battery, reliable performance"
        )

        budget_demo.add_validation(
            "Budget results validation",
            self._validate_budget_results
        )

        scenarios.append(budget_demo)

        # Demo Scenario 2: Premium Gaming Setup
        gaming_demo = DemoScenario(
            "Premium Gaming Demo",
            "High-end gaming equipment search"
        )

        gaming_demo.add_step(
            "Search gaming laptop",
            self.client.search_items_advanced,
            keywords="gaming laptop",
            search_index="Electronics",
            min_price=7500000,  # ₹75,000
            max_price=15000000,  # ₹1,50,000
            item_count=20
        )

        gaming_demo.add_step(
            "AI gaming analysis",
            self.ai_bridge.search_products_with_ai_analysis,
            query="gaming laptop for AAA games",
            search_results=[],  # Will be filled
            user_budget=120000,
            user_requirements="high performance, good cooling, RGB"
        )

        gaming_demo.add_validation(
            "Gaming results validation",
            self._validate_gaming_results
        )

        scenarios.append(gaming_demo)

        # Demo Scenario 3: Category-Specific Search
        category_demo = DemoScenario(
            "Category Search Demo",
            "Browse node filtering demonstration"
        )

        category_demo.add_step(
            "Search monitors",
            self.client.search_items_advanced,
            keywords="4k monitor",
            search_index="Electronics",
            browse_node_id=1951048031,  # Electronics
            item_count=25
        )

        category_demo.add_validation(
            "Category results validation",
            self._validate_category_results
        )

        scenarios.append(category_demo)

        return scenarios

    @pytest.mark.asyncio
    @pytest.mark.demo
    async def test_complete_budget_shopping_demo(self):
        """Demo Test 1: Complete budget shopping experience."""
        logger.info("🎯 MANAGER DEMO: Budget Shopping Experience")
        logger.info("This demo shows the complete journey for a budget-conscious shopper")

        try:
            # Step 1: User searches for budget laptop
            logger.info("🔍 User searches: 'budget laptop under 30000'")
            budget_results = await self.client.search_items_advanced(
                keywords="budget laptop under 30000",
                search_index="Electronics",
                max_price=3000000,  # ₹30,000
                item_count=15
            )

            assert budget_results, "❌ No budget laptops found - Demo failed!"
            assert len(budget_results) >= 5, f"❌ Only {len(budget_results)} results - Demo failed!"

            # Validate results are actually budget-friendly
            prices = [r.get('price', 0) for r in budget_results if r.get('price', 0) > 0]
            if prices:
                avg_price = sum(prices) / len(prices)
                max_price = max(prices)
                assert max_price <= 3500000, f"❌ Results too expensive: ₹{max_price/100:.0f} - Demo failed!"
                logger.info(".0f"
            # Step 2: AI analysis for user requirements
            logger.info("🤖 AI analyzes products for 'good battery, reliable performance'")
            ai_analysis = await self.ai_bridge.search_products_with_ai_analysis(
                query="budget laptop for office work",
                search_results=budget_results,
                user_budget=30000,
                user_requirements="good battery, reliable performance"
            )

            # Should either return AI-enhanced results or fallback
            if 'ai_enhanced' in ai_analysis:
                final_results = ai_analysis.get('results', [])
                logger.info("✅ AI analysis successful")
            else:
                final_results = ai_analysis.get('results', budget_results)
                logger.info("✅ AI fallback working")

            assert final_results, "❌ No final results after AI analysis - Demo failed!"

            # Step 3: Present top recommendations
            logger.info("📋 Presenting top 3 recommendations:")

            for i, product in enumerate(final_results[:3], 1):
                title = product.get('title', 'Unknown Product')[:60]
                price = product.get('price', 0)
                if price > 0:
                    price_display = f"₹{price/100:.0f}"
                else:
                    price_display = "Price not available"

                logger.info(f"  {i}. {title} - {price_display}")

            logger.info("✅ BUDGET SHOPPING DEMO COMPLETED SUCCESSFULLY! 🎉")

        except Exception as e:
            logger.error(f"❌ BUDGET SHOPPING DEMO FAILED: {e}")
            pytest.fail(f"Manager demo failed: {e}")

    @pytest.mark.asyncio
    @pytest.mark.demo
    async def test_premium_gaming_setup_demo(self):
        """Demo Test 2: Premium gaming setup experience."""
        logger.info("🎯 MANAGER DEMO: Premium Gaming Setup")
        logger.info("This demo shows high-end gaming equipment search")

        try:
            # Step 1: Premium gaming laptop search
            logger.info("🔍 Searching premium gaming laptops (₹75k-₹1.5L)")
            premium_results = await self.client.search_items_advanced(
                keywords="gaming laptop high performance",
                search_index="Electronics",
                min_price=7500000,  # ₹75,000
                max_price=15000000,  # ₹1,50,000
                item_count=20
            )

            assert premium_results, "❌ No premium gaming laptops found - Demo failed!"
            assert len(premium_results) >= 3, f"❌ Only {len(premium_results)} premium results - Demo failed!"

            # Validate premium pricing
            prices = [r.get('price', 0) for r in premium_results if r.get('price', 0) > 0]
            if prices:
                min_price = min(prices)
                assert min_price >= 7000000, f"❌ Results too cheap: ₹{min_price/100:.0f} - Demo failed!"
                logger.info(".0f"
            # Step 2: AI analysis for gaming requirements
            logger.info("🎮 AI analyzes for gaming performance")
            ai_gaming = await self.ai_bridge.search_products_with_ai_analysis(
                query="gaming laptop for AAA games",
                search_results=premium_results,
                user_budget=120000,
                user_requirements="high performance, good cooling, RGB lighting"
            )

            # Step 3: Show gaming-focused recommendations
            logger.info("🎯 Gaming-focused recommendations:")

            final_gaming = ai_gaming.get('results', premium_results)
            gaming_specs_found = 0

            for i, product in enumerate(final_gaming[:5], 1):
                title = product.get('title', 'Unknown Product')[:60]
                price = product.get('price', 0)
                price_display = f"₹{price/100:.0f}" if price > 0 else "Price not available"

                # Check for gaming specs in title
                title_lower = title.lower()
                gaming_indicators = ['gaming', 'gtx', 'rtx', 'geforce', 'rgb', 'fps']
                has_gaming_specs = any(spec in title_lower for spec in gaming_indicators)

                if has_gaming_specs:
                    gaming_specs_found += 1

                status = "🎮" if has_gaming_specs else "💻"
                logger.info(f"  {i}. {status} {title} - {price_display}")

            assert gaming_specs_found >= 2, f"❌ Not enough gaming products found: {gaming_specs_found} - Demo failed!"
            logger.info("✅ PREMIUM GAMING DEMO COMPLETED SUCCESSFULLY! 🎉")

        except Exception as e:
            logger.error(f"❌ PREMIUM GAMING DEMO FAILED: {e}")
            pytest.fail(f"Manager demo failed: {e}")

    @pytest.mark.asyncio
    @pytest.mark.demo
    async def test_category_specific_search_demo(self):
        """Demo Test 3: Category-specific search experience."""
        logger.info("🎯 MANAGER DEMO: Category-Specific Search")
        logger.info("This demo shows browse node filtering for Electronics")

        try:
            # Step 1: Electronics category search
            logger.info("📱 Searching Electronics category for 4K monitors")
            electronics_results = await self.client.search_items_advanced(
                keywords="4k monitor 144hz",
                search_index="Electronics",
                browse_node_id=1951048031,  # Electronics category
                item_count=25
            )

            assert electronics_results, "❌ No electronics found - Demo failed!"
            assert len(electronics_results) >= 5, f"❌ Only {len(electronics_results)} electronics results - Demo failed!"

            # Step 2: Validate category relevance
            logger.info("🔍 Analyzing category relevance:")

            monitor_count = 0
            tech_spec_count = 0
            price_range_valid = 0

            for product in electronics_results[:10]:
                title = product.get('title', '').lower()
                price = product.get('price', 0)

                # Check for monitor-related terms
                monitor_terms = ['monitor', 'display', 'screen', '4k', 'uhd', '144hz']
                if any(term in title for term in monitor_terms):
                    monitor_count += 1

                # Check for technical specifications
                tech_terms = ['hz', '4k', 'uhd', 'ips', 'hdr', '144hz', '240hz']
                if any(term in title for term in tech_terms):
                    tech_spec_count += 1

                # Check price range (monitors should be reasonably priced)
                if 1500000 <= price <= 7500000:  # ₹15k-₹75k
                    price_range_valid += 1

            logger.info(f"  📺 Monitor-related products: {monitor_count}/10")
            logger.info(f"  ⚡ Technical specifications: {tech_spec_count}/10")
            logger.info(f"  💰 Reasonable price range: {price_range_valid}/10")

            # Validate category filtering worked
            assert monitor_count >= 6, f"❌ Too few monitor products: {monitor_count}/10 - Demo failed!"
            assert tech_spec_count >= 4, f"❌ Too few tech specs: {tech_spec_count}/10 - Demo failed!"

            # Step 3: Show category-specific recommendations
            logger.info("🏷️ Category-specific recommendations:")

            for i, product in enumerate(electronics_results[:5], 1):
                title = product.get('title', 'Unknown Product')[:50]
                price = product.get('price', 0)
                price_display = f"₹{price/100:.0f}" if price > 0 else "Price not available"

                # Determine product type
                title_lower = title.lower()
                if 'monitor' in title_lower:
                    category_icon = "📺"
                elif 'laptop' in title_lower:
                    category_icon = "💻"
                elif 'keyboard' in title_lower:
                    category_icon = "⌨️"
                else:
                    category_icon = "📱"

                logger.info(f"  {i}. {category_icon} {title} - {price_display}")

            logger.info("✅ CATEGORY SEARCH DEMO COMPLETED SUCCESSFULLY! 🎉")

        except Exception as e:
            logger.error(f"❌ CATEGORY SEARCH DEMO FAILED: {e}")
            pytest.fail(f"Manager demo failed: {e}")

    @pytest.mark.asyncio
    @pytest.mark.demo
    async def test_multi_phase_integration_demo(self):
        """Demo Test 4: All PA-API phases working together."""
        logger.info("🎯 MANAGER DEMO: Complete PA-API Integration")
        logger.info("This demo shows ALL 4 phases working seamlessly")

        try:
            # Phase 1: Price filtering
            logger.info("💰 Phase 1: Price filtering (₹50k-₹1L range)")
            phase1_results = await self.client.search_items_advanced(
                keywords="professional camera",
                search_index="Electronics",
                min_price=5000000,   # ₹50,000
                max_price=10000000,  # ₹1,00,000
                item_count=15
            )

            assert phase1_results, "❌ Phase 1 failed - No price-filtered results!"
            prices = [r.get('price', 0) for r in phase1_results if r.get('price', 0) > 0]
            if prices:
                assert all(4500000 <= p <= 10500000 for p in prices), "❌ Price filtering not working!"

            # Phase 2: Browse node filtering
            logger.info("🏷️ Phase 2: Browse node filtering (Electronics category)")
            phase2_results = await self.client.search_items_advanced(
                keywords="dslr camera",
                search_index="Electronics",
                browse_node_id=1951048031,  # Electronics
                item_count=20
            )

            assert phase2_results, "❌ Phase 2 failed - No category-filtered results!"

            # Phase 3: Extended search depth
            logger.info("🔍 Phase 3: Extended search depth (40 results requested)")
            phase3_results = await self.client.search_items_advanced(
                keywords="professional photography camera",
                search_index="Electronics",
                min_price=7500000,  # ₹75,000 (triggers premium depth)
                item_count=40  # Large count triggers extended depth
            )

            assert phase3_results, "❌ Phase 3 failed - No extended results!"
            assert len(phase3_results) >= 10, f"❌ Phase 3 failed - Only {len(phase3_results)} results!"

            # Phase 4: Smart query enhancement
            logger.info("🧠 Phase 4: Smart query enhancement (₹75k+ budget triggers enhancements)")
            phase4_results = await self.client.search_items_advanced(
                keywords="camera for studio work",
                search_index="Electronics",
                min_price=7500000,  # ₹75,000 (triggers Phase 4 enhancements)
                item_count=25
            )

            assert phase4_results, "❌ Phase 4 failed - No enhanced results!"

            # Validate Phase 4 enhancements were applied
            enhanced_terms_found = 0
            professional_terms = ['professional', 'studio', 'dslr', 'mirrorless', 'full-frame']

            for product in phase4_results[:10]:
                title = product.get('title', '').lower()
                if any(term in title for term in professional_terms):
                    enhanced_terms_found += 1

            assert enhanced_terms_found >= 3, f"❌ Phase 4 failed - Only {enhanced_terms_found} enhanced terms found!"

            # Final integration display
            logger.info("🎉 ALL PHASES INTEGRATION SUCCESSFUL!")
            logger.info("📊 Phase Results Summary:")
            logger.info(f"   💰 Phase 1 (Price): {len(phase1_results)} results")
            logger.info(f"   🏷️ Phase 2 (Browse): {len(phase2_results)} results")
            logger.info(f"   🔍 Phase 3 (Depth): {len(phase3_results)} results")
            logger.info(f"   🧠 Phase 4 (Enhance): {len(phase4_results)} results")

            logger.info("✅ COMPLETE PA-API INTEGRATION DEMO SUCCESSFUL! 🎉")

        except Exception as e:
            logger.error(f"❌ COMPLETE INTEGRATION DEMO FAILED: {e}")
            pytest.fail(f"Manager demo failed: {e}")

    @pytest.mark.asyncio
    @pytest.mark.demo
    async def test_error_handling_demo(self):
        """Demo Test 5: Error handling and recovery demonstration."""
        logger.info("🎯 MANAGER DEMO: Error Handling & Recovery")
        logger.info("This demo shows graceful error handling")

        error_scenarios = [
            ("Invalid browse node", {"browse_node_id": 999999999}),
            ("Empty keywords", {"keywords": ""}),
            ("Extreme price range", {"min_price": 1, "max_price": 1000000000}),
            ("Invalid search index", {"search_index": "InvalidCategory"}),
        ]

        successful_handling = 0

        for scenario_name, error_params in error_scenarios:
            try:
                logger.info(f"🧪 Testing: {scenario_name}")

                params = {
                    "keywords": "test product",
                    "search_index": "Electronics",
                    "item_count": 5,
                    **error_params
                }

                results = await self.client.search_items_advanced(**params)

                # Should either return results or fail gracefully
                if results is not None:
                    logger.info(f"   ✅ {scenario_name}: Handled gracefully (returned {len(results)} results)")
                    successful_handling += 1
                else:
                    logger.info(f"   ✅ {scenario_name}: Handled gracefully (returned None)")
                    successful_handling += 1

            except Exception as e:
                # Should be a clean, user-friendly error
                error_msg = str(e).lower()
                if any(word in error_msg for word in ['traceback', 'exception', 'error']):
                    logger.error(f"   ❌ {scenario_name}: Ugly error message - {e}")
                    pytest.fail(f"Manager demo failed: Ugly error for {scenario_name}")
                else:
                    logger.info(f"   ✅ {scenario_name}: Clean error handling - {e}")
                    successful_handling += 1

        success_rate = successful_handling / len(error_scenarios)
        logger.info(".1%"

        assert success_rate >= 0.9, f"❌ Error handling demo failed: {success_rate:.1%} success rate"
        logger.info("✅ ERROR HANDLING DEMO COMPLETED SUCCESSFULLY! 🎉")

    # Validation helper methods
    def _validate_budget_results(self, results: List[Dict]) -> bool:
        """Validate budget shopping results."""
        if not results:
            return False

        prices = [r.get('price', 0) for r in results if r.get('price', 0) > 0]
        if not prices:
            return False

        avg_price = sum(prices) / len(prices)
        max_price = max(prices)

        # Budget results should be affordable
        return avg_price <= 3500000 and max_price <= 4000000

    def _validate_gaming_results(self, results: List[Dict]) -> bool:
        """Validate gaming results."""
        if not results:
            return False

        gaming_indicators = 0
        for product in results[:10]:
            title = product.get('title', '').lower()
            if any(term in title for term in ['gaming', 'gtx', 'rtx', 'geforce', 'rgb']):
                gaming_indicators += 1

        return gaming_indicators >= 3

    def _validate_category_results(self, results: List[Dict]) -> bool:
        """Validate category-specific results."""
        if not results:
            return False

        category_relevance = 0
        for product in results[:10]:
            title = product.get('title', '').lower()
            if any(term in title for term in ['monitor', 'display', 'screen', '4k', 'uhd']):
                category_relevance += 1

        return category_relevance >= 5

if __name__ == "__main__":
    # Allow running individual demo tests
    pytest.main([__file__, "-v", "-s", "--tb=short", "-k", "demo"])
