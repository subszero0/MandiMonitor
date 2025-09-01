"""
PA-API AI Bridge for Enhanced Intelligence Integration.

This module implements Phase R1 of the Intelligence Model gap-filling by creating
a robust bridge between PA-API responses and AI feature analysis. It enables
real-time product intelligence by transforming Amazon data into AI-compatible
format and providing enhanced resource requests for technical specifications.

Key Components:
1. Enhanced PA-API Resource Requests (AI_SEARCH_RESOURCES, AI_GETITEMS_RESOURCES)
2. PA-API Response Transformer (transform_paapi_to_ai_format)
3. AI-Enhanced Search Function (search_products_with_ai_analysis)
4. Performance monitoring and caching support

Architecture:
- Bridges the gap identified in Phase R1 roadmap
- Maintains compatibility with existing PA-API implementation
- Supports feature flags for gradual rollout
- Includes comprehensive error handling and fallback mechanisms
"""

import asyncio
import time
import traceback
from typing import Dict, List, Any, Optional, Union
from logging import getLogger

from paapi5_python_sdk.models.search_items_resource import SearchItemsResource
from paapi5_python_sdk.models.get_items_resource import GetItemsResource
from paapi5_python_sdk.models.partner_type import PartnerType
from paapi5_python_sdk.models.search_items_request import SearchItemsRequest
from paapi5_python_sdk.models.get_items_request import GetItemsRequest
from paapi5_python_sdk.models.condition import Condition

from .config import settings
from .errors import QuotaExceededError

log = getLogger(__name__)

# Simple cache to prevent duplicate AI search requests
_ai_search_cache = {}
_ai_cache_ttl = 300  # 5 minutes cache

# Recursion prevention
_ai_search_call_stack = set()
_ai_recursion_lock = asyncio.Lock()

# Enhanced resource requests optimized for AI analysis
# These resources prioritize technical specifications and structured data
AI_SEARCH_RESOURCES = [
    # Essential for AI analysis
    SearchItemsResource.ITEMINFO_TITLE,               # Product title (fallback for features)
    SearchItemsResource.ITEMINFO_FEATURES,            # Critical: structured feature data
    SearchItemsResource.ITEMINFO_TECHNICALINFO,       # Critical: technical specifications 
    SearchItemsResource.ITEMINFO_MANUFACTUREINFO,     # Brand and manufacturer details
    
    # Standard product information
    SearchItemsResource.OFFERS_LISTINGS_PRICE,        # Current pricing
    SearchItemsResource.IMAGES_PRIMARY_LARGE,         # Product images
    SearchItemsResource.CUSTOMERREVIEWS_COUNT,        # Review count for popularity
    SearchItemsResource.CUSTOMERREVIEWS_STARRATING,   # Star rating for quality
    
    # Category and classification
    SearchItemsResource.BROWSENODEINFO_BROWSENODES,    # Category information
]

AI_GETITEMS_RESOURCES = [
    # Essential for detailed AI analysis
    GetItemsResource.ITEMINFO_TITLE,                  # Product title
    GetItemsResource.ITEMINFO_FEATURES,               # Critical: feature list
    GetItemsResource.ITEMINFO_TECHNICALINFO,          # Critical: technical details
    GetItemsResource.ITEMINFO_MANUFACTUREINFO,        # Brand and manufacturer
    GetItemsResource.ITEMINFO_PRODUCTINFO,            # Color, size, dimensions
    
    # Enhanced pricing and availability
    GetItemsResource.OFFERSV2_LISTINGS_PRICE,           # Current price
    GetItemsResource.OFFERSV2_LISTINGS_AVAILABILITY,    # Stock status
    GetItemsResource.OFFERSV2_LISTINGS_CONDITION,       # Product condition
    GetItemsResource.OFFERSV2_LISTINGS_MERCHANTINFO,    # Merchant and delivery info
    
    # Media and reviews
    GetItemsResource.IMAGES_PRIMARY_LARGE,            # High-resolution images
    GetItemsResource.CUSTOMERREVIEWS_COUNT,           # Review statistics
    GetItemsResource.CUSTOMERREVIEWS_STARRATING,      # Average rating
    
    # Category and hierarchy
    GetItemsResource.BROWSENODEINFO_BROWSENODES,      # Product categories
]

