#!/usr/bin/env python3
"""
Test PA-API with realistic price ranges to confirm behavior
"""

import asyncio
from bot.paapi_official import OfficialPaapiClient

async def test_realistic_api_filters():
    """Test PA-API with realistic price ranges"""

    client = OfficialPaapiClient()

    print("🔬 PA-API REALISTIC PRICE RANGE TESTING")
    print("=" * 60)

    # Test with realistic price ranges that we know have products
    print("Test 1: Realistic range - ₹2,000 to ₹15,000")
    
    try:
        # Test both filters together
        results_both = await client.search_items_advanced(
            keywords="monitor",
            search_index="Electronics",
            min_price=200000,    # ₹2,000 in paise
            max_price=1500000,   # ₹15,000 in paise
            item_count=10,
            enable_ai_analysis=False
        )

        print(f"Both filters (₹2,000-₹15,000): {len(results_both) if results_both else 0} results")

        # Test min_price only
        results_min = await client.search_items_advanced(
            keywords="monitor",
            search_index="Electronics",
            min_price=200000,    # ₹2,000 in paise
            max_price=None,
            item_count=10,
            enable_ai_analysis=False
        )

        print(f"Min price only (₹2,000+): {len(results_min) if results_min else 0} results")

        # Test max_price only
        results_max = await client.search_items_advanced(
            keywords="monitor",
            search_index="Electronics",
            min_price=None,
            max_price=1500000,   # ₹15,000 in paise
            item_count=10,
            enable_ai_analysis=False
        )

        print(f"Max price only (₹15,000-): {len(results_max) if results_max else 0} results")

        # Test no filters
        results_none = await client.search_items_advanced(
            keywords="monitor",
            search_index="Electronics",
            min_price=None,
            max_price=None,
            item_count=10,
            enable_ai_analysis=False
        )

        print(f"No filters: {len(results_none) if results_none else 0} results")

        print("\n📊 Analysis:")
        
        if results_both and len(results_both) > 0:
            print("✅ BOTH FILTERS WORK!")
            if results_both:
                print("Sample results with both filters:")
                for i, result in enumerate(results_both[:3]):
                    price = result.get('price', 0)
                    price_rupees = price / 100
                    title = result.get('title', 'N/A')[:40]
                    print(f"  {i+1}. ₹{price_rupees:.2f} - {title}")
        else:
            print("❌ Both filters together: No results")
            
        if results_max and len(results_max) > 0:
            print("✅ MAX_PRICE FILTER WORKS!")
        else:
            print("❌ Max price filter: No results (may be ignored)")

        print(f"\nComparison:")
        print(f"  No filters: {len(results_none) if results_none else 0}")
        print(f"  Min only: {len(results_min) if results_min else 0}")
        print(f"  Max only: {len(results_max) if results_max else 0}")
        print(f"  Both: {len(results_both) if results_both else 0}")

        # The key test: if both < min, then max_price is working
        if results_both and results_min:
            if len(results_both) < len(results_min):
                print("🎉 CONCLUSION: PA-API DOES support both filters!")
            elif len(results_both) == len(results_min):
                print("❌ CONCLUSION: max_price is ignored when both are sent")
            else:
                print("🤔 CONCLUSION: Unexpected behavior")

    except Exception as e:
        print(f"❌ Test failed: {e}")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(test_realistic_api_filters())
