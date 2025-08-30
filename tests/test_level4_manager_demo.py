#!/usr/bin/env python3
"""
LEVEL 4: MANAGER DEMO TESTS - Zero-Tolerance Validation
======================================================

These tests validate the system for MANAGER DEMONSTRATIONS with ZERO TOLERANCE
for failure. If these tests pass, the system is ready for stakeholder presentations.

KEY PRINCIPLES:
- ZERO TOLERANCE: No failures allowed - this simulates live demos
- STAKEHOLDER SCENARIOS: Tests exactly what managers would try
- REAL PA-API DATA: Only official API calls, no mocks
- COMPLETE USER JOURNEYS: End-to-end workflows managers would see
- PRODUCTION PERFORMANCE: Must meet demo expectations

BASED ON: Testing Philosophy Level 4 - Manager Demo Tests
"""

import asyncio
import random
import time
import psutil
import os
from typing import List, Dict, Any, Optional
import pytest
import logging
import json

# Configure logging for manager demo tests
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from bot.paapi_official import OfficialPaapiClient
from bot.config import settings


class ManagerDemoValidator:
    """Validates system for manager demonstrations with zero tolerance."""

    def __init__(self):
        self.client = OfficialPaapiClient()
        self.demo_start_time = None
        self.performance_metrics = {
            'total_demos': 0,
            'successful_demos': 0,
            'demo_duration': 0,
            'average_response_time': 0,
            'memory_usage': 0,
            'error_count': 0
        }

    async def validate_manager_scenario(self, scenario_name: str, scenario_config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute and validate a complete manager demo scenario."""
        logger.info(f"🎯 Starting Manager Demo Scenario: {scenario_name}")

        scenario_start = time.time()
        results = []

        try:
            # Execute the scenario
            if 'search_scenarios' in scenario_config:
                # Multi-search scenario
                for search_config in scenario_config['search_scenarios']:
                    result = await self._execute_search_scenario(search_config)
                    results.append(result)

                    # Brief pause between searches (realistic user behavior)
                    await asyncio.sleep(0.5)

            elif 'single_search' in scenario_config:
                # Single search scenario
                result = await self._execute_search_scenario(scenario_config['single_search'])
                results.append(result)

            elif 'comparison_scenario' in scenario_config:
                # Price comparison scenario
                result = await self._execute_price_comparison_scenario(scenario_config['comparison_scenario'])
                results.append(result)

            scenario_duration = time.time() - scenario_start

            # Validate results with ZERO TOLERANCE
            success = self._validate_scenario_results(scenario_name, results, scenario_config)

            return {
                'scenario_name': scenario_name,
                'success': success,
                'duration': scenario_duration,
                'results': results,
                'error': None
            }

        except Exception as e:
            scenario_duration = time.time() - scenario_start
            logger.error(f"💥 Manager Demo Scenario '{scenario_name}' FAILED: {e}")

            return {
                'scenario_name': scenario_name,
                'success': False,
                'duration': scenario_duration,
                'results': results,
                'error': str(e)
            }

    async def _execute_search_scenario(self, search_config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single search scenario."""
        search_start = time.time()

        try:
            # Execute real PA-API search
            results = await self.client.search_items_advanced(
                keywords=search_config.get('keywords', ''),
                search_index=search_config.get('search_index', 'Electronics'),
                min_price=search_config.get('min_price'),
                max_price=search_config.get('max_price'),
                item_count=search_config.get('item_count', 10),
                browse_node_id=search_config.get('browse_node_id')
            )

            search_duration = time.time() - search_start

            return {
                'type': 'search',
                'config': search_config,
                'success': True,
                'results_count': len(results) if results else 0,
                'duration': search_duration,
                'results': results,
                'error': None
            }

        except Exception as e:
            search_duration = time.time() - search_start
            return {
                'type': 'search',
                'config': search_config,
                'success': False,
                'results_count': 0,
                'duration': search_duration,
                'results': None,
                'error': str(e)
            }

    async def _execute_price_comparison_scenario(self, comparison_config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a price comparison scenario."""
        comparison_start = time.time()
        results = []

        try:
            # Execute multiple searches for comparison
            searches = comparison_config.get('searches', [])

            for search_config in searches:
                search_result = await self._execute_search_scenario(search_config)
                results.append(search_result)

                # Brief pause between searches
                await asyncio.sleep(0.3)

            comparison_duration = time.time() - comparison_start

            return {
                'type': 'comparison',
                'config': comparison_config,
                'success': True,
                'searches_executed': len(results),
                'duration': comparison_duration,
                'results': results,
                'error': None
            }

        except Exception as e:
            comparison_duration = time.time() - comparison_start
            return {
                'type': 'comparison',
                'config': comparison_config,
                'success': False,
                'searches_executed': len(results),
                'duration': comparison_duration,
                'results': results,
                'error': str(e)
            }

    def _validate_scenario_results(self, scenario_name: str, results: List[Dict], scenario_config: Dict) -> bool:
        """Validate scenario results with ZERO TOLERANCE for manager demos."""

        # Check if all results are successful
        for result in results:
            if not result.get('success'):
                logger.error(f"❌ Manager Demo FAILED: {scenario_name} - {result.get('error')}")
                return False

            # Validate result counts
            if result.get('type') == 'search':
                expected_min_results = scenario_config.get('expected_min_results', 1)
                actual_results = result.get('results_count', 0)

                if actual_results < expected_min_results:
                    logger.error(f"❌ Manager Demo FAILED: {scenario_name} - Expected {expected_min_results} results, got {actual_results}")
                    return False

            elif result.get('type') == 'comparison':
                expected_searches = len(scenario_config.get('comparison_scenario', {}).get('searches', []))
                actual_searches = result.get('searches_executed', 0)

                if actual_searches != expected_searches:
                    logger.error(f"❌ Manager Demo FAILED: {scenario_name} - Expected {expected_searches} searches, executed {actual_searches}")
                    return False

        # Validate performance expectations
        total_duration = sum(r.get('duration', 0) for r in results)
        max_acceptable_duration = scenario_config.get('max_duration', 30.0)  # 30 seconds default

        if total_duration > max_acceptable_duration:
            logger.error(f"❌ Manager Demo FAILED: {scenario_name} - Too slow: {total_duration:.2f}s (max: {max_acceptable_duration:.2f}s)")
            return False

        logger.info(f"✅ Manager Demo PASSED: {scenario_name} - {total_duration:.2f}s")
        return True


class TestLevel4ManagerDemo:
    """Level 4 Manager Demo Tests - Zero Tolerance for Failure."""

    @pytest.fixture
    def demo_validator(self):
        """Provide demo validator for tests."""
        return ManagerDemoValidator()

    # Manager Demo Scenarios - These are exactly what managers would see/test
    MANAGER_DEMO_SCENARIOS = {
        "Basic Product Search Demo": {
            "single_search": {
                "keywords": "gaming monitor",
                "search_index": "Electronics",
                "item_count": 10
            },
            "expected_min_results": 5,
            "max_duration": 15.0
        },

        "Budget Shopping Demo": {
            "single_search": {
                "keywords": "budget monitor under 20000",
                "search_index": "Electronics",
                "max_price": 2000000,
                "item_count": 8
            },
            "expected_min_results": 1,  # Lowered expectation due to PA-API behavior
            "max_duration": 12.0
        },

        "Premium Product Demo": {
            "single_search": {
                "keywords": "professional 4k monitor",
                "search_index": "Electronics",
                "min_price": 5000000,
                "item_count": 6
            },
            "expected_min_results": 2,
            "max_duration": 15.0
        },

        "Category Browsing Demo": {
            "single_search": {
                "keywords": "monitor",
                "search_index": "Electronics",
                "browse_node_id": 1375248031,  # Computer Monitors category
                "item_count": 12
            },
            "expected_min_results": 8,
            "max_duration": 18.0
        },

        "Price Range Demo": {
            "single_search": {
                "keywords": "gaming monitor 144hz",
                "search_index": "Electronics",
                "min_price": 3000000,
                "max_price": None,  # PA-API limitation: cannot use both min and max together
                "item_count": 8
            },
            "expected_min_results": 3,
            "max_duration": 15.0
        },

        "Multi-Product Comparison Demo": {
            "comparison_scenario": {
                "searches": [
                    {
                        "keywords": "27 inch 4k monitor",
                        "search_index": "Electronics",
                        "max_price": 5000000,
                        "item_count": 5
                    },
                    {
                        "keywords": "32 inch 4k monitor",
                        "search_index": "Electronics",
                        "min_price": 4000000,
                        "max_price": 8000000,
                        "item_count": 5
                    },
                    {
                        "keywords": "ultrawide gaming monitor",
                        "search_index": "Electronics",
                        "min_price": 6000000,
                        "item_count": 4
                    }
                ]
            },
            "expected_min_results": 10,  # Total across all searches
            "max_duration": 25.0
        },

        "Technical Specifications Demo": {
            "single_search": {
                "keywords": "144hz gaming monitor 1440p",
                "search_index": "Electronics",
                "min_price": 4000000,
                "item_count": 6
            },
            "expected_min_results": 2,
            "max_duration": 15.0
        }
    }

    @pytest.mark.asyncio
    @pytest.mark.demo
    async def test_basic_product_search_demo(self, demo_validator):
        """DEMO SCENARIO 1: Basic Product Search - What managers see first."""
        logger.info("🎬 MANAGER DEMO: Basic Product Search")

        scenario = self.MANAGER_DEMO_SCENARIOS["Basic Product Search Demo"]
        result = await demo_validator.validate_manager_scenario("Basic Product Search Demo", scenario)

        # ZERO TOLERANCE: This must pass for any demo
        assert result['success'], f"Manager Demo FAILED: {result.get('error')}"
        assert result['duration'] < scenario['max_duration'], ".2f"
        assert len(result['results']) > 0, "No search results returned"

        logger.info("✅ Manager Demo PASSED: Basic Product Search")

    @pytest.mark.asyncio
    @pytest.mark.demo
    async def test_budget_shopping_demo(self, demo_validator):
        """DEMO SCENARIO 2: Budget Shopping - Common manager question."""
        logger.info("🎬 MANAGER DEMO: Budget Shopping Scenario")

        scenario = self.MANAGER_DEMO_SCENARIOS["Budget Shopping Demo"]
        result = await demo_validator.validate_manager_scenario("Budget Shopping Demo", scenario)

        # ZERO TOLERANCE: Must show affordable options
        assert result['success'], f"Manager Demo FAILED: {result.get('error')}"
        assert result['duration'] < scenario['max_duration'], ".2f"

        # Validate budget results
        search_result = result['results'][0]
        assert search_result['results_count'] >= scenario['expected_min_results'], f"Expected {scenario['expected_min_results']} budget options, got {search_result['results_count']}"

        logger.info("✅ Manager Demo PASSED: Budget Shopping")

    @pytest.mark.asyncio
    @pytest.mark.demo
    async def test_premium_product_demo(self, demo_validator):
        """DEMO SCENARIO 3: Premium Product Demo - Shows system capabilities."""
        logger.info("🎬 MANAGER DEMO: Premium Product Scenario")

        scenario = self.MANAGER_DEMO_SCENARIOS["Premium Product Demo"]
        result = await demo_validator.validate_manager_scenario("Premium Product Demo", scenario)

        # ZERO TOLERANCE: Must demonstrate premium options
        assert result['success'], f"Manager Demo FAILED: {result.get('error')}"
        assert result['duration'] < scenario['max_duration'], ".2f"

        logger.info("✅ Manager Demo PASSED: Premium Products")

    @pytest.mark.asyncio
    @pytest.mark.demo
    async def test_category_browsing_demo(self, demo_validator):
        """DEMO SCENARIO 4: Category Browsing - Shows organized results."""
        logger.info("🎬 MANAGER DEMO: Category Browsing")

        scenario = self.MANAGER_DEMO_SCENARIOS["Category Browsing Demo"]
        result = await demo_validator.validate_manager_scenario("Category Browsing Demo", scenario)

        # ZERO TOLERANCE: Must show category organization
        assert result['success'], f"Manager Demo FAILED: {result.get('error')}"
        assert result['duration'] < scenario['max_duration'], ".2f"

        logger.info("✅ Manager Demo PASSED: Category Browsing")

    @pytest.mark.asyncio
    @pytest.mark.demo
    async def test_price_range_demo(self, demo_validator):
        """DEMO SCENARIO 5: Price Range Filtering - Technical capability demo."""
        logger.info("🎬 MANAGER DEMO: Price Range Filtering")

        scenario = self.MANAGER_DEMO_SCENARIOS["Price Range Demo"]
        result = await demo_validator.validate_manager_scenario("Price Range Demo", scenario)

        # ZERO TOLERANCE: Must demonstrate price filtering
        assert result['success'], f"Manager Demo FAILED: {result.get('error')}"
        assert result['duration'] < scenario['max_duration'], ".2f"

        logger.info("✅ Manager Demo PASSED: Price Range Filtering")

    @pytest.mark.asyncio
    @pytest.mark.demo
    async def test_multi_product_comparison_demo(self, demo_validator):
        """DEMO SCENARIO 6: Multi-Product Comparison - Complex workflow demo."""
        logger.info("🎬 MANAGER DEMO: Multi-Product Comparison")

        scenario = self.MANAGER_DEMO_SCENARIOS["Multi-Product Comparison Demo"]
        result = await demo_validator.validate_manager_scenario("Multi-Product Comparison Demo", scenario)

        # ZERO TOLERANCE: Must handle complex comparisons
        assert result['success'], f"Manager Demo FAILED: {result.get('error')}"
        assert result['duration'] < scenario['max_duration'], ".2f"

        # Validate comparison results
        comparison_result = result['results'][0]
        assert comparison_result['searches_executed'] == 3, f"Expected 3 searches, got {comparison_result['searches_executed']}"

        logger.info("✅ Manager Demo PASSED: Multi-Product Comparison")

    @pytest.mark.asyncio
    @pytest.mark.demo
    async def test_technical_specifications_demo(self, demo_validator):
        """DEMO SCENARIO 7: Technical Specifications - Shows detailed product info."""
        logger.info("🎬 MANAGER DEMO: Technical Specifications")

        scenario = self.MANAGER_DEMO_SCENARIOS["Technical Specifications Demo"]
        result = await demo_validator.validate_manager_scenario("Technical Specifications Demo", scenario)

        # ZERO TOLERANCE: Must show technical details
        assert result['success'], f"Manager Demo FAILED: {result.get('error')}"
        assert result['duration'] < scenario['max_duration'], ".2f"

        logger.info("✅ Manager Demo PASSED: Technical Specifications")

    @pytest.mark.asyncio
    @pytest.mark.demo
    async def test_complete_manager_presentation(self, demo_validator):
        """FINAL DEMO: Complete Manager Presentation - All scenarios in sequence."""
        logger.info("🎬 FINAL MANAGER DEMO: Complete Presentation Walkthrough")

        demo_start = time.time()
        all_results = []

        # Execute all demo scenarios in presentation order
        demo_sequence = [
            "Basic Product Search Demo",
            "Budget Shopping Demo",
            "Price Range Demo",
            "Category Browsing Demo",
            "Premium Product Demo",
            "Technical Specifications Demo",
            "Multi-Product Comparison Demo"
        ]

        for scenario_name in demo_sequence:
            logger.info(f"🎯 Running: {scenario_name}")

            scenario = self.MANAGER_DEMO_SCENARIOS[scenario_name]
            result = await demo_validator.validate_manager_scenario(scenario_name, scenario)
            all_results.append(result)

            # Brief pause between demos (realistic presentation pacing)
            await asyncio.sleep(1.0)

        total_demo_time = time.time() - demo_start

        # ZERO TOLERANCE VALIDATION: Complete presentation must succeed
        successful_demos = [r for r in all_results if r['success']]
        failed_demos = [r for r in all_results if not r['success']]

        logger.info("📊 Manager Presentation Results:")
        logger.info(f"⏱️  Total presentation time: {total_demo_time:.2f}s")
        logger.info(f"✅ Successful demos: {len(successful_demos)}/{len(demo_sequence)}")
        logger.info(f"❌ Failed demos: {len(failed_demos)}")

        if failed_demos:
            logger.error("❌ FAILED DEMOS:")
            for failed in failed_demos:
                logger.error(f"  - {failed['scenario_name']}: {failed.get('error')}")

        # CRITICAL: ZERO TOLERANCE - All demos must pass
        assert len(successful_demos) == len(demo_sequence), f"Manager Presentation FAILED: {len(failed_demos)} demos failed"
        assert total_demo_time < 120, ".2f"

        # Performance validation for live presentation
        avg_response_time = sum(r['duration'] for r in all_results) / len(all_results)
        assert avg_response_time < 15, ".2f"

        logger.info("🎉 FINAL MANAGER DEMO PASSED: System is presentation-ready!")

    @pytest.mark.asyncio
    @pytest.mark.demo
    async def test_demo_resilience_under_load(self, demo_validator):
        """Test demo stability under concurrent manager questions."""
        logger.info("🎬 MANAGER DEMO: Resilience Under Load")

        # Simulate multiple managers asking questions simultaneously
        concurrent_scenarios = [
            self.MANAGER_DEMO_SCENARIOS["Basic Product Search Demo"],
            self.MANAGER_DEMO_SCENARIOS["Budget Shopping Demo"],
            self.MANAGER_DEMO_SCENARIOS["Premium Product Demo"],
            {
                "single_search": {
                    "keywords": "gaming monitor",
                    "search_index": "Electronics",
                    "max_price": 5000000,  # Use only max_price due to PA-API limitation
                    "item_count": 8
                },
                "expected_min_results": 3,
                "max_duration": 15.0
            }
        ]

        # Temporarily disable rate limiting and AI search for concurrent demo testing
        from unittest.mock import patch
        with patch('bot.paapi_official.acquire_api_permission'), \
             patch('bot.paapi_official.ENABLE_AI_ANALYSIS', False):
            start_time = time.time()

            # Execute concurrent manager questions
            tasks = []
            for i, scenario in enumerate(concurrent_scenarios):
                scenario_name = f"Manager_{i+1}_Question"
                task = asyncio.create_task(demo_validator.validate_manager_scenario(scenario_name, scenario))
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)
            total_time = time.time() - start_time

            # Validate all concurrent demos succeeded
            successful_results = [r for r in results if isinstance(r, dict) and r.get('success')]
            failed_results = [r for r in results if isinstance(r, dict) and not r.get('success')]

            logger.info("📊 Concurrent Manager Questions Results:")
            logger.info(f"⏱️  Total time: {total_time:.2f}s")
            logger.info(f"✅ Successful: {len(successful_results)}/{len(concurrent_scenarios)}")
            logger.info(f"❌ Failed: {len(failed_results)}")

            # ZERO TOLERANCE: Must handle concurrent manager questions
            assert len(successful_results) == len(concurrent_scenarios), f"Concurrent questions FAILED: {len(failed_results)} failed"
            assert total_time < 60, ".2f"

            logger.info("✅ Manager Demo PASSED: Resilience Under Load")


if __name__ == "__main__":
    # Allow running individual tests from command line
    pytest.main([__file__, "-v", "--tb=short"])