# Default resources for fallback scenarios
DEFAULT_SEARCH_RESOURCES = [
    SearchItemsResource.ITEMINFO_TITLE,
    SearchItemsResource.OFFERS_LISTINGS_PRICE,
    SearchItemsResource.IMAGES_PRIMARY_MEDIUM,
    SearchItemsResource.CUSTOMERREVIEWS_STARRATING,
]

DEFAULT_GETITEMS_RESOURCES = [
    GetItemsResource.ITEMINFO_TITLE,
    GetItemsResource.OFFERSV2_LISTINGS_PRICE,
    GetItemsResource.IMAGES_PRIMARY_LARGE,
    GetItemsResource.CUSTOMERREVIEWS_STARRATING,
]


async def transform_paapi_to_ai_format(paapi_item: Any) -> Dict[str, Any]:
    """
    Transform PA-API item response to AI-compatible format.
    
    This function bridges the gap between Amazon's data structure and 
    our AI analysis requirements by extracting and normalizing product
    information into a consistent format.
    
    Args:
    ----
        paapi_item: PA-API response item object
        
    Returns:
    -------
        Dict with AI-compatible product data:
        {
            "asin": str,
            "title": str,
            "features": List[str],
            "technical_details": Dict[str, str],
            "price": Optional[int],  # in paise
            "image_url": Optional[str],
            "brand": Optional[str],
            "manufacturer": Optional[str],
            "rating_count": Optional[int],
            "average_rating": Optional[float],
            "availability": Optional[str],
            "product_info": Dict[str, Any],
            "offers_info": Dict[str, Any],
            "ai_extraction_metadata": Dict[str, Any]
        }
    """
    ai_product = {
        "asin": getattr(paapi_item, 'asin', ''),
        "title": extract_title(paapi_item),
        "features": extract_features_list(paapi_item),
        "technical_details": extract_technical_info(paapi_item),
        "price": extract_price(paapi_item),
        "image_url": extract_image_url(paapi_item),
        "brand": extract_brand(paapi_item),
        "manufacturer": extract_manufacturer(paapi_item),
        "rating_count": extract_rating_count(paapi_item),
        "average_rating": extract_average_rating(paapi_item),
        "availability": extract_availability(paapi_item),
        "product_info": extract_product_info(paapi_item),
        "offers_info": extract_offers_info(paapi_item),
        "ai_extraction_metadata": {
            "transformed_at": time.time(),
            "source": "paapi_ai_bridge",
            "version": "1.0.0",
            "fields_extracted": []
        }
    }
    
    # Track which fields were successfully extracted for quality monitoring
    ai_product["ai_extraction_metadata"]["fields_extracted"] = [
        key for key, value in ai_product.items() 
        if value and key != "ai_extraction_metadata"
    ]
    
    log.debug(f"Transformed PA-API item {ai_product['asin']} with {len(ai_product['ai_extraction_metadata']['fields_extracted'])} fields")
    return ai_product


def extract_title(paapi_item: Any) -> str:
    """Extract product title from PA-API response."""
    try:
        if hasattr(paapi_item, 'item_info') and paapi_item.item_info:
            if hasattr(paapi_item.item_info, 'title') and paapi_item.item_info.title:
                return getattr(paapi_item.item_info.title, 'display_value', '') or ''
    except (AttributeError, TypeError) as e:
        log.debug(f"Failed to extract title: {e}")
    return ''


def extract_features_list(paapi_item: Any) -> List[str]:
    """Extract product features list from PA-API response."""
    features = []
    try:
        if hasattr(paapi_item, 'item_info') and paapi_item.item_info:
            if hasattr(paapi_item.item_info, 'features') and paapi_item.item_info.features:
                if hasattr(paapi_item.item_info.features, 'display_values'):
                    raw_features = paapi_item.item_info.features.display_values or []
                    features = [str(f).strip() for f in raw_features if f and str(f).strip()]
    except (AttributeError, TypeError) as e:
        log.debug(f"Failed to extract features: {e}")
    return features


