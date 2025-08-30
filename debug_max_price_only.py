#!/usr/bin/env python3
"""
Debug why max_price only returns 0 results
"""

import asyncio
from bot.paapi_official import OfficialPaapiClient

async def debug_max_price():
    """Debug max_price filtering"""

    client = OfficialPaapiClient()

    print("🔍 Debugging max_price filtering")
    print("=" * 50)

    # Test 1: Just max_price
    print("Test 1: max_price only (₹8,000)")
    try:
        results1 = await client.search_items_advanced(
            keywords="monitor",
            search_index="Electronics",
            max_price=800000,  # ₹8,000
            item_count=5
        )
        print(f"Results: {len(results1) if results1 else 0}")
        if results1:
            for i, r in enumerate(results1):
                print(f"  {i+1}. ₹{r.get('price', 0):.2f}")
    except Exception as e:
        print(f"Error: {e}")

    # Test 2: No price filters
    print("\nTest 2: No price filters")
    try:
        results2 = await client.search_items_advanced(
            keywords="monitor",
            search_index="Electronics",
            item_count=5
        )
        print(f"Results: {len(results2) if results2 else 0}")
        if results2:
            for i, r in enumerate(results2):
                print(f"  {i+1}. ₹{r.get('price', 0):.2f}")
    except Exception as e:
        print(f"Error: {e}")

    print("\n" + "=" * 50)

if __name__ == "__main__":
    asyncio.run(debug_max_price())
