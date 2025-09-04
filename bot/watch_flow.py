"""Watch creation flow handlers with Phase R3 AI integration."""

from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Optional, List, Dict, Any

from sqlmodel import Session, select
import telegram
from telegram import Update
from telegram.ext import ContextTypes

from .cache_service import engine, get_price, get_price_async
from .carousel import build_single_card, build_single_card_with_alternatives
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


async def _cached_search_items_advanced(keywords: str, item_count: int = 30, priority: str = "normal", min_price: Optional[int] = None, max_price: Optional[int] = None):
    """
    Cache wrapper around search_items_advanced to prevent duplicate API calls.

    Args:
        keywords: Search keywords
        item_count: Number of items to retrieve
        priority: Request priority
        min_price: Minimum price in paise
        max_price: Maximum price in paise

    Returns:
        List of search results or None if error
    """
    cache_key = f"{keywords}_{item_count}_{priority}"
    current_time = time.time()

    # Check cache first
    if cache_key in _search_cache:
        cached_data, cache_time = _search_cache[cache_key]
        if current_time - cache_time < _cache_ttl:
            log.debug("Cache hit for search: %s", keywords)
            return cached_data
        else:
            # Remove expired cache entry
            del _search_cache[cache_key]

    # Check if same search is already in progress
    if cache_key in _active_searches:
        log.debug("Search already in progress, waiting: %s", keywords)
        try:
            # Wait for the ongoing search with timeout
            await asyncio.wait_for(_active_searches[cache_key], timeout=30.0)
            # Check cache again after the wait
            if cache_key in _search_cache:
                cached_data, _ = _search_cache[cache_key]
                return cached_data
        except asyncio.TimeoutError:
            log.warning("Timeout waiting for ongoing search: %s", keywords)
        except Exception as e:
            log.warning("Error waiting for ongoing search: %s", e)
        finally:
            _active_searches.pop(cache_key, None)

    # Start new search
    search_future = asyncio.create_task(_perform_search(keywords, item_count, priority, min_price, max_price))
    _active_searches[cache_key] = search_future

    try:
        result = await search_future
        # Cache the result
        _search_cache[cache_key] = (result, current_time)
        return result
    except Exception as e:
        log.error("Search failed for '%s': %s", keywords, e)
        return None
    finally:
        _active_searches.pop(cache_key, None)


async def _perform_search(keywords: str, item_count: int, priority: str, min_price: Optional[int] = None, max_price: Optional[int] = None):
    """Perform the actual search operation."""
    return await search_items_advanced(
        keywords=keywords,
        item_count=item_count,
        priority=priority,
        min_price=min_price,
        max_price=max_price
        # enable_ai_analysis defaults to ENABLE_AI_ANALYSIS=True via factory
    )


def _filter_products_by_criteria(products: List[Dict], watch_data: dict) -> List[Dict]:
    """Filter products based on user criteria."""
    if not products:
        return []

    filtered = []
    max_price = watch_data.get("max_price")
    min_price = watch_data.get("min_price")
    min_discount = watch_data.get("min_discount")
    brand = watch_data.get("brand")

    for product in products:
        # Price filter (supports both min and max price ranges)
        product_price = product.get("price", 0)

        # Ensure price is numeric before comparison
        if product_price and isinstance(product_price, (int, float)):
            product_price_paise = product_price  # Assume already in paise

            # Check minimum price
            if min_price and product_price_paise < min_price:
                continue

            # Check maximum price
            if max_price and product_price_paise > max_price:
                continue
        elif max_price or min_price:
            # If we have price filters but product has no price, skip it
            continue

        # Brand filter
        if brand:
            product_title = product.get("title", "").lower()
            if brand.lower() not in product_title:
                continue

        # Discount filter
        if min_discount:
            product_discount = product.get("discount", 0)
            if product_discount < min_discount:
                continue

        filtered.append(product)

    return filtered


def _extract_asin_from_url(url: str) -> Optional[str]:
    """Extract ASIN from Amazon URL."""
    asin_patterns = [
        r"/dp/([A-Z0-9]{10})",
        r"/gp/product/([A-Z0-9]{10})",
        r"asin=([A-Z0-9]{10})",
        r"/([A-Z0-9]{10})(?:/|$|\?)",
    ]
    
    for pattern in asin_patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None


