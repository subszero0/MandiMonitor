#!/usr/bin/env python3
"""
Test script for PA-API Smart Query Enhancement implementation (Phase 4).
This script tests the newly implemented intelligent query enhancement functionality.
"""

import sys
import os

# Add the bot directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))

from bot.paapi_official import OfficialPaapiClient

def test_smart_query_enhancement():
    """Test smart query enhancement functionality."""
    print("🧪 Testing PA-API Smart Query Enhancement Implementation (Phase 4)")
    print("=" * 75)

    try:
        # Initialize client
        client = OfficialPaapiClient()
        print("✅ OfficialPaapiClient initialized successfully")

        # Test 1: Ultra-premium budget enhancement (₹1 lakh+)
        print("\n📊 Test 1: Ultra-premium budget enhancement (₹1 lakh+)")
        enhanced_ultra = client._enhance_search_query(
            keywords="monitor",
            title=None,
            brand=None,
            min_price=10000000,  # ₹1,00,000 (1 lakh)
            max_price=None,
            search_index="Electronics"
        )
        print(f"Original: 'monitor'")
        print(f"Enhanced: '{enhanced_ultra}'")
        ultra_premium_terms = ["professional", "studio", "enterprise", "premium"]
        ultra_has_terms = enhanced_ultra and any(term in enhanced_ultra for term in ultra_premium_terms)
        print(f"✅ Ultra-premium terms added: {ultra_has_terms}")

        # Test 2: Premium budget enhancement (₹50k-99k)
        print("\n📊 Test 2: Premium budget enhancement (₹50k-99k)")
        enhanced_premium = client._enhance_search_query(
            keywords="laptop",
            title=None,
            brand=None,
            min_price=7500000,  # ₹75,000
            max_price=None,
            search_index="Electronics"
        )
        print(f"Original: 'laptop'")
        print(f"Enhanced: '{enhanced_premium}'")
        premium_terms = ["professional", "premium", "high-performance", "creator"]
        premium_has_terms = enhanced_premium and any(term in enhanced_premium for term in premium_terms)
        print(f"✅ Premium terms added: {premium_has_terms}")

        # Test 3: Mid-premium budget enhancement (₹25k-49k)
        print("\n📊 Test 3: Mid-premium budget enhancement (₹25k-49k)")
        enhanced_mid = client._enhance_search_query(
            keywords="monitor",
            title=None,
            brand=None,
            min_price=3500000,  # ₹35,000
            max_price=None,
            search_index="Electronics"
        )
        print(f"Original: 'monitor'")
        print(f"Enhanced: '{enhanced_mid}'")
        mid_terms = ["gaming", "performance", "quality", "144hz"]
        mid_has_terms = enhanced_mid and any(term in enhanced_mid for term in mid_terms)
        print(f"✅ Mid-premium terms added: {mid_has_terms}")

        # Test 4: Budget range enhancement (₹10k-24k)
        print("\n📊 Test 4: Budget range enhancement (₹10k-24k)")
        enhanced_budget = client._enhance_search_query(
            keywords="headphone",
            title=None,
            brand=None,
            min_price=1500000,  # ₹15,000
            max_price=None,
            search_index="Electronics"
        )
        print(f"Original: 'headphone'")
        print(f"Enhanced: '{enhanced_budget}'")
        budget_terms = ["value", "reliable", "quality", "wireless"]
        budget_has_terms = enhanced_budget and any(term in enhanced_budget for term in budget_terms)
        print(f"✅ Budget terms added: {budget_has_terms}")

        # Test 5: Electronics monitor premium specs
        print("\n📊 Test 5: Electronics monitor premium specs (₹30k+)")
        enhanced_monitor_premium = client._enhance_search_query(
            keywords="gaming monitor",
            title=None,
            brand=None,
            min_price=4000000,  # ₹40,000
            max_price=None,
            search_index="Electronics"
        )
        print(f"Original: 'gaming monitor'")
        print(f"Enhanced: '{enhanced_monitor_premium}'")
        monitor_premium_specs = ["4k", "uhd", "hdr", "ips", "144hz"]
        monitor_has_premium = enhanced_monitor_premium and any(spec in enhanced_monitor_premium for spec in monitor_premium_specs)
        print(f"✅ Premium monitor specs added: {monitor_has_premium}")

        # Test 6: Electronics laptop premium specs
        print("\n📊 Test 6: Electronics laptop premium specs (₹50k+)")
        enhanced_laptop_premium = client._enhance_search_query(
            keywords="laptop",
            title=None,
            brand=None,
            min_price=6000000,  # ₹60,000
            max_price=None,
            search_index="Electronics"
        )
        print(f"Original: 'laptop'")
        print(f"Enhanced: '{enhanced_laptop_premium}'")
        laptop_premium_specs = ["high-performance", "creator", "workstation", "ssd"]
        laptop_has_premium = enhanced_laptop_premium and any(spec in enhanced_laptop_premium for spec in laptop_premium_specs)
        print(f"✅ Premium laptop specs added: {laptop_has_premium}")

        # Test 7: Computer accessories premium features
        print("\n📊 Test 7: Computer accessories premium features (₹5k+)")
        enhanced_accessory = client._enhance_search_query(
            keywords="wireless keyboard",
            title=None,
            brand=None,
            min_price=600000,  # ₹6,000
            max_price=None,
            search_index="Computers"
        )
        print(f"Original: 'wireless keyboard'")
        print(f"Enhanced: '{enhanced_accessory}'")
        accessory_premium = ["wireless", "bluetooth", "ergonomic", "premium"]
        accessory_has_premium = enhanced_accessory and any(feature in enhanced_accessory for feature in accessory_premium)
        print(f"✅ Premium accessory features: {accessory_has_premium}")

        # Test 8: No enhancement for low budget
        print("\n📊 Test 8: No enhancement for low budget (< ₹10k)")
        enhanced_low = client._enhance_search_query(
            keywords="basic mouse",
            title=None,
            brand=None,
            min_price=500000,  # ₹5,000
            max_price=None,
            search_index="Electronics"
        )
        print(f"Original: 'basic mouse'")
        print(f"Enhanced: '{enhanced_low}'")
        low_budget_no_enhancement = enhanced_low is None
        print(f"✅ No enhancement for low budget: {low_budget_no_enhancement}")

        # Test 9: Brand consistency check
        print("\n📊 Test 9: Brand consistency check (avoid duplication)")
        enhanced_brand_check = client._enhance_search_query(
            keywords="laptop",
            title=None,
            brand="Apple",
            min_price=7500000,  # ₹75,000
            max_price=None,
            search_index="Electronics"
        )
        print(f"Original: 'laptop' (brand: 'Apple')")
        print(f"Enhanced: '{enhanced_brand_check}'")
        # Should not contain Apple-related terms to avoid duplication
        no_brand_duplication = enhanced_brand_check and "apple" not in enhanced_brand_check.lower()
        print(f"✅ No brand duplication: {no_brand_duplication}")

        # Test 10: Quality enhancement for high budgets
        print("\n📊 Test 10: Quality enhancement for high budgets (₹20k+)")
        enhanced_quality = client._enhance_search_query(
            keywords="camera",
            title=None,
            brand=None,
            min_price=2500000,  # ₹25,000
            max_price=None,
            search_index="Electronics"
        )
        print(f"Original: 'camera'")
        print(f"Enhanced: '{enhanced_quality}'")
        quality_terms = ["quality", "reliable", "durable", "premium-build"]
        quality_has_terms = enhanced_quality and any(term in enhanced_quality for term in quality_terms)
        print(f"✅ Quality terms added: {quality_has_terms}")

        # Overall Analysis
        print("\n🔍 Smart Query Enhancement Analysis:")
        print("=" * 50)

        # Collect all test results
        test_results = [
            ("Ultra-premium enhancement", ultra_has_terms),
            ("Premium enhancement", premium_has_terms),
            ("Mid-premium enhancement", mid_has_terms),
            ("Budget enhancement", budget_has_terms),
            ("Monitor premium specs", monitor_has_premium),
            ("Laptop premium specs", laptop_has_premium),
            ("Accessory premium features", accessory_has_premium),
            ("Low budget no enhancement", low_budget_no_enhancement),
            ("Brand consistency", no_brand_duplication),
            ("Quality enhancement", quality_has_terms)
        ]

        # Display results
        for test_name, result in test_results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"• {test_name}: {status}")

        # Calculate success rate
        successful_tests = sum(1 for _, result in test_results if result)
        total_tests = len(test_results)
        success_rate = successful_tests / total_tests

        print("\n📊 Smart Query Enhancement Validation:")
        print(f"✅ {successful_tests}/{total_tests} tests passed ({success_rate:.1%} success rate)")

        if success_rate >= 0.9:  # 90% success rate
            print("\n🎉 SMART QUERY ENHANCEMENT SUCCESS: Implementation working perfectly!")
            print("\n📋 Phase 4 Implementation Summary:")
            print("   • Budget-based intelligent term addition")
            print("   • Category-specific enhancements (Electronics, Computers)")
            print("   • Premium specs for monitors, laptops, accessories")
            print("   • Quality indicators for higher budgets")
            print("   • Brand consistency (no duplication)")
            print("   • Comprehensive logging and debugging")
            return True
        elif success_rate >= 0.7:  # 70% success rate
            print("\n⚠️ SMART QUERY ENHANCEMENT PARTIAL SUCCESS: Working but needs refinement")
            print("   Some enhancements may need adjustment")
            return False
        else:
            print("\n❌ SMART QUERY ENHANCEMENT ISSUES: Significant problems detected")
            print("   Implementation may need major fixes")
            return False

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_smart_query_enhancement()
    sys.exit(0 if success else 1)
