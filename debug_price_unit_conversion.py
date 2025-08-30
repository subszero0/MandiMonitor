#!/usr/bin/env python3
"""
Debug the price unit conversion issue
The prices we see are in paise (₹3249900) but we're filtering in rupees
"""

import asyncio
from bot.paapi_official import OfficialPaapiClient

async def debug_price_units():
    """Debug the price unit conversion issue"""

    client = OfficialPaapiClient()

    print("🔬 DEBUGGING PRICE UNIT CONVERSION")
    print("=" * 60)

    # Get raw results to understand the price format
    print("Step 1: Getting raw results to understand price format")

    try:
        raw_results = await client.search_items_advanced(
            keywords="monitor",
            search_index="Electronics",
            min_price=None,
            max_price=None,
            item_count=5
        )

        print(f"Raw results: {len(raw_results) if raw_results else 0}")

        if raw_results:
            print("\n📊 Price Analysis:")
            for i, result in enumerate(raw_results[:3]):
                price = result.get('price', 0)
                title = result.get('title', 'N/A')[:40]
                
                # Convert to different units to understand the format
                price_in_rupees = price / 100 if price else 0
                
                print(f"  {i+1}. {title}")
                print(f"      Raw price: {price}")
                print(f"      As rupees (÷100): ₹{price_in_rupees:.2f}")
                print(f"      Price looks like: {'Paise' if price > 10000 else 'Rupees'}")
                print()

        # Now test with a filter that accounts for paise
        print("Step 2: Testing with paise-aware filtering")
        print("Applying filter: ₹100,000 - ₹600,000 (in paise: 10,000,000 - 60,000,000)")

        # Test with understanding that prices are in paise
        results_filtered = await client.search_items_advanced(
            keywords="monitor",
            search_index="Electronics",
            min_price=10000000,  # ₹100,000 in paise
            max_price=60000000,  # ₹600,000 in paise
            item_count=5
        )

        print(f"Filtered results: {len(results_filtered) if results_filtered else 0}")

        if results_filtered:
            print("\n✅ Filtered Results (should be in ₹100,000 - ₹600,000 range):")
            for i, result in enumerate(results_filtered):
                price = result.get('price', 0)
                price_in_rupees = price / 100
                title = result.get('title', 'N/A')[:40]
                
                print(f"  {i+1}. ₹{price_in_rupees:.2f} - {title}")
                
                # Check if it's actually in our range
                if 100000 <= price_in_rupees <= 600000:
                    print("      ✅ CORRECT: Within range")
                else:
                    print("      ❌ ERROR: Outside range")
        else:
            print("❌ No filtered results")

    except Exception as e:
        print(f"❌ Test failed: {e}")

    print("\n" + "=" * 60)
    print("🎯 Price Unit Analysis Complete")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(debug_price_units())