def _extract_budget_from_query(query: str) -> Optional[int]:
    """Extract budget/price limit from user query."""
    price_patterns = [
        r"under\s+₹?(\d+(?:,\d+)*(?:k|000)?)",
        r"below\s+₹?(\d+(?:,\d+)*(?:k|000)?)",
        r"less\s+than\s+₹?(\d+(?:,\d+)*(?:k|000)?)",
        r"within\s+₹?(\d+(?:,\d+)*(?:k|000)?)",
        r"budget\s+₹?(\d+(?:,\d+)*(?:k|000)?)",
        r"₹(\d+(?:,\d+)*(?:k|000)?)",
        r"(\d+(?:,\d+)*(?:k|000)?)\s*rs",
        r"(\d+(?:,\d+)*(?:k|000)?)\s*rupees",
    ]
    
    for pattern in price_patterns:
        matches = re.finditer(pattern, query.lower())
        for match in matches:
            price_str = match.group(1)
            
            # Remove commas
            price_str = price_str.replace(",", "")
            
            # Handle 'k' suffix
            if price_str.endswith("k"):
                try:
                    return int(price_str[:-1]) * 1000
                except ValueError:
                    continue
            elif price_str.endswith("000"):
                try:
                    return int(price_str)
                except ValueError:
                    continue
            else:
                try:
                    price = int(price_str)
                    # If it's a reasonable price (not just years or other numbers)
                    if 100 <= price <= 10000000:
                        return price
                except ValueError:
                    continue

    return None


async def start_watch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /watch command to start watch creation flow."""
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
    # Field priority order: discount, price, brand, mode (as expected by tests)
    missing_fields = []
    
    # Check if discount is missing (not set explicitly and no value in parsed data)
    if not parsed_data.get("_discount_selected", False) and "min_discount" not in parsed_data:
        missing_fields.append("discount")
    
    # Check if price is missing (not set explicitly and no value in parsed data)
    if not parsed_data.get("_price_selected", False) and "max_price" not in parsed_data:
        missing_fields.append("price")
    
    # Check if brand is missing (not set explicitly and no value in parsed data)
    if not parsed_data.get("_brand_selected", False) and "brand" not in parsed_data:
        missing_fields.append("brand")
    
    # Set default mode if not specified (mode is optional, defaults to "daily")
    if not parsed_data.get("mode"):
        parsed_data["mode"] = "daily"

    # If nothing is missing, finalize the watch
    if not missing_fields:
        await _finalize_watch(update, context, parsed_data)
    else:
        # Ask for the first missing field
        await _ask_for_missing_field(update, context, missing_fields[0])


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button callbacks for watch creation."""
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
        # Invalid callback data
        await query.edit_message_text("❌ Unknown option selected.")
        return

    # Update user data
    context.user_data["pending_watch"] = parsed_data

    # Check what's still missing (same priority order as start_watch)
    missing_fields = []
    
    # Check if discount is missing (not set explicitly and no value in parsed data)
    if not parsed_data.get("_discount_selected", False) and "min_discount" not in parsed_data:
        missing_fields.append("discount")
    
    # Check if price is missing (not set explicitly and no value in parsed data)
    if not parsed_data.get("_price_selected", False) and "max_price" not in parsed_data:
        missing_fields.append("price")
    
    # Check if brand is missing (not set explicitly and no value in parsed data)
    if not parsed_data.get("_brand_selected", False) and "brand" not in parsed_data:
        missing_fields.append("brand")
    
    # Set default mode if not specified (mode is optional, defaults to "daily")
    if not parsed_data.get("mode"):
        parsed_data["mode"] = "daily"

    if missing_fields:
        # Ask for next missing field
        await _ask_for_missing_field(update, context, missing_fields[0], edit=True)
    else:
        # All fields collected, finalize the watch
        await _finalize_watch(update, context, parsed_data)


async def _ask_for_missing_field(
    update: Update, context: ContextTypes.DEFAULT_TYPE, field: str, edit: bool = False
) -> None:
    """Ask user for a missing field with appropriate UI."""
    parsed_data = context.user_data.get("pending_watch", {})
    
    if field == "brand":
        message = (
            "🏷️ *Select Brand Preference*\n\n"
            "Choose a specific brand or skip for any brand:"
        )
        keyboard = build_brand_buttons(COMMON_BRANDS)
        
    elif field == "discount":
        message = (
            "💸 *Minimum Discount Required*\n\n"
            "What's the minimum discount you want?"
        )
        keyboard = build_discount_buttons()
        
    elif field == "price":
        message = (
            "💰 *Maximum Price*\n\n"
            "What's your budget for this product?"
        )
        
        # Try to suggest price based on query
        suggested_price = _extract_budget_from_query(parsed_data.get("keywords", ""))
        keyboard = build_price_buttons(suggested_price)
        
    elif field == "mode":
        message = (
            "⏰ *Monitoring Frequency*\n\n"
            "How often should I check for deals?"
        )
        keyboard = build_mode_buttons()
    
    else:
        log.error("Unknown field requested: %s", field)
        return

    try:
        if edit and update.callback_query:
            await update.callback_query.edit_message_text(
                message,
                reply_markup=keyboard,
                parse_mode="Markdown",
            )
        else:
            await update.effective_message.reply_text(
                message,
                reply_markup=keyboard,
                parse_mode="Markdown",
            )
    except Exception as e:
        log.error("Error sending field request for %s: %s", field, e)
        # Fallback to finalization if UI fails
        await _finalize_watch(update, context, parsed_data)


