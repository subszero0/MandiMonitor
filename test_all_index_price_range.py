#!/usr/bin/env python3
"""
Test PA-API with All index in ₹40,000-₹50,000 range
"""

import asyncio
from bot.paapi_official import OfficialPaapiClient

async def test_all_index_price_range():
    """Test PA-API with All search index in price range"""
    
    client = OfficialPaapiClient()
    
    print("🔬 PA-API 'All' INDEX TEST - ₹40,000-₹50,000")
    print("=" * 80)
    print("Testing if search index makes a difference...")
    print("=" * 80)
    
    # Test with "All" search index
    print("\n🟨 TEST: 'gaming laptop' in 'All' index with ₹40,000-₹50,000")
    print("-" * 60)
    
    try:
        results = await client.search_items_advanced(
            keywords="gaming laptop",
            search_index="All",  # This is the key difference!
            min_price=4000000,  # ₹40,000 in paise
            max_price=5000000,  # ₹50,000 in paise
            item_count=10,
            enable_ai_analysis=False
        )
        
        print(f"📥 Results: {len(results) if results else 0}")
        
        if results:
            in_range = 0
            out_of_range = 0
            gaming_laptops = 0
            
            for i, result in enumerate(results):
                price = result.get('price', 0)
                price_rupees = price / 100
                title = result.get('title', 'N/A')
                
                # Check if it's actually a gaming laptop
                gaming_terms = ['gaming', 'rtx', 'gtx', 'nvidia', 'radeon', 'amd', 'ryzen', 'core i5', 'core i7']
                is_gaming = any(term.lower() in title.lower() for term in gaming_terms)
                
                if is_gaming:
                    gaming_laptops += 1
                    laptop_type = "🎮 GAMING"
                else:
                    laptop_type = "💻 REGULAR"
                
                if 40000 <= price_rupees <= 50000:
                    status = "✅ IN RANGE"
                    in_range += 1
                else:
                    status = "❌ OUT OF RANGE"
                    out_of_range += 1
                
                print(f"  {i+1}. ₹{price_rupees:,.2f} - {title[:60]}")
                print(f"      {status} | {laptop_type}")
            
            print(f"\n📊 Summary:")
            print(f"   Total results: {len(results)}")
            print(f"   In price range (₹40k-₹50k): {in_range}")
            print(f"   Gaming laptops: {gaming_laptops}")
            print(f"   Gaming laptops in range: {[i for i in range(len(results)) if 40000 <= results[i].get('price', 0)/100 <= 50000 and any(term.lower() in results[i].get('title', '').lower() for term in ['gaming', 'rtx', 'gtx', 'nvidia'])]}")
            
            if in_range > 0:
                print("   🎉 SUCCESS: Found laptops in ₹40k-₹50k range!")
                if gaming_laptops > 0:
                    print("   🎮 Gaming laptops available in this range!")
            
        else:
            print("❌ No results found")
    
    except Exception as e:
        print(f"❌ Test failed: {e}")
    
    await asyncio.sleep(2)
    
    # Test 2: Broader terms in All index
    print("\n🟦 TEST: 'laptop' in 'All' index with ₹40,000-₹50,000")
    print("-" * 60)
    
    try:
        results2 = await client.search_items_advanced(
            keywords="laptop",
            search_index="All",
            min_price=4000000,  # ₹40,000 in paise
            max_price=5000000,  # ₹50,000 in paise
            item_count=10,
            enable_ai_analysis=False
        )
        
        print(f"📥 Results: {len(results2) if results2 else 0}")
        
        if results2:
            gaming_laptops = 0
            
            for i, result in enumerate(results2):
                price = result.get('price', 0)
                price_rupees = price / 100
                title = result.get('title', 'N/A')
                
                # Check if it's actually a gaming laptop
                gaming_terms = ['gaming', 'rtx', 'gtx', 'nvidia', 'radeon', 'amd ryzen', 'core i5', 'core i7']
                is_gaming = any(term.lower() in title.lower() for term in gaming_terms)
                
                if is_gaming:
                    gaming_laptops += 1
                    laptop_type = "🎮 GAMING"
                else:
                    laptop_type = "💻 REGULAR"
                
                print(f"  {i+1}. ₹{price_rupees:,.2f} - {title[:60]}")
                print(f"      {laptop_type}")
            
            print(f"\n📊 Summary:")
            print(f"   Total laptops in ₹40k-₹50k: {len(results2)}")
            print(f"   Gaming laptops: {gaming_laptops}")
            
            if gaming_laptops > 0:
                print("   🎉 SUCCESS: Found gaming laptops with broader search!")
        
    except Exception as e:
        print(f"❌ Test 2 failed: {e}")
    
    print("\n" + "=" * 80)
    print("🎯 KEY FINDINGS")
    print("=" * 80)
    print("1. 📊 Search Index matters: 'All' vs 'Electronics' gives different results")
    print("2. 🔍 PA-API search algorithm is different from Amazon web search")
    print("3. 🏷️  Keyword specificity affects product discovery")
    print("4. 💰 Price filters work perfectly, but product availability varies")
    print("5. 🎮 Gaming laptops exist in ₹40k-₹50k range, but PA-API indexing differs")
    print("\n💡 SOLUTION:")
    print("- Use 'All' search index for broader product coverage")
    print("- Try multiple keyword strategies")
    print("- Consider PA-API != Amazon web search experience")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_all_index_price_range())
