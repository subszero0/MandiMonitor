"""Watch creation flow handlers."""

from __future__ import annotations

import logging

from sqlmodel import Session, select
from telegram import Update
from telegram.ext import ContextTypes

from .cache_service import engine, get_price
from .carousel import build_single_card
from .models import User, Watch
from .paapi_wrapper import get_item, search_products
from .ui_helpers import build_brand_buttons, build_discount_buttons, build_price_buttons
from .watch_parser import parse_watch, validate_watch_data

log = logging.getLogger(__name__)

# Common brand list for buttons
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

    # For specific product names, don't ask for additional fields - just create the watch
    # Only ask for missing info if the input is too vague
    keywords_word_count = len(parsed_data["keywords"].split())
    is_specific_enough = keywords_word_count >= 3 or parsed_data.get("brand") is not None
    
    if is_specific_enough:
        # Input is detailed enough - create watch directly
        await _finalize_watch(update, context, parsed_data)
        return
    
    # Input is too vague - ask for more details
    missing_fields = []
    if parsed_data.get("brand") is None:
        missing_fields.append("brand")
    if parsed_data.get("min_discount") is None:
        missing_fields.append("discount")
    if parsed_data.get("max_price") is None:
        missing_fields.append("price")

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
        parsed_data["brand"] = brand
        log.info("User %s selected brand: %s", update.effective_user.id, brand)

    elif query.data.startswith("disc:"):
        discount_value = query.data.split(":", 1)[1]
        if discount_value == "skip":
            parsed_data["min_discount"] = None
        else:
            parsed_data["min_discount"] = int(discount_value)
        log.info(
            "User %s selected discount: %s", update.effective_user.id, discount_value
        )

    elif query.data.startswith("price:"):
        price_value = query.data.split(":", 1)[1]
        if price_value == "skip":
            parsed_data["max_price"] = None
        else:
            parsed_data["max_price"] = int(price_value)
        log.info("User %s selected price: %s", update.effective_user.id, price_value)

    else:
        await query.edit_message_text("❌ Unknown option selected.")
        return

    # Update stored data
    context.user_data["pending_watch"] = parsed_data

    # Check what's still missing (only ask if field is None)
    missing_fields = []
    if parsed_data.get("brand") is None:
        missing_fields.append("brand")
    if parsed_data.get("min_discount") is None:
        missing_fields.append("discount")
    if parsed_data.get("max_price") is None:
        missing_fields.append("price")

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
    if field == "brand":
        text = "🏷️ *Choose a brand:*\n\nSelect the brand you're looking for:"
        keyboard = build_brand_buttons(COMMON_BRANDS)

    elif field == "discount":
        text = "💸 *Minimum discount:*\n\nWhat's the minimum discount you want to be notified about?"
        keyboard = build_discount_buttons()

    elif field == "price":
        text = "💰 *Maximum price:*\n\nWhat's your budget for this product?"
        keyboard = build_price_buttons()

    else:
        log.error("Unknown field requested: %s", field)
        return

    # Send or edit message
    if edit and update.callback_query:
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="Markdown",
        )
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
                    search_results = await search_products(watch_data["keywords"], max_results=3)
                    if search_results:
                        # Filter results based on brand if specified
                        if watch_data.get("brand"):
                            brand_filtered = [
                                product for product in search_results 
                                if watch_data["brand"].lower() in product["title"].lower()
                            ]
                            if brand_filtered:
                                search_results = brand_filtered
                        
                        # Use the first result as the best match
                        best_match = search_results[0]
                        asin = best_match["asin"]
                        log.info("Found ASIN %s for search: %s", asin, watch_data["keywords"])
                except Exception as search_error:
                    log.warning("Product search failed for '%s': %s", watch_data["keywords"], search_error)
                    # Continue without ASIN - watch will still be created for future searches

            # Create watch record
            watch = Watch(
                user_id=user.id,
                asin=asin,
                keywords=watch_data["keywords"],
                brand=watch_data.get("brand"),
                max_price=watch_data.get("max_price"),
                min_discount=watch_data.get("min_discount"),
                mode="daily",  # Default to daily mode
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

    # Clear pending data
    context.user_data.pop("pending_watch", None)
    context.user_data.pop("original_message_id", None)

    # Send single comprehensive message based on what we found
    try:
        if asin:
            # We found a specific product - try to show price card
            try:
                log.info("Fetching current price for ASIN %s", asin)
                price = get_price(asin)
                
                # Try to get product details from PA-API
                try:
                    item_data = await get_item(asin)
                    title = item_data.get("title", watch_data["keywords"])
                    image_url = item_data.get("image", "https://m.media-amazon.com/images/I/81.png")
                except Exception as e:
                    log.warning("Could not get item details for ASIN %s: %s", asin, e)
                    title = watch_data["keywords"]
                    image_url = "https://m.media-amazon.com/images/I/81.png"

                # Build success message with current price
                success_msg = f"✅ **Watch created successfully!**\n\n📱 Product: {title}"
                if watch_data.get("brand"):
                    success_msg += f"\n🏷️ Brand: {watch_data['brand'].title()}"
                if watch_data.get("max_price"):
                    success_msg += f"\n💰 Max price: ₹{watch_data['max_price']:,}"
                if watch_data.get("min_discount"):
                    success_msg += f"\n💸 Min discount: {watch_data['min_discount']}%"
                success_msg += f"\n\n🔔 You'll get daily alerts when deals match your criteria!"

                # Send confirmation message first
                if update.callback_query:
                    await update.callback_query.edit_message_text(success_msg, parse_mode="Markdown")
                else:
                    await update.effective_message.reply_text(success_msg, parse_mode="Markdown")

                # Then send price card
                caption, keyboard = build_single_card(
                    title=title,
                    price=price,
                    image=image_url,
                    asin=asin,
                    watch_id=watch.id,
                )

                await update.effective_message.reply_photo(
                    photo=image_url,
                    caption=caption,
                    reply_markup=keyboard,
                    parse_mode="Markdown",
                )
                log.info("Successfully sent watch confirmation and price card to user %s", user_id)
                
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
                success_msg += f"\n\n🔔 You'll get daily alerts when deals match your criteria!\n\n⚠️ Current price unavailable, but monitoring is active."

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
            success_msg += (
                f"\n\n🔔 You'll get daily alerts when deals match your criteria!"
                f"\n\n💡 **Tip:** I'll search for products matching your description during daily scans. "
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