def _is_technical_query(query: str) -> bool:
    """
    Enhanced technical query detection for multi-card eligibility.

    Uses the global has_technical_features function with additional checks
    to determine if a query warrants AI-powered multi-card selection.
    """
    if not query or not query.strip():
        return False

    # Import the global technical detection function
    from .product_selection_models import has_technical_features

    # Use the global function as primary check
    if has_technical_features(query):
        return True

    # Additional fallback checks for common technical patterns
    query_lower = query.lower()

    # Check for product categories that benefit from AI analysis
    tech_categories = ["monitor", "laptop", "gaming", "computer", "phone", "display"]
    if any(category in query_lower for category in tech_categories):
        log.debug(f"Technical category detected in query: {query}")
        return True

    # Check for specific technical specifications
    tech_specs = ["inch", "hz", "fps", "gb", "ssd", "hdd", "ram"]
    spec_count = sum(1 for spec in tech_specs if spec in query_lower)

    if spec_count >= 1:
        log.debug(f"Technical specifications detected ({spec_count}) in query: {query}")
        return True

    return False


async def _finalize_watch(
    update: Update, context: ContextTypes.DEFAULT_TYPE, watch_data: dict
) -> None:
    """Enhanced watch finalization with AI integration (Phase R3)."""
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

            asin = watch_data.get("asin")
            
            # Try to find ASIN if not provided
            if not asin:
                try:
                    # Check if PA-API is in cooldown
                    if is_in_cooldown():
                        log.warning("PA-API in cooldown, skipping product search")
                    else:
                        # STEP 1: Use cached search first, then AI enhancement
                        # Use existing cached search to prevent duplicate API calls
                        log.info(f"Searching for: '{watch_data['keywords']}'")
                        search_results = await _cached_search_items_advanced(
                            keywords=watch_data["keywords"],
                            item_count=30,  # Get more products for better AI selection
                            priority="normal",
                            min_price=watch_data.get("min_price"),
                            max_price=watch_data.get("max_price")
                        )
                        
                        if search_results:
                            log.info(f"CACHED_SEARCH: Found {len(search_results)} products for '{watch_data['keywords']}'")
                            
                            # Apply AI enhancement to existing search results if enabled
                            try:
                                from .paapi_ai_bridge import is_ai_analysis_enabled
                                if is_ai_analysis_enabled():
                                    # Transform existing results to AI format without additional API calls
                                    from .paapi_ai_bridge import transform_paapi_to_ai_format, create_mock_paapi_item_from_result
                                    
                                    ai_enhanced_results = []
                                    for result in search_results[:10]:  # Process top 10 products for AI enhancement
                                        try:
                                            mock_item = create_mock_paapi_item_from_result(result)
                                            ai_product = await transform_paapi_to_ai_format(mock_item)
                                            ai_enhanced_results.append(ai_product)
                                        except Exception as e:
                                            log.warning(f"AI enhancement failed for {result.get('asin', 'unknown')}: {e}")
                                            ai_enhanced_results.append(result)  # Use original
                                    
                                    # Use AI-enhanced results if successful
                                    if ai_enhanced_results:
                                        search_results = ai_enhanced_results
                                        log.info(f"AI_ENHANCED: Processed {len(ai_enhanced_results)} products")
                            except Exception as e:
                                log.warning(f"AI enhancement failed, using original results: {e}")
                                # Continue with original search_results
                        else:
                            log.warning("No search results found for query")
                            search_results = []
                        
                        if search_results:
                            # STEP 2: Apply existing filters
                            filtered_products = _filter_products_by_criteria(search_results, watch_data)
                            
                            if not filtered_products:
                                # Send no products message with price range information
                                min_price = watch_data.get("min_price")
                                max_price = watch_data.get("max_price")
                                brand = watch_data.get("brand")

                                if min_price and max_price:
                                    price_msg = f"between ₹{min_price:,} and ₹{max_price:,}"
                                elif max_price:
                                    price_msg = f"within ₹{max_price:,}"
                                elif min_price:
                                    price_msg = f"above ₹{min_price:,}"
                                else:
                                    price_msg = None

                                if price_msg:
                                    message = f"❌ No products found {price_msg}"
                                    if brand:
                                        message += f" from {brand.title()}"
                                    message += f".\n\n💡 *Try:*\n• Adjusting your price range\n"
                                else:
                                    message = f"❌ No products found matching your criteria"
                                    if brand:
                                        message += f" from {brand.title()}"
                                    message += f".\n\n💡 *Try:*\n• Adjusting your requirements\n"

                                message += "• Using different keywords\n• Checking back later for new products"

                                await update.effective_chat.send_message(
                                    text=message,
                                    parse_mode="Markdown"
                                )
                                return
                            
                            # STEP 3: Use intelligent product selection with AI integration (R7: with rollout)
                            from .feature_rollout import is_ai_feature_enabled
                            
                            # R7: Check if multi-card experience is enabled for this user
                            enable_multi_card = is_ai_feature_enabled(
                                "ai_multi_card_experience",
                                user_id,
                                has_technical_features=True,
                                product_count=len(filtered_products),
                                multi_card_available=True
                            )
                            
                            selected_result = await smart_product_selection_with_ai(
                                products=filtered_products,
                                user_query=watch_data["keywords"],
                                user_preferences=watch_data,
                                enable_multi_card=enable_multi_card,
                                user_id=user_id  # R7: Pass user_id for rollout decisions
                            )
                            
                            # STEP 4: Handle single vs multi-card results
                            if selected_result and selected_result.get("selection_type") == "multi_card":
                                await send_multi_card_experience(update, context, selected_result, watch_data)
                                return
                            else:
                                await send_single_card_experience(update, context, selected_result, watch_data)
                                return
                                
                except Exception as e:
                    log.error(f"Search error: {e}")
                    # Continue with empty search results instead of infinite fallback
                    search_results = []

            # If we have an ASIN (from URL or found via search), create the watch directly
            watch = Watch(
                user_id=user.id,
                asin=asin,
                keywords=watch_data["keywords"],
                brand=watch_data.get("brand"),
                max_price=watch_data.get("max_price"),
                min_discount=watch_data.get("min_discount"),
                mode=watch_data.get("mode", "daily"),
            )

            session.add(watch)
            session.commit()
            session.refresh(watch)
            
            log.info("Created watch %d for user %s", watch.id, user_id)

    except Exception as e:
        log.error("Database error in finalize_watch for user %s: %s", user_id, e)
        error_msg = "❌ Failed to create watch due to database error. Please try again."
        if update.callback_query:
            await update.callback_query.edit_message_text(error_msg)
        else:
            await update.effective_message.reply_text(error_msg)
        return

    # Clean up user data
    context.user_data.pop("pending_watch", None)
    context.user_data.pop("original_message_id", None)

    # Send success message
    try:
        success_msg = "✅ **Watch created successfully!** You'll get alerts when deals match your criteria!"
        if update.callback_query:
            await update.callback_query.edit_message_text(success_msg, parse_mode="Markdown")
        else:
            await update.effective_message.reply_text(success_msg, parse_mode="Markdown")
    except Exception as fallback_error:
        log.error("Error sending success message: %s", fallback_error)


