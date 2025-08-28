"""Watch creation flow handlers."""

from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Optional

from sqlmodel import Session, select
import telegram
from telegram import Update
from telegram.ext import ContextTypes

from .cache_service import engine, get_price
from .carousel import build_single_card
from .models import User, Watch
from .paapi_factory import get_item_detailed, search_items_advanced
from .paapi_health import is_in_cooldown, set_rate_limit_cooldown
from .ui_helpers import build_brand_buttons, build_discount_buttons, build_price_buttons, build_mode_buttons
from .watch_parser import parse_watch, validate_watch_data

# Enhanced cache to completely eliminate duplicate API calls during watch creation
_search_cache = {}
_cache_ttl = 300  # Cache results for 5 minutes
_active_searches = {}  # Track ongoing searches to prevent duplicates

log = logging.getLogger(__name__)


async def _cached_search_items_advanced(keywords: str, item_count: int = 30, priority: str = "normal"):
    """Enhanced cached version that completely eliminates duplicate API calls."""
    cache_key = f"{keywords}:{item_count}"
    current_time = time.time()
    
    # Check if we have a valid cached result FIRST
    if cache_key in _search_cache:
        cached_data, timestamp = _search_cache[cache_key]
        if current_time - timestamp < _cache_ttl:
            log.info("Using cached search results for: %s", keywords)
            return cached_data
    
    # Check if there's already an active search for this key
    if cache_key in _active_searches:
        log.info("Waiting for active search to complete for: %s", keywords)
        try:
            return await _active_searches[cache_key]
        except Exception as e:
            log.warning("Active search failed for %s: %s", keywords, e)
            # Continue to make fresh call below
    
    # Create a future for this search to prevent duplicates
    search_future = asyncio.Future()
    _active_searches[cache_key] = search_future
    
    try:
        # Check if we're in a cooldown period
        if is_in_cooldown():
            log.warning("PA-API in cooldown, skipping call for: %s", keywords)
            search_future.set_result([])
            return []
        
        # Make the API call and cache the result
        log.info("Making fresh API call for: %s", keywords)
        results = await search_items_advanced(
            keywords=keywords,
            item_count=item_count,
            priority=priority
        )
        
        # Cache the results
        _search_cache[cache_key] = (results, current_time)
        
        # Clean up old cache entries
        keys_to_remove = [k for k, (_, ts) in _search_cache.items() if current_time - ts > _cache_ttl]
        for k in keys_to_remove:
            del _search_cache[k]
        
        # Signal completion to any waiting coroutines
        search_future.set_result(results)
        
        return results
        
    except Exception as e:
        # Check if this is a rate limiting error and activate cooldown
        error_str = str(e).lower()
        if "limit" in error_str or "quota" in error_str or "throttling" in error_str:
            log.error("Rate limiting detected, activating 10-minute cooldown")
            set_rate_limit_cooldown(600)  # 10 minute cooldown
        
        # Signal error to any waiting coroutines
        search_future.set_exception(e)
        raise
    finally:
        # Clean up the active search
        _active_searches.pop(cache_key, None)


# Common brand list for buttons (fallback)
COMMON_BRANDS = [
    "samsung",
    "lg",
    "sony",
    "boat",
    "apple",
    "mi",
    "oneplus",
    "realme",
    "oppo",
    "vivo",
    "xiaomi",
]