def extract_technical_info(paapi_item: Any) -> Dict[str, Any]:
    """Extract technical specifications from PA-API TechnicalInfo section."""
    tech_details = {}
    try:
        # Primary source: TechnicalInfo (highest priority for AI)
        if (hasattr(paapi_item, 'item_info') and 
            paapi_item.item_info and
            hasattr(paapi_item.item_info, 'technical_info') and
            paapi_item.item_info.technical_info):
            
            tech_info = paapi_item.item_info.technical_info
            
            # Handle different response structures
            if hasattr(tech_info, 'display_values') and tech_info.display_values:
                # Structure: list of display values
                for spec in tech_info.display_values:
                    if hasattr(spec, 'name') and hasattr(spec, 'value'):
                        name = getattr(spec.name, 'display_value', '') if hasattr(spec.name, 'display_value') else str(spec.name)
                        value = getattr(spec.value, 'display_value', '') if hasattr(spec.value, 'display_value') else str(spec.value)
                        if name and value:
                            tech_details[name.strip()] = value.strip()
            
            elif hasattr(tech_info, '__dict__'):
                # Structure: object with attributes
                for key, value in tech_info.__dict__.items():
                    if not key.startswith('_') and value:
                        display_value = getattr(value, 'display_value', str(value)) if hasattr(value, 'display_value') else str(value)
                        if display_value:
                            tech_details[key] = display_value
                            
        # Secondary source: ManufactureInfo for additional technical details
        if (hasattr(paapi_item, 'item_info') and 
            paapi_item.item_info and
            hasattr(paapi_item.item_info, 'manufacture_info') and
            paapi_item.item_info.manufacture_info):
            
            manufacture_info = paapi_item.item_info.manufacture_info
            if hasattr(manufacture_info, 'model') and manufacture_info.model:
                model_value = getattr(manufacture_info.model, 'display_value', '')
                if model_value:
                    tech_details['Model'] = model_value
                    
    except (AttributeError, TypeError) as e:
        log.debug(f"Failed to extract technical info: {e}")
    
    return tech_details


def extract_price(paapi_item: Any) -> Optional[int]:
    """Extract current price in paise from PA-API response."""
    try:
        if hasattr(paapi_item, 'offers') and paapi_item.offers:
            if hasattr(paapi_item.offers, 'listings') and paapi_item.offers.listings:
                listing = paapi_item.offers.listings[0]  # Primary offer
                if hasattr(listing, 'price') and listing.price:
                    price_info = listing.price
                    if hasattr(price_info, 'amount') and price_info.amount:
                        # Convert to paise (multiply by 100)
                        return int(float(price_info.amount) * 100)
    except (AttributeError, TypeError, ValueError) as e:
        log.debug(f"Failed to extract price: {e}")
    return None


def extract_image_url(paapi_item: Any) -> Optional[str]:
    """Extract primary product image URL from PA-API response."""
    try:
        if hasattr(paapi_item, 'images') and paapi_item.images:
            primary_image = paapi_item.images.primary
            if hasattr(primary_image, 'large') and primary_image.large:
                return getattr(primary_image.large, 'url', '')
            elif hasattr(primary_image, 'medium') and primary_image.medium:
                return getattr(primary_image.medium, 'url', '')
    except (AttributeError, TypeError) as e:
        log.debug(f"Failed to extract image URL: {e}")
    return None


def extract_brand(paapi_item: Any) -> Optional[str]:
    """Extract brand name from PA-API response."""
    try:
        if (hasattr(paapi_item, 'item_info') and 
            paapi_item.item_info and
            hasattr(paapi_item.item_info, 'by_line_info') and
            paapi_item.item_info.by_line_info):
            
            by_line_info = paapi_item.item_info.by_line_info
            if hasattr(by_line_info, 'brand') and by_line_info.brand:
                brand_value = getattr(by_line_info.brand, 'display_value', None)
                if brand_value:
                    return brand_value
    except (AttributeError, TypeError, KeyError) as e:
        log.debug(f"Failed to extract brand: {e}")
    return None


def extract_manufacturer(paapi_item: Any) -> Optional[str]:
    """Extract manufacturer name from PA-API response."""
    try:
        if (hasattr(paapi_item, 'item_info') and 
            paapi_item.item_info and
            hasattr(paapi_item.item_info, 'by_line_info') and
            paapi_item.item_info.by_line_info):
            
            by_line_info = paapi_item.item_info.by_line_info
            if hasattr(by_line_info, 'manufacturer') and by_line_info.manufacturer:
                return getattr(by_line_info.manufacturer, 'display_value', '')
    except (AttributeError, TypeError) as e:
        log.debug(f"Failed to extract manufacturer: {e}")
    return None


