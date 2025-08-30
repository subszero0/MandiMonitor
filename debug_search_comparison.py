#!/usr/bin/env python3
"""
Debug PA-API search vs Amazon web search discrepancy
"""

import asyncio
from bot.paapi_official import OfficialPaapiClient

async def debug_search_comparison():
    """Compare PA-API search behavior with different parameters"""
    
    client = OfficialPaapiClient()
    
    print("🔬 PA-API vs AMAZON.IN SEARCH COMPARISON")
    print("=" * 80)
    print("Investigating why PA-API returns different results than Amazon web search")
    print("=" * 80)
    
    # Test 1: Exact query as entered
    print("\n🟦 TEST 1: EXACT QUERY 'gaming laptop'")
    print("-" * 50)
    
    try:
        results1 = await client.search_items_advanced(
            keywords="gaming laptop",
            search_index="Electronics",
            min_price=None,
            max_price=None,
            item_count=10,
            enable_ai_analysis=False
        )
        
        print(f"📥 Results: {len(results1) if results1 else 0}")
        
        if results1:
            for i, result in enumerate(results1[:5]):
                price = result.get('price', 0)
                price_rupees = price / 100
                title = result.get('title', 'N/A')
                print(f"  {i+1}. ₹{price_rupees:,.2f} - {title}")
        
    except Exception as e:
        print(f"❌ Test 1 failed: {e}")
    
    await asyncio.sleep(2)
    
    # Test 2: Different search index
    print("\n🟧 TEST 2: SEARCH IN 'All' CATEGORIES")
    print("-" * 50)
    
    try:
        results2 = await client.search_items_advanced(
            keywords="gaming laptop",
            search_index="All",
            min_price=None,
            max_price=None,
            item_count=10,
            enable_ai_analysis=False
        )
        
        print(f"📥 Results: {len(results2) if results2 else 0}")
        
        if results2:
            for i, result in enumerate(results2[:5]):
                price = result.get('price', 0)
                price_rupees = price / 100
                title = result.get('title', 'N/A')
                print(f"  {i+1}. ₹{price_rupees:,.2f} - {title}")
        
    except Exception as e:
        print(f"❌ Test 2 failed: {e}")
    
    await asyncio.sleep(2)
    
    # Test 3: Alternative keywords
    print("\n🟨 TEST 3: ALTERNATIVE KEYWORDS 'laptop gaming'")
    print("-" * 50)
    
    try:
        results3 = await client.search_items_advanced(
            keywords="laptop gaming",
            search_index="Electronics",
            min_price=None,
            max_price=None,
            item_count=10,
            enable_ai_analysis=False
        )
        
        print(f"📥 Results: {len(results3) if results3 else 0}")
        
        if results3:
            for i, result in enumerate(results3[:5]):
                price = result.get('price', 0)
                price_rupees = price / 100
                title = result.get('title', 'N/A')
                print(f"  {i+1}. ₹{price_rupees:,.2f} - {title}")
        
    except Exception as e:
        print(f"❌ Test 3 failed: {e}")
    
    await asyncio.sleep(2)
    
    # Test 4: More specific gaming terms
    print("\n🟪 TEST 4: SPECIFIC GAMING TERMS 'gaming laptop nvidia gtx rtx'")
    print("-" * 50)
    
    try:
        results4 = await client.search_items_advanced(
            keywords="gaming laptop nvidia gtx rtx",
            search_index="Electronics",
            min_price=None,
            max_price=None,
            item_count=10,
            enable_ai_analysis=False
        )
        
        print(f"📥 Results: {len(results4) if results4 else 0}")
        
        if results4:
            for i, result in enumerate(results4[:5]):
                price = result.get('price', 0)
                price_rupees = price / 100
                title = result.get('title', 'N/A')
                print(f"  {i+1}. ₹{price_rupees:,.2f} - {title}")
        
    except Exception as e:
        print(f"❌ Test 4 failed: {e}")
    
    await asyncio.sleep(2)
    
    # Test 5: Just 'laptop' to see the broader selection
    print("\n🟫 TEST 5: BROADER SEARCH 'laptop' only")
    print("-" * 50)
    
    try:
        results5 = await client.search_items_advanced(
            keywords="laptop",
            search_index="Electronics",
            min_price=4000000,  # ₹40,000 in paise
            max_price=5000000,  # ₹50,000 in paise
            item_count=10,
            enable_ai_analysis=False
        )
        
        print(f"📥 Results: {len(results5) if results5 else 0}")
        
        if results5:
            gaming_related = 0
            for i, result in enumerate(results5):
                price = result.get('price', 0)
                price_rupees = price / 100
                title = result.get('title', 'N/A')
                
                # Check if title contains gaming-related terms
                gaming_terms = ['gaming', 'gamer', 'rtx', 'gtx', 'nvidia', 'radeon', 'ryzen']
                is_gaming = any(term.lower() in title.lower() for term in gaming_terms)
                
                if is_gaming:
                    gaming_related += 1
                    status = "🎮 GAMING"
                else:
                    status = "💻 REGULAR"
                
                print(f"  {i+1}. ₹{price_rupees:,.2f} - {title[:60]} {status}")
            
            print(f"\n   📊 Gaming-related laptops found: {gaming_related}")
        
    except Exception as e:
        print(f"❌ Test 5 failed: {e}")
    
    print("\n" + "=" * 80)
    print("🎯 ANALYSIS OF PA-API vs AMAZON.IN DISCREPANCY")
    print("=" * 80)
    
    print("Possible reasons for different results:")
    print("1. 🔍 PA-API search algorithm differs from Amazon web search")
    print("2. 📊 PA-API may have limited product access compared to web")
    print("3. 🏷️  'Gaming laptop' as exact phrase may be too restrictive")
    print("4. 📋 PA-API may prioritize different ranking factors")
    print("5. 🛒 PA-API may filter out certain seller types")
    print("6. 💰 Price range filtering may interact differently with search")
    
    print("\n💡 RECOMMENDATIONS:")
    print("- Try broader keywords like 'laptop' + price filters")
    print("- Use multiple search strategies for better coverage")
    print("- Consider that PA-API != Amazon web search")
    print("- Test different search indices (All vs Electronics)")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(debug_search_comparison())
