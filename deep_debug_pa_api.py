#!/usr/bin/env python3
"""
Deep debug analysis of PA-API behavior with full request/response logging
"""

import asyncio
import json
import time
from datetime import datetime
from unittest.mock import patch
from bot.paapi_official import OfficialPaapiClient

# Storage for captured data
debug_data = {
    "timestamp": datetime.now().isoformat(),
    "tests": {}
}

def capture_api_request(test_name, original_method):
    """Decorator to capture API requests and responses"""
    
    def wrapper(self, *args, **kwargs):
        # Capture request details
        request_data = {
            "method": "search_items",
            "timestamp": datetime.now().isoformat(),
            "args": args,
            "kwargs": kwargs
        }
        
        # Extract SearchItemsRequest details if available
        request_details = {}
        if len(args) > 1:
            search_request = args[1]
            request_details = {
                "keywords": getattr(search_request, 'keywords', None),
                "search_index": getattr(search_request, 'search_index', None),
                "min_price": getattr(search_request, 'min_price', None),
                "max_price": getattr(search_request, 'max_price', None),
                "item_count": getattr(search_request, 'item_count', None),
                "item_page": getattr(search_request, 'item_page', None),
                "partner_tag": getattr(search_request, 'partner_tag', None),
                "partner_type": getattr(search_request, 'partner_type', None),
                "marketplace": getattr(search_request, 'marketplace', None),
                "resources": getattr(search_request, 'resources', None)
            }
            request_data["search_request"] = request_details
        
        print(f"\n🔍 API CALL [{test_name}] - Page {getattr(search_request, 'item_page', 1) if len(args) > 1 else 1}")
        print(f"   Keywords: {request_details.get('keywords', 'N/A')}")
        print(f"   Min Price: {request_details.get('min_price', 'None')}")
        print(f"   Max Price: {request_details.get('max_price', 'None')}")
        print(f"   Item Count: {request_details.get('item_count', 'N/A')}")
        print(f"   Page: {request_details.get('item_page', 'N/A')}")
        
        # Call original method
        start_time = time.time()
        try:
            response = original_method(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Capture response details
            response_data = {
                "success": True,
                "execution_time": execution_time,
                "has_results": hasattr(response, 'search_result') and response.search_result is not None,
                "items_count": 0
            }
            
            if hasattr(response, 'search_result') and response.search_result:
                if hasattr(response.search_result, 'items') and response.search_result.items:
                    response_data["items_count"] = len(response.search_result.items)
                    
                    # Extract item details for analysis
                    items_data = []
                    for item in response.search_result.items:
                        item_data = {
                            "asin": getattr(item, 'asin', None),
                            "title": None,
                            "price": None,
                            "currency": None
                        }
                        
                        # Extract title
                        if hasattr(item, 'item_info') and item.item_info:
                            if hasattr(item.item_info, 'title') and item.item_info.title:
                                item_data["title"] = getattr(item.item_info.title, 'display_value', None)
                        
                        # Extract price
                        if hasattr(item, 'offers') and item.offers:
                            if hasattr(item.offers, 'listings') and item.offers.listings:
                                for listing in item.offers.listings:
                                    if hasattr(listing, 'price') and listing.price:
                                        if hasattr(listing.price, 'amount'):
                                            item_data["price"] = listing.price.amount
                                        if hasattr(listing.price, 'currency'):
                                            item_data["currency"] = listing.price.currency
                                        break
                        
                        items_data.append(item_data)
                    
                    response_data["items"] = items_data
                    
                    # Print immediate analysis
                    print(f"   ✅ Response: {response_data['items_count']} items")
                    if items_data:
                        prices = [item['price'] for item in items_data if item['price'] is not None]
                        if prices:
                            min_price_response = min(prices) / 100
                            max_price_response = max(prices) / 100
                            print(f"   💰 Price Range: ₹{min_price_response:.2f} - ₹{max_price_response:.2f}")
                else:
                    print(f"   ❌ Response: No items in search result")
            else:
                print(f"   ❌ Response: No search result")
            
            # Store in debug data
            page_key = f"page_{getattr(search_request, 'item_page', 1) if len(args) > 1 else 1}"
            if test_name not in debug_data["tests"]:
                debug_data["tests"][test_name] = {}
            debug_data["tests"][test_name][page_key] = {
                "request": request_data,
                "response": response_data
            }
            
            return response
            
        except Exception as e:
            execution_time = time.time() - start_time
            print(f"   ❌ API Error: {str(e)}")
            
            # Store error in debug data
            page_key = f"page_{getattr(search_request, 'item_page', 1) if len(args) > 1 else 1}"
            if test_name not in debug_data["tests"]:
                debug_data["tests"][test_name] = {}
            debug_data["tests"][test_name][page_key] = {
                "request": request_data,
                "response": {
                    "success": False,
                    "error": str(e),
                    "execution_time": execution_time
                }
            }
            raise
    
    return wrapper

async def deep_debug_pa_api():
    """Deep debug analysis with full logging"""
    
    client = OfficialPaapiClient()
    
    print("🔬 DEEP PA-API DEBUG ANALYSIS")
    print("=" * 80)
    print("Query: 'Gaming monitor'")
    print("Price Range: ₹20,000 - ₹60,000")
    print("Pages: 3 pages")
    print("=" * 80)
    
    # Test 1: Min price only (₹20,000)
    print("\n🟦 TEST 1: MIN PRICE ONLY (₹20,000)")
    print("-" * 50)
    
    with patch.object(client.api, 'search_items', capture_api_request("min_price_only", client.api.search_items)):
        try:
            results_min = await client.search_items_advanced(
                keywords="Gaming monitor",
                search_index="Electronics",
                min_price=2000000,  # ₹20,000 in paise
                max_price=None,
                item_count=30,  # 3 pages * 10 items
                enable_ai_analysis=False
            )
            
            print(f"\n📊 MIN PRICE ONLY SUMMARY:")
            print(f"   Total Results: {len(results_min) if results_min else 0}")
            if results_min:
                prices = [r.get('price', 0)/100 for r in results_min if r.get('price')]
                if prices:
                    print(f"   Price Range: ₹{min(prices):.2f} - ₹{max(prices):.2f}")
                    print(f"   Avg Price: ₹{sum(prices)/len(prices):.2f}")
                    
                    # Check if all prices meet min criteria
                    below_min = [p for p in prices if p < 20000]
                    print(f"   Items below ₹20,000: {len(below_min)}")
                    
        except Exception as e:
            print(f"❌ Min price test failed: {e}")
    
    # Wait before next test
    await asyncio.sleep(3)
    
    # Test 2: Max price only (₹60,000)
    print("\n🟧 TEST 2: MAX PRICE ONLY (₹60,000)")
    print("-" * 50)
    
    with patch.object(client.api, 'search_items', capture_api_request("max_price_only", client.api.search_items)):
        try:
            results_max = await client.search_items_advanced(
                keywords="Gaming monitor",
                search_index="Electronics",
                min_price=None,
                max_price=6000000,  # ₹60,000 in paise
                item_count=30,  # 3 pages * 10 items
                enable_ai_analysis=False
            )
            
            print(f"\n📊 MAX PRICE ONLY SUMMARY:")
            print(f"   Total Results: {len(results_max) if results_max else 0}")
            if results_max:
                prices = [r.get('price', 0)/100 for r in results_max if r.get('price')]
                if prices:
                    print(f"   Price Range: ₹{min(prices):.2f} - ₹{max(prices):.2f}")
                    print(f"   Avg Price: ₹{sum(prices)/len(prices):.2f}")
                    
                    # Check if all prices meet max criteria
                    above_max = [p for p in prices if p > 60000]
                    print(f"   Items above ₹60,000: {len(above_max)}")
                    
        except Exception as e:
            print(f"❌ Max price test failed: {e}")
    
    # Wait before next test
    await asyncio.sleep(3)
    
    # Test 3: Both filters (₹20,000 - ₹60,000)
    print("\n🟨 TEST 3: BOTH FILTERS (₹20,000 - ₹60,000)")
    print("-" * 50)
    
    # Temporarily modify to send both to PA-API
    original_both_logic = client._sync_search_items
    
    def modified_both_logic(self, *args, **kwargs):
        # Force both parameters to be sent to PA-API
        if len(args) > 1:
            search_request = args[1]
            # Ensure both parameters are set
            if hasattr(search_request, 'min_price') and hasattr(search_request, 'max_price'):
                if search_request.min_price and not search_request.max_price:
                    search_request.max_price = 600.0  # ₹60,000 in rupees
                    print(f"   🔧 FORCING max_price to be sent: {search_request.max_price}")
        
        return original_both_logic(*args, **kwargs)
    
    with patch.object(client.api, 'search_items', capture_api_request("both_filters", client.api.search_items)):
        try:
            results_both = await client.search_items_advanced(
                keywords="Gaming monitor",
                search_index="Electronics",
                min_price=2000000,  # ₹20,000 in paise
                max_price=6000000,  # ₹60,000 in paise
                item_count=30,  # 3 pages * 10 items
                enable_ai_analysis=False
            )
            
            print(f"\n📊 BOTH FILTERS SUMMARY:")
            print(f"   Total Results: {len(results_both) if results_both else 0}")
            if results_both:
                prices = [r.get('price', 0)/100 for r in results_both if r.get('price')]
                if prices:
                    print(f"   Price Range: ₹{min(prices):.2f} - ₹{max(prices):.2f}")
                    print(f"   Avg Price: ₹{sum(prices)/len(prices):.2f}")
                    
                    # Check if all prices meet both criteria
                    out_of_range = [p for p in prices if p < 20000 or p > 60000]
                    print(f"   Items outside ₹20,000-₹60,000: {len(out_of_range)}")
                    
        except Exception as e:
            print(f"❌ Both filters test failed: {e}")
    
    # Save debug data to file
    with open('pa_api_debug_data.json', 'w', encoding='utf-8') as f:
        json.dump(debug_data, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 80)
    print("🎯 DEEP ANALYSIS RESULTS")
    print("=" * 80)
    
    # Comparative analysis
    min_count = len(results_min) if 'results_min' in locals() and results_min else 0
    max_count = len(results_max) if 'results_max' in locals() and results_max else 0
    both_count = len(results_both) if 'results_both' in locals() and results_both else 0
    
    print(f"Results Count Comparison:")
    print(f"  Min price only:  {min_count} results")
    print(f"  Max price only:  {max_count} results")
    print(f"  Both filters:    {both_count} results")
    
    print(f"\nLogical Expectations:")
    print(f"  If both filters work: both_count ≤ min(min_count, max_count)")
    print(f"  If max ignored: both_count = min_count")
    print(f"  If both ignored: both_count = no_filter_count")
    
    # Determine what's happening
    if both_count == 0 and min_count > 0:
        print(f"\n❌ CONCLUSION: PA-API rejects both filters together")
        print(f"   WHY: API validation might fail when both parameters present")
    elif both_count == min_count and max_count == 0:
        print(f"\n❌ CONCLUSION: max_price parameter is ignored/invalid")
        print(f"   WHY: max_price might not be supported in this marketplace/region")
    elif both_count < min_count and both_count > 0:
        print(f"\n✅ CONCLUSION: Both filters work at PA-API level!")
        print(f"   WHY: Our implementation was incorrect")
    else:
        print(f"\n🤔 CONCLUSION: Unexpected behavior - needs further investigation")
    
    print(f"\n📁 Detailed debug data saved to: pa_api_debug_data.json")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(deep_debug_pa_api())
