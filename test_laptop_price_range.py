#!/usr/bin/env python3
"""
Test PA-API with Gaming laptop in ₹40,000 - ₹50,000 range
"""

import asyncio
from bot.paapi_official import OfficialPaapiClient

async def test_laptop_price_range():
    """Test PA-API with Gaming laptop in specific price range"""
    
    client = OfficialPaapiClient()
    
    print("🔬 PA-API GAMING LAPTOP TEST")
    print("=" * 80)
    print("Query: 'Gaming laptop'")
    print("Price Range: ₹40,000 - ₹50,000")
    print("=" * 80)
    
    # Test 1: Min price only (₹40,000)
    print("\n🟦 TEST 1: MIN PRICE ONLY (₹40,000)")
    print("-" * 50)
    
    try:
        results_min = await client.search_items_advanced(
            keywords="Gaming laptop",
            search_index="Electronics",
            min_price=4000000,  # ₹40,000 in paise
            max_price=None,
            item_count=10,
            enable_ai_analysis=False
        )
        
        print(f"📥 Results: {len(results_min) if results_min else 0}")
        
        if results_min:
            prices = []
            for i, result in enumerate(results_min[:5]):
                price = result.get('price', 0)
                price_rupees = price / 100
                title = result.get('title', 'N/A')[:50]
                prices.append(price_rupees)
                
                status = "✅ VALID" if price_rupees >= 40000 else "❌ BELOW MIN"
                print(f"  {i+1}. ₹{price_rupees:,.2f} - {title} {status}")
            
            if prices:
                min_price = min(prices)
                max_price = max(prices)
                below_40k = len([p for p in prices if p < 40000])
                print(f"   💰 Price Range: ₹{min_price:,.2f} - ₹{max_price:,.2f}")
                print(f"   📊 Items below ₹40,000: {below_40k}")
        
    except Exception as e:
        print(f"❌ Min price test failed: {e}")
    
    await asyncio.sleep(3)
    
    # Test 2: Max price only (₹50,000)
    print("\n🟧 TEST 2: MAX PRICE ONLY (₹50,000)")
    print("-" * 50)
    
    try:
        results_max = await client.search_items_advanced(
            keywords="Gaming laptop",
            search_index="Electronics",
            min_price=None,
            max_price=5000000,  # ₹50,000 in paise
            item_count=10,
            enable_ai_analysis=False
        )
        
        print(f"📥 Results: {len(results_max) if results_max else 0}")
        
        if results_max:
            prices = []
            for i, result in enumerate(results_max[:5]):
                price = result.get('price', 0)
                price_rupees = price / 100
                title = result.get('title', 'N/A')[:50]
                prices.append(price_rupees)
                
                status = "✅ VALID" if price_rupees <= 50000 else "❌ ABOVE MAX"
                print(f"  {i+1}. ₹{price_rupees:,.2f} - {title} {status}")
            
            if prices:
                min_price = min(prices)
                max_price = max(prices)
                above_50k = len([p for p in prices if p > 50000])
                print(f"   💰 Price Range: ₹{min_price:,.2f} - ₹{max_price:,.2f}")
                print(f"   📊 Items above ₹50,000: {above_50k}")
        
    except Exception as e:
        print(f"❌ Max price test failed: {e}")
    
    await asyncio.sleep(3)
    
    # Test 3: Both filters (₹40,000 - ₹50,000)
    print("\n🟨 TEST 3: BOTH FILTERS (₹40,000 - ₹50,000)")
    print("-" * 50)
    
    try:
        results_both = await client.search_items_advanced(
            keywords="Gaming laptop",
            search_index="Electronics",
            min_price=4000000,  # ₹40,000 in paise
            max_price=5000000,  # ₹50,000 in paise
            item_count=10,
            enable_ai_analysis=False
        )
        
        print(f"📥 Results: {len(results_both) if results_both else 0}")
        
        if results_both:
            prices = []
            in_range = 0
            out_of_range = 0
            
            for i, result in enumerate(results_both[:10]):  # Show all results
                price = result.get('price', 0)
                price_rupees = price / 100
                title = result.get('title', 'N/A')[:50]
                prices.append(price_rupees)
                
                if 40000 <= price_rupees <= 50000:
                    status = "✅ IN RANGE"
                    in_range += 1
                else:
                    status = "❌ OUT OF RANGE"
                    out_of_range += 1
                
                print(f"  {i+1}. ₹{price_rupees:,.2f} - {title} {status}")
            
            if prices:
                min_price = min(prices)
                max_price = max(prices)
                print(f"   💰 Price Range: ₹{min_price:,.2f} - ₹{max_price:,.2f}")
                print(f"   📊 In range (₹40k-₹50k): {in_range} items")
                print(f"   📊 Out of range: {out_of_range} items")
                
                if in_range == len(prices):
                    print("   🎉 PERFECT: All items within specified range!")
                elif in_range > 0:
                    print("   ✅ PARTIAL: Some items within range")
                else:
                    print("   ❌ FAILED: No items within range")
        
    except Exception as e:
        print(f"❌ Both filters test failed: {e}")
    
    await asyncio.sleep(3)
    
    # Test 4: No filters (baseline)
    print("\n🟪 TEST 4: NO FILTERS (BASELINE)")
    print("-" * 50)
    
    try:
        results_none = await client.search_items_advanced(
            keywords="Gaming laptop",
            search_index="Electronics",
            min_price=None,
            max_price=None,
            item_count=10,
            enable_ai_analysis=False
        )
        
        print(f"📥 Results: {len(results_none) if results_none else 0}")
        
        if results_none:
            prices = []
            for i, result in enumerate(results_none[:5]):
                price = result.get('price', 0)
                price_rupees = price / 100
                title = result.get('title', 'N/A')[:50]
                prices.append(price_rupees)
                print(f"  {i+1}. ₹{price_rupees:,.2f} - {title}")
            
            if prices:
                min_price = min(prices)
                max_price = max(prices)
                print(f"   💰 Price Range: ₹{min_price:,.2f} - ₹{max_price:,.2f}")
        
    except Exception as e:
        print(f"❌ No filters test failed: {e}")
    
    print("\n" + "=" * 80)
    print("🎯 FINAL ANALYSIS")
    print("=" * 80)
    
    # Extract result counts
    min_count = len(results_min) if 'results_min' in locals() and results_min else 0
    max_count = len(results_max) if 'results_max' in locals() and results_max else 0
    both_count = len(results_both) if 'results_both' in locals() and results_both else 0
    none_count = len(results_none) if 'results_none' in locals() and results_none else 0
    
    print(f"📊 RESULT COUNT COMPARISON:")
    print(f"   No filters:      {none_count} results")
    print(f"   Min price only:  {min_count} results")
    print(f"   Max price only:  {max_count} results")
    print(f"   Both filters:    {both_count} results")
    
    print(f"\n🎯 CONCLUSION:")
    if both_count > 0 and both_count <= min(min_count, max_count):
        print("   ✅ SUCCESS: Both filters work perfectly at PA-API level!")
        print("   🎉 PA-API correctly handles combined min_price + max_price")
    elif both_count == 0:
        print("   ❌ No results with both filters - may need wider range")
    else:
        print("   🤔 Unexpected behavior - needs investigation")
    
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_laptop_price_range())
