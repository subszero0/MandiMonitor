#!/usr/bin/env python3
"""Automatic test for scraper functionality with Amazon URLs."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

async def test_scraper_functionality():
    """Test the enhanced scraper with real Amazon URLs."""
    print("🧪 Testing Enhanced Scraper Functionality\n")
    
    # Test ASIN from user's screenshot
    test_asin = "B09XYZ1234"
    test_url = f"https://amazon.in/dp/{test_asin}"
    
    print(f"🎯 Testing ASIN: {test_asin}")
    print(f"🔗 URL: {test_url}\n")
    
    try:
        # Test 1: Import modules
        print("📦 Testing module imports...")
        from bot.scraper import scrape_product_data, scrape_price
        from bot.paapi_wrapper import get_item
        from bot.cache_service import get_price
        print("✅ All modules imported successfully\n")
        
        # Test 2: Test scrape_product_data directly
        print("🔍 Testing scrape_product_data()...")
        try:
            product_data = scrape_product_data(test_asin)
            print(f"✅ Scraper returned:")
            print(f"   📱 Title: {product_data.get('title', 'None')}")
            print(f"   💰 Price: {product_data.get('price', 'None')}")
            print(f"   🖼️ Image: {'Yes' if product_data.get('image') else 'None'}")
            print(f"   🆔 ASIN: {product_data.get('asin', 'None')}")
            
            if product_data.get('title') and product_data['title'] != f"Product {test_asin}":
                print("✅ Successfully extracted product title!")
            else:
                print("⚠️ Could not extract meaningful product title")
                
            if product_data.get('price'):
                print("✅ Successfully extracted price!")
            else:
                print("⚠️ Could not extract price")
                
        except Exception as e:
            print(f"❌ Scraper failed: {e}")
            
        print()
        
        # Test 3: Test PA-API (should fail without credentials)
        print("🔍 Testing PA-API (expected to fail without credentials)...")
        try:
            item_data = await get_item(test_asin)
            print(f"✅ PA-API returned: {item_data}")
        except Exception as e:
            print(f"⚠️ PA-API failed as expected: {e}")
            
        print()
        
        # Test 4: Test cache service integration
        print("🔍 Testing cache service integration...")
        try:
            price = get_price(test_asin)
            print(f"✅ Cache service returned price: {price}")
        except Exception as e:
            print(f"⚠️ Cache service failed: {e}")
            
        print()
        
        # Test 5: Test ASIN extraction from URL
        print("🔍 Testing ASIN extraction from URL...")
        from bot.patterns import PAT_ASIN
        import re
        
        test_urls = [
            "https://amazon.in/dp/B09XYZ1234",
            "https://www.amazon.in/dp/B09XYZ1234?ref=something",
            "B09XYZ1234"
        ]
        
        for url in test_urls:
            match = PAT_ASIN.search(url)
            if match:
                extracted_asin = match.group(1) if match.group(1) else match.group(2)
                print(f"✅ From '{url}' → ASIN: {extracted_asin}")
            else:
                print(f"❌ Could not extract ASIN from: {url}")
                
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        
    print("\n🎯 Test Summary:")
    print("If scraper extracted title and/or price, the fix should work!")
    print("If all extractions failed, check Amazon's current page structure.")
    print("\n🚀 Next: Restart bot and test with real Amazon link")

if __name__ == "__main__":
    asyncio.run(test_scraper_functionality())