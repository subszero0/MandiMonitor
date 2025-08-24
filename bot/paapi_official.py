"""Official Amazon PA-API SDK wrapper implementation.

This module provides a parallel implementation using the official paapi5-python-sdk
to replace the current third-party amazon-paapi implementation. Built according
to the migration roadmap in paapi_corrections.md.
"""

import asyncio
from logging import getLogger
from typing import Dict, List, Optional

from paapi5_python_sdk.api.default_api import DefaultApi
from paapi5_python_sdk.models.condition import Condition
from paapi5_python_sdk.models.get_items_request import GetItemsRequest
from paapi5_python_sdk.models.get_items_resource import GetItemsResource
from paapi5_python_sdk.models.partner_type import PartnerType
from paapi5_python_sdk.models.search_items_request import SearchItemsRequest
from paapi5_python_sdk.models.search_items_resource import SearchItemsResource
from paapi5_python_sdk.models.search_index import SearchIndex
from paapi5_python_sdk.models.get_browse_nodes_request import GetBrowseNodesRequest
from paapi5_python_sdk.models.get_browse_nodes_resource import GetBrowseNodesResource
from paapi5_python_sdk.rest import ApiException

from .api_rate_limiter import acquire_api_permission
from .config import settings
from .errors import QuotaExceededError
from .paapi_resource_manager import get_resource_manager

log = getLogger(__name__)


