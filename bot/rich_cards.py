"""Rich Product Cards Builder for enhanced user experience."""

from datetime import datetime
from logging import getLogger
from typing import Dict, List, Optional

from sqlmodel import Session, select
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .cache_service import engine
from .carousel import build_single_card, build_deal_card
from .enhanced_models import Product, ProductOffers, CustomerReviews
from .market_intelligence import MarketIntelligence
from .models import Price

log = getLogger(__name__)


class RichCardBuilder:
    """Enhanced card builder extending existing carousel functionality."""

    def __init__(self):
        """Initialize rich card builder."""
        self.market_intel = MarketIntelligence()

    async def build_comprehensive_card(
        self, asin: str, context: str = "search", watch_id: Optional[int] = None
    ) -> Dict:
        """Build comprehensive product card with all available data.

        Args:
        ----
            asin: Product ASIN
            context: Context for card building ("search", "watch", "comparison")
            watch_id: Optional watch ID for tracking

        Returns:
        -------
            Dict with enhanced card data
        """
        try:
            log.info("Building comprehensive card for ASIN: %s", asin)

            with Session(engine) as session:
                # Get comprehensive product data
                product = session.get(Product, asin)
                offers = session.exec(
                    select(ProductOffers)
                    .where(ProductOffers.asin == asin)
                    .order_by(ProductOffers.fetched_at.desc())
                ).first()
                reviews = session.get(CustomerReviews, asin)

                if not product:
                    # Fallback to basic card
                    return await self._build_fallback_card(asin, watch_id)

                # Get deal quality if we have pricing data
                deal_quality = None
                if offers and offers.price:
                    deal_quality = await self.market_intel.calculate_deal_quality(
                        asin, offers.price
                    )

                # Build enhanced caption
                caption = await self._build_enhanced_caption(
                    product, offers, reviews, deal_quality
                )

                # Build enhanced keyboard
                keyboard = await self._build_enhanced_keyboard(
                    asin, product, context, watch_id
                )

                # Select best image
                image = (
                    product.large_image
                    or product.medium_image
                    or product.small_image
                    or "https://via.placeholder.com/300x300?text=No+Image"
                )

                return {
                    "caption": caption,
                    "keyboard": keyboard,
                    "image": image,
                    "enhanced": True,
                    "deal_quality": deal_quality.get("score", 0) if deal_quality else 0,
                    "product_data": {
                        "title": product.title,
                        "brand": product.brand,
                        "asin": asin,
                        "price": offers.price if offers else None,
                    },
                }

        except Exception as e:
            log.error("Failed to build comprehensive card for %s: %s", asin, e)
            return await self._build_fallback_card(asin, watch_id)

    async def build_comparison_carousel(
        self, products: List[str], context: str = "comparison"
    ) -> List[Dict]:
        """Build comparison carousel for multiple products.

        Args:
        ----
            products: List of ASINs to compare
            context: Context for comparison

        Returns:
        -------
            List of enhanced card dictionaries
        """
        try:
            log.info("Building comparison carousel for %d products", len(products))

            carousel_cards = []
            for asin in products[:5]:  # Limit to 5 for performance
                card = await self.build_comprehensive_card(asin, context)
                if card and not card.get("error"):
                    carousel_cards.append(card)

            # Sort by deal quality if available
            carousel_cards.sort(
                key=lambda x: x.get("deal_quality", 0), reverse=True
            )

            return carousel_cards

        except Exception as e:
            log.error("Failed to build comparison carousel: %s", e)
            return []

    async def build_enhanced_deal_card(
        self,
        asin: str,
        current_price: int,
        watch_id: Optional[int] = None,
        urgency: str = "normal",
    ) -> Dict:
        """Build enhanced deal announcement card.

        Args:
        ----
            asin: Product ASIN
            current_price: Current price in paise
            watch_id: Optional watch ID
            urgency: Deal urgency level

        Returns:
        -------
            Enhanced deal card dictionary
        """
        try:
            with Session(engine) as session:
                product = session.get(Product, asin)
                offers = session.exec(
                    select(ProductOffers)
                    .where(ProductOffers.asin == asin)
                    .order_by(ProductOffers.fetched_at.desc())
                ).first()
                reviews = session.get(CustomerReviews, asin)

                if not product:
                    return await self._build_fallback_card(asin, watch_id)

                # Calculate deal quality
                deal_quality = await self.market_intel.calculate_deal_quality(
                    asin, current_price
                )

                # Build deal-specific caption
                caption = await self._build_deal_caption(
                    product, offers, reviews, deal_quality, current_price, urgency
                )

                # Build deal-specific keyboard
                keyboard = await self._build_deal_keyboard(
                    asin, product, deal_quality, watch_id
                )

                return {
                    "caption": caption,
                    "keyboard": keyboard,
                    "image": product.large_image or product.medium_image,
                    "enhanced": True,
                    "deal_type": "enhanced",
                    "urgency": urgency,
                    "deal_quality": deal_quality.get("score", 0),
                }

        except Exception as e:
            log.error("Failed to build enhanced deal card for %s: %s", asin, e)
            return await self._build_fallback_card(asin, watch_id)

    async def _build_enhanced_caption(
        self,
        product: Product,
        offers: Optional[ProductOffers],
        reviews: Optional[CustomerReviews],
        deal_quality: Optional[Dict],
    ) -> str:
        """Build enhanced product caption with all available data."""
        try:
            # Start with title and brand
            caption = f"📱 **{product.title[:60]}...**\n"
            if product.brand:
                caption += f"🏷️ **Brand:** {product.brand}\n"

            caption += "\n"

            # Add pricing information
            if offers and offers.price:
                caption += f"💰 **Price:** ₹{offers.price//100:.2f}"

                # Add discount information
                if offers.list_price and offers.list_price > offers.price:
                    savings = offers.list_price - offers.price
                    savings_pct = (savings / offers.list_price) * 100
                    caption += f" ~~₹{offers.list_price//100:.2f}~~\n"
                    caption += f"💸 **Save:** ₹{savings//100:.2f} ({savings_pct:.0f}% OFF)\n"
                else:
                    caption += "\n"

                # Add availability
                if offers.availability_type:
                    if offers.availability_type == "InStock":
                        caption += "✅ **In Stock**\n"
                    elif offers.availability_type == "OutOfStock":
                        caption += "❌ **Out of Stock**\n"
                    else:
                        caption += f"📦 **{offers.availability_type}**\n"

                # Add Prime eligibility
                if offers.is_prime_eligible:
                    caption += "🚀 **Prime Eligible**\n"

            caption += "\n"

            # Add review information
            if reviews and reviews.review_count > 0:
                rating_stars = "⭐" * int(reviews.average_rating or 0)
                caption += f"{rating_stars} **{reviews.average_rating:.1f}/5** ({reviews.review_count:,} reviews)\n"

            # Add deal quality if available
            if deal_quality and deal_quality.get("score"):
                score = deal_quality["score"]
                quality = deal_quality.get("quality", "unknown")
                caption += f"🎯 **Deal Quality:** {score:.0f}/100 ({quality.title()})\n"

            # Add key features
            if product.features_list and len(product.features_list) > 0:
                caption += "\n📋 **Key Features:**\n"
                for feature in product.features_list[:3]:  # Limit to top 3
                    caption += f"• {feature[:50]}...\n"

            return caption

        except Exception as e:
            log.error("Failed to build enhanced caption: %s", e)
            return f"📱 {product.title}\n💰 Price information unavailable"

    async def _build_enhanced_keyboard(
        self,
        asin: str,
        product: Product,
        context: str,
        watch_id: Optional[int] = None,
    ) -> InlineKeyboardMarkup:
        """Build enhanced keyboard with context-appropriate buttons."""
        try:
            buttons = []

            # Primary action button
            if watch_id:
                buy_button = InlineKeyboardButton(
                    "🛒 BUY NOW", callback_data=f"click:{watch_id}:{asin}"
                )
            else:
                buy_button = InlineKeyboardButton(
                    "🛒 View Product", url=f"https://amazon.in/dp/{asin}"
                )
            buttons.append([buy_button])

            # Context-specific buttons
            if context == "search":
                buttons.append(
                    [
                        InlineKeyboardButton(
                            "👁️ Create Watch", callback_data=f"watch_create:{asin}"
                        ),
                        InlineKeyboardButton(
                            "📊 Price History", callback_data=f"price_history:{asin}"
                        ),
                    ]
                )
                buttons.append(
                    [
                        InlineKeyboardButton(
                            "🔍 Find Similar", callback_data=f"similar:{asin}"
                        ),
                        InlineKeyboardButton(
                            "📈 Market Info", callback_data=f"market_info:{asin}"
                        ),
                    ]
                )
            elif context == "watch":
                buttons.append(
                    [
                        InlineKeyboardButton(
                            "⏸️ Pause Watch", callback_data=f"pause_watch:{watch_id}"
                        ),
                        InlineKeyboardButton(
                            "🗑️ Delete Watch", callback_data=f"delete_watch:{watch_id}"
                        ),
                    ]
                )
            elif context == "comparison":
                buttons.append(
                    [
                        InlineKeyboardButton(
                            "📊 Compare Details", callback_data=f"compare_details:{asin}"
                        ),
                        InlineKeyboardButton(
                            "👁️ Watch This", callback_data=f"watch_create:{asin}"
                        ),
                    ]
                )

            return InlineKeyboardMarkup(buttons)

        except Exception as e:
            log.error("Failed to build enhanced keyboard: %s", e)
            # Fallback to simple keyboard
            return InlineKeyboardMarkup(
                [[InlineKeyboardButton("🛒 View Product", url=f"https://amazon.in/dp/{asin}")]]
            )

    async def _build_deal_caption(
        self,
        product: Product,
        offers: Optional[ProductOffers],
        reviews: Optional[CustomerReviews],
        deal_quality: Dict,
        current_price: int,
        urgency: str,
    ) -> str:
        """Build deal-specific caption with urgency indicators."""
        try:
            # Deal header based on quality and urgency
            quality_score = deal_quality.get("score", 0)

            if quality_score >= 90:
                header = "🔥 **EXCEPTIONAL DEAL!** 🔥"
            elif quality_score >= 80:
                header = "✨ **EXCELLENT DEAL!** ✨"
            elif quality_score >= 70:
                header = "💫 **GREAT DEAL!** 💫"
            else:
                header = "📢 **DEAL ALERT!** 📢"

            caption = f"{header}\n\n"

            # Product info
            caption += f"📱 **{product.title[:50]}...**\n"
            if product.brand:
                caption += f"🏷️ {product.brand}\n"

            caption += "\n"

            # Price with emphasis
            caption += f"💰 **₹{current_price//100:.2f}**"

            # Add comparison price if available
            if offers and offers.list_price and offers.list_price > current_price:
                savings = offers.list_price - current_price
                savings_pct = (savings / offers.list_price) * 100
                caption += f" ~~₹{offers.list_price//100:.2f}~~\n"
                caption += f"💸 **SAVE ₹{savings//100:.2f}** ({savings_pct:.0f}% OFF)\n"
            else:
                caption += "\n"

            # Deal quality indicator
            caption += f"🎯 **Deal Score:** {quality_score:.0f}/100\n"

            # Review info if available
            if reviews and reviews.review_count > 0:
                stars = "⭐" * int(reviews.average_rating or 0)
                caption += f"{stars} {reviews.average_rating:.1f} ({reviews.review_count:,} reviews)\n"

            # Urgency indicator
            if urgency == "critical":
                caption += "\n⚡ **LIMITED TIME - ACT FAST!**\n"
            elif urgency == "high":
                caption += "\n🕒 **High Priority Deal**\n"

            # Availability
            if offers and offers.availability_type == "InStock":
                caption += "✅ In Stock"
                if offers.is_prime_eligible:
                    caption += " | 🚀 Prime"

            return caption

        except Exception as e:
            log.error("Failed to build deal caption: %s", e)
            return f"🔥 DEAL ALERT!\n{product.title}\n💰 ₹{current_price//100:.2f}"

    async def _build_deal_keyboard(
        self,
        asin: str,
        product: Product,
        deal_quality: Dict,
        watch_id: Optional[int] = None,
    ) -> InlineKeyboardMarkup:
        """Build deal-specific keyboard with urgency actions."""
        try:
            buttons = []

            # Primary buy button with emphasis
            if deal_quality.get("score", 0) >= 80:
                buy_text = "🔥 BUY NOW - GREAT DEAL!"
            else:
                buy_text = "🛒 BUY NOW"

            if watch_id:
                buy_button = InlineKeyboardButton(
                    buy_text, callback_data=f"click:{watch_id}:{asin}"
                )
            else:
                buy_button = InlineKeyboardButton(
                    buy_text, url=f"https://amazon.in/dp/{asin}"
                )
            buttons.append([buy_button])

            # Secondary actions
            buttons.append(
                [
                    InlineKeyboardButton(
                        "📊 Price History", callback_data=f"price_history:{asin}"
                    ),
                    InlineKeyboardButton(
                        "🔍 Similar Deals", callback_data=f"similar_deals:{asin}"
                    ),
                ]
            )

            # Watch management if applicable
            if watch_id:
                buttons.append(
                    [
                        InlineKeyboardButton(
                            "⏸️ Pause Alerts", callback_data=f"pause_watch:{watch_id}"
                        )
                    ]
                )
            else:
                buttons.append(
                    [
                        InlineKeyboardButton(
                            "👁️ Watch for Better Deals", callback_data=f"watch_create:{asin}"
                        )
                    ]
                )

            return InlineKeyboardMarkup(buttons)

        except Exception as e:
            log.error("Failed to build deal keyboard: %s", e)
            return InlineKeyboardMarkup(
                [[InlineKeyboardButton("🛒 BUY NOW", url=f"https://amazon.in/dp/{asin}")]]
            )

    async def _build_fallback_card(
        self, asin: str, watch_id: Optional[int] = None
    ) -> Dict:
        """Build fallback card when enhanced data is not available."""
        try:
            # Try to get basic price data
            with Session(engine) as session:
                price_record = session.exec(
                    select(Price)
                    .where(Price.asin == asin)
                    .order_by(Price.fetched_at.desc())
                ).first()

                if price_record and watch_id:
                    # Use existing simple card function
                    caption, keyboard = build_single_card(
                        "Product Details", price_record.price, "", asin, watch_id
                    )
                else:
                    # Basic fallback
                    caption = f"📱 Product Information\n💰 Price updates available\n\n🔍 ASIN: {asin}"
                    keyboard = InlineKeyboardMarkup(
                        [[InlineKeyboardButton("🛒 View Product", url=f"https://amazon.in/dp/{asin}")]]
                    )

                return {
                    "caption": caption,
                    "keyboard": keyboard,
                    "image": "https://via.placeholder.com/300x300?text=Product",
                    "enhanced": False,
                    "fallback": True,
                }

        except Exception as e:
            log.error("Failed to build fallback card: %s", e)
            return {
                "caption": f"📱 Product\n🔍 ASIN: {asin}",
                "keyboard": InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🛒 View Product", url=f"https://amazon.in/dp/{asin}")]]
                ),
                "image": "https://via.placeholder.com/300x300?text=Error",
                "enhanced": False,
                "error": str(e),
            }


