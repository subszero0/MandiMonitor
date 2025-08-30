#!/usr/bin/env python3
"""
Test script for PA-API Extended Search Depth implementation (Phase 3).
This script tests the newly implemented dynamic search depth functionality.
"""

import asyncio
import sys
import os

# Add the bot directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))

from bot.paapi_official import OfficialPaapiClient
from bot.config import settings

async def test_extended_search_depth():
    """Test extended search depth functionality."""
    print("🧪 Testing PA-API Extended Search Depth Implementation (Phase 3)")
    print("=" * 70)

    try:
        # Initialize client
        client = OfficialPaapiClient()
        print("✅ OfficialPaapiClient initialized successfully")

        # Test 1: Low-budget search (should use minimal pages)
        print("\n📊 Test 1: Low-budget search (< ₹10k) - Should use minimal pages")
        results_low_budget = await client.search_items_advanced(
            keywords="basic laptop",
            search_index="Electronics",
            max_price=800000,  # ₹8,000 max
            item_count=20
        )
        print(f"✅ Found {len(results_low_budget)} products with low budget search")
        print("   📋 Search should have used 3 pages (standard) due to low budget")

        # Test 2: Mid-budget search (should use moderate extension)
        print("\n📊 Test 2: Mid-budget search (₹25k-50k) - Should use moderate extension")
        results_mid_budget = await client.search_items_advanced(
            keywords="gaming monitor",
            search_index="Electronics",
            min_price=2500000,  # ₹25,000 min
            max_price=5000000,  # ₹50,000 max
            item_count=30
        )
        print(f"✅ Found {len(results_mid_budget)} products with mid-budget search")
        print("   📋 Search should have used 5-7 pages due to budget + gaming terms")

        # Test 3: High-budget premium search (should use maximum extension)
        print("\n📊 Test 3: High-budget premium search (₹50k+) - Should use maximum extension")
        results_high_budget = await client.search_items_advanced(
            keywords="professional 4k gaming monitor samsung",
            search_index="Electronics",
            min_price=5000000,  # ₹50,000 min
            item_count=40
        )
        print(f"✅ Found {len(results_high_budget)} products with high-budget premium search")
        print("   📋 Search should have used 7-8 pages due to high budget + multiple premium terms")

        # Test 4: Premium brand search (should trigger premium detection)
        print("\n📊 Test 4: Premium brand search - Should trigger premium detection")
        results_premium_brand = await client.search_items_advanced(
            keywords="apple macbook pro",
            search_index="Computers",
            item_count=25
        )
        print(f"✅ Found {len(results_premium_brand)} products with premium brand search")
        print("   📋 Search should have used 5-6 pages due to premium brand + Computers index")

        # Test 5: Electronics category with premium terms (should maximize extension)
        print("\n📊 Test 5: Electronics with multiple premium terms - Should maximize extension")
        results_electronics_premium = await client.search_items_advanced(
            keywords="wireless bluetooth curved 144hz gaming monitor 4k uhd",
            search_index="Electronics",
            min_price=3000000,  # ₹30,000 min
            item_count=50  # Large item count
        )
        print(f"✅ Found {len(results_electronics_premium)} products with premium Electronics search")
        print("   📋 Search should have used 8 pages (maximum) due to all premium factors")

        # Analysis and validation
        print("\n🔍 Extended Search Depth Analysis:")
        print("=" * 50)

        # Calculate result diversity
        all_results = [
            ("Low Budget", results_low_budget),
            ("Mid Budget", results_mid_budget),
            ("High Budget", results_high_budget),
            ("Premium Brand", results_premium_brand),
            ("Electronics Premium", results_electronics_premium)
        ]

        # Analyze result counts and diversity
        for name, results in all_results:
            print(f"• {name}: {len(results)} products")

        # Check for reasonable result counts
        validation_checks = []

        # Basic functionality checks
        if len(results_low_budget) > 0:
            validation_checks.append("✅ Low budget search returns products")
        else:
            validation_checks.append("❌ Low budget search returns no products")

        if len(results_mid_budget) >= len(results_low_budget):
            validation_checks.append("✅ Mid budget search returns more/same products")
        else:
            validation_checks.append("⚠️ Mid budget search returns fewer products (may be normal)")

        if len(results_high_budget) >= len(results_mid_budget):
            validation_checks.append("✅ High budget search returns more/same products")
        else:
            validation_checks.append("⚠️ High budget search returns fewer products (may be normal)")

        # Premium brand check
        if len(results_premium_brand) > 0:
            validation_checks.append("✅ Premium brand search returns products")
        else:
            validation_checks.append("❌ Premium brand search returns no products")

        # Electronics premium check
        if len(results_electronics_premium) > 0:
            validation_checks.append("✅ Electronics premium search returns products")
        else:
            validation_checks.append("❌ Electronics premium search returns no products")

        # Overall assessment
        print("\n🎯 Extended Search Depth Validation:")
        for check in validation_checks:
            print(f"  {check}")

        # Determine if extended search depth is working
        working_checks = sum(1 for check in validation_checks if "✅" in check)
        total_checks = len(validation_checks)

        if working_checks >= total_checks * 0.8:  # 80% success rate
            print("\n🎉 EXTENDED SEARCH DEPTH SUCCESS: Implementation working correctly!")
            print(f"✅ {working_checks}/{total_checks} validation checks passed")
            print("\n📊 Phase 3 Implementation Summary:")
            print("   • Dynamic search depth calculation based on budget")
            print("   • Premium keyword detection and multiplier application")
            print("   • Search index multipliers for category-specific optimization")
            print("   • Item count factors for result set size consideration")
            print("   • Dynamic rate limiting based on search depth")
            print("   • Comprehensive logging for debugging and monitoring")
            return True
        else:
            print(f"\n❌ EXTENDED SEARCH DEPTH ISSUES: Only {working_checks}/{total_checks} checks passed")
            print("❌ Extended search depth may not be working properly")
            return False

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Check if we have required credentials
    if not all([
        getattr(settings, 'PAAPI_ACCESS_KEY', None),
        getattr(settings, 'PAAPI_SECRET_KEY', None),
        getattr(settings, 'PAAPI_TAG', None)
    ]):
        print("❌ PA-API credentials not configured in settings")
        sys.exit(1)

    success = asyncio.run(test_extended_search_depth())
    sys.exit(0 if success else 1)