class OfficialPaapiClient:
    """Official Amazon PA-API SDK client wrapper.
    
    This class provides the same interface as the existing PA-API implementation
    but uses the official paapi5-python-sdk for better reliability and rate limit compliance.
    """

    def __init__(self):
        """Initialize the official PA-API client with proper regional configuration."""
        if not all([
            settings.PAAPI_ACCESS_KEY,
            settings.PAAPI_SECRET_KEY, 
            settings.PAAPI_TAG
        ]):
            raise ValueError("PA-API credentials must be configured")
            
        self.api = DefaultApi(
            access_key=settings.PAAPI_ACCESS_KEY,
            secret_key=settings.PAAPI_SECRET_KEY,
            host=settings.PAAPI_HOST,  # "webservices.amazon.in"
            region=settings.PAAPI_REGION,  # "eu-west-1" 
        )
        
        # Initialize resource manager
        self.resource_manager = get_resource_manager()
        
    async def get_item_detailed(
        self, asin: str, resources: Optional[List[str]] = None, priority: str = "normal"
    ) -> Dict:
        """Get comprehensive product information from PA-API.

        Args:
        ----
            asin: Amazon Standard Identification Number
            resources: List of PA-API resources to fetch (ignored for now, using defaults)
            priority: Request priority for rate limiting

        Returns:
        -------
            Dict with comprehensive product information

        Raises:
        ------
            QuotaExceededError: When PA-API quota is exceeded
        """
        await acquire_api_permission(priority)

        try:
            result = await asyncio.to_thread(self._sync_get_item_detailed, asin)
            return result
        except ApiException as exc:
            if exc.status in [503, 429]:
                log.warning("PA-API quota exceeded for ASIN: %s", asin)
                raise QuotaExceededError(f"PA-API quota exceeded for {asin}") from exc
            log.error("PA-API error for ASIN %s: %s", asin, exc)
            log.error("Request ID: %s", exc.headers.get("x-amzn-RequestId", "N/A"))
            raise
        except Exception as exc:
            log.error("Unexpected PA-API error for ASIN %s: %s", asin, exc)
            raise

    def _sync_get_item_detailed(self, asin: str) -> Dict:
        """Synchronous detailed PA-API call using official SDK."""
        # Get appropriate resources from resource manager
        resources = self.resource_manager.get_detailed_resources("get_items")
        
        # Create the request object with proper marketplace configuration
        get_items_request = GetItemsRequest(
            partner_tag=settings.PAAPI_TAG,
            partner_type=PartnerType.ASSOCIATES,
            marketplace=settings.PAAPI_MARKETPLACE,  # "www.amazon.in"
            condition=Condition.NEW,
            item_ids=[asin],
            resources=resources
        )

        try:
            response = self.api.get_items(get_items_request)
            
            if not response.items_result or not response.items_result.items:
                raise ValueError(f"No item found for ASIN: {asin}")

            item = response.items_result.items[0]
            return self._extract_comprehensive_data(item)

        except ApiException as e:
            log.error("Official PA-API detailed call failed for ASIN %s: Status %s, Body: %s", asin, e.status, e.body)
            log.error("Request ID: %s", e.headers.get("x-amzn-RequestId", "N/A"))
            raise
        except Exception as e:
            log.error("Official PA-API detailed call failed for ASIN %s: %s", asin, e)
            raise

    async def search_items_advanced(
        self,
        keywords: Optional[str] = None,
        title: Optional[str] = None,
        brand: Optional[str] = None,
        search_index: str = "All",
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        min_reviews_rating: Optional[float] = None,
        min_savings_percent: Optional[int] = None,
        merchant: str = "All",
        condition: str = "New",
        item_count: int = 10,
        item_page: int = 1,
        sort_by: Optional[str] = None,
        browse_node_id: Optional[int] = None,
        priority: str = "normal",
    ) -> List[Dict]:
        """Advanced product search using official SDK.

        Args:
        ----
            keywords: Search keywords
            title: Search by product title (combined with keywords)
            brand: Search by brand name (combined with keywords)
            search_index: Product category to search within
            min_price: Minimum price in paise (converted to rupees)
            max_price: Maximum price in paise (converted to rupees)
            min_reviews_rating: Minimum review rating (1-5)
            min_savings_percent: Minimum discount percentage
            merchant: "Amazon" or "All" (ignored for now)
            condition: "New", "Used", "Refurbished"
            item_count: Number of items to return (1-10)
            item_page: Page number (1-10)
            sort_by: Sort criteria (ignored for now)
            browse_node_id: Specific category ID (ignored for now)
            priority: Request priority for rate limiting

        Returns:
        -------
            List of product dictionaries

        Raises:
        ------
            QuotaExceededError: When PA-API quota is exceeded
        """
        if not keywords and not title and not brand:
            log.warning("Search requires at least keywords, title, or brand")
            return []

        await acquire_api_permission(priority)

        try:
            result = await asyncio.to_thread(
                self._sync_search_items,
                keywords=keywords,
                title=title,
                brand=brand,
                search_index=search_index,
                min_price=min_price,
                max_price=max_price,
                min_reviews_rating=min_reviews_rating,
                min_savings_percent=min_savings_percent,
                condition=condition,
                item_count=item_count,
                item_page=item_page,
            )
            return result
        except ApiException as exc:
            if exc.status in [503, 429]:
                log.warning("PA-API quota exceeded for search: %s", keywords)
                raise QuotaExceededError(f"PA-API quota exceeded for search: {keywords}") from exc
            log.error("PA-API search error: %s", exc)
            log.error("Request ID: %s", exc.headers.get("x-amzn-RequestId", "N/A"))
            raise
        except Exception as exc:
            log.error("Unexpected PA-API search error: %s", exc)
            raise

    def _sync_search_items(
        self,
        keywords: Optional[str] = None,
        title: Optional[str] = None,
        brand: Optional[str] = None,
        search_index: str = "All",
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        min_reviews_rating: Optional[float] = None,
        min_savings_percent: Optional[int] = None,
        condition: str = "New",
        item_count: int = 10,
        item_page: int = 1,
    ) -> List[Dict]:
        """Synchronous search using official SDK."""
        # Combine search terms
        search_terms = []
        if keywords:
            search_terms.append(keywords)
        if title:
            search_terms.append(title)
        if brand:
            search_terms.append(brand)
        
        final_keywords = " ".join(search_terms)
        
        # Map condition
        condition_map = {
            "New": Condition.NEW,
            "Used": Condition.USED,
            "Refurbished": Condition.REFURBISHED,
        }
        api_condition = condition_map.get(condition, Condition.NEW)
        
        # Get appropriate resources from resource manager
        resources = self.resource_manager.get_detailed_resources("search_items")
        
        # Create the search request
        search_items_request = SearchItemsRequest(
            partner_tag=settings.PAAPI_TAG,
            partner_type=PartnerType.ASSOCIATES,
            marketplace=settings.PAAPI_MARKETPLACE,  # "www.amazon.in"
            keywords=final_keywords,
            search_index=search_index,
            condition=api_condition,
            item_count=min(item_count, 10),  # Max 10 per request
            item_page=item_page,
            resources=resources
        )
        
        # Add price filters if specified (convert paise to rupees)
        # Note: PA-API expects price in currency units (rupees for INR)
        # min_price and max_price are in paise, so divide by 100
        # TODO: Implement price filtering when available in SDK
        
        # Add review rating filter if specified
        # TODO: Implement review rating filtering when available in SDK
        
        # Add savings percent filter if specified
        # TODO: Implement savings filtering when available in SDK

        try:
            response = self.api.search_items(search_items_request)
            
            if not response.search_result or not response.search_result.items:
                log.info("No items found for search: %s", final_keywords)
                return []

            items = []
            for item in response.search_result.items:
                items.append(self._extract_search_data(item))
            
            return items

        except ApiException as e:
            log.error("Official PA-API search failed: Status %s, Body: %s", e.status, e.body)
            log.error("Request ID: %s", e.headers.get("x-amzn-RequestId", "N/A"))
            raise
        except Exception as e:
            log.error("Official PA-API search failed: %s", e)
            raise

    def _extract_comprehensive_data(self, item) -> Dict:
        """Extract comprehensive data from official SDK item response.
        
        This method maps the official SDK response structure to our expected format,
        ensuring compatibility with existing code that uses the data.
        """
        data = {
            "asin": item.asin if item.asin else "",
            "title": "",
            "brand": None,
            "manufacturer": None,
            "product_group": None,
            "binding": None,
            "features": [],
            "color": None,
            "size": None,
            "item_dimensions": None,
            "item_weight": None,
            "is_adult_product": False,
            "technical_details": {},
            "ean": None,
            "isbn": None,
            "upc": None,
            "languages": [],
            "page_count": None,
            "publication_date": None,
            "images": {"small": "", "medium": "", "large": "", "variants": []},
            "offers": {
                "price": None,
                "list_price": None,
                "savings": None,
                "savings_percent": None,
                "availability": "Unknown",
                "condition": "New",
                "merchant": "Amazon.in",
                "prime": False,
                "shipping": None,
            },
            "reviews": {
                "rating": None,
                "count": None,
            },
            "categories": [],
            "rank": None,
            "detail_page_url": "",
        }

        # Extract basic item information
        if item.item_info:
            if item.item_info.title:
                data["title"] = item.item_info.title.display_value or ""
                
            if item.item_info.by_line_info:
                data["brand"] = item.item_info.by_line_info.brand.display_value if item.item_info.by_line_info.brand else None
                data["manufacturer"] = item.item_info.by_line_info.manufacturer.display_value if item.item_info.by_line_info.manufacturer else None
                
            if item.item_info.features:
                data["features"] = item.item_info.features.display_values if item.item_info.features.display_values else []
                
            if item.item_info.product_info:
                data["color"] = item.item_info.product_info.color.display_value if hasattr(item.item_info.product_info, 'color') and item.item_info.product_info.color else None
                data["size"] = item.item_info.product_info.size.display_value if hasattr(item.item_info.product_info, 'size') and item.item_info.product_info.size else None
                data["item_weight"] = item.item_info.product_info.item_weight.display_value if hasattr(item.item_info.product_info, 'item_weight') and item.item_info.product_info.item_weight else None
                data["is_adult_product"] = item.item_info.product_info.is_adult_product.display_value if hasattr(item.item_info.product_info, 'is_adult_product') and item.item_info.product_info.is_adult_product else False
                
            if item.item_info.technical_info:
                # TODO: Extract technical details based on available fields
                pass
                
            if item.item_info.external_ids:
                data["ean"] = item.item_info.external_ids.ean.display_value if hasattr(item.item_info.external_ids, 'ean') and item.item_info.external_ids.ean else None
                data["isbn"] = item.item_info.external_ids.isbn.display_value if hasattr(item.item_info.external_ids, 'isbn') and item.item_info.external_ids.isbn else None
                data["upc"] = item.item_info.external_ids.upc.display_value if hasattr(item.item_info.external_ids, 'upc') and item.item_info.external_ids.upc else None

        # Extract pricing information from offersV2
        if item.offers_v2 and item.offers_v2.listings:
            offer = item.offers_v2.listings[0]  # Take the first offer
            
            # Offers are returned as dictionaries in the response
            if isinstance(offer, dict):
                # Extract price
                if 'Price' in offer and 'Money' in offer['Price']:
                    # Convert to paise (multiply by 100)
                    data["offers"]["price"] = int(offer['Price']['Money']['Amount'] * 100)
                    
                # Extract list price (savings basis)
                if 'Price' in offer and 'SavingBasis' in offer['Price'] and 'Money' in offer['Price']['SavingBasis']:
                    data["offers"]["list_price"] = int(offer['Price']['SavingBasis']['Money']['Amount'] * 100)
                    
                # Extract savings information
                if 'Price' in offer and 'Savings' in offer['Price']:
                    savings = offer['Price']['Savings']
                    if 'Money' in savings:
                        data["offers"]["savings"] = int(savings['Money']['Amount'] * 100)
                    if 'Percentage' in savings:
                        data["offers"]["savings_percent"] = savings['Percentage']
                        
                # Extract availability
                if 'Availability' in offer and 'Message' in offer['Availability']:
                    data["offers"]["availability"] = offer['Availability']['Message']
                    
                # Extract condition
                if 'Condition' in offer and 'Value' in offer['Condition']:
                    data["offers"]["condition"] = offer['Condition']['Value']
                    
                # Extract merchant info
                if 'MerchantInfo' in offer and 'Name' in offer['MerchantInfo']:
                    data["offers"]["merchant"] = offer['MerchantInfo']['Name']
            else:
                # Fallback for object-style access (in case the structure changes)
                if hasattr(offer, 'price') and offer.price and hasattr(offer.price, 'money'):
                    data["offers"]["price"] = int(offer.price.money.amount * 100)
                    
                if hasattr(offer, 'price') and offer.price and hasattr(offer.price, 'saving_basis') and offer.price.saving_basis and hasattr(offer.price.saving_basis, 'money'):
                    data["offers"]["list_price"] = int(offer.price.saving_basis.money.amount * 100)

        # Extract images
        if item.images and item.images.primary:
            if item.images.primary.small:
                data["images"]["small"] = item.images.primary.small.url
            if item.images.primary.medium:
                data["images"]["medium"] = item.images.primary.medium.url
            if item.images.primary.large:
                data["images"]["large"] = item.images.primary.large.url
                
        # Extract customer reviews
        if item.customer_reviews:
            if item.customer_reviews.star_rating:
                data["reviews"]["rating"] = item.customer_reviews.star_rating.value
            if item.customer_reviews.count:
                data["reviews"]["count"] = item.customer_reviews.count

        # Extract categories from browse node info
        if item.browse_node_info and item.browse_node_info.browse_nodes:
            for node in item.browse_node_info.browse_nodes:
                data["categories"].append({
                    "id": node.id,
                    "name": node.display_name,
                    "is_root": node.is_root if hasattr(node, 'is_root') else False,
                })

        # Set detail page URL
        if item.detail_page_url:
            data["detail_page_url"] = item.detail_page_url

        # Map offers data to main data fields for backward compatibility
        if data["offers"]["price"]:
            data["price"] = data["offers"]["price"]
        if data["offers"]["availability"]:
            data["availability"] = data["offers"]["availability"]
        if data["offers"]["price"]:
            data["currency"] = "INR"  # India marketplace always uses INR
        
        # Map primary image to main image_url field
        if data["images"]["large"]:
            data["image_url"] = data["images"]["large"]
        elif data["images"]["medium"]:
            data["image_url"] = data["images"]["medium"]
        elif data["images"]["small"]:
            data["image_url"] = data["images"]["small"]

        return data

    def _extract_search_data(self, item) -> Dict:
        """Extract data from search result item (simplified version)."""
        data = {
            "asin": item.asin if item.asin else "",
            "title": "",
            "price": None,
            "list_price": None,
            "savings_percent": None,
            "rating": None,
            "review_count": None,
            "image_url": "",
            "detail_page_url": item.detail_page_url if item.detail_page_url else "",
        }

        # Extract title
        if item.item_info and item.item_info.title:
            data["title"] = item.item_info.title.display_value or ""

        # Extract pricing from offersV2
        if item.offers_v2 and item.offers_v2.listings:
            offer = item.offers_v2.listings[0]
            
            # Offers are returned as dictionaries
            if isinstance(offer, dict):
                if 'Price' in offer and 'Money' in offer['Price']:
                    data["price"] = int(offer['Price']['Money']['Amount'] * 100)  # Convert to paise
                    
                if 'Price' in offer and 'SavingBasis' in offer['Price'] and 'Money' in offer['Price']['SavingBasis']:
                    data["list_price"] = int(offer['Price']['SavingBasis']['Money']['Amount'] * 100)
                    
                if 'Price' in offer and 'Savings' in offer['Price'] and 'Percentage' in offer['Price']['Savings']:
                    data["savings_percent"] = offer['Price']['Savings']['Percentage']

        # Extract reviews
        if item.customer_reviews:
            if item.customer_reviews.star_rating:
                data["rating"] = item.customer_reviews.star_rating.value
            if item.customer_reviews.count:
                data["review_count"] = item.customer_reviews.count

        # Extract image
        if item.images and item.images.primary and item.images.primary.medium:
            data["image_url"] = item.images.primary.medium.url

        return data

    async def get_browse_nodes_hierarchy(
        self, browse_node_id: int, priority: str = "normal"
    ) -> Dict:
        """Get complete category hierarchy information using official SDK.

        Args:
        ----
            browse_node_id: Browse node ID to fetch
            priority: Request priority for rate limiting

        Returns:
        -------
            Dict with browse node hierarchy information

        Raises:
        ------
            QuotaExceededError: When PA-API quota is exceeded
        """
        await acquire_api_permission(priority)

        try:
            result = await asyncio.to_thread(self._sync_get_browse_nodes, browse_node_id)
            return result
        except ApiException as exc:
            if exc.status in [503, 429]:
                log.warning("PA-API quota exceeded for browse node: %s", browse_node_id)
                raise QuotaExceededError(f"PA-API quota exceeded for browse node {browse_node_id}") from exc
            log.error("PA-API browse node error: %s", exc)
            log.error("Request ID: %s", exc.headers.get("x-amzn-RequestId", "N/A"))
            raise
        except Exception as exc:
            log.error("Unexpected PA-API browse node error: %s", exc)
            raise

    def _sync_get_browse_nodes(self, browse_node_id: int) -> Dict:
        """Synchronous browse nodes implementation using official SDK."""
        # Get appropriate resources from resource manager
        resources = self.resource_manager.get_resources_for_context("browse_nodes")
        
        # Create the request object
        get_browse_nodes_request = GetBrowseNodesRequest(
            partner_tag=settings.PAAPI_TAG,
            partner_type=PartnerType.ASSOCIATES,
            marketplace=settings.PAAPI_MARKETPLACE,  # "www.amazon.in"
            browse_node_ids=[str(browse_node_id)],
            resources=resources
        )

        try:
            response = self.api.get_browse_nodes(get_browse_nodes_request)
            
            if not response.browse_nodes_result or not response.browse_nodes_result.browse_nodes:
                raise ValueError(f"No browse node found for ID: {browse_node_id}")

            node = response.browse_nodes_result.browse_nodes[0]
            
            return {
                "id": node.id,
                "name": node.display_name,
                "children": [
                    {"id": child.id, "name": child.display_name}
                    for child in (node.children or [])
                ],
                "ancestors": [
                    {"id": ancestor.id, "name": ancestor.display_name}
                    for ancestor in (node.ancestor if isinstance(node.ancestor, list) else [node.ancestor] if node.ancestor else [])
                ],
                "sales_rank": getattr(node, "sales_rank", None),
            }

        except ApiException as e:
            log.error("Official PA-API browse nodes request failed: Status %s, Body: %s", e.status, e.body)
            log.error("Request ID: %s", e.headers.get("x-amzn-RequestId", "N/A"))
            raise
        except Exception as e:
            log.error("Official PA-API browse nodes request failed: %s", e)
            raise


# Factory function for dependency injection
def create_official_paapi_client() -> OfficialPaapiClient:
    """Create an instance of the official PA-API client."""
    return OfficialPaapiClient()
