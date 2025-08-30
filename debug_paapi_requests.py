#!/usr/bin/env python3
"""
Debug PA-API requests to understand exactly what's being sent
"""

import asyncio
from unittest.mock import patch
from bot.paapi_official import OfficialPaapiClient
from bot.config import settings

async def debug_paapi_requests():
    """Debug what PA-API requests are actually being sent"""

    client = OfficialPaapiClient()

    # Patch the actual API call to see what gets sent
    original_method = None

    def capture_request(*args, **kwargs):
        print(f"\n{'='*80}")
        print("PA-API REQUEST CAPTURED:")
        print(f"Method: {original_method}")
        print(f"Args: {args}")
        print(f"Kwargs: {kwargs}")
        print(f"{'='*80}")

        # Try to extract the request body if it's there
        if args and len(args) > 1:
            request_obj = args[1]  # Usually the SearchItemsRequest object
            if hasattr(request_obj, 'to_dict'):
                request_dict = request_obj.to_dict()
                print(f"REQUEST BODY: {request_dict}")

        print(f"{'='*80}\n")
        # Try to make the actual request to see what happens
        try:
            from paapi5_python_sdk.models.search_items_response import SearchItemsResponse
            from paapi5_python_sdk.models.search_result import SearchResult
            from paapi5_python_sdk.models.item import Item

            # Create a mock response that matches the expected structure
            mock_response = SearchItemsResponse()
            mock_response.search_result = SearchResult()
            mock_response.search_result.items = []

            print("RETURNING MOCK RESPONSE STRUCTURE")
            return mock_response
        except Exception as e:
            print(f"Error creating mock response: {e}")
            return {"Items": []}

    # Test different scenarios
    test_cases = [
        {
            "name": "Only max_price (should work)",
            "min_price": None,
            "max_price": 1000000,  # ₹10,000
            "keywords": "monitor"
        },
        {
            "name": "Both min and max (might not work)",
            "min_price": 200000,  # ₹2,000
            "max_price": 800000,  # ₹8,000
            "keywords": "monitor"
        }
    ]

    for test_case in test_cases:
        print(f"\n{'*'*60}")
        print(f"Testing: {test_case['name']}")
        print(f"Min: {test_case['min_price']}, Max: {test_case['max_price']}")
        print(f"{'*'*60}")

        # Patch the search_items method to capture the request
        with patch.object(client.api, 'search_items', side_effect=capture_request) as mock_method:
            original_method = "search_items"
            try:
                await client.search_items_advanced(
                    keywords=test_case['keywords'],
                    search_index='Electronics',
                    min_price=test_case['min_price'],
                    max_price=test_case['max_price'],
                    item_count=5
                )
            except Exception as e:
                print(f"Exception during test: {e}")

        print(f"Mock called: {mock_method.called}")
        print(f"Call count: {mock_method.call_count}")

if __name__ == "__main__":
    asyncio.run(debug_paapi_requests())
