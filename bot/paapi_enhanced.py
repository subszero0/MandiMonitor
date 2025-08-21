"""Enhanced Amazon PA-API wrapper with comprehensive functionality."""

import asyncio
from logging import getLogger
from typing import Dict, List, Optional

from amazon_paapi import AmazonApi

from .api_rate_limiter import acquire_api_permission
from .config import settings
from .errors import QuotaExceededError
from .paapi_resources import get_resources_for_context

log = getLogger(__name__)


async def get_item_detailed(
    asin: str, resources: Optional[List[str]] = None, priority: str = "normal"
) -> Dict:
    """Get comprehensive product information from PA-API.

    Args:
    ----
        asin: Amazon Standard Identification Number
        resources: List of PA-API resources to fetch (defaults to detailed)
        priority: Request priority for rate limiting

    Returns:
    -------
        Dict with comprehensive product information

    Raises:
    ------
        QuotaExceededError: When PA-API quota is exceeded
    """
    if not resources:
        resources = get_resources_for_context("product_details")

    await acquire_api_permission(priority)

    try:
        result = await asyncio.to_thread(_sync_get_item_detailed, asin, resources)
        return result
    except Exception as exc:
        if "503" in str(exc) or "quota" in str(exc).lower():
            log.warning("PA-API quota exceeded for ASIN: %s", asin)
            raise QuotaExceededError(f"PA-API quota exceeded for {asin}") from exc
        log.error("PA-API error for ASIN %s: %s", asin, exc)
        raise


def _sync_get_item_detailed(asin: str, resources: List[str]) -> Dict:
    """Synchronous detailed PA-API call."""
    api = AmazonApi(
        key=settings.PAAPI_ACCESS_KEY,
        secret=settings.PAAPI_SECRET_KEY,
        tag=settings.PAAPI_TAG,
        country="IN",
    )

    try:
        items = api.get_items(asin, resources=resources)
        if not items:
            raise ValueError(f"No item found for ASIN: {asin}")

        item = items[0]
        return _extract_comprehensive_data(item)

    except Exception as e:
        log.error("PA-API detailed call failed for ASIN %s: %s", asin, e)
        raise


def _extract_comprehensive_data(item) -> Dict:
    """Extract comprehensive data from PA-API item response."""
    data = {
        "asin": getattr(item, "asin", ""),
        "title": getattr(item, "title", ""),
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
            "savings_amount": None,
            "savings_percentage": None,
            "availability_type": None,
            "availability_message": None,
            "condition": "New",
            "is_prime_eligible": False,
            "is_amazon_fulfilled": False,
            "merchant_name": None,
            "promotions": [],
        },
        "reviews": {"count": 0, "average_rating": None},
        "browse_nodes": [],
        "variations": {"parent_asin": None},
    }

    # Extract ItemInfo data
    if hasattr(item, "item_info"):
        _extract_item_info(item.item_info, data)

    # Extract offers data
    if hasattr(item, "offers"):
        _extract_offers_data(item.offers, data)

    # Extract images
    if hasattr(item, "images"):
        _extract_images_data(item.images, data)

    # Extract reviews
    if hasattr(item, "customer_reviews"):
        _extract_reviews_data(item.customer_reviews, data)

    # Extract browse nodes
    if hasattr(item, "browse_node_info"):
        _extract_browse_node_data(item.browse_node_info, data)

    # Extract parent ASIN
    if hasattr(item, "parent_asin"):
        data["variations"]["parent_asin"] = item.parent_asin

    return data


