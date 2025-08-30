#!/usr/bin/env python3
"""
Test both min_price and max_price directly at PA-API level
Let's see if PA-API actually supports both filters when sent correctly
"""

import asyncio
from bot.paapi_official import OfficialPaapiClient
from unittest.mock import patch

async def test_api_level_both_filters():
    """Test if PA-API can handle both filters at API level"""

    client = OfficialPaapiClient()

    print("🔬 TESTING BOTH FILTERS AT PA-API LEVEL")
    print("=" * 60)

    # We'll temporarily bypass our client-side filtering to test pure PA-API behavior
    def mock_no_client_filtering(*args, **kwargs):
        """Mock to bypass client-side filtering and see raw PA-API results"""
        # Call the original method but return results without client-side filtering
        return original_method(*args, **kwargs)

    # Store original method
    original_method = client._sync_search_items

    # Test 1: Both filters sent to PA-API directly
    print("Test 1: Send both min_price and max_price to PA-API")
    print("Range: ₹20 - ₹100 (in PA-API format: 20.00 - 100.00 rupees)")

    try:
        # Temporarily disable client-side filtering to see raw PA-API response
        with patch.object(client, '_client_side_min_price', None), \
             patch.object(client, '_client_side_max_price', None):
            
            # Modify the search to send both parameters directly to PA-API
            results_both = await client.search_items_advanced(
                keywords="monitor",
                search_index="Electronics",
                min_price=2000,    # ₹20 in paise
                max_price=10000,   # ₹100 in paise
                item_count=10,
                enable_ai_analysis=False  # Disable AI to avoid complications
            )

        print(f"✅ PA-API with both filters: Got {len(results_both) if results_both else 0} results")

        if results_both:
            print("📊 Raw PA-API Results (both filters):")
            for i, result in enumerate(results_both[:5]):
                price = result.get('price', 0)
                price_rupees = price / 100 if price else 0
                title = result.get('title', 'N/A')[:40]
                
                if 20 <= price_rupees <= 100:
                    status = "✅ IN RANGE"
                else:
                    status = "❌ OUT OF RANGE"
                
                print(f"  {i+1}. ₹{price_rupees:.2f} - {title} {status}")

    except Exception as e:
        print(f"❌ Test 1 failed: {e}")

    print("\n" + "-" * 40)

    # Test 2: Compare with min_price only
    print("Test 2: Send only min_price to PA-API (for comparison)")
    print("Min price: ₹20")

    try:
        results_min_only = await client.search_items_advanced(
            keywords="monitor",
            search_index="Electronics",
            min_price=2000,    # ₹20 in paise
            max_price=None,
            item_count=10,
            enable_ai_analysis=False
        )

        print(f"✅ PA-API with min_price only: Got {len(results_min_only) if results_min_only else 0} results")

        if results_min_only:
            print("📊 Min-price only results:")
            for i, result in enumerate(results_min_only[:3]):
                price = result.get('price', 0)
                price_rupees = price / 100 if price else 0
                title = result.get('title', 'N/A')[:40]
                print(f"  {i+1}. ₹{price_rupees:.2f} - {title}")

    except Exception as e:
        print(f"❌ Test 2 failed: {e}")

    print("\n" + "-" * 40)

    # Test 3: Compare with max_price only
    print("Test 3: Send only max_price to PA-API (for comparison)")
    print("Max price: ₹100")

    try:
        results_max_only = await client.search_items_advanced(
            keywords="monitor",
            search_index="Electronics",
            min_price=None,
            max_price=10000,   # ₹100 in paise
            item_count=10,
            enable_ai_analysis=False
        )

        print(f"✅ PA-API with max_price only: Got {len(results_max_only) if results_max_only else 0} results")

        if results_max_only:
            print("📊 Max-price only results:")
            for i, result in enumerate(results_max_only[:3]):
                price = result.get('price', 0)
                price_rupees = price / 100 if price else 0
                title = result.get('title', 'N/A')[:40]
                print(f"  {i+1}. ₹{price_rupees:.2f} - {title}")

    except Exception as e:
        print(f"❌ Test 3 failed: {e}")

    print("\n" + "=" * 60)
    print("🎯 API LEVEL ANALYSIS:")
    
    if 'results_both' in locals() and 'results_min_only' in locals():
        both_count = len(results_both) if results_both else 0
        min_count = len(results_min_only) if results_min_only else 0
        
        print(f"  Both filters: {both_count} results")
        print(f"  Min only: {min_count} results")
        
        if both_count > 0 and both_count < min_count:
            print("  ✅ BOTH FILTERS WORK! PA-API is applying max_price filter")
        elif both_count == min_count:
            print("  ❌ MAX_PRICE IGNORED: Same results as min-only")
        elif both_count == 0:
            print("  ❌ BOTH FILTERS FAIL: No results returned")
    
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_api_level_both_filters())