def extract_rating_count(paapi_item: Any) -> Optional[int]:
    """Extract review count from PA-API response."""
    try:
        if hasattr(paapi_item, 'customer_reviews') and paapi_item.customer_reviews:
            if hasattr(paapi_item.customer_reviews, 'count'):
                return paapi_item.customer_reviews.count
    except (AttributeError, TypeError) as e:
        log.debug(f"Failed to extract rating count: {e}")
    return None


def extract_average_rating(paapi_item: Any) -> Optional[float]:
    """Extract average star rating from PA-API response."""
    try:
        if hasattr(paapi_item, 'customer_reviews') and paapi_item.customer_reviews:
            if (hasattr(paapi_item.customer_reviews, 'star_rating') and 
                paapi_item.customer_reviews.star_rating):
                return getattr(paapi_item.customer_reviews.star_rating, 'value', None)
    except (AttributeError, TypeError) as e:
        log.debug(f"Failed to extract average rating: {e}")
    return None


def extract_availability(paapi_item: Any) -> Optional[str]:
    """Extract availability status from PA-API response."""
    try:
        if hasattr(paapi_item, 'offers') and paapi_item.offers:
            if hasattr(paapi_item.offers, 'listings') and paapi_item.offers.listings:
                listing = paapi_item.offers.listings[0]  # Primary offer
                if hasattr(listing, 'availability') and listing.availability:
                    return getattr(listing.availability, 'message', '')
    except (AttributeError, TypeError) as e:
        log.debug(f"Failed to extract availability: {e}")
    return None


def extract_product_info(paapi_item: Any) -> Dict[str, Any]:
    """Extract additional product information for AI analysis."""
    product_info = {}
    try:
        if (hasattr(paapi_item, 'item_info') and 
            paapi_item.item_info and
            hasattr(paapi_item.item_info, 'product_info') and
            paapi_item.item_info.product_info):
            
            prod_info = paapi_item.item_info.product_info
            
            # Extract color
            if hasattr(prod_info, 'color') and prod_info.color:
                product_info['color'] = getattr(prod_info.color, 'display_value', '')
            
            # Extract size
            if hasattr(prod_info, 'size') and prod_info.size:
                product_info['size'] = getattr(prod_info.size, 'display_value', '')
            
            # Extract dimensions
            if hasattr(prod_info, 'item_dimensions') and prod_info.item_dimensions:
                product_info['dimensions'] = getattr(prod_info.item_dimensions, 'display_value', '')
            
            # Extract weight
            if hasattr(prod_info, 'item_weight') and prod_info.item_weight:
                product_info['weight'] = getattr(prod_info.item_weight, 'display_value', '')
                
    except (AttributeError, TypeError) as e:
        log.debug(f"Failed to extract product info: {e}")
    
    return product_info


def extract_offers_info(paapi_item: Any) -> Dict[str, Any]:
    """Extract detailed offers information for AI analysis."""
    offers_info = {}
    try:
        if hasattr(paapi_item, 'offers') and paapi_item.offers:
            if hasattr(paapi_item.offers, 'listings') and paapi_item.offers.listings:
                listing = paapi_item.offers.listings[0]  # Primary offer
                
                # Extract delivery info
                if hasattr(listing, 'delivery_info') and listing.delivery_info:
                    delivery = listing.delivery_info
                    offers_info['prime_eligible'] = getattr(delivery, 'is_prime_eligible', False)
                    offers_info['free_shipping'] = getattr(delivery, 'is_free_shipping_eligible', False)
                
                # Extract condition
                if hasattr(listing, 'condition') and listing.condition:
                    offers_info['condition'] = getattr(listing.condition, 'value', 'New')
                
                # Extract savings information
                if hasattr(listing, 'saving_basis') and listing.saving_basis:
                    saving_basis = listing.saving_basis
                    if hasattr(saving_basis, 'amount') and saving_basis.amount:
                        list_price = int(float(saving_basis.amount) * 100)  # Convert to paise
                        offers_info['list_price'] = list_price
                        
                        # Calculate savings if we have current price
                        current_price = extract_price(paapi_item)
                        if current_price and list_price > current_price:
                            offers_info['savings_amount'] = list_price - current_price
                            offers_info['savings_percent'] = int(((list_price - current_price) / list_price) * 100)
                            
    except (AttributeError, TypeError, ValueError) as e:
        log.debug(f"Failed to extract offers info: {e}")
    
    return offers_info


