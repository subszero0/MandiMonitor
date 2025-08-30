#!/usr/bin/env python3
"""
Final debug to trace exactly what's happening in the filtering
"""

import asyncio
from bot.paapi_official import OfficialPaapiClient

async def debug_final_filtering():
    """Final debug to trace the filtering process step by step"""

    client = OfficialPaapiClient()

    print("🔬 FINAL FILTERING DEBUG")
    print("=" * 60)

    # Step 1: Get raw results
    print("Step 1: Getting raw results")
    raw_results = await client.search_items_advanced(
        keywords="monitor",
        search_index="Electronics",
        min_price=None,
        max_price=None,
        item_count=5
    )

    print(f"Raw results: {len(raw_results) if raw_results else 0}")
    if raw_results:
        print("Raw prices (in paise):")
        for i, result in enumerate(raw_results[:3]):
            price = result.get('price', 0)
            price_rupees = price / 100
            title = result.get('title', 'N/A')[:30]
            print(f"  {i+1}. {price} paise = ₹{price_rupees:.2f} - {title}")

    print("\nStep 2: Manual filtering simulation")
    print("Filter: ₹2,000 - ₹50,000 (in paise: 200,000 - 5,000,000)")

    min_filter_paise = 200000  # ₹2,000
    max_filter_paise = 5000000  # ₹50,000

    manual_filtered = []
    for result in raw_results:
        price = result.get('price', 0)
        if price is None or price == 0:
            continue
        
        if min_filter_paise <= price <= max_filter_paise:
            manual_filtered.append(result)
            price_rupees = price / 100
            title = result.get('title', 'N/A')[:30]
            print(f"  ✅ PASS: ₹{price_rupees:.2f} - {title}")

    print(f"\nManual filtering result: {len(manual_filtered)} items")

    print("\nStep 3: Testing with actual client-side filtering")
    filtered_results = await client.search_items_advanced(
        keywords="monitor",
        search_index="Electronics",
        min_price=200000,  # ₹2,000 in paise
        max_price=5000000,  # ₹50,000 in paise
        item_count=5
    )

    print(f"Client-side filtering result: {len(filtered_results) if filtered_results else 0} items")

    if filtered_results:
        print("Filtered results:")
        for i, result in enumerate(filtered_results):
            price = result.get('price', 0)
            price_rupees = price / 100
            title = result.get('title', 'N/A')[:30]
            print(f"  {i+1}. ₹{price_rupees:.2f} - {title}")
    else:
        print("❌ Client-side filtering returned no results")

    print("\n" + "=" * 60)
    print("🎯 Final Analysis:")
    print(f"  Manual filtering: {len(manual_filtered)} results")
    print(f"  Client filtering: {len(filtered_results) if filtered_results else 0} results")
    print("  If manual works but client doesn't -> bug in client-side logic")
    print("  If both work -> SUCCESS!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(debug_final_filtering())
