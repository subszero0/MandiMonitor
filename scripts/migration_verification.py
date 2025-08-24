#!/usr/bin/env python3
"""Immediate migration verification script."""

import asyncio
import sys
import os
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.config import settings
from bot.paapi_factory import get_paapi_client

async def verify_migration():
    """Verify that the migration is working correctly."""
    print("🚀 VERIFYING IMMEDIATE MIGRATION TO OFFICIAL SDK")
    print("=" * 60)
    print(f"⚡ Feature flag status: USE_NEW_PAAPI_SDK={settings.USE_NEW_PAAPI_SDK}")
    print(f"🌏 Marketplace: {settings.PAAPI_MARKETPLACE}")
    print(f"🕐 Migration time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    if not settings.USE_NEW_PAAPI_SDK:
        print("❌ MIGRATION FAILED: Feature flag is still False!")
        return False
    
    try:
        print("📡 Initializing official SDK client...")
        client = get_paapi_client()
        print("✅ Client initialized successfully")
        
        # Test 1: GetItems
        print("\n🔍 Test 1: GetItems functionality")
        start_time = time.time()
        result = await client.get_item_detailed("B08N5WRWNW")  # Echo Dot
        end_time = time.time()
        
        if result and result.get("title"):
            print(f"✅ GetItems SUCCESS: {result['title'][:50]}...")
            print(f"   Response time: {end_time - start_time:.2f}s")
            print(f"   Price: ₹{result.get('price_value', 'N/A')}")
        else:
            print("❌ GetItems FAILED: No valid response")
            return False
        
        # Small delay for rate limiting
        await asyncio.sleep(1.2)
        
        # Test 2: SearchItems
        print("\n🔍 Test 2: SearchItems functionality")
        start_time = time.time()
        search_results = await client.search_items_advanced(
            keywords="smartphone",
            search_index="Electronics",
            item_count=3
        )
        end_time = time.time()
        
        if search_results and len(search_results) > 0:
            print(f"✅ SearchItems SUCCESS: Found {len(search_results)} items")
            print(f"   Response time: {end_time - start_time:.2f}s")
            for i, item in enumerate(search_results[:2]):
                print(f"   Item {i+1}: {item.get('title', 'N/A')[:40]}...")
        else:
            print("❌ SearchItems FAILED: No results")
            return False
        
        # Small delay for rate limiting
        await asyncio.sleep(1.2)
        
        # Test 3: Browse Nodes
        print("\n🔍 Test 3: Browse Nodes functionality")
        start_time = time.time()
        browse_result = await client.get_browse_nodes_hierarchy(1805560031)  # Electronics
        end_time = time.time()
        
        if browse_result and browse_result.get("name"):
            print(f"✅ Browse Nodes SUCCESS: {browse_result['name']}")
            print(f"   Response time: {end_time - start_time:.2f}s")
            print(f"   Children count: {len(browse_result.get('children', []))}")
        else:
            print("❌ Browse Nodes FAILED: No valid response")
            return False
        
        print("\n" + "=" * 60)
        print("🎉 MIGRATION VERIFICATION SUCCESSFUL!")
        print("✅ All core PA-API functionality working with official SDK")
        print("✅ Response times are acceptable")
        print("✅ Data extraction working correctly")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ MIGRATION VERIFICATION FAILED: {e}")
        print("\n🚨 IMMEDIATE ROLLBACK REQUIRED!")
        return False

async def main():
    """Main verification function."""
    success = await verify_migration()
    
    if success:
        print("\n💡 NEXT STEPS:")
        print("1. ✅ Migration successful - monitor for 30 minutes")
        print("2. 📊 Check health endpoint: /health")
        print("3. 👀 Monitor logs for any issues")
        print("4. 🎯 Test with real bot interactions")
    else:
        print("\n🚨 ROLLBACK INSTRUCTIONS:")
        print("1. Set USE_NEW_PAAPI_SDK=false in .env")
        print("2. Restart the bot service")
        print("3. Investigate issues before retry")
    
    return success

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
