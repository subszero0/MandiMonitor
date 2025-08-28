"""Official Amazon PA-API SDK wrapper implementation.

This module provides a parallel implementation using the official paapi5-python-sdk
to replace the current third-party amazon-paapi implementation. Built according
to the migration roadmap in paapi_corrections.md.
"""

import asyncio
import time
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

    async def get_items_batch(
        self, asins: List[str], resources: Optional[List[str]] = None, priority: str = "normal"
    ) -> Dict[str, Dict]:
        """Get comprehensive product information for multiple ASINs in batches.

        PA-API supports up to 10 ASINs per GetItems request, this method handles batching
        automatically and significantly reduces API calls and rate limiting delays.

        Args:
        ----
            asins: List of Amazon Standard Identification Numbers (max recommended: 50)
            resources: List of PA-API resources to fetch (ignored for now, using defaults)
            priority: Request priority for rate limiting

        Returns:
        -------
            Dict mapping ASIN to product information dict
            
        Raises:
        ------
            QuotaExceededError: When PA-API quota is exceeded
        """
        if not asins:
            return {}
            
        # Remove duplicates while preserving order
        unique_asins = list(dict.fromkeys(asins))
        
        # PA-API supports max 10 ASINs per GetItems request
        batch_size = 10
        batches = [unique_asins[i:i + batch_size] for i in range(0, len(unique_asins), batch_size)]
        
        log.info("Processing %d ASINs in %d batch(es) of max %d items each", 
                len(unique_asins), len(batches), batch_size)
        
        results = {}
        
        for batch_idx, batch_asins in enumerate(batches):
            log.info("Processing batch %d/%d with %d ASINs: %s", 
                    batch_idx + 1, len(batches), len(batch_asins), batch_asins)
            
            await acquire_api_permission(priority)
            
            try:
                batch_result = await asyncio.to_thread(self._sync_get_items_batch, batch_asins)
                results.update(batch_result)
                
                log.info("Batch %d/%d completed successfully, got %d results", 
                        batch_idx + 1, len(batches), len(batch_result))
                        
            except ApiException as exc:
                if exc.status in [503, 429]:
                    log.warning("PA-API quota exceeded for batch %d: %s", batch_idx + 1, batch_asins)
                    raise QuotaExceededError(f"PA-API quota exceeded for batch {batch_idx + 1}") from exc
                log.error("PA-API error for batch %d (%s): %s", batch_idx + 1, batch_asins, exc)
                log.error("Request ID: %s", exc.headers.get("x-amzn-RequestId", "N/A"))
                # Continue with next batch rather than failing completely
                continue
            except Exception as exc:
                log.error("Unexpected PA-API error for batch %d (%s): %s", batch_idx + 1, batch_asins, exc)
                # Continue with next batch rather than failing completely
                continue
        
        log.info("Batch processing completed: %d/%d ASINs successfully processed", 
                len(results), len(unique_asins))
        
        return results

    def _sync_get_items_batch(self, asins: List[str]) -> Dict[str, Dict]:
        """Synchronous batch GetItems PA-API call using official SDK."""
        if not asins:
            return {}
            
        # Get appropriate resources from resource manager
        resources = self.resource_manager.get_detailed_resources("get_items")
        
        # Create the request object with proper marketplace configuration
        get_items_request = GetItemsRequest(
            partner_tag=settings.PAAPI_TAG,
            partner_type=PartnerType.ASSOCIATES,
            marketplace=settings.PAAPI_MARKETPLACE,  # "www.amazon.in"
            condition=Condition.NEW,
            item_ids=asins,  # List of ASINs
            resources=resources
        )
        
        # Make the API call
        response = self.api.get_items(get_items_request)
        
        # Extract data and convert to expected format
        results = {}
        
        if hasattr(response, 'items_result') and response.items_result:
            items = response.items_result.items or []
            log.info("Official PA-API batch call returned %d items for %d requested ASINs", 
                    len(items), len(asins))
                    
            for item in items:
                try:
                    asin = item.asin
                    
                    # Extract comprehensive product information
                    product_data = {
                        "asin": asin,
                        "title": getattr(item.item_info.title, 'display_value', '') if hasattr(item, 'item_info') and item.item_info and hasattr(item.item_info, 'title') else '',
                        "price": None,
                        "list_price": None,
                        "savings_amount": None,
                        "savings_percent": None,
                        "image_url": None,
                        "rating": None,
                        "review_count": None,
                        "brand": None,
                        "model": None,
                        "color": None,
                        "size": None,
                        "weight": None,
                        "dimensions": None,
                        "features": [],
                        "specifications": {},
                        "availability": None,
                        "prime": False,
                        "free_shipping": False,
                        "url": None
                    }
                    
                    # Extract pricing information
                    if hasattr(item, 'offers') and item.offers and hasattr(item.offers, 'listings') and item.offers.listings:
                        listing = item.offers.listings[0]  # Get primary offer
                        
                        # Current price
                        if hasattr(listing, 'price') and listing.price:
                            price_info = listing.price
                            if hasattr(price_info, 'amount') and price_info.amount:
                                product_data["price"] = int(float(price_info.amount) * 100)  # Convert to paise
                        
                        # List price and savings
                        if hasattr(listing, 'saving_basis') and listing.saving_basis:
                            saving_basis = listing.saving_basis
                            if hasattr(saving_basis, 'amount') and saving_basis.amount:
                                product_data["list_price"] = int(float(saving_basis.amount) * 100)  # Convert to paise
                                
                                # Calculate savings
                                if product_data["price"]:
                                    product_data["savings_amount"] = product_data["list_price"] - product_data["price"]
                                    if product_data["list_price"] > 0:
                                        product_data["savings_percent"] = int((product_data["savings_amount"] / product_data["list_price"]) * 100)
                        
                        # Availability
                        if hasattr(listing, 'availability') and listing.availability:
                            product_data["availability"] = getattr(listing.availability, 'message', '')
                        
                        # Prime and shipping
                        if hasattr(listing, 'delivery_info') and listing.delivery_info:
                            delivery = listing.delivery_info
                            product_data["prime"] = getattr(delivery, 'is_prime_eligible', False)
                            product_data["free_shipping"] = getattr(delivery, 'is_free_shipping_eligible', False)
                    
                    # Extract images
                    if hasattr(item, 'images') and item.images:
                        primary_image = item.images.primary
                        if hasattr(primary_image, 'large') and primary_image.large:
                            product_data["image_url"] = primary_image.large.url
                        elif hasattr(primary_image, 'medium') and primary_image.medium:
                            product_data["image_url"] = primary_image.medium.url
                    
                    # Extract customer reviews
                    if hasattr(item, 'customer_reviews') and item.customer_reviews:
                        reviews = item.customer_reviews
                        if hasattr(reviews, 'star_rating') and reviews.star_rating:
                            product_data["rating"] = getattr(reviews.star_rating, 'value', None)
                        if hasattr(reviews, 'count') and reviews.count:
                            product_data["review_count"] = reviews.count
                    
                    # Extract item info details
                    if hasattr(item, 'item_info') and item.item_info:
                        info = item.item_info
                        
                        # Brand
                        if hasattr(info, 'by_line_info') and info.by_line_info:
                            brand_info = info.by_line_info
                            if hasattr(brand_info, 'brand') and brand_info.brand:
                                product_data["brand"] = getattr(brand_info.brand, 'display_value', '')
                        
                        # Model
                        if hasattr(info, 'model_number') and info.model_number:
                            product_data["model"] = getattr(info.model_number, 'display_value', '')
                        
                        # Color  
                        if hasattr(info, 'color') and info.color:
                            product_data["color"] = getattr(info.color, 'display_value', '')
                        
                        # Size
                        if hasattr(info, 'size') and info.size:
                            product_data["size"] = getattr(info.size, 'display_value', '')
                        
                        # Features
                        if hasattr(info, 'features') and info.features and hasattr(info.features, 'display_values'):
                            product_data["features"] = info.features.display_values or []
                        
                        # Technical specifications
                        if hasattr(info, 'technical_details') and info.technical_details:
                            tech_details = info.technical_details
                            if hasattr(tech_details, 'display_values'):
                                for detail in (tech_details.display_values or []):
                                    if hasattr(detail, 'label') and hasattr(detail, 'value'):
                                        product_data["specifications"][detail.label] = detail.value
                        
                        # Product dimensions
                        if hasattr(info, 'product_dimensions') and info.product_dimensions:
                            product_data["dimensions"] = getattr(info.product_dimensions, 'display_value', '')
                        
                        # Item weight
                        if hasattr(info, 'item_weight') and info.item_weight:
                            product_data["weight"] = getattr(info.item_weight, 'display_value', '')
                    
                    # Product URL
                    if hasattr(item, 'detail_page_url'):
                        product_data["url"] = item.detail_page_url
                    
                    results[asin] = product_data
                    log.debug("Processed batch item %s: %s", asin, product_data["title"][:50])
                    
                except Exception as item_error:
                    log.warning("Failed to process batch item %s: %s", getattr(item, 'asin', 'unknown'), item_error)
                    continue
        
        # Log any ASINs that weren't found
        found_asins = set(results.keys())
        missing_asins = set(asins) - found_asins
        if missing_asins:
            log.warning("Batch processing: %d ASINs not found in response: %s", 
                       len(missing_asins), list(missing_asins))
        
        return results

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
        item_count: int = 30,
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
            item_count: Number of items to return (1-30, uses pagination for >10)
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
        item_count: int = 30,
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
        
        # Force refresh resource manager to ensure latest resources are used
        from .paapi_resource_manager import force_refresh_resources
        force_refresh_resources()
        
        # Get appropriate resources from resource manager
        resources = self.resource_manager.get_detailed_resources("search_items")
        log.info("Using SearchItems resources: %s", [str(r) for r in resources])
        
        # Amazon PA-API has a hard limit of 10 items per SearchItems request
        # To get more items, we need to use pagination
        max_items_per_request = 10
        all_items = []
        pages_needed = min(3, (item_count + max_items_per_request - 1) // max_items_per_request)  # Max 3 pages for 30 items
        
        for page in range(1, pages_needed + 1):
            items_for_this_page = min(max_items_per_request, item_count - len(all_items))
            if items_for_this_page <= 0:
                break
                
            # Create the search request for this page
            search_items_request = SearchItemsRequest(
                partner_tag=settings.PAAPI_TAG,
                partner_type=PartnerType.ASSOCIATES,
                marketplace=settings.PAAPI_MARKETPLACE,  # "www.amazon.in"
                keywords=final_keywords,
                search_index=search_index,
                condition=api_condition,
                item_count=items_for_this_page,  # Max 10 per request (Amazon limit)
                item_page=page,
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
                log.info("Making PA-API SearchItems request for page %d/%d (items %d-%d)", 
                        page, pages_needed, len(all_items) + 1, len(all_items) + items_for_this_page)
                        
                response = self.api.search_items(search_items_request)
                
                if not response.search_result or not response.search_result.items:
                    log.info("No items found for search page %d: %s", page, final_keywords)
                    break  # No more items available

                page_items = []
                for item in response.search_result.items:
                    page_items.append(self._extract_search_data(item))
                
                all_items.extend(page_items)
                log.info("Retrieved %d items from page %d, total so far: %d", 
                        len(page_items), page, len(all_items))
                
                # Rate limiting: Wait longer between requests to respect PA-API limits
                # Amazon PA-API is very strict about rate limits for SearchItems requests
                if page < pages_needed:  # Don't wait after the last request
                    # Use a longer delay for pagination to avoid 429 errors
                    # SearchItems has stricter limits than GetItems
                    import time
                    time.sleep(2.5)  # Increased from 1.1s to 2.5s for pagination
                    log.info("Applied 2.5s rate limiting between pagination requests")

            except ApiException as e:
                log.error("Official PA-API search failed on page %d: Status %s, Body: %s", page, e.status, e.body)
                log.error("Request ID: %s", e.headers.get("x-amzn-RequestId", "N/A"))
                if page == 1:  # If first page fails, raise error
                    raise
                else:  # If later pages fail, return what we have so far
                    log.warning("Page %d failed, returning %d items from previous pages", page, len(all_items))
                    break
            except Exception as e:
                log.error("Official PA-API search failed on page %d: %s", page, e)
                if page == 1:  # If first page fails, raise error
                    raise
                else:  # If later pages fail, return what we have so far
                    log.warning("Page %d failed, returning %d items from previous pages", page, len(all_items))
                    break
        
        log.info("Pagination complete: Retrieved %d total items from %d pages", len(all_items), pages_needed)
        return all_items

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

        # Extract pricing from offers (use the same logic as detailed extraction)
        if hasattr(item, 'offers') and item.offers and hasattr(item.offers, 'listings') and item.offers.listings:
            listing = item.offers.listings[0]  # Get primary offer
            
            # Current price
            if hasattr(listing, 'price') and listing.price:
                price_info = listing.price
                if hasattr(price_info, 'amount') and price_info.amount:
                    data["price"] = int(float(price_info.amount) * 100)  # Convert to paise
            
            # List price and savings
            if hasattr(listing, 'saving_basis') and listing.saving_basis:
                saving_basis = listing.saving_basis
                if hasattr(saving_basis, 'amount') and saving_basis.amount:
                    data["list_price"] = int(float(saving_basis.amount) * 100)  # Convert to paise
                    
                    # Calculate savings percentage
                    if data["price"] and data["list_price"] > 0:
                        savings_amount = data["list_price"] - data["price"]
                        data["savings_percent"] = int((savings_amount / data["list_price"]) * 100)

        # Fallback: Try alternate offer structure if main offers didn't work
        if data["price"] is None and hasattr(item, 'offers') and item.offers:
            if hasattr(item.offers, 'summaries') and item.offers.summaries:
                for summary in item.offers.summaries:
                    if hasattr(summary, 'lowest_price') and summary.lowest_price:
                        if hasattr(summary.lowest_price, 'amount') and summary.lowest_price.amount:
                            data["price"] = int(float(summary.lowest_price.amount) * 100)
                            break

        # Extract reviews
        if item.customer_reviews:
            if item.customer_reviews.star_rating:
                data["rating"] = item.customer_reviews.star_rating.value
            if item.customer_reviews.count:
                data["review_count"] = item.customer_reviews.count

        # Extract image
        if item.images and item.images.primary:
            if item.images.primary.medium:
                data["image_url"] = item.images.primary.medium.url
            elif item.images.primary.large:
                data["image_url"] = item.images.primary.large.url

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