class CarouselBuilder:
    """Enhanced carousel builder for multiple product displays."""

    def __init__(self):
        """Initialize carousel builder."""
        self.rich_card_builder = RichCardBuilder()

    async def build_search_results_carousel(
        self, products: List[str], query: str = ""
    ) -> Dict:
        """Build search results carousel with enhanced cards.

        Args:
        ----
            products: List of ASINs
            query: Original search query

        Returns:
        -------
            Carousel data with header and cards
        """
        try:
            log.info("Building search results carousel for %d products", len(products))

            # Build cards for all products
            cards = await self.rich_card_builder.build_comparison_carousel(
                products, "search"
            )

            if not cards:
                return {
                    "header": f"No results found for: {query}",
                    "cards": [],
                    "total_products": 0,
                    "has_enhanced": False,
                }

            # Create header
            enhanced_count = sum(1 for card in cards if card.get("enhanced"))
            header = f"🔍 **Search Results** ({len(cards)} products)\n"
            if query:
                header += f"**Query:** {query}\n"
            header += f"**Enhanced Cards:** {enhanced_count}/{len(cards)}"

            return {
                "header": header,
                "cards": cards,
                "total_products": len(cards),
                "has_enhanced": enhanced_count > 0,
                "query": query,
            }

        except Exception as e:
            log.error("Failed to build search results carousel: %s", e)
            return {
                "header": "Search Results (Error)",
                "cards": [],
                "total_products": 0,
                "has_enhanced": False,
                "error": str(e),
            }

    async def build_deals_carousel(self, deals: List[Dict]) -> Dict:
        """Build deals carousel with enhanced deal cards.

        Args:
        ----
            deals: List of deal dictionaries with ASIN and pricing info

        Returns:
        -------
            Deals carousel data
        """
        try:
            log.info("Building deals carousel for %d deals", len(deals))

            cards = []
            for deal in deals[:10]:  # Limit to top 10 deals
                asin = deal.get("asin")
                current_price = deal.get("current_price", 0)
                urgency = deal.get("urgency", "normal")
                watch_id = deal.get("watch_id")

                if asin:
                    card = await self.rich_card_builder.build_enhanced_deal_card(
                        asin, current_price, watch_id, urgency
                    )
                    if card and not card.get("error"):
                        cards.append(card)

            # Sort by deal quality
            cards.sort(key=lambda x: x.get("deal_quality", 0), reverse=True)

            # Create header
            total_deals = len(cards)
            avg_quality = (
                sum(card.get("deal_quality", 0) for card in cards) / total_deals
                if total_deals > 0
                else 0
            )

            header = f"🔥 **Deal Alerts** ({total_deals} deals)\n"
            header += f"📊 **Avg Quality:** {avg_quality:.0f}/100"

            return {
                "header": header,
                "cards": cards,
                "total_deals": total_deals,
                "average_quality": avg_quality,
            }

        except Exception as e:
            log.error("Failed to build deals carousel: %s", e)
            return {
                "header": "Deal Alerts (Error)",
                "cards": [],
                "total_deals": 0,
                "average_quality": 0,
                "error": str(e),
            }

    async def build_watch_summary_carousel(self, user_id: int) -> Dict:
        """Build user watch summary carousel.

        Args:
        ----
            user_id: User ID to get watches for

        Returns:
        -------
            Watch summary carousel data
        """
        try:
            log.info("Building watch summary carousel for user %d", user_id)

            with Session(engine) as session:
                # Get user's watches (would need to import Watch model)
                # For now, return placeholder
                cards = []

                return {
                    "header": f"👁️ **Your Watches** ({len(cards)} active)",
                    "cards": cards,
                    "total_watches": len(cards),
                    "active_watches": len(cards),
                }

        except Exception as e:
            log.error("Failed to build watch summary carousel: %s", e)
            return {
                "header": "Your Watches (Error)",
                "cards": [],
                "total_watches": 0,
                "active_watches": 0,
                "error": str(e),
            }