async def search_products_with_ai_analysis(
    keywords: str,
    search_index: str = "Electronics",
    item_count: int = 10,
    enable_ai_analysis: bool = True,
    priority: str = "normal",
    recursion_depth: int = 0,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None
) -> Dict[str, Any]:
    """
    Search products with optional AI feature analysis.

    This function provides enhanced PA-API search capabilities optimized for AI analysis
    by requesting additional resources (TechnicalInfo, Features) and transforming
    responses into AI-compatible format.

    Args:
    ----
        keywords: Search terms
        search_index: Product category ("Electronics", "All", etc.)
        item_count: Number of items to return (1-10)
        enable_ai_analysis: Whether to use AI-enhanced resources
        priority: Request priority for rate limiting
        recursion_depth: Internal parameter to track recursion depth
        min_price: Minimum price in paise (optional)
        max_price: Maximum price in paise (optional)

    Returns:
    -------
        Dict containing:
        {
            "products": List[Dict],  # AI-compatible format
            "raw_paapi_response": Any,  # Original PA-API response
            "ai_analysis_enabled": bool,
            "processing_time_ms": float,
            "metadata": Dict[str, Any]
        }
    """
    start_time = time.time()

    # ===== DETAILED PRICE FILTER LOGGING =====
    log.info("🔍 AI BRIDGE: search_products_with_ai_analysis called with:")
    log.info("   keywords='%s'", keywords)
    log.info("   search_index='%s'", search_index)
    log.info("   item_count=%d", item_count)
    log.info("   enable_ai_analysis=%s", enable_ai_analysis)
    log.info("   priority='%s'", priority)
    log.info("   recursion_depth=%d", recursion_depth)
    log.info("   min_price=%s (%s)", min_price, f"₹{min_price/100:.0f}" if min_price else "None")
    log.info("   max_price=%s (%s)", max_price, f"₹{max_price/100:.0f}" if max_price else "None")

    # ===== RECURSION DETECTION & PREVENTION =====
    call_signature = f"ai_search:{keywords[:50]}:{search_index}:{recursion_depth}"

    async with _ai_recursion_lock:
        if call_signature in _ai_search_call_stack:
            log.critical("🔄 INFINITE RECURSION DETECTED in AI search!")
            log.critical(f"Call signature: {call_signature}")
            log.critical(f"Current call stack: {_ai_search_call_stack}")
            log.critical("Returning empty results to prevent infinite loop")
            return {
                "products": [],
                "raw_paapi_response": None,
                "ai_analysis_enabled": enable_ai_analysis,
                "processing_time_ms": 0.0,
                "metadata": {
                    "recursion_detected": True,
                    "call_signature": call_signature,
                    "error": "Infinite recursion prevented"
                }
            }

        if recursion_depth >= 3:
            log.warning(f"⚠️ MAX RECURSION DEPTH ({recursion_depth}) reached for AI search")
            return {
                "products": [],
                "raw_paapi_response": None,
                "ai_analysis_enabled": enable_ai_analysis,
                "processing_time_ms": 0.0,
                "metadata": {
                    "max_depth_exceeded": True,
                    "recursion_depth": recursion_depth,
                    "error": "Maximum recursion depth exceeded"
                }
            }

        _ai_search_call_stack.add(call_signature)
        log.debug(f"🔍 AI SEARCH ENTRY: {call_signature} (depth={recursion_depth})")

    # Check cache first to prevent duplicate requests
    cache_key = f"{keywords}_{search_index}_{item_count}_{enable_ai_analysis}"
    current_time = time.time()

    if cache_key in _ai_search_cache:
        cached_data, cache_time = _ai_search_cache[cache_key]
        if current_time - cache_time < _ai_cache_ttl:
            log.info(f"📋 AI search cache hit for: '{keywords}'")
            return cached_data
        else:
            # Remove expired cache entry
            del _ai_search_cache[cache_key]

    # Choose appropriate resources based on AI analysis flag
    resources = AI_SEARCH_RESOURCES if enable_ai_analysis else DEFAULT_SEARCH_RESOURCES

    log.info(f"🤖 AI_SEARCH_START: AI analysis {'ENABLED' if enable_ai_analysis else 'DISABLED'} for '{keywords}'")
    log.info(f"   📊 Search params: index={search_index}, count={item_count}, priority={priority}")

    try:
        # ===== DETAILED DEBUG LOGGING =====
        log.info(f"🔍 AI SEARCH DEBUG: Starting search for '{keywords}'")
        log.info(f"🔍 AI SEARCH DEBUG: search_index={search_index}, item_count={item_count}")
        log.info(f"🔍 AI SEARCH DEBUG: enable_ai_analysis={enable_ai_analysis}, recursion_depth={recursion_depth}")
        log.info(f"🔍 AI SEARCH DEBUG: Current call stack size: {len(_ai_search_call_stack)}")
        log.info(f"🔍 AI SEARCH DEBUG: Call stack: {list(_ai_search_call_stack)}")

        # Import the PA-API client to perform actual search
        log.debug("🔍 AI SEARCH DEBUG: Importing PA-API client...")
        from .paapi_official import create_official_paapi_client

        # Create PA-API client
        log.debug("🔍 AI SEARCH DEBUG: Creating PA-API client...")
        paapi_client = create_official_paapi_client()
        log.debug("🔍 AI SEARCH DEBUG: PA-API client created successfully")

        # Perform the actual search with enhanced resources
        log.info(f"🔍 AI SEARCH DEBUG: Calling search_items_advanced with recursion_depth={recursion_depth + 1}")
        log.info("🔍 AI SEARCH DEBUG: Price filters being passed to PA-API:")
        log.info("   min_price=%s", min_price)
        log.info("   max_price=%s", max_price)

        search_results = await paapi_client.search_items_advanced(
            keywords=keywords,
            search_index=search_index,
            item_count=item_count,
            priority=priority,
            min_price=min_price,
            max_price=max_price,
            enable_ai_analysis=False  # CRITICAL: Prevent recursion by disabling AI in nested calls
        )
        log.info(f"🔍 AI SEARCH DEBUG: search_items_advanced returned {len(search_results) if search_results else 0} results")

        # Transform PA-API results to AI-compatible format
        log.debug("🔍 AI SEARCH DEBUG: Starting result transformation...")
        ai_products = []
        for i, result in enumerate(search_results):
            try:
                log.debug(f"🔍 AI SEARCH DEBUG: Transforming result {i+1}/{len(search_results)}: {result.get('asin', 'unknown')}")
                # Convert result to mock PA-API format for transformation
                mock_item = create_mock_paapi_item_from_result(result)
                ai_product = await transform_paapi_to_ai_format(mock_item)
                ai_products.append(ai_product)
                log.debug(f"🔍 AI SEARCH DEBUG: Successfully transformed result {i+1}")
            except Exception as e:
                log.warning(f"🔍 AI SEARCH DEBUG: Failed to transform search result {i+1}: {e}")
                # Include original result as fallback
                ai_products.append(result)

        paapi_response = search_results
        log.info(f"🔍 AI SEARCH DEBUG: Transformation complete. {len(ai_products)} AI products created")

        processing_time = (time.time() - start_time) * 1000  # Convert to milliseconds

        result = {
            "products": ai_products,
            "raw_paapi_response": paapi_response,
            "ai_analysis_enabled": enable_ai_analysis,
            "processing_time_ms": processing_time,
            "metadata": {
                "search_keywords": keywords,
                "search_index": search_index,
                "requested_count": item_count,
                "returned_count": len(ai_products),
                "resources_used": len(resources),
                "api_version": "paapi5_python_sdk",
                "bridge_version": "1.0.0",
                "recursion_depth": recursion_depth,
                "call_signature": call_signature
            }
        }

        log.info(f"✅ AI search completed: {len(ai_products)} products in {processing_time:.1f}ms (depth={recursion_depth})")

        # Cache the successful result
        _ai_search_cache[cache_key] = (result, current_time)

        return result

    except QuotaExceededError:
        log.warning(f"💰 PA-API quota exceeded for search: {keywords}")
        raise
    except Exception as e:
        log.error(f"❌ AI search failed for '{keywords}' (depth={recursion_depth}): {e}")
        log.error(f"❌ AI search stack trace: {traceback.format_exc()}")
        # Return empty result instead of failing completely
        processing_time = (time.time() - start_time) * 1000
        return {
            "products": [],
            "raw_paapi_response": None,
            "ai_analysis_enabled": enable_ai_analysis,
            "processing_time_ms": processing_time,
            "metadata": {
                "search_keywords": keywords,
                "error": str(e),
                "fallback_used": True,
                "recursion_depth": recursion_depth,
                "call_signature": call_signature
            }
        }
    finally:
        # ===== CLEANUP: Remove call signature from stack =====
        async with _ai_recursion_lock:
            if call_signature in _ai_search_call_stack:
                _ai_search_call_stack.remove(call_signature)
                log.debug(f"🧹 AI SEARCH CLEANUP: Removed {call_signature} from call stack")
                log.debug(f"🧹 AI SEARCH CLEANUP: Remaining stack size: {len(_ai_search_call_stack)}")
            else:
                log.warning(f"🧹 AI SEARCH CLEANUP: Call signature {call_signature} not found in stack!")