# ============================================================================
# Phase R3: Enhanced Watch Flow Integration Functions
# ============================================================================

async def smart_product_selection_with_ai(
    products: List[Dict], 
    user_query: str, 
    user_preferences: Dict,
    enable_multi_card: bool = True,
    user_id: str = "7332386643"  # R7: Default to dev user for development testing
) -> Dict[str, Any]:
    """Enhanced product selection that supports both single and multi-card experiences."""
    from .ai.feature_extractor import FeatureExtractor
    from .product_selection_models import smart_product_selection
    
    log.info(f"smart_product_selection_with_ai: {len(products)} products, query='{user_query}'")
    
    try:
        # Extract user features for AI analysis
        extractor = FeatureExtractor()
        user_features = extractor.extract_features(user_query)
        
        # R7: Check if enhanced features are enabled before multi-card experience
        from .feature_rollout import is_ai_feature_enabled
        
        enhanced_carousel_enabled = is_ai_feature_enabled(
            "ai_enhanced_carousel",
            user_id,
            multi_card_enabled=enable_multi_card,
            product_count=len(products),
            has_technical_features=bool(user_features)
        )
        
        # Check if we should use multi-card experience (Phase 6)
        # Enhanced: More permissive conditions for multi-card selection
        has_features_or_tech_query = user_features or _is_technical_query(user_query)

        if enable_multi_card and len(products) >= 3 and has_features_or_tech_query and enhanced_carousel_enabled:
            from .ai.enhanced_product_selection import EnhancedFeatureMatchModel

            log.info(f"🎯 ATTEMPTING_MULTI_CARD: enabled={enable_multi_card}, products={len(products)} (>=3), tech_query={has_features_or_tech_query}, carousel={enhanced_carousel_enabled}")
            enhanced_model = EnhancedFeatureMatchModel()
            result = await enhanced_model.select_products(
                products=products,
                user_query=user_query,
                user_preferences=user_preferences,
                enable_multi_card=True
            )

            selection_type = result.get('selection_type', 'unknown')
            product_count = len(result.get('products', []))
            log.info(f"✅ MULTI_CARD_RESULT: type={selection_type}, products={product_count}")
            if selection_type == 'multi_card':
                log.info(f"   🎉 SUCCESS: Multi-card experience selected with {product_count} products")
            else:
                log.info(f"   ⚠️ FALLBACK: Single card selected instead")

            # DEBUG: Check multi-card result before returning
            if result.get('products'):
                log.info(f"DEBUG: smart_product_selection_with_ai returning multi_card with {len(result['products'])} products")
                first_prod = result['products'][0]
                log.info(f"DEBUG: First product type: {type(first_prod)}")
                log.info(f"DEBUG: First product keys: {list(first_prod.keys()) if isinstance(first_prod, dict) else 'Not a dict'}")

            return result

        else:
            # Use single-card selection (existing logic) with R7 rollout management
            log.info(f"Using single-card selection (enhanced_carousel={enhanced_carousel_enabled})")

            # R7: Pass user_id for rollout decisions in smart_product_selection
            user_preferences_with_id = dict(user_preferences)
            user_preferences_with_id["user_id"] = user_id

            selected_product = await smart_product_selection(products, user_query, **user_preferences_with_id)

            single_result = {
                "selection_type": "single_card",
                "products": [selected_product] if selected_product else [],
                "presentation_mode": "single",
                "ai_message": "🎯 AI found your best match!" if selected_product and selected_product.get("_ai_metadata") else "⭐ Popular choice selected",
                "metadata": selected_product.get("_ai_metadata", {}) if selected_product else {}
            }

            # DEBUG: Check single card result
            log.info(f"DEBUG: smart_product_selection_with_ai returning single_card with {len(single_result.get('products', []))} products")

            return single_result
            
    except Exception as e:
        log.error(f"smart_product_selection_with_ai failed: {e}")
        # Fallback to basic selection
        if products:
            return {
                "selection_type": "single_card",
                "products": [products[0]],
                "presentation_mode": "single",
                "ai_message": "📦 Product selected",
                "metadata": {"fallback": True, "error": str(e)}
            }
        else:
            return {
                "selection_type": "none",
                "products": [],
                "presentation_mode": "none",
                "ai_message": "❌ No products found",
                "metadata": {"error": str(e)}
            }


