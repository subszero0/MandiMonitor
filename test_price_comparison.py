#!/usr/bin/env python3
"""
Compare results with individual vs combined price parameters
"""

import asyncio
from bot.paapi_official import OfficialPaapiClient

async def compare_price_filters():
    """Compare results when using individual vs combined price parameters"""

    client = OfficialPaapiClient()

    test_cases = [
        {
            "name": "Only min_price",
            "min_price": 100000,  # ₹1,000
            "max_price": None,
            "expected_results": "Should find cheap monitors"
        },
        {
            "name": "Only max_price",
            "min_price": None,
            "max_price": 1000000,  # ₹10,000
            "expected_results": "Should find monitors under ₹10k"
        },
        {
            "name": "Both min and max",
            "min_price": 100000,  # ₹1,000
            "max_price": 1000000,  # ₹10,000
            "expected_results": "Should find monitors between ₹1k-10k"
        }
    ]

    for test_case in test_cases:
        print(f"\n{'='*60}")
        print(f"Test: {test_case['name']}")
        print(f"Expected: {test_case['expected_results']}")
        print(f"{'='*60}")

        try:
            results = await client.search_items_advanced(
                keywords="monitor",
                search_index="Electronics",
                min_price=test_case['min_price'],
                max_price=test_case['max_price'],
                item_count=5
            )

            print(f"Results: {len(results) if results else 0} found")

            if results:
                print("Sample products:")
                for i, result in enumerate(results[:3]):
                    price = result.get('price', 0)
                    title = result.get('title', 'N/A')[:50] + '...' if len(result.get('title', '')) > 50 else result.get('title', 'N/A')
                    print(f"  {i+1}. ₹{price/100:.0f} - {title}")
            else:
                print("❌ No results found")

        except Exception as e:
            print(f"❌ Error: {e}")

    print(f"\n{'='*60}")
    print("Analysis:")
    print("- If individual filters work but combined doesn't -> PA-API limitation")
    print("- If all fail -> different issue")
    print("- If combined works -> our assumption was wrong")
    print(f"{'='*60}")

if __name__ == "__main__":
    asyncio.run(compare_price_filters())