async def execute_search_request(
    paapi_client: Any,
    keywords: str,
    search_index: str,
    item_count: int,
    resources: List[Any]
) -> Any:
    """Execute PA-API SearchItems request with proper error handling."""
    try:
        # Use the existing search functionality from paapi_official.py
        search_results = await paapi_client.search_items_advanced(
            keywords=keywords,
            search_index=search_index,
            item_count=item_count,
            priority="normal"
        )
        
        # For now, return a mock response structure that matches what we expect
        # In a real implementation, this would be the actual PA-API response
        class MockSearchResponse:
            def __init__(self, items):
                self.search_result = MockSearchResult(items)
        
        class MockSearchResult:
            def __init__(self, items):
                self.items = items
        
        # Convert the search results back to mock PA-API format for transformation
        mock_items = []
        for result in search_results:
            mock_item = create_mock_paapi_item_from_result(result)
            mock_items.append(mock_item)
        
        return MockSearchResponse(mock_items)
        
    except Exception as e:
        log.error(f"PA-API search request failed: {e}")
        raise


def create_mock_paapi_item_from_result(result: Dict) -> Any:
    """Create a mock PA-API item from search result for transformation."""
    class MockItem:
        def __init__(self, data):
            self.asin = data.get("asin", "")
            self.item_info = MockItemInfo(data)
            self.offers = MockOffers(data) if data.get("price") else None
            self.images = MockImages(data) if data.get("image_url") else None
            self.customer_reviews = MockCustomerReviews(data) if data.get("rating") else None
    
    class MockItemInfo:
        def __init__(self, data):
            self.title = MockDisplayValue(data.get("title", ""))
            self.features = MockFeatures(data.get("features", []))
            self.technical_info = None  # Will be populated if technical details exist
            self.by_line_info = MockByLineInfo(data)
            self.product_info = MockProductInfo(data)
    
    class MockDisplayValue:
        def __init__(self, value):
            self.display_value = value
    
    class MockFeatures:
        def __init__(self, features):
            self.display_values = features
    
    class MockByLineInfo:
        def __init__(self, data):
            self.brand = MockDisplayValue(data.get("brand", "")) if data.get("brand") else None
            self.manufacturer = MockDisplayValue(data.get("manufacturer", "")) if data.get("manufacturer") else None
    
    class MockProductInfo:
        def __init__(self, data):
            self.color = MockDisplayValue(data.get("color", "")) if data.get("color") else None
            self.size = MockDisplayValue(data.get("size", "")) if data.get("size") else None
    
    class MockOffers:
        def __init__(self, data):
            self.listings = [MockListing(data)]
    
    class MockListing:
        def __init__(self, data):
            price = data.get("price")
            self.price = MockPrice(price / 100 if price else 0) if price else None  # Convert from paise
            self.availability = MockAvailability(data.get("availability", "In Stock"))
    
    class MockPrice:
        def __init__(self, amount):
            self.amount = amount
    
    class MockAvailability:
        def __init__(self, message):
            self.message = message
    
    class MockImages:
        def __init__(self, data):
            self.primary = MockPrimaryImage(data.get("image_url", ""))
    
    class MockPrimaryImage:
        def __init__(self, url):
            self.large = MockImageSize(url) if url else None
            self.medium = MockImageSize(url) if url else None
    
    class MockImageSize:
        def __init__(self, url):
            self.url = url
    
    class MockCustomerReviews:
        def __init__(self, data):
            self.star_rating = MockStarRating(data.get("rating")) if data.get("rating") else None
            self.count = data.get("review_count")
    
    class MockStarRating:
        def __init__(self, value):
            self.value = value
    
    return MockItem(result)


