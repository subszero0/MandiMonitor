#!/usr/bin/env python3
"""
Debug script to test MinPrice and MaxPrice parameters in PA-API
"""

import asyncio
from bot.paapi_official import OfficialPaapiClient
from bot.config import settings

async def test_price_combinations():
    """Test various combinations of min_price and max_price parameters"""

    client = OfficialPaapiClient()

    test_cases = [
        {
            "name": "Only min_price (baseline)",
            "min_price": 500000,  # ₹5,000
            "max_price": None,
            "keywords": "monitor"
        },
        {
            "name": "Only max_price (baseline)",
            "min_price": None,
            "max_price": 1000000,  # ₹10,000
            "keywords": "monitor"
        },
        {
            "name": "Both min and max (should work)",
            "min_price": 200000,  # ₹2,000
            "max_price": 800000,  # ₹8,000
            "keywords": "monitor"
        },
        {
            "name": "Both min and max (medium range)",
            "min_price": 1000000,  # ₹10,000
            "max_price": 1500000,  # ₹15,000
            "keywords": "monitor"
        },
        {
            "name": "Both min and max (very narrow)",
            "min_price": 500000,  # ₹5,000
            "max_price": 700000,  # ₹7,000
            "keywords": "monitor"
        },
        {
            "name": "Both min and max (luxury)",
            "min_price": 5000000,  # ₹50,000
            "max_price": 10000000, # ₹100,000
            "keywords": "monitor"
        },
        {
            "name": "Comparison: individual vs combined (min only)",
            "min_price": 200000,  # ₹2,000
            "max_price": None,
            "keywords": "monitor"
        },
        {
            "name": "Comparison: individual vs combined (max only)",
            "min_price": None,
            "max_price": 800000,  # ₹8,000
            "keywords": "monitor"
        }
    ]

    for i, test_case in enumerate(test_cases):
        print(f"\n{'='*60}")
        print(f"Test {i+1}: {test_case['name']}")
        print(f"Keywords: {test_case['keywords']}")
        print(f"Min Price: {test_case['min_price']} paise ({test_case['min_price']/100 if test_case['min_price'] else 'None'} rupees)")
        print(f"Max Price: {test_case['max_price']} paise ({test_case['max_price']/100 if test_case['max_price'] else 'None'} rupees)")
        print(f"{'='*60}")

        try:
            results = await client.search_items_advanced(
                keywords=test_case['keywords'],
                search_index='Electronics',
                min_price=test_case['min_price'],
                max_price=test_case['max_price'],
                item_count=5
            )

            print(f"✅ SUCCESS: Got {len(results) if results else 0} results")

            if results:
                for j, result in enumerate(results[:3]):
                    title = result.get('title', 'N/A')[:80] + '...' if len(result.get('title', '')) > 80 else result.get('title', 'N/A')
                    price = result.get('price', 0)
                    print(f"  {j+1}. {title}")
                    print(f"      Price: ₹{price/100:.2f}")
            else:
                print("  No results returned")

        except Exception as e:
            print(f"❌ FAILED: {e}")

    print(f"\n{'='*60}")
    print("Test completed!")
    print(f"{'='*60}")

if __name__ == "__main__":
    asyncio.run(test_price_combinations())