async def send_multi_card_experience(
    update: Update, 
    context: ContextTypes.DEFAULT_TYPE, 
    selection_result: Dict, 
    watch_data: Dict
) -> None:
    """Send multi-card carousel experience to user."""
    from .ai.enhanced_carousel import build_product_carousel
    from .models import User, Watch
    from sqlmodel import Session, select
    
    try:
        # DEBUG: Check selection_result structure
        log.info(f"DEBUG: send_multi_card_experience - selection_result keys: {list(selection_result.keys()) if isinstance(selection_result, dict) else 'Not a dict'}")
        log.info(f"DEBUG: send_multi_card_experience - selection_result type: {type(selection_result)}")

        products = selection_result.get("products", [])
        comparison_table = selection_result.get("comparison_table", {})
        selection_reason = selection_result.get("selection_reason", "AI found multiple great options")

        # DEBUG: Check what send_multi_card_experience received
        log.info(f"DEBUG: send_multi_card_experience received {len(products)} products")
        if products:
            log.info(f"DEBUG: send_multi_card_experience first product type: {type(products[0])}")
            if isinstance(products[0], dict):
                log.info(f"DEBUG: send_multi_card_experience first product keys: {list(products[0].keys())}")
                log.info(f"DEBUG: send_multi_card_experience first product asin: {products[0].get('asin', 'No asin')}")
            elif isinstance(products[0], list):
                log.info(f"DEBUG: send_multi_card_experience first product is a LIST with {len(products[0])} items")
                log.info(f"DEBUG: send_multi_card_experience first item of list: {products[0][0] if products[0] else 'Empty list'}")
            else:
                log.info(f"DEBUG: send_multi_card_experience first product is neither dict nor list: {type(products[0])}")

        if not products:
            log.warning("No products for multi-card experience, falling back to single card")
            await send_single_card_experience(update, context, selection_result, watch_data)
            return

        # FIX: Handle corrupted data structure - check ALL products, not just the first one
        if products:
            corrupted_items = [i for i, product in enumerate(products) if isinstance(product, list)]
            if corrupted_items:
                log.error(f"CRITICAL: Products data structure corrupted - found {len(corrupted_items)} list items in products: {corrupted_items}")
                log.error(f"Raw products data: {products}")
                # Emergency fallback to single card
                await send_single_card_experience(update, context, selection_result, watch_data)
                return

        # DEBUG: Check products again before accessing
        log.info(f"DEBUG: About to access products[0] - products length: {len(products)}")
        if products:
            log.info(f"DEBUG: products[0] type before access: {type(products[0])}")
            log.info(f"DEBUG: products[0] content before access: {products[0]}")

        # Create watch record for the first (best) product
        user_id = update.effective_user.id
        best_product = products[0]
        asin = best_product.get("asin")
        
        with Session(engine) as session:
            # Get user
            user_statement = select(User).where(User.tg_user_id == user_id)
            user = session.exec(user_statement).first()
            
            if not user:
                user = User(tg_user_id=user_id)
                session.add(user)
                session.commit()
                session.refresh(user)
            
            # Create watch for best product
            watch = Watch(
                user_id=user.id,
                asin=asin,
                keywords=watch_data["keywords"],
                brand=watch_data.get("brand"),
                max_price=watch_data.get("max_price"),
                min_discount=watch_data.get("min_discount"),
                mode=watch_data.get("mode", "daily"),
            )
            
            session.add(watch)
            session.commit()
            session.refresh(watch)
            
            log.info("Created watch %d for multi-card experience", watch.id)
        
        # Build carousel cards
        carousel_cards = build_product_carousel(
            products=products,
            comparison_table=comparison_table,
            selection_reason=selection_reason,
            watch_id=watch.id
        )
        
        # Send AI introduction message
        ai_message = selection_result.get("ai_message", "🤖 AI found multiple great options!")
        await update.effective_chat.send_message(
            text=ai_message,
            parse_mode="Markdown"
        )
        
        # CRITICAL DEBUG: Check carousel_cards structure right before loop
        log.info(f"DEBUG: About to iterate carousel_cards - length: {len(carousel_cards)}")
        for i, card in enumerate(carousel_cards):
            log.info(f"DEBUG: Processing card {i} - type: {type(card)}")
            if not isinstance(card, dict):
                log.error(f"CRITICAL: Card {i} is not a dict: type={type(card)}, content={card}")
                continue  # Skip corrupted cards
                
        # Send product cards
        for i, card in enumerate(carousel_cards):
            try:
                # CRITICAL FIX: Validate card structure before accessing
                if not isinstance(card, dict):
                    log.error(f"CRITICAL: Skipping corrupted card {i}: type={type(card)}")
                    continue
                    
                if card.get("type") == "product_card":
                    image_url = card.get("image", "")
                    log.info(f"Sending card {i+1}: image_url={image_url[:100]}...")

                    if image_url and image_url.startswith("http"):
                        await update.effective_chat.send_photo(
                            photo=image_url,
                            caption=card["caption"],
                            reply_markup=card.get("keyboard"),
                            parse_mode="Markdown"
                        )
                    else:
                        log.warning(f"No valid image URL for card {i+1}, sending text only")
                        await update.effective_chat.send_message(
                            text=card["caption"],
                            reply_markup=card.get("keyboard"),
                            parse_mode="Markdown"
                        )
                elif card.get("type") == "summary_card":
                    await update.effective_chat.send_message(
                        text=card["caption"],
                        parse_mode="Markdown"
                    )
            except Exception as card_error:
                log.error(f"Failed to send card {i+1}: {card_error}")
                # Try to send text-only version
                try:
                    await update.effective_chat.send_message(
                        text=f"Card {i+1} (image failed to load):\n\n{card['caption']}",
                        reply_markup=card.get("keyboard"),
                        parse_mode="Markdown"
                    )
                except Exception as fallback_error:
                    log.error(f"Fallback also failed: {fallback_error}")
                    continue
        
        # Log multi-card experience
        from .ai_performance_monitor import log_ai_selection
        log_ai_selection(
            model_name="EnhancedFeatureMatchModel",
            user_query=watch_data["keywords"],
            product_count=len(products),
            selection_metadata={
                "presentation_mode": selection_result.get("presentation_mode"),
                "card_count": len(products),
                **selection_result.get("metadata", {})
            }
        )
        
        log.info(f"Sent multi-card experience with {len(products)} products")
        
    except Exception as e:
        log.error(f"send_multi_card_experience failed: {e}")
        # Fallback to single card
        await send_single_card_experience(update, context, selection_result, watch_data)