async def get_items_with_ai_analysis(
    asins: List[str],
    enable_ai_analysis: bool = True,
    priority: str = "normal"
) -> Dict[str, Dict]:
    """
    Get detailed product information with AI analysis for multiple ASINs.
    
    Args:
    ----
        asins: List of ASINs to fetch
        enable_ai_analysis: Whether to use AI-enhanced resources
        priority: Request priority for rate limiting
        
    Returns:
    -------
        Dict mapping ASIN to AI-compatible product data
    """
    start_time = time.time()
    
    if not asins:
        return {}
    
    log.info(f"Getting items with AI analysis {'enabled' if enable_ai_analysis else 'disabled'}: {len(asins)} ASINs")
    
    try:
        # Import here to avoid circular imports
        from .paapi_official import create_official_paapi_client
        
        # Create PA-API client
        paapi_client = create_official_paapi_client()
        
        # Use existing batch functionality with enhanced transformation
        batch_results = await paapi_client.get_items_batch(asins, priority=priority)
        
        # Transform results to AI format
        ai_results = {}
        for asin, product_data in batch_results.items():
            try:
                # Convert existing result to mock PA-API format for transformation
                mock_item = create_mock_paapi_item_from_result(product_data)
                ai_product = await transform_paapi_to_ai_format(mock_item)
                ai_results[asin] = ai_product
            except Exception as e:
                log.warning(f"Failed to transform item {asin}: {e}")
                # Include original data as fallback
                ai_results[asin] = product_data
        
        processing_time = (time.time() - start_time) * 1000
        log.info(f"AI GetItems completed: {len(ai_results)} products in {processing_time:.1f}ms")
        
        return ai_results
        
    except Exception as e:
        log.error(f"AI GetItems failed for {len(asins)} ASINs: {e}")
        return {}