async def get_dynamic_brands(search_query: str, max_brands: int = 20, cached_results: list = None, max_price_filter: int = None, min_discount_filter: int = None) -> list[str]:
    """Get relevant brands from Amazon search results for the given query.
    
    Args:
    ----
        search_query: User's search query 
        max_brands: Maximum number of brands to return
        cached_results: Pre-fetched search results to avoid extra API calls
        max_price_filter: Optional price filter to only show brands with products within this price
        min_discount_filter: Optional discount filter to only show brands with products meeting discount requirement
        
    Returns:
    -------
        List of brand names relevant to the search query
        
    """
    try:
        log.info("Fetching dynamic brands for query: %s", search_query)
        
        # Use provided cached results first to avoid duplicate API calls
        if cached_results:
            log.info("Using provided cached results for brand extraction: %s", search_query)
            search_results = cached_results
        else:
            # Try enhanced PA-API only if no cached results provided (cached)
            search_results = await _cached_search_items_advanced(
                keywords=search_query, 
                item_count=30,
                priority="normal"
            )
        # Convert to expected format
        search_results = [
            {
                "title": item.get("title", ""),
                "asin": item.get("asin", ""),
                "price": item.get("price"),  # Price is at root level in official PA-API response
                "list_price": item.get("list_price"),  # List price for discount calculation
                "savings_percent": item.get("savings_percent")  # Pre-calculated savings if available
            }
            for item in search_results
        ]
        
        # Debug: Log first few products to see actual structure
        if search_results:
            log.info("CONVERSION DEBUG - First 3 converted products:")
            for i, item in enumerate(search_results[:3]):
                log.info("Product %d: %s", i+1, item)
        
        # If PA-API failed or returned no results, try scraper fallback
        if not search_results:
            log.info("PA-API returned no results for '%s', trying scraper fallback", search_query)
            from .scraper import scrape_amazon_search
            try:
                search_results = await scrape_amazon_search(search_query, max_results=20)
                log.info("Scraper found %d results for brand extraction: %s", len(search_results), search_query)
            except Exception as scraper_error:
                log.warning("Scraper also failed for '%s': %s", search_query, scraper_error)
                search_results = []
        
        if not search_results:
            log.warning("No search results from any source for dynamic brand extraction: %s", search_query)
            return COMMON_BRANDS[:max_brands]
        
        # Apply filters if specified to ensure brands only come from relevant products
        if max_price_filter or min_discount_filter:
            filtered_results = []
            log.info("Filtering %d products for brand extraction (price≤₹%s, discount≥%s%%)", 
                    len(search_results), max_price_filter or "any", min_discount_filter or "any")
            
            for product in search_results:
                include_product = True
                
                # Apply price filter
                if max_price_filter and include_product:
                    price = product.get("price")
                    if price and isinstance(price, (int, float)) and price > 0:
                        price_rs = price / 100 if price > 10000 else price
                        if price_rs > max_price_filter:
                            include_product = False
                    else:
                        # No price data - exclude from filtered brands
                        include_product = False
                
                # Apply discount filter  
                if min_discount_filter and include_product:
                    list_price = product.get("list_price")
                    current_price = product.get("price")
                    if list_price and current_price and isinstance(list_price, (int, float)) and isinstance(current_price, (int, float)):
                        if list_price > current_price:
                            discount_percent = ((list_price - current_price) / list_price) * 100
                            if discount_percent < min_discount_filter:
                                include_product = False
                        else:
                            include_product = False  # No actual discount
                    else:
                        include_product = False  # No discount data
                
                if include_product:
                    filtered_results.append(product)
            
            if filtered_results:
                search_results = filtered_results
                log.info("Filtered to %d products for brand extraction", len(filtered_results))
            else:
                log.warning("No products match filters for brand extraction, using unfiltered results")
        
        # Extract potential brands from product titles
        brands = set()
        
        # Enhanced brand extraction patterns
        brand_patterns = [
            # Brand at start: "Samsung Galaxy S24", "3M Car Polish" 
            r"^([A-Za-z][A-Za-z0-9]*(?:\s+[A-Za-z][A-Za-z0-9]*)?)\s+",
            # Brand in parentheses: "Polish (3M Brand)" or "(Apple iPhone 15)"
            r"\(([A-Za-z][A-Za-z0-9]*(?:\s+[A-Za-z][A-Za-z0-9]*(?:\s+[A-Za-z0-9]+)?)?)\)",
            # Brand with "by": "Polish by 3M Premium", "Made by Meguiar's"
            r"by\s+([A-Za-z0-9]+(?:\s+[A-Za-z]+)?)",
            # Common separators: "Brand - Product" or "Brand | Product"
            r"^([A-Za-z0-9]+(?:\s+[A-Za-z0-9]+)?)\s*[-|]\s*",
            # Brand with possessive: "Meguiar's Gold Class"
            r"^([A-Za-z][A-Za-z0-9]*'[s])\s+",
            # Brand with dots: "Dr. Smith's Face Wash"
            r"^([A-Za-z][A-Za-z0-9]*\.?\s+[A-Za-z][A-Za-z0-9]*)\s+",
            # Standalone possessive brands: "Meguiar's" anywhere in title
            r"\b([A-Za-z][A-Za-z0-9]*'[s])\b",
            # Find known brand patterns: "Turtle Wax", "Chemical Guys", etc.
            r"\b([A-Za-z]+(?:\s+[A-Za-z]+)?)\s+(wax|guys|care|polish|wash)\b",
            # Simple two-word brands: "Turtle Wax", "Chemical Guys" - more direct extraction
            r"\b(turtle|chemical|armor|mothers|sonax|griot's|meguiar's|3m|dr)\s+([a-z]+)\b",
        ]
        
        # Expanded filter list for non-brand words
        non_brand_words = {
            "the", "and", "for", "with", "pack", "set", "new", "pro", "max", "mini", "ultra", "plus", 
            "case", "cover", "phone", "mobile", "car", "auto", "face", "skin", "hair", "body", 
            "wash", "care", "polish", "wax", "cream", "gel", "soap", "shampoo", "oil", "spray",
            "liquid", "foam", "paste", "kit", "combo", "organic", "natural", "herbal",
            "advanced", "professional", "instant", "quick", "easy", "super", "mega", "extra",
            "best", "top", "high", "low", "pure", "fresh", "clean", "soft", "hard", "heavy",
            "light", "dark", "white", "black", "red", "blue", "green", "ml", "gm", "kg", "pcs",
            "litre", "liter", "gram", "all", "some", "many", "car polish", "phone case"
        }
        
        for product in search_results:
            title = product.get("title", "").strip()
            if not title:
                continue
                
            log.debug("Processing title for brands: %s", title[:80])
                
            # Try each pattern to extract brand
            for i, pattern in enumerate(brand_patterns):
                try:
                    matches = re.findall(pattern, title, re.IGNORECASE)
                    for match in matches:
                        brand = match.strip().lower()
                        # Enhanced filtering
                        if (brand and len(brand) >= 2 and 
                            brand not in non_brand_words and
                            not brand.isdigit() and  # Exclude pure numbers
                            not re.match(r'^\d+\s*[a-z]*$', brand) and  # Exclude "250ml", "5kg", "1 l" etc
                            not re.match(r'^[a-z]*\d+[a-z]*\d*', brand) and  # Exclude product codes like "ia260166334"
                            not brand.endswith('gm') and not brand.endswith('ml')):  # Exclude quantities
                            brands.add(brand)
                            log.debug("Pattern %d extracted brand: '%s'", i+1, brand)
                except Exception as pattern_error:
                    log.debug("Pattern %d failed: %s", i+1, pattern_error)
                    continue
                        
            # Also check first word of title (common for brand-first naming)
            words = title.split()
            if words:
                first_word = words[0].lower()
                if (first_word and len(first_word) >= 2 and 
                    first_word not in non_brand_words and
                    not first_word.isdigit() and
                    not re.match(r'^\d+\s*[a-z]*$', first_word) and
                    not re.match(r'^[a-z]*\d+[a-z]*\d*', first_word) and
                    not first_word.endswith('gm') and not first_word.endswith('ml')):
                    brands.add(first_word)
                    log.debug("First word extracted: '%s'", first_word)
        
        # Convert to list and prioritize known common brands, then alphabetical
        brand_list = list(brands)
        # Sort to prioritize common brands first, then alphabetically
        common_brand_names = {brand.lower() for brand in COMMON_BRANDS}
        brand_list.sort(key=lambda x: (x not in common_brand_names, x))
        brand_list = brand_list[:max_brands]
        
        if brand_list:
            log.info("Extracted %d dynamic brands for '%s': %s", len(brand_list), search_query, brand_list)
            return brand_list
        else:
            log.warning("No valid brands extracted, using fallback for: %s", search_query)
            return COMMON_BRANDS[:max_brands]
            
    except Exception as e:
        log.error("Error fetching dynamic brands for '%s': %s", search_query, e)
        # Fallback to common brands
        return COMMON_BRANDS[:max_brands]


