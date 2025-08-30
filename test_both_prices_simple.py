#!/usr/bin/env python3
"""
Simple test to verify both min_price and max_price work together
"""

import asyncio
from bot.paapi_official import OfficialPaapiClient

async def test_both_prices():
    """Test if both min_price and max_price work together"""

    client = OfficialPaapiClient()

    # Test with a price range that should definitely have results
    print("Testing both min_price and max_price together...")
    print("Price range: ₹1,000 - ₹10,000")
    print("Keywords: monitor")

    try:
        results = await client.search_items_advanced(
            keywords="monitor",
            search_index="Electronics",
            min_price=100000,  # ₹1,000
            max_price=1000000, # ₹10,000
            item_count=10
        )

        print(f"\n✅ SUCCESS: Got {len(results) if results else 0} results")

        if results:
            print("Sample results:")
            for i, result in enumerate(results[:3]):
                price = result.get('price', 0)
                title = result.get('title', 'N/A')[:60] + '...' if len(result.get('title', '')) > 60 else result.get('title', 'N/A')
                print(f"  {i+1}. {title}")
                print(f"     Price: ₹{price/100:.2f}")
        else:
            print("❌ No results found - this suggests PA-API cannot handle both parameters")

    except Exception as e:
        print(f"❌ FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(test_both_prices())