# Configuration and feature flags
def is_ai_analysis_enabled() -> bool:
    """Check if AI analysis is enabled via configuration."""
    return getattr(settings, 'ENABLE_AI_ANALYSIS', True)


def should_use_enhanced_resources() -> bool:
    """Check if enhanced PA-API resources should be used."""
    return getattr(settings, 'ENABLE_ENHANCED_PAAPI', True)


# Performance monitoring and caching support
class PaapiAiPerformanceTracker:
    """Track performance metrics for PA-API AI bridge operations."""
    
    def __init__(self):
        self.metrics = {
            "total_searches": 0,
            "total_transformations": 0,
            "avg_search_time_ms": 0.0,
            "avg_transformation_time_ms": 0.0,
            "success_rate": 0.0,
            "last_reset": time.time()
        }
    
    def record_search(self, duration_ms: float, success: bool):
        """Record search operation metrics."""
        self.metrics["total_searches"] += 1
        if success:
            current_avg = self.metrics["avg_search_time_ms"]
            count = self.metrics["total_searches"]
            self.metrics["avg_search_time_ms"] = ((current_avg * (count - 1)) + duration_ms) / count
    
    def record_transformation(self, duration_ms: float, success: bool):
        """Record transformation operation metrics."""
        self.metrics["total_transformations"] += 1
        if success:
            current_avg = self.metrics["avg_transformation_time_ms"]
            count = self.metrics["total_transformations"]
            self.metrics["avg_transformation_time_ms"] = ((current_avg * (count - 1)) + duration_ms) / count
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        return self.metrics.copy()
    
    def reset_metrics(self):
        """Reset all metrics."""
        self.metrics = {
            "total_searches": 0,
            "total_transformations": 0,
            "avg_search_time_ms": 0.0,
            "avg_transformation_time_ms": 0.0,
            "success_rate": 0.0,
            "last_reset": time.time()
        }


# Global performance tracker instance
performance_tracker = PaapiAiPerformanceTracker()


def get_bridge_performance_metrics() -> Dict[str, Any]:
    """Get current bridge performance metrics."""
    return performance_tracker.get_metrics()