async def get_dynamic_price_ranges(search_query: str, cached_results: list = None, brand_filter: str = None, min_discount_filter: int = None) -> list[tuple[str, int]]:
    """Get relevant price ranges from Amazon search results for the given query.
    
    Args:
    ----
        search_query: User's search query 
        cached_results: Pre-fetched search results to avoid extra API calls
        brand_filter: Optional brand filter to only consider products from this brand
        min_discount_filter: Optional discount filter to only consider products with this discount
        
    Returns:
    -------
        List of (display_text, price_value) tuples for price range buttons
        
    """
    try:
        log.info("Fetching dynamic price ranges for query: %s", search_query)
        
        # Extract user's stated budget from query
        user_budget = _extract_budget_from_query(search_query)
        if user_budget:
            log.info("Extracted user budget from query '%s': ₹%s", search_query, user_budget)
        
        # Use provided cached results first to avoid duplicate API calls
        if cached_results:
            log.info("Using provided cached results for price extraction: %s", search_query)
            search_results = cached_results
        else:
            # Search for products related to the query using enhanced PA-API only if needed (cached)
            search_results = await _cached_search_items_advanced(
                keywords=search_query, 
                item_count=30,
                priority="normal"
            )
        # Convert to expected format for price extraction
        search_results = [
            {
                "title": item.get("title", ""),
                "asin": item.get("asin", ""),
                "price": item.get("price")  # Price is at root level in official PA-API response
            }
            for item in search_results
        ]
        
        if not search_results:
            log.warning("No search results for dynamic price extraction: %s", search_query)
            return _get_default_price_ranges()
        
        # Apply filters if specified to ensure price ranges only come from relevant products
        if brand_filter or min_discount_filter:
            filtered_results = []
            log.info("Filtering %d products for price range extraction (brand='%s', discount≥%s%%)", 
                    len(search_results), brand_filter or "any", min_discount_filter or "any")
            
            for product in search_results:
                include_product = True
                
                # Apply brand filter
                if brand_filter and include_product:
                    title = product.get("title", "").lower()
                    if brand_filter.lower() not in title:
                        include_product = False
                
                # Apply discount filter  
                if min_discount_filter and include_product:
                    list_price = product.get("list_price")
                    current_price = product.get("price")
                    if list_price and current_price and isinstance(list_price, (int, float)) and isinstance(current_price, (int, float)):
                        if list_price > current_price:
                            discount_percent = ((list_price - current_price) / list_price) * 100
                            if discount_percent < min_discount_filter:
                                include_product = False
                        else:
                            include_product = False  # No actual discount
                    else:
                        include_product = False  # No discount data
                
                if include_product:
                    filtered_results.append(product)
            
            if filtered_results:
                search_results = filtered_results
                log.info("Filtered to %d products for price range extraction", len(filtered_results))
            else:
                log.warning("No products match filters for price range extraction - using broader criteria")
                # Instead of using completely unfiltered results, try relaxing filters incrementally
                if brand_filter and min_discount_filter:
                    # Try with brand only (remove discount filter)
                    log.info("Trying price ranges with brand filter only (removing discount requirement)")
                    filtered_results = [p for p in search_results if brand_filter.lower() in p.get("title", "").lower()]
                    if filtered_results:
                        search_results = filtered_results
                        log.info("Found %d products with brand filter only", len(filtered_results))
        
        # Extract prices from search results
        prices = []
        
        for i, product in enumerate(search_results[:5]):  # Debug first 5 products
            price = product.get("price")
            list_price = product.get("list_price")
            log.info("PRICE DEBUG - Product %d: title='%s', price=%s (type=%s), list_price=%s (type=%s)", 
                     i+1, product.get("title", "")[:50], price, type(price), list_price, type(list_price))
            # Also log the full product structure for the first product
            if i == 0:
                log.info("STRUCTURE DEBUG - Full first product: %s", product)
            if price and isinstance(price, (int, float)) and price > 0:
                # Convert to rupees if in paise
                price_rs = price / 100 if price > 10000 else price
                if 10 <= price_rs <= 1000000:  # Reasonable price range
                    prices.append(int(price_rs))
                    log.debug("Added price: %s paise → ₹%s", price, int(price_rs))
            elif price == 0:
                log.debug("Zero price found for product: %s", product.get("title", "")[:50])
            elif not price:
                log.debug("No price data for product: %s", product.get("title", "")[:50])
        
        if not prices:
            log.warning("No valid prices found from SearchItems for '%s' - trying GetItems fallback", search_query)
            # Fallback: Try to get prices using GetItems for first few ASINs
            try:
                from .paapi_factory import get_paapi_client
                client = await get_paapi_client()
                
                # Get ASINs from search results  
                asins_to_check = [item.get("asin") for item in search_results[:10] if item.get("asin")][:5]  # Check first 5 ASINs
                log.info("Attempting GetItems price lookup for ASINs: %s", asins_to_check)
                
                prices_from_getitems = []
                for asin in asins_to_check:
                    try:
                        item_data = await client.get_item_detailed(asin, priority="high")
                        if item_data and item_data.get("price"):
                            price = item_data["price"]
                            price_rs = price / 100 if price > 10000 else price
                            if 10 <= price_rs <= 1000000:
                                prices_from_getitems.append(int(price_rs))
                                log.info("GetItems found price for %s: ₹%s", asin, int(price_rs))
                    except Exception as e:
                        log.debug("GetItems failed for ASIN %s: %s", asin, e)
                        continue
                
                if prices_from_getitems:
                    log.info("Using %d prices from GetItems fallback", len(prices_from_getitems))
                    prices = prices_from_getitems
                else:
                    log.warning("GetItems fallback also failed, using default ranges")
                    return _get_default_price_ranges()
            except Exception as e:
                log.warning("GetItems fallback error: %s, using default ranges", e)
                return _get_default_price_ranges()
        
        # Sort prices to analyze distribution
        prices.sort()
        log.debug("Found %d prices for '%s': %s", len(prices), search_query, prices[:10])
        
        # Remove outliers (bottom 10% and top 10%)
        if len(prices) >= 10:
            start_idx = len(prices) // 10
            end_idx = len(prices) - (len(prices) // 10)
            prices = prices[start_idx:end_idx]
        
        # Generate price ranges based on distribution and user budget
        min_price = prices[0]
        max_price = prices[-1]
        
        # Use user budget as ceiling if provided and higher than max product price
        effective_max_price = max_price
        if user_budget and user_budget > max_price:
            effective_max_price = user_budget
            log.info("Using user budget ₹%s as ceiling (higher than max product price ₹%s)", 
                    user_budget, max_price)
        
        # Create 4-5 meaningful price brackets based on effective max price
        price_ranges = []
        
        if effective_max_price <= 1500:
            # Low-priced items (under ₹1500) - car polish, accessories
            brackets = [300, 500, 800, 1200]
        elif effective_max_price <= 5000:
            # Mid-priced items (₹1500-5000) - gadgets, tools
            brackets = [1000, 2000, 3000, 5000]
        elif effective_max_price <= 25000:
            # Higher-priced items (₹5000-25000) - appliances, electronics
            brackets = [5000, 10000, 15000, 25000]
        elif effective_max_price <= 100000:
            # Premium items (₹25000-100000) - phones, laptops, monitors
            brackets = [25000, 50000, 75000, 100000]
        else:
            # Luxury items (₹100000+) - high-end electronics
            brackets = [100000, 200000, 500000, 1000000]
        
        # Filter brackets to only include relevant ranges
        relevant_brackets = []
        for bracket in brackets:
            if bracket >= min_price * 0.8:  # Include ranges that make sense
                relevant_brackets.append(bracket)
                if len(relevant_brackets) >= 4:  # Limit to 4 ranges
                    break
        
        # Format price ranges
        for price in relevant_brackets:
            if price >= 100000:
                display = f"Under ₹{price//100000}L"
            elif price >= 1000:
                display = f"Under ₹{price//1000}k"
            else:
                display = f"Under ₹{price}"
            price_ranges.append((display, price))
        
        log.info("Generated %d dynamic price ranges for '%s': %s", 
                len(price_ranges), search_query, [r[0] for r in price_ranges])
        
        return price_ranges
        
    except Exception as e:
        log.error("Error fetching dynamic price ranges for '%s': %s", search_query, e)
        return _get_default_price_ranges()


def _get_default_price_ranges() -> list[tuple[str, int]]:
    """Get default price ranges as fallback."""
    return [
        ("Under ₹10k", 10000),
        ("Under ₹25k", 25000), 
        ("Under ₹50k", 50000),
        ("Under ₹1L", 100000),
    ]


def _extract_budget_from_query(query: str) -> Optional[int]:
    """Extract budget/price constraint from natural language query.
    
    Args:
    ----
        query: User's search query (e.g., "monitor under INR 50000")
        
    Returns:
    -------
        Budget in rupees if found, None otherwise
        
    Examples:
    --------
        "monitor under INR 50000" -> 50000
        "laptop below 75k" -> 75000
        "phone under ₹25000" -> 25000
    """
    import re
    
    # Patterns to match budget expressions
    patterns = [
        r'under\s+(?:inr\s+|₹\s*)?(\d+(?:,\d{3})*(?:k|000)?)',  # "under INR 50000", "under ₹50k"
        r'below\s+(?:inr\s+|₹\s*)?(\d+(?:,\d{3})*(?:k|000)?)',  # "below 50k"
        r'within\s+(?:inr\s+|₹\s*)?(\d+(?:,\d{3})*(?:k|000)?)', # "within ₹50000"
        r'budget\s+(?:of\s+)?(?:inr\s+|₹\s*)?(\d+(?:,\d{3})*(?:k|000)?)', # "budget of 50k"
        r'max\s+(?:price\s+)?(?:inr\s+|₹\s*)?(\d+(?:,\d{3})*(?:k|000)?)', # "max price 50k"
        r'up\s+to\s+(?:inr\s+|₹\s*)?(\d+(?:,\d{3})*(?:k|000)?)', # "up to ₹50000"
    ]
    
    query_lower = query.lower()
    
    for pattern in patterns:
        match = re.search(pattern, query_lower)
        if match:
            amount_str = match.group(1).replace(',', '')  # Remove commas
            
            try:
                # Handle 'k' suffix (thousands)
                if amount_str.endswith('k'):
                    amount = int(float(amount_str[:-1]) * 1000)
                elif amount_str.endswith('000') and len(amount_str) <= 6:  # e.g., "50000"
                    amount = int(amount_str)
                else:
                    amount = int(amount_str)
                
                # Sanity check - budget should be reasonable (₹100 to ₹10L)
                if 100 <= amount <= 1000000:
                    return amount
                    
            except (ValueError, TypeError):
                continue
    
    return None


async def start_watch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /watch command to start watch creation flow.

    Args:
    ----
        update: Telegram update object
        context: Bot context with user data and args

    """
    if not context.args:
        await update.message.reply_text(
            "🔍 *Add a Watch*\n\n"
            "Send me a product description or Amazon link!\n\n"
            "*Examples:*\n"
            "• `Samsung 27 inch gaming monitor under 30000`\n"
            "• `https://amazon.in/dp/B09XYZ1234`\n"
            "• `Apple iPhone 15 with minimum 20% discount`",
            parse_mode="Markdown",
        )
        return

    # Join all arguments as search text
    search_text = " ".join(context.args)

    # Parse the input text
    parsed_data = parse_watch(search_text)
    log.info("Parsed watch data for user %s: %s", update.effective_user.id, parsed_data)

    # Validate the parsed data
    errors = validate_watch_data(parsed_data)
    if errors:
        error_msg = "⚠️ *Found some issues:*\n" + "\n".join(
            f"• {err}" for err in errors.values()
        )
        await update.message.reply_text(error_msg, parse_mode="Markdown")
        return

    # Store in user data for later use
    context.user_data["pending_watch"] = parsed_data
    context.user_data["original_message_id"] = update.message.message_id

    # Always ask for missing fields to give users control over their watch criteria
    missing_fields = []
    if not parsed_data.get("_brand_selected", False):
        missing_fields.append("brand")
    if not parsed_data.get("_discount_selected", False):
        missing_fields.append("discount")
    if not parsed_data.get("_price_selected", False):
        missing_fields.append("price")
    
    # Also ask for monitoring mode if not specified
    if not parsed_data.get("mode"):
        missing_fields.append("mode")

    # If nothing is missing, finalize the watch
    if not missing_fields:
        await _finalize_watch(update, context, parsed_data)
        return

    # Ask for the first missing field
    await _ask_for_missing_field(update, context, missing_fields[0])


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button callbacks for watch creation.

    Args:
    ----
        update: Telegram update object with callback query
        context: Bot context with user data

    """
    query = update.callback_query
    await query.answer()

    # Get pending watch data
    parsed_data = context.user_data.get("pending_watch", {})
    if not parsed_data:
        await query.edit_message_text(
            "❌ Session expired. Please start a new /watch command."
        )
        return

    # Handle different callback types
    if query.data.startswith("brand:"):
        brand = query.data.split(":", 1)[1]
        if brand == "skip":
            parsed_data["brand"] = None
        else:
            parsed_data["brand"] = brand
        parsed_data["_brand_selected"] = True  # Mark as processed
        log.info("User %s selected brand: %s", update.effective_user.id, brand)

    elif query.data.startswith("disc:"):
        discount_value = query.data.split(":", 1)[1]
        if discount_value == "skip":
            parsed_data["min_discount"] = None
        else:
            parsed_data["min_discount"] = int(discount_value)
        parsed_data["_discount_selected"] = True  # Mark as processed
        log.info(
            "User %s selected discount: %s", update.effective_user.id, discount_value
        )

    elif query.data.startswith("price:"):
        price_value = query.data.split(":", 1)[1]
        if price_value == "skip":
            parsed_data["max_price"] = None
        else:
            parsed_data["max_price"] = int(price_value)
        parsed_data["_price_selected"] = True  # Mark as processed
        log.info("User %s selected price: %s", update.effective_user.id, price_value)

    elif query.data.startswith("mode:"):
        mode_value = query.data.split(":", 1)[1]
        parsed_data["mode"] = mode_value
        log.info("User %s selected mode: %s", update.effective_user.id, mode_value)

    else:
        await query.edit_message_text("❌ Unknown option selected.")
        return

    # Update stored data
    context.user_data["pending_watch"] = parsed_data

    # Check what's still missing (use processed markers to avoid re-asking skipped fields)
    missing_fields = []
    if not parsed_data.get("_brand_selected", False):
        missing_fields.append("brand")
    if not parsed_data.get("_discount_selected", False):
        missing_fields.append("discount")
    if not parsed_data.get("_price_selected", False):
        missing_fields.append("price")
    if not parsed_data.get("mode"):
        missing_fields.append("mode")

    log.info(
        "User %s callback processed. Current data: %s, missing fields: %s",
        update.effective_user.id,
        parsed_data,
        missing_fields,
    )

    # If nothing is missing, finalize the watch
    if not missing_fields:
        log.info(
            "All fields complete, finalizing watch for user %s",
            update.effective_user.id,
        )
        await _finalize_watch(update, context, parsed_data)
        return

    # Ask for the next missing field
    log.info(
        "Asking for next missing field '%s' for user %s",
        missing_fields[0],
        update.effective_user.id,
    )
    await _ask_for_missing_field(update, context, missing_fields[0], edit=True)


async def _ask_for_missing_field(
    update: Update, context: ContextTypes.DEFAULT_TYPE, field: str, edit: bool = False
) -> None:
    """Ask user for a missing field using inline buttons.

    Args:
    ----
        update: Telegram update object
        context: Bot context
        field: Name of missing field ('brand', 'discount', 'price')
        edit: Whether to edit existing message or send new one

    """
    # Pre-fetch search results ONCE and reuse for both brands and prices
    search_query = context.user_data.get("pending_watch", {}).get("keywords", "")
    search_results = None
    
    # Only fetch search results if we need them for dynamic data (brand or price)
    if field in ["brand", "price"] and search_query:
        try:
            # Check if we already have cached search results in user data
            search_results = context.user_data.get("search_results")
            if not search_results:
                log.info("Pre-fetching search results for dynamic options: %s", search_query)
                search_results = await _cached_search_items_advanced(
                    keywords=search_query, 
                    item_count=30,
                    priority="normal"
                )
                # Cache in user data to prevent future calls during this session
                context.user_data["search_results"] = search_results
                log.info("Cached search results for session: %d items", len(search_results))
            else:
                log.info("Using session cached search results: %d items", len(search_results))
        except Exception as e:
            log.warning("Failed to pre-fetch search results for '%s': %s", search_query, e)
            search_results = None
    
    if field == "brand":
        text = "🏷️ *Choose a brand:*\n\nSelect the brand you're looking for:"
        
        if search_query and search_results is not None:
            try:
                # Get existing filters to make brand suggestions more relevant
                pending_watch = context.user_data.get("pending_watch", {})
                max_price = pending_watch.get("max_price")
                min_discount = pending_watch.get("min_discount")
                
                dynamic_brands = await get_dynamic_brands(
                    search_query, 
                    cached_results=search_results,
                    max_price_filter=max_price,
                    min_discount_filter=min_discount
                )
                keyboard = build_brand_buttons(dynamic_brands)
            except Exception as e:
                log.warning("Failed to get dynamic brands for '%s': %s, using fallback", search_query, e)
                keyboard = build_brand_buttons(COMMON_BRANDS)
        else:
            keyboard = build_brand_buttons(COMMON_BRANDS)

    elif field == "discount":
        text = "💸 *Minimum discount:*\n\nWhat's the minimum discount you want to be notified about?"
        keyboard = build_discount_buttons()

    elif field == "price":
        text = "💰 *Maximum price:*\n\nWhat's your budget for this product?"
        
        if search_query and search_results is not None:
            try:
                # Get existing filters to make price suggestions more relevant
                pending_watch = context.user_data.get("pending_watch", {})
                selected_brand = pending_watch.get("brand")
                min_discount = pending_watch.get("min_discount")
                
                dynamic_ranges = await get_dynamic_price_ranges(
                    search_query, 
                    cached_results=search_results,
                    brand_filter=selected_brand,
                    min_discount_filter=min_discount
                )
                keyboard = build_price_buttons(dynamic_ranges)
            except Exception as e:
                log.warning("Failed to get dynamic price ranges for '%s': %s, using fallback", search_query, e)
                keyboard = build_price_buttons()
        else:
            keyboard = build_price_buttons()

    elif field == "mode":
        text = "⏰ *Monitoring mode:*\n\nHow often would you like to check for deals?"
        keyboard = build_mode_buttons()

    else:
        log.error("Unknown field requested: %s", field)
        return

    # Send or edit message
    if edit and update.callback_query:
        try:
            await update.callback_query.edit_message_text(
                text=text,
                reply_markup=keyboard,
                parse_mode="Markdown",
            )
        except telegram.error.BadRequest as e:
            # Handle case where message content is identical
            if "Message is not modified" in str(e):
                log.warning("Message content identical, skipping edit for field: %s", field)
                # Just answer the callback query to remove the loading state
                await update.callback_query.answer()
            else:
                # Re-raise other BadRequest errors
                raise
    else:
        await update.effective_message.reply_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="Markdown",
        )