async def send_search_refinement_options(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    watch_data: Dict
) -> None:
    """Send search refinement options to help users narrow down their search."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    # Extract current search criteria
    keywords = watch_data.get("keywords", "")
    max_price = watch_data.get("max_price")
    min_discount = watch_data.get("min_discount")

    # Create refinement options based on the original query
    refinement_message = """🔧 **Not quite what you're looking for?**

Try refining your search with these quick options:"""

    keyboard_buttons = []

    # Brand-specific refinements
    if "monitor" in keywords.lower():
        keyboard_buttons.append([
            InlineKeyboardButton("🏢 Dell Monitors", callback_data=f"refine_brand:dell:{max_price}"),
            InlineKeyboardButton("🏢 LG Monitors", callback_data=f"refine_brand:lg:{max_price}"),
            InlineKeyboardButton("🏢 Samsung Monitors", callback_data=f"refine_brand:samsung:{max_price}")
        ])

    # Size refinements for monitors
    if "monitor" in keywords.lower():
        keyboard_buttons.append([
            InlineKeyboardButton("📺 24″ Monitors", callback_data=f"refine_size:24:{max_price}"),
            InlineKeyboardButton("📺 27″ Monitors", callback_data=f"refine_size:27:{max_price}"),
            InlineKeyboardButton("📺 32″ Monitors", callback_data=f"refine_size:32:{max_price}")
        ])

    # Feature refinements
    if "monitor" in keywords.lower():
        keyboard_buttons.append([
            InlineKeyboardButton("🎨 IPS Panel", callback_data=f"refine_panel:ips:{max_price}"),
            InlineKeyboardButton("⚡ 144Hz+", callback_data=f"refine_refresh:144:{max_price}"),
            InlineKeyboardButton("🔍 4K Resolution", callback_data=f"refine_resolution:4k:{max_price}")
        ])

    # Price refinements
    if max_price:
        lower_price = int(max_price * 0.8)  # 20% lower
        higher_price = int(max_price * 1.2)  # 20% higher
        keyboard_buttons.append([
            InlineKeyboardButton(f"💰 Under ₹{lower_price:,}", callback_data=f"refine_price:{lower_price}:{max_price}"),
            InlineKeyboardButton(f"💰 Under ₹{higher_price:,}", callback_data=f"refine_price:{higher_price}:{max_price}")
        ])

    # Add a cancel option
    keyboard_buttons.append([
        InlineKeyboardButton("❌ Keep Current Watch", callback_data="refine_cancel")
    ])

    keyboard = InlineKeyboardMarkup(keyboard_buttons)

    try:
        await update.effective_chat.send_message(
            text=refinement_message,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    except Exception as e:
        log.error("Failed to send refinement options: %s", e)


async def send_single_card_experience(
    update: Update, 
    context: ContextTypes.DEFAULT_TYPE, 
    selection_result: Dict, 
    watch_data: Dict
) -> None:
    """Send single-card experience to user."""
    from .models import User, Watch
    from sqlmodel import Session, select
    
    try:
        products = selection_result.get("products", [])
        if not products:
            log.error("No products for single card experience")
            await update.effective_chat.send_message(
                text="❌ Sorry, couldn't find any suitable products. Please try adjusting your search criteria.",
                parse_mode="Markdown"
            )
            return
        
        selected_product = products[0]
        asin = selected_product.get("asin")
        
        # Create watch record
        user_id = update.effective_user.id
        
        with Session(engine) as session:
            # Get user
            user_statement = select(User).where(User.tg_user_id == user_id)
            user = session.exec(user_statement).first()
            
            if not user:
                user = User(tg_user_id=user_id)
                session.add(user)
                session.commit()
                session.refresh(user)
            
            # Create watch
            watch = Watch(
                user_id=user.id,
                asin=asin,
                keywords=watch_data["keywords"],
                brand=watch_data.get("brand"),
                max_price=watch_data.get("max_price"),
                min_discount=watch_data.get("min_discount"),
                mode=watch_data.get("mode", "daily"),
            )
            
            session.add(watch)
            session.commit()
            session.refresh(watch)
            
            log.info("Created watch %d for single-card experience", watch.id)
        
        # Get current price and build card
        try:
            current_price = await get_price_async(asin)
        except Exception as price_error:
            log.warning(f"Failed to get current price for {asin}: {price_error}")
            # Get price from product data, default to 0 if not available
            fallback_price = selected_product.get("price", 0)
            current_price = fallback_price if isinstance(fallback_price, (int, float)) else 0
        
        # Build single card with alternatives option
        # Ensure current_price is an integer for build_single_card
        price_for_card = current_price if isinstance(current_price, (int, float)) else 0
        caption, keyboard = build_single_card_with_alternatives(
            title=selected_product.get("title", "Product"),
            price=int(price_for_card),
            image=selected_product.get("image", ""),
            asin=asin,
            watch_id=watch.id,
            alternatives_count=min(3, len(products) - 1)  # Up to 3 alternatives
        )
        
        # Send AI message based on selection type
        ai_message = selection_result.get("ai_message", "📦 Watch created successfully!")
        ai_metadata = selection_result.get("metadata", {})
        
        if ai_metadata.get("ai_selection"):
            # Use the score for display confidence (more meaningful for users)
            display_confidence = ai_metadata.get("ai_score", 0)
            rationale = ai_metadata.get("ai_rationale", "")
            ai_message = f"""🎯 **Smart Match Found!**

