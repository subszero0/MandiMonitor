#!/usr/bin/env python3
"""
Test script for PA-API Browse Node Filtering implementation.
This script tests the newly implemented browse node filtering functionality.
"""

import asyncio
import sys
import os

# Add the bot directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))

from bot.paapi_official import OfficialPaapiClient
from bot.config import settings

async def test_browse_node_filtering():
    """Test browse node filtering functionality."""
    print("🧪 Testing PA-API Browse Node Filtering Implementation")
    print("=" * 60)

    try:
        # Initialize client
        client = OfficialPaapiClient()
        print("✅ OfficialPaapiClient initialized successfully")

        # Test 1: Search without browse node filter (baseline)
        print("\n📊 Test 1: Search without browse node filter (baseline)")
        results_baseline = await client.search_items_advanced(
            keywords="laptop",
            search_index="Electronics",
            item_count=10
        )
        print(f"✅ Found {len(results_baseline)} products without browse node filter")

        # Show sample products from baseline
        print("   📋 Sample products from baseline:")
        for i, product in enumerate(results_baseline[:3]):
            print(f"   {i+1}. Title: {product.get('title', 'N/A')[:60]}...")
            if 'asin' in product:
                print(f"      ASIN: {product['asin']}")

        # Test 2: Search with Computers & Accessories browse node (1951049031)
        print("\n📊 Test 2: Search with Computers & Accessories browse node (1951049031)")
        results_computers = await client.search_items_advanced(
            keywords="laptop",  # Same keyword
            search_index="Electronics",  # Same search index
            browse_node_id=1951049031,  # Computers & Accessories category
            item_count=10
        )
        print(f"✅ Found {len(results_computers)} products with Computers & Accessories browse node")

        # Show sample products from browse node filtered search
        print("   📋 Sample products from browse node filtered search:")
        for i, product in enumerate(results_computers[:3]):
            print(f"   {i+1}. Title: {product.get('title', 'N/A')[:60]}...")
            if 'asin' in product:
                print(f"      ASIN: {product['asin']}")

        # Test 3: Search with Electronics browse node (1951048031)
        print("\n📊 Test 3: Search with Electronics browse node (1951048031)")
        results_electronics = await client.search_items_advanced(
            keywords="laptop",  # Same keyword
            search_index="Electronics",  # Same search index
            browse_node_id=1951048031,  # Electronics category
            item_count=10
        )
        print(f"✅ Found {len(results_electronics)} products with Electronics browse node")

        # Test 4: Compare result sets to validate browse node filtering effectiveness
        print("\n🔍 Browse Node Filtering Effectiveness Analysis:")
        print(f"• Baseline (no filter): {len(results_baseline)} products")
        print(f"• Computers & Accessories: {len(results_computers)} products")
        print(f"• Electronics: {len(results_electronics)} products")

        # Check if browse node filtering is returning different results
        baseline_asins = {p.get('asin') for p in results_baseline if p.get('asin')}
        computers_asins = {p.get('asin') for p in results_computers if p.get('asin')}
        electronics_asins = {p.get('asin') for p in results_electronics if p.get('asin')}

        # Calculate overlap and uniqueness
        computers_overlap = len(baseline_asins & computers_asins)
        electronics_overlap = len(baseline_asins & electronics_asins)
        computers_unique = len(computers_asins - baseline_asins)
        electronics_unique = len(electronics_asins - baseline_asins)

        print("\n📊 Result Set Analysis:")
        print(f"• Computers & Accessories overlap with baseline: {computers_overlap}/{len(results_computers)} ({computers_overlap/len(results_computers)*100:.1f}%)")
        print(f"• Electronics overlap with baseline: {electronics_overlap}/{len(results_electronics)} ({electronics_overlap/len(results_electronics)*100:.1f}%)")
        print(f"• Computers & Accessories unique products: {computers_unique}")
        print(f"• Electronics unique products: {electronics_unique}")

        # Validate browse node filtering effectiveness
        effectiveness_checks = []

        # Check 1: Browse node filtering should return different results than baseline
        if computers_overlap < len(results_computers) * 0.8:  # Less than 80% overlap
            effectiveness_checks.append("✅ Computers browse node returns different results")
        else:
            effectiveness_checks.append("⚠️ Computers browse node results too similar to baseline")

        if electronics_overlap < len(results_electronics) * 0.8:  # Less than 80% overlap
            effectiveness_checks.append("✅ Electronics browse node returns different results")
        else:
            effectiveness_checks.append("⚠️ Electronics browse node results too similar to baseline")

        # Check 2: Browse node filtering should return valid products
        if len(results_computers) > 0:
            effectiveness_checks.append("✅ Computers browse node returns valid products")
        else:
            effectiveness_checks.append("❌ Computers browse node returns no products")

        if len(results_electronics) > 0:
            effectiveness_checks.append("✅ Electronics browse node returns valid products")
        else:
            effectiveness_checks.append("❌ Electronics browse node returns no products")

        # Overall assessment
        print("\n🎯 Effectiveness Assessment:")
        for check in effectiveness_checks:
            print(f"  {check}")

        # Determine if browse node filtering is working
        working_checks = sum(1 for check in effectiveness_checks if "✅" in check)
        total_checks = len(effectiveness_checks)

        if working_checks >= total_checks * 0.75:  # 75% success rate
            print("\n🎉 BROWSE NODE FILTERING SUCCESS: Working correctly!")
            print(f"✅ {working_checks}/{total_checks} effectiveness checks passed")
            return True
        else:
            print(f"\n❌ BROWSE NODE FILTERING ISSUES: Only {working_checks}/{total_checks} checks passed")
            print("❌ Browse node filtering may not be working properly")
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

    success = asyncio.run(test_browse_node_filtering())
    sys.exit(0 if success else 1)
