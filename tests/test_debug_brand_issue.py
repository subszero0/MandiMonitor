"""Debug the brand extraction issue."""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from bot.watch_flow import _finalize_watch
from bot.paapi_ai_bridge import create_mock_paapi_item_from_result, transform_paapi_to_ai_format


class TestDebugBrandIssue:
    """Debug the specific brand extraction issue."""

    @pytest.mark.asyncio
    async def test_debug_brand_extraction(self):
        """Debug exactly what's happening with brand extraction."""
        
        # Create a test product like the ones generated in the simulation
        test_product = {
            "asin": "B12345678",
            "title": "Samsung 27 inch Gaming Monitor",
            "price": 45000,
            "image": "https://example.com/image.jpg",
            "features": ["27 inch display", "Gaming"],
            "brand": "Samsung"  # This should be extracted
        }
        
        print(f"Original product: {test_product}")
        
        try:
            # Test the mock item creation
            mock_item = create_mock_paapi_item_from_result(test_product)
            print(f"Mock item created: {type(mock_item)}")
            print(f"Mock item has item_info: {hasattr(mock_item, 'item_info')}")
            print(f"Mock item_info has by_line_info: {hasattr(mock_item.item_info, 'by_line_info')}")
            print(f"Mock by_line_info has brand: {hasattr(mock_item.item_info.by_line_info, 'brand')}")
            print(f"Mock brand value: {mock_item.item_info.by_line_info.brand}")
            
            # Test the transformation
            ai_product = await transform_paapi_to_ai_format(mock_item)
            print(f"AI product: {ai_product}")
            
        except Exception as e:
            print(f"ERROR during transformation: {e}")
            import traceback
            traceback.print_exc()

    @pytest.mark.asyncio
    async def test_debug_full_flow(self):
        """Debug the full flow to see where it breaks."""
        
        mock_update = MagicMock()
        mock_update.effective_user.id = 999999
        mock_update.effective_chat.send_message = AsyncMock()
        mock_update.effective_chat.send_photo = AsyncMock()
        mock_context = MagicMock()
        mock_context.user_data = {}
        
        watch_data = {
            "asin": None,
            "brand": None,
            "max_price": 50000,
            "keywords": "gaming monitor",
            "mode": "daily"
        }
        
        # Create realistic products
        products = [
            {
                "asin": "B12345678",
                "title": "Samsung Gaming Monitor",
                "price": 45000,
                "image": "https://example.com/image.jpg",
                "features": ["Gaming", "27 inch"],
                "brand": "Samsung"
            }
        ]
        
        print(f"Test products: {products}")
        
        with patch('bot.watch_flow._cached_search_items_advanced', return_value=products):
            with patch('bot.cache_service.get_price', return_value=45000):
                try:
                    await _finalize_watch(mock_update, mock_context, watch_data)
                    print("✅ Flow completed successfully")
                except Exception as e:
                    print(f"❌ Flow failed: {e}")
                    import traceback
                    traceback.print_exc()


if __name__ == "__main__":
    import asyncio
    
    test = TestDebugBrandIssue()
    asyncio.run(test.test_debug_brand_extraction())