I analyzed your requirements and found this product that best matches your needs.

🤖 **AI Confidence**: {display_confidence:.0%}
💡 **Why this product**: {rationale}

✅ **Watch created successfully!** You'll get alerts when the price drops or deals become available."""
        else:
            ai_message = f"""⭐ **Popular Choice Selected**

Selected based on customer ratings and popularity.

✅ **Watch created successfully!** You'll get alerts when the price drops or deals become available."""
        
        # Send the message and card
        await update.effective_chat.send_message(
            text=ai_message,
            parse_mode="Markdown"
        )

        # Only send photo if we have a valid image URL
        image_url = selected_product.get("image", "")
        if image_url and image_url.strip():
            await update.effective_chat.send_photo(
                photo=image_url,
                caption=caption,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        else:
            # Fallback: send as text message with keyboard if no image
            await update.effective_chat.send_message(
                text=caption,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )

        # Send refinement options
        await send_search_refinement_options(update, context, watch_data)
        
        # Log single-card experience
        from .ai_performance_monitor import log_ai_selection
        model_name = ai_metadata.get("model_name", "EnhancedFeatureMatchModel")
        log_ai_selection(
            model_name=model_name,
            user_query=watch_data["keywords"],
            product_count=1,
            selection_metadata={
                "presentation_mode": "single",
                **ai_metadata
            }
        )
        
        log.info(f"Sent single-card experience with {model_name}")
        
    except Exception as e:
        log.error(f"send_single_card_experience failed: {e}")
        # Final fallback message
        try:
            await update.effective_chat.send_message(
                text="✅ Watch created successfully! You'll get daily alerts when deals match your criteria!",
                parse_mode="Markdown"
            )
        except Exception as fallback_error:
            log.error(f"Final fallback message failed: {fallback_error}")


async def _finalize_watch_fallback(
    update: Update, context: ContextTypes.DEFAULT_TYPE, watch_data: dict
) -> None:
    """Fallback function when AI integration fails."""
    from .product_selection_models import smart_product_selection
    from .models import User, Watch
    from sqlmodel import Session, select
    
    log.info("Using fallback watch creation logic")
    
    user_id = update.effective_user.id
    
    try:
        with Session(engine) as session:
            # Ensure user exists
            user_statement = select(User).where(User.tg_user_id == user_id)
            user = session.exec(user_statement).first()
            
            if not user:
                user = User(tg_user_id=user_id)
                session.add(user)
                session.commit()
                session.refresh(user)
            
            # Simple product search using existing logic
            if not watch_data.get("asin"):
                try:
                    search_results = await _cached_search_items_advanced(
                        keywords=watch_data["keywords"],
                        item_count=10,
                        min_price=watch_data.get("min_price"),
                        max_price=watch_data.get("max_price")
                    )
                    
                    if search_results:
                        # Use simple selection
                        best_match = await smart_product_selection(
                            products=search_results,
                            user_query=watch_data["keywords"],
                            user_preferences=watch_data
                        )
                        
                        if best_match:
                            watch_data["asin"] = best_match.get("asin")
                        else:
                            watch_data["asin"] = search_results[0].get("asin")
                    
                except Exception as search_error:
                    log.error(f"Fallback search failed: {search_error}")
            
            # Create watch
            watch = Watch(
                user_id=user.id,
                asin=watch_data.get("asin"),
                keywords=watch_data["keywords"],
                brand=watch_data.get("brand"),
                max_price=watch_data.get("max_price"),
                min_discount=watch_data.get("min_discount"),
                mode=watch_data.get("mode", "daily"),
            )
            
            session.add(watch)
            session.commit()
            session.refresh(watch)
            
            log.info("Created fallback watch %d", watch.id)
            
            # Send simple success message
            await update.effective_chat.send_message(
                text="✅ Watch created successfully! You'll get daily alerts when deals match your criteria!",
                parse_mode="Markdown"
            )
            
    except Exception as e:
        log.error(f"Fallback watch creation failed: {e}")
        await update.effective_chat.send_message(
            text="❌ Sorry, there was an error creating your watch. Please try again later.",
            parse_mode="Markdown"
        )