def _extract_item_info(item_info, data: Dict) -> None:
    """Extract ItemInfo data from PA-API response."""
    # Basic info
    if hasattr(item_info, "by_line_info"):
        by_line = item_info.by_line_info
        if hasattr(by_line, "brand"):
            data["brand"] = by_line.brand.display_value
        if hasattr(by_line, "manufacturer"):
            data["manufacturer"] = by_line.manufacturer.display_value

    # Classifications
    if hasattr(item_info, "classifications"):
        classifications = item_info.classifications
        if hasattr(classifications, "product_group"):
            data["product_group"] = classifications.product_group.display_value
        if hasattr(classifications, "binding"):
            data["binding"] = classifications.binding.display_value

    # Features
    if hasattr(item_info, "features"):
        if hasattr(item_info.features, "display_values"):
            data["features"] = item_info.features.display_values

    # Product info
    if hasattr(item_info, "product_info"):
        product_info = item_info.product_info
        if hasattr(product_info, "color"):
            data["color"] = product_info.color.display_value
        if hasattr(product_info, "size"):
            data["size"] = product_info.size.display_value
        if hasattr(product_info, "is_adult_product"):
            data["is_adult_product"] = product_info.is_adult_product.display_value

    # External IDs
    if hasattr(item_info, "external_ids"):
        external_ids = item_info.external_ids
        if hasattr(external_ids, "eans"):
            data["ean"] = (
                external_ids.eans.display_values[0]
                if external_ids.eans.display_values
                else None
            )
        if hasattr(external_ids, "isbns"):
            data["isbn"] = (
                external_ids.isbns.display_values[0]
                if external_ids.isbns.display_values
                else None
            )
        if hasattr(external_ids, "upcs"):
            data["upc"] = (
                external_ids.upcs.display_values[0]
                if external_ids.upcs.display_values
                else None
            )

    # Content info
    if hasattr(item_info, "content_info"):
        content_info = item_info.content_info
        if hasattr(content_info, "languages"):
            data["languages"] = [
                lang.display_value for lang in content_info.languages.display_values
            ]
        if hasattr(content_info, "pages_count"):
            data["page_count"] = content_info.pages_count.display_value
        if hasattr(content_info, "publication_date"):
            data["publication_date"] = content_info.publication_date.display_value


def _extract_offers_data(offers, data: Dict) -> None:
    """Extract offers data from PA-API response."""
    if hasattr(offers, "listings") and offers.listings:
        listing = offers.listings[0]  # Get first (usually buy box) listing

        # Price information
        if hasattr(listing, "price"):
            data["offers"]["price"] = int(
                float(listing.price.amount) * 100
            )  # Convert to paise

        if hasattr(listing, "saving_basis"):
            data["offers"]["list_price"] = int(float(listing.saving_basis.amount) * 100)
            # Calculate savings
            if data["offers"]["price"] and data["offers"]["list_price"]:
                savings = data["offers"]["list_price"] - data["offers"]["price"]
                data["offers"]["savings_amount"] = savings
                data["offers"]["savings_percentage"] = int(
                    (savings / data["offers"]["list_price"]) * 100
                )

        # Availability
        if hasattr(listing, "availability"):
            availability = listing.availability
            if hasattr(availability, "type"):
                data["offers"]["availability_type"] = availability.type
            if hasattr(availability, "message"):
                data["offers"]["availability_message"] = availability.message

        # Condition
        if hasattr(listing, "condition"):
            data["offers"]["condition"] = listing.condition.display_value

        # Delivery info
        if hasattr(listing, "delivery_info"):
            delivery = listing.delivery_info
            if hasattr(delivery, "is_prime_eligible"):
                data["offers"]["is_prime_eligible"] = delivery.is_prime_eligible
            if hasattr(delivery, "is_amazon_fulfilled"):
                data["offers"]["is_amazon_fulfilled"] = delivery.is_amazon_fulfilled

        # Merchant info
        if hasattr(listing, "merchant_info"):
            data["offers"]["merchant_name"] = listing.merchant_info.name

        # Promotions
        if hasattr(listing, "promotions"):
            data["offers"]["promotions"] = [
                {"type": promo.type, "display_name": promo.display_name}
                for promo in listing.promotions
            ]


def _extract_images_data(images, data: Dict) -> None:
    """Extract images data from PA-API response."""
    if hasattr(images, "primary"):
        primary = images.primary
        if hasattr(primary, "small"):
            data["images"]["small"] = primary.small.url
        if hasattr(primary, "medium"):
            data["images"]["medium"] = primary.medium.url
        if hasattr(primary, "large"):
            data["images"]["large"] = primary.large.url

    if hasattr(images, "variants"):
        data["images"]["variants"] = [
            variant.large.url
            for variant in images.variants
            if hasattr(variant, "large")
        ]


