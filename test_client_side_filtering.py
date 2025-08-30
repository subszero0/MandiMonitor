#!/usr/bin/env python3
"""
Test client-side filtering for both min_price and max_price
"""

import asyncio
from bot.paapi_official import OfficialPaapiClient

async def test_client_side_filtering():
    """Test that client-side filtering works for both min_price and max_price"""

    client = OfficialPaapiClient()

    print("🔬 Testing Client-Side Price Filtering")
    print("=" * 60)

    # Test case: Both min and max price should work now with range that captures the high-priced monitors we see
    print("Test: Both min_price (₹10,000) and max_price (₹100,000)")

    try:
        results = await client.search_items_advanced(
            keywords="monitor",
            search_index="Electronics",
            min_price=1000000,  # ₹10,000 (low min_price to get broad results)
            max_price=10000000,  # ₹100,000
            item_count=10
        )

        print(f"✅ SUCCESS: Got {len(results) if results else 0} results")

        if results:
            print("📊 Result Analysis:")
            prices = []
            valid_results = 0

            for i, result in enumerate(results[:5]):  # Check first 5 results
                price = result.get('price', 0)
                prices.append(price)

                # Check if price is within our range (price is in paise, so convert to rupees for display)
                price_in_rupees = price / 100
                if 10000 <= price_in_rupees <= 100000:  # ₹10,000 - ₹100,000
                    valid_results += 1
                    print(f"  ✅ {i+1}. ₹{price_in_rupees:.2f} - WITHIN RANGE")
                else:
                    print(f"  ❌ {i+1}. ₹{price_in_rupees:.2f} - OUT OF RANGE")

            print(f"📈 Summary: {valid_results}/{len(results[:5])} results within price range")
            prices_in_rupees = [p/100 for p in prices]
            print(f"💰 Price range: ₹{min(prices_in_rupees):.2f} - ₹{max(prices_in_rupees):.2f}")
        else:
            print("❌ No results returned")

    except Exception as e:
        print(f"❌ FAILED: {e}")

    print("\n" + "=" * 60)
    print("🎯 Client-side filtering test complete!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_client_side_filtering())