async def _finalize_watch(
    update: Update, context: ContextTypes.DEFAULT_TYPE, watch_data: dict
) -> None:
    """Finalize watch creation by saving to DB and fetching current price.

    Args:
    ----
        update: Telegram update object
        context: Bot context
        watch_data: Complete watch data dictionary

    """
    user_id = update.effective_user.id

    log.info("Starting finalize_watch for user %s with data: %s", user_id, watch_data)

    try:
        # Ensure user exists in database
        with Session(engine) as session:
            # Check if user exists
            user_statement = select(User).where(User.tg_user_id == user_id)
            user = session.exec(user_statement).first()

            # Create user if doesn't exist
            if not user:
                user = User(tg_user_id=user_id)
                session.add(user)
                session.commit()
                session.refresh(user)
                log.info("Created new user: %s", user_id)

            # Try to find ASIN if not provided
            asin = watch_data.get("asin")
            if not asin:
                try:
                    log.info("No ASIN provided, attempting product search for: %s", watch_data["keywords"])
                    
                    # First check if we have cached results from the watch creation flow
                    search_results = context.user_data.get("search_results")
                    if search_results:
                        log.info("Using session cached search results for ASIN lookup: %d items", len(search_results))
                    else:
                        # Only make API call if we don't have cached results
                        search_results = await _cached_search_items_advanced(
                            keywords=watch_data["keywords"],
                            item_count=30,  # Use same count as price range search for better cache hits
                            priority="high"  # High priority for user watch creation
                        )
                    if search_results:
                        # Filter results based on brand if specified
                        if watch_data.get("brand"):
                            brand_filtered = [
                                product for product in search_results 
                                if watch_data["brand"].lower() in product.get("title", "").lower()
                            ]
                            if brand_filtered:
                                search_results = brand_filtered
                        
                        # Filter results based on max_price if specified
                        if watch_data.get("max_price"):
                            max_price = watch_data["max_price"]
                            log.info("Applying price filter ≤₹%s to %d products", max_price, len(search_results))
                            
                            # Check if any products have price data from SearchItems
                            products_with_prices = [p for p in search_results if p.get("price")]
                            
                            if not products_with_prices:
                                log.info("No price data from SearchItems, using batch GetItems to fetch pricing for filtering")
                                # Enrich search results with batch GetItems pricing data
                                try:
                                    from .paapi_factory import get_items_batch
                                    
                                    # Extract ASINs for batch processing
                                    asins_to_enrich = [product.get("asin") for product in search_results if product.get("asin")]
                                    
                                    if asins_to_enrich:
                                        log.info("Processing %d ASINs in batches for price enrichment", len(asins_to_enrich))
                                        
                                        # Use batch processing - much faster than individual calls
                                        batch_results = await get_items_batch(asins_to_enrich, priority="high")
                                        
                                        # Enrich search results with batch data
                                        enriched_results = []
                                        for product in search_results:
                                            asin = product.get("asin")
                                            if asin and asin in batch_results:
                                                item_data = batch_results[asin]
                                                if item_data and item_data.get("price"):
                                                    # Enrich with price data
                                                    enriched_product = product.copy()
                                                    enriched_product["price"] = item_data["price"]
                                                    enriched_product["list_price"] = item_data.get("list_price")
                                                    enriched_results.append(enriched_product)
                                                    log.info("Enriched %s with price: ₹%s", asin, item_data["price"]//100 if item_data["price"] > 10000 else item_data["price"])
                                                else:
                                                    # Keep product without price
                                                    enriched_results.append(product)
                                            else:
                                                # Keep product without enrichment data
                                                enriched_results.append(product)
                                        
                                        search_results = enriched_results
                                        log.info("Enriched %d products with GetItems pricing data", len([p for p in search_results if p.get("price")]))
                                    else:
                                        log.warning("No valid ASINs found for batch enrichment")
                                
                                except Exception as e:
                                    log.warning("Failed to enrich with GetItems data: %s", e)
                            
                            # Now apply price filtering with enriched data
                            price_filtered = []
                            for i, product in enumerate(search_results):
                                price = product.get("price")
                                log.info("FINAL FILTER DEBUG - Product %d: title='%s', price=%s (type=%s)", 
                                        i+1, product.get("title", "")[:40], price, type(price))
                                if price and isinstance(price, (int, float)) and price > 0:
                                    # Convert to rupees if in paise (same logic as price extraction)
                                    price_rs = price / 100 if price > 10000 else price
                                    log.info("FINAL FILTER DEBUG - Product %d: '%s' - Price: ₹%s (within limit: %s)", 
                                             i+1, product.get("title", "")[:40], int(price_rs), price_rs <= max_price)
                                    if price_rs <= max_price:
                                        price_filtered.append(product)
                                else:
                                    log.debug("Product %d: '%s' - No valid price data", i+1, product.get("title", "")[:40])
                            
                            if price_filtered:
                                search_results = price_filtered
                                log.info("Applied price filter ≤₹%s, found %d matching products", max_price, len(price_filtered))
                            else:
                                log.warning("No products found within price limit ₹%s - will not create watch", max_price)
                                # Don't create watch if no products meet price criteria
                                await update.callback_query.edit_message_text(
                                    f"❌ **No products found!**\n\n"
                                    f"Couldn't find any **{watch_data.get('brand', '')} {watch_data['keywords']}** "
                                    f"under **₹{max_price:,}**.\n\n"
                                    f"💡 *Try:*\n"
                                    f"• Increasing your budget\n"
                                    f"• Removing brand filter\n"
                                    f"• Using broader search terms",
                                    parse_mode="Markdown"
                                )
                                return
                        
                        # Filter results based on min_discount if specified  
                        if watch_data.get("min_discount"):
                            min_discount = watch_data["min_discount"]
                            discount_filtered = []
                            log.info("Applying discount filter ≥%s%% to %d products", min_discount, len(search_results))
                            for i, product in enumerate(search_results):
                                # Check if product has discount information
                                list_price = product.get("list_price")
                                current_price = product.get("price")
                                
                                if list_price and current_price and isinstance(list_price, (int, float)) and isinstance(current_price, (int, float)):
                                    if list_price > current_price:  # Ensure there's actually a discount
                                        discount_percent = ((list_price - current_price) / list_price) * 100
                                        log.debug("Product %d: '%s' - Discount: %s%% (meets requirement: %s)", 
                                                 i+1, product.get("title", "")[:40], int(discount_percent), discount_percent >= min_discount)
                                        if discount_percent >= min_discount:
                                            discount_filtered.append(product)
                                    else:
                                        log.debug("Product %d: '%s' - No actual discount (list=current price)", i+1, product.get("title", "")[:40])
                                else:
                                    log.debug("Product %d: '%s' - No discount data available", i+1, product.get("title", "")[:40])
                            
                            if discount_filtered:
                                search_results = discount_filtered
                                log.info("Applied discount filter ≥%s%%, found %d matching products", min_discount, len(discount_filtered))
                            else:
                                log.warning("No products found with ≥%s%% discount - will not create watch", min_discount)
                                # Don't create watch if no products meet discount criteria
                                brand_text = f"{watch_data.get('brand', '')} " if watch_data.get('brand') else ""
                                price_text = f" under ₹{watch_data.get('max_price', 0):,}" if watch_data.get('max_price') else ""
                                await update.callback_query.edit_message_text(
                                    f"❌ **No deals found!**\n\n"
                                    f"Couldn't find any **{brand_text}{watch_data['keywords']}**{price_text} "
                                    f"with **≥{min_discount}% discount**.\n\n"
                                    f"💡 *Try:*\n"
                                    f"• Lowering discount requirement\n"
                                    f"• Removing price/brand filters\n"
                                    f"• Checking back later for new deals",
                                    parse_mode="Markdown"
                                )
                                return
                        
                        # Use intelligent product selection (Phase 4: AI-powered selection)
                        from .product_selection_models import smart_product_selection
                        from .ai_performance_monitor import log_ai_selection
                        
                        best_match = await smart_product_selection(
                            products=search_results,
                            user_query=watch_data["keywords"],
                            user_preferences=watch_data
                        )
                        
                        if not best_match:
                            # Fallback to first result if all models fail
                            best_match = search_results[0]
                        
                        asin = best_match.get("asin")
                        
                        # Create watch record first (needed for multi-card experience)
                        watch = Watch(
                            user_id=user.id,
                            asin=asin,
                            keywords=watch_data["keywords"],
                            brand=watch_data.get("brand"),
                            max_price=watch_data.get("max_price"),
                            min_discount=watch_data.get("min_discount"),
                            mode=watch_data.get("mode", "daily"),  # Use selected mode or default to daily
                        )

                        session.add(watch)
                        session.commit()
                        session.refresh(watch)
                        
                        log.info("Created watch %d for user %s", watch.id, user_id)
                        
                        # Check if we should use multi-card experience (Phase 6 enhancement)
                        use_multi_card = False
                        if best_match and len(search_results) >= 3:
                            # Check if multi-card would provide value
                            ai_metadata = best_match.get("_ai_metadata", {})
                            ai_confidence = ai_metadata.get("ai_confidence", 0) if ai_metadata else 0
                            
                            # Use multi-card if:
                            # 1. AI was used and confidence is moderate (not too high, indicating competition)
                            # 2. OR no AI was used but we have multiple good products 
                            use_ai_multicard = (ai_metadata and ai_confidence < 0.9)
                            use_general_multicard = (not ai_metadata and len(search_results) >= 5)
                            
                            if use_ai_multicard or use_general_multicard:
                                use_multi_card = True
                                log.info("Using multi-card experience: %d products, AI confidence: %.3f", 
                                        len(search_results), ai_confidence)

                        if use_multi_card:
                            # Use Phase 6 multi-card experience
                            try:
                                from .ai.enhanced_product_selection import EnhancedFeatureMatchModel
                                from .ai.enhanced_carousel import build_product_carousel
                                
                                enhanced_model = EnhancedFeatureMatchModel()
                                selection_result = await enhanced_model.select_products(
                                    products=search_results[:5],  # Top 5 candidates
                                    user_query=watch_data["keywords"],
                                    user_preferences=watch_data,
                                    enable_multi_card=True
                                )
                                
                                if selection_result.get("presentation_mode") != "single":
                                    # Send multi-card carousel and skip single card logic
                                    cards = build_product_carousel(
                                        products=selection_result["products"],
                                        comparison_table=selection_result["comparison_table"],
                                        selection_reason=selection_result["selection_reason"],
                                        watch_id=watch.id
                                    )
                                    
                                    # Send intro message
                                    intro_msg = f"🤖 **AI Found {len(selection_result['products'])} Great Options**\n\n"
                                    intro_msg += selection_result["selection_reason"]
                                    intro_msg += "\n\n👆 Tap any product to create your watch!"
                                    
                                    if update.callback_query:
                                        await update.callback_query.edit_message_text(intro_msg, parse_mode="Markdown")
                                    else:
                                        await update.effective_message.reply_text(intro_msg, parse_mode="Markdown")
                                    
                                    # Send product cards
                                    for card in cards:
                                        if card["type"] == "product_card":
                                            # Validate image URL before sending
                                            image_url = card.get("image", "").strip()
                                            if image_url and image_url.startswith(('http://', 'https://')):
                                                try:
                                                    await update.effective_message.reply_photo(
                                                        photo=image_url,
                                                        caption=card["caption"],
                                                        reply_markup=card["keyboard"],
                                                        parse_mode="Markdown"
                                                    )
                                                except telegram.error.BadRequest as img_error:
                                                    log.warning("Failed to send image %s: %s", image_url, img_error)
                                                    # Fallback to text message
                                                    await update.effective_message.reply_text(
                                                        card["caption"],
                                                        reply_markup=card["keyboard"],
                                                        parse_mode="Markdown"
                                                    )
                                            else:
                                                log.warning("Invalid or missing image URL for product card: %s", image_url)
                                                # Send as text message when no valid image
                                                await update.effective_message.reply_text(
                                                    card["caption"],
                                                    reply_markup=card["keyboard"],
                                                    parse_mode="Markdown"
                                                )
                                        else:
                                            await update.effective_message.reply_text(
                                                card["caption"],
                                                reply_markup=card.get("keyboard"),
                                                parse_mode="Markdown"
                                            )
                                    
                                    log.info("Successfully sent multi-card carousel with %d products to user %s", 
                                            len(selection_result["products"]), user_id)
                                    
                                    # Update final message to indicate success
                                    success_msg = "✅ **Multi-card experience sent successfully!**"
                                    log.info("Successfully created watch and sent confirmation to user %s", user_id)
                                    return
                                    
                            except Exception as multi_card_error:
                                log.warning("Multi-card experience failed, falling back to single card: %s", multi_card_error)
                                log.debug("Multi-card error details", exc_info=True)
                                # Continue to single card fallback below
                        
                        # Log AI selection performance for monitoring
                        selection_metadata = {}
                        model_used = "UltimateFallback"
                        
                        if "_ai_metadata" in best_match:
                            ai_data = best_match["_ai_metadata"]
                            model_used = "FeatureMatchModel"
                            selection_metadata.update({
                                "model_used": model_used,
                                "ai_score": ai_data.get("ai_score", 0),
                                "ai_confidence": ai_data.get("ai_confidence", 0),
                                "matched_features": ai_data.get("matched_features", []),
                                "processing_time_ms": ai_data.get("processing_time_ms", 0)
                            })
                            log.info("AI_SELECTION: model=FeatureMatch, score=%.3f, confidence=%.3f, features=%s, latency=%.1fms",
                                    ai_data.get("ai_score", 0), ai_data.get("ai_confidence", 0), 
                                    ai_data.get("matched_features", []), ai_data.get("processing_time_ms", 0))
                        elif "_popularity_metadata" in best_match:
                            pop_data = best_match["_popularity_metadata"]
                            model_used = "PopularityModel"
                            selection_metadata.update({
                                "model_used": model_used,
                                "popularity_score": pop_data.get("popularity_score", 0),
                                "processing_time_ms": pop_data.get("processing_time_ms", 0)
                            })
                            log.info("AI_SELECTION: model=Popularity, score=%.3f", pop_data.get("popularity_score", 0))
                        elif "_random_metadata" in best_match:
                            model_used = "RandomSelectionModel"
                            selection_metadata.update({
                                "model_used": model_used,
                                "processing_time_ms": best_match["_random_metadata"].get("processing_time_ms", 0)
                            })
                            log.info("AI_SELECTION: model=Random")
                        else:
                            selection_metadata["model_used"] = model_used
                            log.info("AI_SELECTION: model=UltimateFallback")
                        
                        # Log to performance monitor
                        log_ai_selection(
                            model_name=model_used,
                            user_query=watch_data["keywords"],
                            product_count=len(search_results),
                            selection_metadata=selection_metadata,
                            success=True
                        )
                        
                        product_price = best_match.get("price")
                        if product_price:
                            price_rs = product_price / 100 if product_price > 10000 else product_price
                            log.info("Selected ASIN %s for search: %s (Price: ₹%s, Model: %s)", 
                                    asin, watch_data["keywords"], int(price_rs), selection_metadata.get("model_used", "Unknown"))
                        else:
                            log.info("Selected ASIN %s for search: %s (Price: Unknown, Model: %s)", 
                                    asin, watch_data["keywords"], selection_metadata.get("model_used", "Unknown"))
                except Exception as search_error:
                    log.warning("Product search failed for '%s': %s", watch_data["keywords"], search_error)
                    # Continue without ASIN - watch will still be created for future searches

            # Create watch record (only if not already created in search logic above)
            if 'watch' not in locals():
                watch = Watch(
                    user_id=user.id,
                    asin=asin,
                    keywords=watch_data["keywords"],
                    brand=watch_data.get("brand"),
                    max_price=watch_data.get("max_price"),
                    min_discount=watch_data.get("min_discount"),
                    mode=watch_data.get("mode", "daily"),  # Use selected mode or default to daily
                )

                session.add(watch)
                session.commit()
                session.refresh(watch)
                log.info("Created watch %s for user %s", watch.id, user_id)

            # Schedule the watch for monitoring
            try:
                from .scheduler import schedule_watch

                schedule_watch(watch)
                log.info("Successfully scheduled watch %s", watch.id)
            except Exception as e:
                log.error("Failed to schedule watch %s: %s", watch.id, e)
                # Continue with finalization even if scheduling fails

    except Exception as e:
        log.error("Database error in finalize_watch for user %s: %s", user_id, e)
        error_msg = "❌ Failed to create watch due to database error. Please try again."
        if update.callback_query:
            await update.callback_query.edit_message_text(error_msg)
        else:
            await update.effective_message.reply_text(error_msg)
        return

    # Clean up internal tracking fields
    watch_data.pop("_brand_selected", None)
    watch_data.pop("_discount_selected", None)
    watch_data.pop("_price_selected", None)
    
    # Clear pending data AND session cached search results
    context.user_data.pop("pending_watch", None)
    context.user_data.pop("original_message_id", None)
    context.user_data.pop("search_results", None)  # Clear session cache to prevent memory leaks

    # Send single comprehensive message based on what we found
    try:
        if asin:
            # We found a specific product - try to get comprehensive product data
            try:
                log.info("Fetching product data for ASIN %s", asin)
                
                # Try to get complete product data from PA-API first
                title = watch_data["keywords"]
                image_url = "https://m.media-amazon.com/images/I/81.png"
                price = None
                
                try:
                    log.info("Trying enhanced PA-API for ASIN %s", asin)
                    item_data = await get_item_detailed(asin, priority="high")
                    title = item_data.get("title", watch_data["keywords"])
                    # Handle both image_url and images structure
                    if item_data.get("image_url"):
                        image_url = item_data["image_url"]
                    elif item_data.get("images", {}).get("large"):
                        image_url = item_data["images"]["large"]
                    else:
                        image_url = "https://m.media-amazon.com/images/I/81.png"
                    price = item_data.get("price")
                    log.info("Enhanced PA-API succeeded for ASIN %s", asin)
                except Exception as e:
                    log.warning("PA-API failed for ASIN %s: %s, trying scraper", asin, e)
                
                # If PA-API failed or didn't get complete data, try scraper
                if not title or title == watch_data["keywords"] or not price:
                    try:
                        log.info("Using scraper for comprehensive data for ASIN %s", asin)
                        from .scraper import scrape_product_data
                        scraped_data = await scrape_product_data(asin)
                        
                        # Use scraped data if we got better info
                        if scraped_data.get("title") and scraped_data["title"] != f"Product {asin}":
                            title = scraped_data["title"]
                        if scraped_data.get("image") and scraped_data["image"].startswith("http"):
                            # Validate image URL
                            image_url = scraped_data["image"]
                        if scraped_data.get("price"):
                            price = scraped_data["price"]
                        
                        log.info("Successfully scraped product data for ASIN %s: title=%s, price=%s", asin, title, price)
                    except Exception as scrape_error:
                        log.warning("Scraper also failed for ASIN %s: %s", asin, scrape_error)
                
                # If we still don't have price, try the cache service as last resort
                if not price:
                    try:
                        log.info("Trying async cache service for price only for ASIN %s", asin)
                        from .cache_service import get_price_async
                        price = await get_price_async(asin)
                        log.info("Cache service returned price for ASIN %s: %s", asin, price)
                    except Exception as cache_error:
                        log.warning("Cache service also failed for ASIN %s: %s", asin, cache_error)

                # Build success message
                def escape_markdown(text: str) -> str:
                    """Escape special characters for Telegram Markdown."""
                    special_chars = ['*', '_', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
                    for char in special_chars:
                        text = text.replace(char, f'\\{char}')
                    return text
                
                escaped_title = escape_markdown(title)
                success_msg = f"✅ **Watch created successfully!**\n\n📱 Product: {escaped_title}"
                if watch_data.get("brand"):
                    escaped_brand = escape_markdown(watch_data['brand'].title())
                    success_msg += f"\n🏷️ Brand: {escaped_brand}"
                if watch_data.get("max_price"):
                    success_msg += f"\n💰 Max price: ₹{watch_data['max_price']:,}"
                if watch_data.get("min_discount"):
                    success_msg += f"\n💸 Min discount: {watch_data['min_discount']}%"
                
                # Add mode-specific alert message
                mode = watch_data.get("mode", "daily")
                if mode == "rt":
                    success_msg += f"\n\n🔔 You'll get real-time alerts every 10 minutes when deals match your criteria!"
                else:
                    success_msg += f"\n\n🔔 You'll get daily alerts at 9 AM IST when deals match your criteria!"

                # Send confirmation message first
                if update.callback_query:
                    await update.callback_query.edit_message_text(success_msg, parse_mode="Markdown")
                else:
                    await update.effective_message.reply_text(success_msg, parse_mode="Markdown")

                # Send price card if we have price, otherwise send product card without price
                if price:
                    caption, keyboard = build_single_card(
                        title=title,
                        price=price,
                        image=image_url,
                        asin=asin,
                        watch_id=watch.id,
                    )
                else:
                    # Build card without price
                    caption = f"📱 {title}\n\n🔍 Monitoring for price updates..."
                    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("🛒 VIEW ON AMAZON", callback_data=f"click:{watch.id}:{asin}")]
                    ])

                try:
                    await update.effective_message.reply_photo(
                        photo=image_url,
                        caption=caption,
                        reply_markup=keyboard,
                        parse_mode="Markdown",
                    )
                    log.info("Successfully sent watch confirmation and product card to user %s (price: %s)", user_id, "available" if price else "unavailable")
                except Exception as photo_error:
                    log.warning("Failed to send photo, sending text message instead: %s", photo_error)
                    # Fallback to text message if photo fails
                    await update.effective_message.reply_text(
                        caption,
                        reply_markup=keyboard,
                        parse_mode="Markdown",
                    )
                    log.info("Successfully sent text fallback message to user %s", user_id)
                
            except Exception as price_error:
                log.error("Error fetching price for ASIN %s: %s", asin, price_error)
                # Send success message without price card
                success_msg = f"✅ **Watch created successfully!**\n\n📱 Product: {watch_data['keywords']}"
                if watch_data.get("brand"):
                    success_msg += f"\n🏷️ Brand: {watch_data['brand'].title()}"
                if watch_data.get("max_price"):
                    success_msg += f"\n💰 Max price: ₹{watch_data['max_price']:,}"
                if watch_data.get("min_discount"):
                    success_msg += f"\n💸 Min discount: {watch_data['min_discount']}%"
                
                # Add mode-specific alert message
                mode = watch_data.get("mode", "daily")
                if mode == "rt":
                    success_msg += f"\n\n🔔 You'll get real-time alerts every 10 minutes when deals match your criteria!"
                else:
                    success_msg += f"\n\n🔔 You'll get daily alerts at 9 AM IST when deals match your criteria!"
                success_msg += f"\n\n⚠️ Current price unavailable, but monitoring is active."

                if update.callback_query:
                    await update.callback_query.edit_message_text(success_msg, parse_mode="Markdown")
                else:
                    await update.effective_message.reply_text(success_msg, parse_mode="Markdown")
        else:
            # No specific product found - general watch created
            success_msg = f"✅ **Watch created successfully!**\n\n📱 Product: {watch_data['keywords']}"
            if watch_data.get("brand"):
                success_msg += f"\n🏷️ Brand: {watch_data['brand'].title()}"
            if watch_data.get("max_price"):
                success_msg += f"\n💰 Max price: ₹{watch_data['max_price']:,}"
            if watch_data.get("min_discount"):
                success_msg += f"\n💸 Min discount: {watch_data['min_discount']}%"
            
            # Add mode-specific alert message
            mode = watch_data.get("mode", "daily")
            if mode == "rt":
                success_msg += f"\n\n🔔 You'll get real-time alerts every 10 minutes when deals match your criteria!"
            else:
                success_msg += f"\n\n🔔 You'll get daily alerts at 9 AM IST when deals match your criteria!"
            success_msg += (
                f"\n\n💡 **Tip:** I'll search for products matching your description during scans. "
                f"For immediate results, try providing Amazon links or more specific product details."
            )

            if update.callback_query:
                await update.callback_query.edit_message_text(success_msg, parse_mode="Markdown")
            else:
                await update.effective_message.reply_text(success_msg, parse_mode="Markdown")
                
        log.info("Successfully created watch and sent confirmation to user %s", user_id)
        
    except Exception as e:
        log.error("Error in watch finalization messaging for user %s: %s", user_id, e)
        # Fallback message
        try:
            fallback_msg = "✅ Watch created successfully! You'll get daily alerts when deals match your criteria!"
            if update.callback_query:
                await update.callback_query.edit_message_text(fallback_msg, parse_mode="Markdown")
            else:
                await update.effective_message.reply_text(fallback_msg, parse_mode="Markdown")
        except Exception as fallback_error:
            log.error("Error sending fallback message: %s", fallback_error)