def _extract_reviews_data(customer_reviews, data: Dict) -> None:
    """Extract customer reviews data from PA-API response."""
    if hasattr(customer_reviews, "count"):
        data["reviews"]["count"] = customer_reviews.count

    if hasattr(customer_reviews, "star_rating"):
        data["reviews"]["average_rating"] = customer_reviews.star_rating.value


def _extract_browse_node_data(browse_node_info, data: Dict) -> None:
    """Extract browse node data from PA-API response."""
    if hasattr(browse_node_info, "browse_nodes"):
        data["browse_nodes"] = [
            {
                "id": node.id,
                "name": node.display_name,
                "sales_rank": getattr(node, "sales_rank", None),
            }
            for node in browse_node_info.browse_nodes
        ]


async def search_items_advanced(
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
    """Advanced product search with comprehensive filtering.

    Args:
    ----
        keywords: Search keywords
        title: Search by product title
        brand: Search by brand name
        search_index: Product category to search within
        min_price: Minimum price in paise
        max_price: Maximum price in paise
        min_reviews_rating: Minimum review rating (1-5)
        min_savings_percent: Minimum discount percentage
        merchant: "Amazon" or "All"
        condition: "New", "Used", "Refurbished"
        item_count: Number of items to return (1-10)
        item_page: Page number (1-10)
        sort_by: Sort criteria
        browse_node_id: Specific category ID
        priority: Request priority for rate limiting

    Returns:
    -------
        List of product dictionaries

    Raises:
    ------
        QuotaExceededError: When PA-API quota is exceeded
    """
    if (
        not settings.PAAPI_ACCESS_KEY
        or not settings.PAAPI_SECRET_KEY
        or not settings.PAAPI_TAG
    ):
        log.warning("PA-API credentials not configured")
        return []

    await acquire_api_permission(priority)

    try:
        result = await asyncio.to_thread(
            _sync_search_items_advanced,
            keywords,
            title,
            brand,
            search_index,
            min_price,
            max_price,
            min_reviews_rating,
            min_savings_percent,
            merchant,
            condition,
            item_count,
            item_page,
            sort_by,
            browse_node_id,
        )
        return result
    except Exception as exc:
        if "503" in str(exc) or "quota" in str(exc).lower():
            log.warning("PA-API quota exceeded for search")
            raise QuotaExceededError("PA-API quota exceeded for search") from exc
        log.error("PA-API advanced search error: %s", exc)
        return []


def _sync_search_items_advanced(
    keywords,
    title,
    brand,
    search_index,
    min_price,
    max_price,
    min_reviews_rating,
    min_savings_percent,
    merchant,
    condition,
    item_count,
    item_page,
    sort_by,
    browse_node_id,
) -> List[Dict]:
    """Synchronous advanced search implementation."""
    api = AmazonApi(
        key=settings.PAAPI_ACCESS_KEY,
        secret=settings.PAAPI_SECRET_KEY,
        tag=settings.PAAPI_TAG,
        country="IN",
    )

    # Build search parameters
    search_params = {
        "item_count": item_count,
        "item_page": item_page,
        "resources": get_resources_for_context("search_results"),
    }

    if keywords:
        search_params["keywords"] = keywords
    if title:
        search_params["title"] = title
    if brand:
        search_params["brand"] = brand
    if search_index != "All":
        search_params["search_index"] = search_index
    if min_price:
        search_params["min_price"] = min_price // 100  # Convert from paise to rupees
    if max_price:
        search_params["max_price"] = max_price // 100
    if merchant != "All":
        search_params["merchant"] = merchant
    if condition != "New":
        search_params["condition"] = condition
    if sort_by:
        search_params["sort_by"] = sort_by
    if browse_node_id:
        search_params["browse_node_id"] = browse_node_id

    try:
        results = api.search_items(**search_params)
        if not results:
            return []

        products = []
        for item in results:
            try:
                product_data = _extract_comprehensive_data(item)

                # Apply additional filtering
                if min_reviews_rating and product_data["reviews"]["average_rating"]:
                    if product_data["reviews"]["average_rating"] < min_reviews_rating:
                        continue

                if min_savings_percent and product_data["offers"]["savings_percentage"]:
                    if (
                        product_data["offers"]["savings_percentage"]
                        < min_savings_percent
                    ):
                        continue

                products.append(product_data)

            except Exception as item_error:
                log.warning("Error processing search result: %s", item_error)
                continue

        return products

    except Exception as e:
        log.error("PA-API advanced search failed: %s", e)
        raise


async def batch_get_items(
    asins: List[str], priority: str = "normal"
) -> Dict[str, Dict]:
    """Batch fetch up to 10 ASINs efficiently.

    Args:
    ----
        asins: List of ASINs (up to 10)
        priority: Request priority for rate limiting

    Returns:
    -------
        Dict mapping ASIN to product data

    Raises:
    ------
        QuotaExceededError: When PA-API quota is exceeded
    """
    if len(asins) > 10:
        raise ValueError("PA-API supports maximum 10 ASINs per batch request")

    if not asins:
        return {}

    await acquire_api_permission(priority)

    try:
        result = await asyncio.to_thread(_sync_batch_get_items, asins)
        return result
    except Exception as exc:
        if "503" in str(exc) or "quota" in str(exc).lower():
            log.warning("PA-API quota exceeded for batch request")
            raise QuotaExceededError("PA-API quota exceeded for batch request") from exc
        log.error("PA-API batch request error: %s", exc)
        raise


def _sync_batch_get_items(asins: List[str]) -> Dict[str, Dict]:
    """Synchronous batch get items implementation."""
    api = AmazonApi(
        key=settings.PAAPI_ACCESS_KEY,
        secret=settings.PAAPI_SECRET_KEY,
        tag=settings.PAAPI_TAG,
        country="IN",
    )

    try:
        resources = get_resources_for_context("product_details")
        items = api.get_items(asins, resources=resources)

        result = {}
        for item in items:
            asin = getattr(item, "asin", "")
            if asin:
                result[asin] = _extract_comprehensive_data(item)

        return result

    except Exception as e:
        log.error("PA-API batch request failed: %s", e)
        raise


async def get_browse_nodes_hierarchy(
    browse_node_id: int, priority: str = "normal"
) -> Dict:
    """Get complete category hierarchy information.

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
        result = await asyncio.to_thread(_sync_get_browse_nodes, browse_node_id)
        return result
    except Exception as exc:
        if "503" in str(exc) or "quota" in str(exc).lower():
            log.warning("PA-API quota exceeded for browse node: %s", browse_node_id)
            raise QuotaExceededError(
                f"PA-API quota exceeded for browse node {browse_node_id}"
            ) from exc
        log.error("PA-API browse node error: %s", exc)
        raise


def _sync_get_browse_nodes(browse_node_id: int) -> Dict:
    """Synchronous browse nodes implementation."""
    api = AmazonApi(
        key=settings.PAAPI_ACCESS_KEY,
        secret=settings.PAAPI_SECRET_KEY,
        tag=settings.PAAPI_TAG,
        country="IN",
    )

    try:
        resources = get_resources_for_context("browse_nodes")
        browse_nodes = api.get_browse_nodes([browse_node_id], resources=resources)

        if not browse_nodes:
            raise ValueError(f"No browse node found for ID: {browse_node_id}")

        node = browse_nodes[0]
        return {
            "id": node.id,
            "name": node.display_name,
            "children": [
                {"id": child.id, "name": child.display_name}
                for child in (node.children or [])
            ],
            "ancestors": [
                {"id": ancestor.id, "name": ancestor.display_name}
                for ancestor in (node.ancestor or [])
            ],
            "sales_rank": getattr(node, "sales_rank", None),
        }

    except Exception as e:
        log.error("PA-API browse nodes request failed: %s", e)
        raise
