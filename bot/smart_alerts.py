"""Smart Alert Engine for enhanced deal notifications and market insights."""

from datetime import datetime, timedelta
from logging import getLogger
from typing import Dict, List

from sqlmodel import Session, select
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

from .cache_service import engine
from .carousel import build_single_card
from .config import settings
from .enhanced_models import DealAlert
from .market_intelligence import MarketIntelligence
from .models import Watch
from .predictive_ai import predictive_engine

log = getLogger(__name__)


class SmartAlertEngine:
    """Enhanced notifications built on existing alert system."""

    def __init__(self):
        """Initialize smart alert engine."""
        self.market_intel = MarketIntelligence()
        self.bot = Bot(token=settings.TELEGRAM_TOKEN)

    async def generate_enhanced_deal_alert(
        self, watch: Watch, current_data: Dict
    ) -> Dict:
        """Enhanced version of existing deal alerts with quality assessment and AI predictions.

        Args:
        ----
            watch: Watch object triggering the alert
            current_data: Current product data (price, title, image, etc.)

        Returns:
        -------
            Dict with enhanced alert data and quality metrics
        """
        try:
            log.info("Generating enhanced deal alert for watch %d", watch.id)

            # Calculate deal quality using market intelligence
            deal_quality = await self.market_intel.calculate_deal_quality(
                watch.asin, current_data["price"]
            )

            # Get AI prediction for deal success
            deal_prediction = await predictive_engine.predict_deal_success(
                watch.asin, current_data["price"]
            )

            # Determine alert urgency (enhanced with AI insights)
            urgency = await self._calculate_urgency_with_ai(
                deal_quality, deal_prediction, current_data, watch
            )

            # Get price trend context
            price_context = await self._get_price_context(
                watch.asin, current_data["price"]
            )

            # Generate appropriate card based on quality
            if deal_quality["score"] >= 80:
                # High quality deal - use enhanced card
                caption, keyboard = await self._build_premium_deal_card(
                    watch, current_data, deal_quality, urgency, price_context
                )
            elif deal_quality["score"] >= 60:
                # Good quality deal - use enhanced card with moderate emphasis
                caption, keyboard = await self._build_good_deal_card(
                    watch, current_data, deal_quality, urgency, price_context
                )
            else:
                # Regular deal - use existing card with quality info
                caption, keyboard = await self._build_standard_deal_card(
                    watch, current_data, deal_quality, urgency
                )

            # Store alert in database for analytics
            await self._store_deal_alert(watch, current_data, deal_quality)

            return {
                "caption": caption,
                "keyboard": keyboard,
                "quality_score": deal_quality["score"],
                "quality_category": deal_quality.get("quality", "unknown"),
                "urgency": urgency,
                "price_context": price_context,
                "recommendations": deal_quality.get("recommendations", []),
                "ai_prediction": deal_prediction,
            }

        except Exception as e:
            log.error("Failed to generate enhanced deal alert: %s", e)
            # Fallback to basic alert
            return await self._generate_fallback_alert(watch, current_data)

    async def generate_market_insight_notification(
        self, user_id: int, insight_type: str, data: Dict
    ) -> Dict:
        """Generate market insight notifications for users.

        Args:
        ----
            user_id: User ID to send notification to
            insight_type: Type of insight (weekly_roundup, seasonal_opportunity, etc.)
            data: Insight data

        Returns:
        -------
            Dict with notification data
        """
        try:
            if insight_type == "weekly_roundup":
                return await self._generate_weekly_roundup(user_id, data)
            elif insight_type == "seasonal_opportunity":
                return await self._generate_seasonal_opportunity(user_id, data)
            elif insight_type == "price_drop_prediction":
                return await self._generate_price_drop_prediction(user_id, data)
            elif insight_type == "category_trend":
                return await self._generate_category_trend(user_id, data)
            else:
                return {"error": f"Unknown insight type: {insight_type}"}

        except Exception as e:
            log.error("Failed to generate market insight notification: %s", e)
            return {"error": str(e)}

    async def send_comparison_alert(
        self, user_id: int, original_asin: str, alternatives: List[Dict]
    ) -> bool:
        """Send alert with alternative product suggestions.

        Args:
        ----
            user_id: User ID to send alert to
            original_asin: Original product ASIN
            alternatives: List of alternative products with better deals

        Returns:
        -------
            True if sent successfully, False otherwise
        """
        try:
            if not alternatives:
                return False

            # Build comparison message
            caption = "🔄 **Better Deal Found!**\n\n"
            caption += "We found better alternatives to your watched product:\n\n"

            for i, alt in enumerate(alternatives[:3], 1):  # Limit to top 3
                caption += f"{i}. **{alt['title'][:50]}...**\n"
                caption += f"   💰 ₹{alt['price']//100:.2f} "
                if alt.get("savings_percentage"):
                    caption += f"({alt['savings_percentage']}% off)\n"
                else:
                    caption += "\n"
                caption += f"   ⭐ {alt.get('rating', 'N/A')} ({alt.get('review_count', 0)} reviews)\n\n"

            # Create keyboard with alternative product links
            keyboard_buttons = []
            for i, alt in enumerate(alternatives[:3], 1):
                keyboard_buttons.append(
                    [
                        InlineKeyboardButton(
                            f"View Alternative {i}",
                            url=f"https://amazon.in/dp/{alt['asin']}",
                        )
                    ]
                )

            keyboard = InlineKeyboardMarkup(keyboard_buttons)

            # Send notification
            await self.bot.send_message(
                chat_id=user_id,
                text=caption,
                reply_markup=keyboard,
                parse_mode="Markdown",
            )

            return True

        except Exception as e:
            log.error("Failed to send comparison alert: %s", e)
            return False

    async def send_price_drop_prediction_alert(
        self, user_id: int, asin: str, prediction_data: Dict
    ) -> bool:
        """Send alert about predicted price drop.

        Args:
        ----
            user_id: User ID to send alert to
            asin: Product ASIN
            prediction_data: Price prediction data

        Returns:
        -------
            True if sent successfully, False otherwise
        """
        try:
            confidence = prediction_data.get("confidence", 0)
            predicted_price = prediction_data.get("predicted_price", 0)
            current_price = prediction_data.get("current_price", 0)

            if confidence < 0.6:  # Only send if confidence is reasonable
                return False

            # Calculate expected savings
            expected_savings = current_price - predicted_price
            savings_percentage = (
                (expected_savings / current_price) * 100 if current_price > 0 else 0
            )

            caption = "📉 **Price Drop Predicted!**\n\n"
            caption += "Our AI predicts a price drop for your watched product:\n\n"
            caption += f"**Current Price:** ₹{current_price//100:.2f}\n"
            caption += f"**Predicted Price:** ₹{predicted_price//100:.2f}\n"
            caption += f"**Expected Savings:** ₹{expected_savings//100:.2f} ({savings_percentage:.1f}%)\n"
            caption += f"**Confidence:** {confidence*100:.0f}%\n\n"

            if confidence >= 0.8:
                caption += "🎯 High confidence - consider waiting for the drop!"
            elif confidence >= 0.7:
                caption += "⚖️ Good confidence - might be worth waiting."
            else:
                caption += "⚠️ Moderate confidence - use your judgment."

            # Create keyboard
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "View Product", url=f"https://amazon.in/dp/{asin}"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "Disable Predictions",
                            callback_data=f"disable_predictions_{asin}",
                        )
                    ],
                ]
            )

            await self.bot.send_message(
                chat_id=user_id,
                text=caption,
                reply_markup=keyboard,
                parse_mode="Markdown",
            )

            return True

        except Exception as e:
            log.error("Failed to send price drop prediction alert: %s", e)
            return False

    # Helper methods for alert generation

    async def _calculate_urgency(
        self, deal_quality: Dict, current_data: Dict, watch: Watch
    ) -> str:
        """Calculate urgency level for deal alert."""
        try:
            score = deal_quality.get("score", 0)

            # Check stock availability
            stock_urgent = "stock" in current_data.get("availability", "").lower()

            # Check if price just dropped significantly
            price_drop_urgent = False
            with Session(engine) as session:
                # Get recent price history
                recent_prices = session.exec(
                    select(DealAlert)
                    .where(
                        DealAlert.asin == watch.asin,
                        DealAlert.sent_at >= datetime.utcnow() - timedelta(days=7),
                    )
                    .order_by(DealAlert.sent_at.desc())
                ).all()

                if recent_prices and len(recent_prices) > 0:
                    last_price = recent_prices[0].current_price
                    if current_data["price"] < last_price * 0.9:  # 10% drop
                        price_drop_urgent = True

            # Determine urgency
            if score >= 90 and (stock_urgent or price_drop_urgent):
                return "critical"
            elif score >= 80:
                return "high"
            elif score >= 60:
                return "medium"
            else:
                return "low"

        except Exception as e:
            log.error("Failed to calculate urgency: %s", e)
            return "low"

    async def _get_price_context(self, asin: str, current_price: int) -> Dict:
        """Get price context for the alert."""
        try:
            # Get price trends from market intelligence
            trends = await self.market_intel.analyze_price_trends(asin, "1month")

            if "error" in trends:
                return {"context": "No price history available"}

            metrics = trends.get("price_metrics", {})

            context = {}

            # Compare to historical prices
            min_price = metrics.get("min_price", current_price)
            max_price = metrics.get("max_price", current_price)
            avg_price = metrics.get("average_price", current_price)

            if current_price <= min_price * 1.05:  # Within 5% of historical minimum
                context["price_level"] = "historical_low"
            elif current_price <= avg_price * 0.9:  # 10% below average
                context["price_level"] = "below_average"
            elif current_price >= max_price * 0.95:  # Within 5% of historical maximum
                context["price_level"] = "historical_high"
            else:
                context["price_level"] = "average"

            # Add trend information
            trend_analysis = trends.get("trend_analysis", {})
            context["trend"] = trend_analysis.get("direction", "stable")
            context["volatility"] = metrics.get("volatility_percentage", 0)

            return context

        except Exception as e:
            log.error("Failed to get price context: %s", e)
            return {"context": "Unable to analyze price context"}

    async def _build_premium_deal_card(
        self,
        watch: Watch,
        current_data: Dict,
        deal_quality: Dict,
        urgency: str,
        price_context: Dict,
    ) -> tuple:
        """Build premium deal card for high-quality deals."""
        try:
            # Enhanced caption with quality indicators
            caption = "🔥 **PREMIUM DEAL ALERT!** 🔥\n\n"
            caption += f"**{current_data['title'][:60]}...**\n\n"

            # Price information
            caption += f"💰 **₹{current_data['price']//100:.2f}**"
            if current_data.get("list_price"):
                savings = current_data["list_price"] - current_data["price"]
                savings_pct = (savings / current_data["list_price"]) * 100
                caption += f" ~~₹{current_data['list_price']//100:.2f}~~\n"
                caption += (
                    f"💸 **Save ₹{savings//100:.2f} ({savings_pct:.0f}% OFF)**\n\n"
                )
            else:
                caption += "\n\n"

            # Quality indicators
            caption += f"⭐ **Deal Quality:** {deal_quality['score']:.0f}/100 ({deal_quality.get('quality', 'excellent').title()})\n"

            # Price context
            if price_context.get("price_level") == "historical_low":
                caption += "📉 **Historical Low Price!**\n"
            elif price_context.get("price_level") == "below_average":
                caption += "📊 **Below Average Price**\n"

            # Urgency indicator
            if urgency == "critical":
                caption += "⚡ **LIMITED TIME - ACT NOW!**\n"
            elif urgency == "high":
                caption += "🕒 **High Priority Deal**\n"

            caption += f"\n🔍 **Keywords:** {watch.keywords}"

            # Enhanced keyboard
            keyboard_buttons = [
                [
                    InlineKeyboardButton(
                        "🛒 BUY NOW", url=f"https://amazon.in/dp/{watch.asin}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "📊 Price History", callback_data=f"price_history_{watch.asin}"
                    ),
                    InlineKeyboardButton(
                        "🔍 Similar Deals", callback_data=f"similar_{watch.asin}"
                    ),
                ],
                [
                    InlineKeyboardButton(
                        "⏸️ Pause Watch", callback_data=f"pause_{watch.id}"
                    )
                ],
            ]

            keyboard = InlineKeyboardMarkup(keyboard_buttons)

            return caption, keyboard

        except Exception as e:
            log.error("Failed to build premium deal card: %s", e)
            # Fallback to basic card
            return build_single_card(
                watch.keywords,
                current_data["price"],
                current_data.get("image", ""),
                watch.asin,
                watch.id,
            )

    async def _build_good_deal_card(
        self,
        watch: Watch,
        current_data: Dict,
        deal_quality: Dict,
        urgency: str,
        price_context: Dict,
    ) -> tuple:
        """Build good deal card for quality deals."""
        try:
            caption = "✨ **GOOD DEAL ALERT** ✨\n\n"
            caption += f"**{current_data['title'][:60]}...**\n\n"
            caption += f"💰 **₹{current_data['price']//100:.2f}**\n"
            caption += f"⭐ **Deal Quality:** {deal_quality['score']:.0f}/100\n"

            if price_context.get("price_level") == "below_average":
                caption += "📊 **Below Average Price**\n"

            caption += f"\n🔍 **Keywords:** {watch.keywords}"

            keyboard_buttons = [
                [
                    InlineKeyboardButton(
                        "🛒 Buy Now", url=f"https://amazon.in/dp/{watch.asin}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "📊 Details", callback_data=f"details_{watch.asin}"
                    )
                ],
            ]

            keyboard = InlineKeyboardMarkup(keyboard_buttons)
            return caption, keyboard

        except Exception as e:
            log.error("Failed to build good deal card: %s", e)
            return build_single_card(
                watch.keywords,
                current_data["price"],
                current_data.get("image", ""),
                watch.asin,
                watch.id,
            )

    async def _build_standard_deal_card(
        self, watch: Watch, current_data: Dict, deal_quality: Dict, urgency: str
    ) -> tuple:
        """Build standard deal card with quality info."""
        try:
            # Use existing card builder and enhance caption
            caption, keyboard = build_single_card(
                watch.keywords,
                current_data["price"],
                current_data.get("image", ""),
                watch.asin,
                watch.id,
            )

            # Add quality score to caption
            quality_line = f"\n⭐ Deal Quality: {deal_quality['score']:.0f}/100"
            caption += quality_line

            return caption, keyboard

        except Exception as e:
            log.error("Failed to build standard deal card: %s", e)
            return build_single_card(
                watch.keywords,
                current_data["price"],
                current_data.get("image", ""),
                watch.asin,
                watch.id,
            )

    async def _store_deal_alert(
        self, watch: Watch, current_data: Dict, deal_quality: Dict
    ) -> None:
        """Store deal alert in database for analytics."""
        try:
            with Session(engine) as session:
                alert = DealAlert(
                    watch_id=watch.id,
                    asin=watch.asin,
                    alert_type="deal_quality",
                    current_price=current_data["price"],
                    deal_quality_score=deal_quality.get("score", 0),
                    discount_percentage=current_data.get("savings_percentage"),
                )
                session.add(alert)
                session.commit()

        except Exception as e:
            log.error("Failed to store deal alert: %s", e)

    async def _generate_fallback_alert(self, watch: Watch, current_data: Dict) -> Dict:
        """Generate fallback alert if enhanced alert fails."""
        try:
            caption, keyboard = build_single_card(
                watch.keywords,
                current_data["price"],
                current_data.get("image", ""),
                watch.asin,
                watch.id,
            )

            return {
                "caption": caption,
                "keyboard": keyboard,
                "quality_score": 50.0,
                "urgency": "low",
                "fallback": True,
            }

        except Exception as e:
            log.error("Failed to generate fallback alert: %s", e)
            return {"error": str(e)}

    # Market insight notification generators (placeholders for now)

    async def _generate_weekly_roundup(self, user_id: int, data: Dict) -> Dict:
        """Generate weekly market roundup notification."""
        # Placeholder implementation
        return {
            "type": "weekly_roundup",
            "caption": "📊 **Weekly Market Roundup**\n\nYour watched categories are showing stable trends.",
            "keyboard": InlineKeyboardMarkup([]),
        }

    async def _generate_seasonal_opportunity(self, user_id: int, data: Dict) -> Dict:
        """Generate seasonal opportunity notification."""
        # Placeholder implementation
        return {
            "type": "seasonal_opportunity",
            "caption": "🌟 **Seasonal Opportunity**\n\nGreat deals expected in your categories!",
            "keyboard": InlineKeyboardMarkup([]),
        }

    async def _generate_price_drop_prediction(self, user_id: int, data: Dict) -> Dict:
        """Generate price drop prediction notification."""
        # Placeholder implementation
        return {
            "type": "price_drop_prediction",
            "caption": "📉 **Price Drop Predicted**\n\nOur AI suggests waiting for better prices.",
            "keyboard": InlineKeyboardMarkup([]),
        }

    async def _generate_category_trend(self, user_id: int, data: Dict) -> Dict:
        """Generate category trend notification."""
        # Placeholder implementation
        return {
            "type": "category_trend",
            "caption": "📈 **Category Trend Alert**\n\nInteresting trends in your watched categories.",
            "keyboard": InlineKeyboardMarkup([]),
        }


class UserPreferenceManager:
    """Manage user notification preferences."""

    def __init__(self):
        """Initialize preference manager."""
        pass

    async def get_user_preferences(self, user_id: int) -> Dict:
        """Get user notification preferences."""
        # Placeholder - would integrate with enhanced User model
        return {
            "notification_frequency": "normal",  # low, normal, high
            "deal_quality_threshold": 70,
            "categories_of_interest": [],
            "quiet_hours": {"start": 22, "end": 8},  # 22:00 to 08:00
            "enabled_notification_types": [
                "deal_alerts",
                "price_drops",
                "weekly_roundup",
            ],
        }

    async def update_user_preferences(self, user_id: int, preferences: Dict) -> bool:
        """Update user notification preferences."""
        # Placeholder implementation
        try:
            # Would store in enhanced User model or separate preferences table
            log.info("Updated preferences for user %d", user_id)
            return True
        except Exception as e:
            log.error("Failed to update preferences for user %d: %s", user_id, e)
            return False

    async def should_send_notification(
        self, user_id: int, notification_type: str, current_time: datetime = None
    ) -> bool:
        """Check if notification should be sent based on user preferences."""
        try:
            if current_time is None:
                current_time = datetime.utcnow()

            preferences = await self.get_user_preferences(user_id)

            # Check if notification type is enabled
            if notification_type not in preferences.get(
                "enabled_notification_types", []
            ):
                return False

            # Check quiet hours
            quiet_hours = preferences.get("quiet_hours", {})
            current_hour = current_time.hour

            if quiet_hours:
                start_hour = quiet_hours.get("start", 22)
                end_hour = quiet_hours.get("end", 8)

                if start_hour > end_hour:  # Crosses midnight
                    if current_hour >= start_hour or current_hour < end_hour:
                        return False
                else:  # Same day
                    if start_hour <= current_hour < end_hour:
                        return False

            return True

        except Exception as e:
            log.error("Failed to check notification permissions: %s", e)
            return True  # Default to allowing notifications

    async def generate_smart_inventory_alert(self, asin: str) -> Dict:
        """Generate smart inventory alerts using AI predictions.
        
        Args:
        ----
            asin: Product ASIN to analyze
            
        Returns:
        -------
            Dict with inventory alert data and AI insights
        """
        try:
            log.info("Generating smart inventory alert for ASIN %s", asin)
            
            # Get AI prediction for inventory
            inventory_prediction = await predictive_engine.predict_inventory_alerts(asin)
            
            if inventory_prediction.get("prediction") == "insufficient_data":
                return {"status": "insufficient_data", "message": "Not enough data for prediction"}
            
            # Get product data for alert
            with Session(engine) as session:
                from .enhanced_models import Product
                product = session.get(Product, asin)
                
                if not product:
                    return {"status": "product_not_found", "message": "Product not found"}
                
                # Generate alert message based on urgency
                urgency = inventory_prediction.get("urgency_level", "low")
                alert_data = await self._build_inventory_alert_message(
                    product, inventory_prediction, urgency
                )
                
                return {
                    "status": "success",
                    "alert_data": alert_data,
                    "prediction": inventory_prediction,
                    "urgency": urgency,
                    "should_send": urgency in ["high", "critical"]
                }
                
        except Exception as e:
            log.error("Error generating smart inventory alert for ASIN %s: %s", asin, e)
            return {"status": "error", "message": str(e)}

    async def generate_personalized_recommendations(self, user_id: int) -> Dict:
        """Generate personalized product recommendations using AI.
        
        Args:
        ----
            user_id: User ID to generate recommendations for
            
        Returns:
        -------
            Dict with personalized recommendations and explanations
        """
        try:
            log.info("Generating personalized recommendations for user %d", user_id)
            
            # Get AI-powered recommendations
            recommendations = await predictive_engine.predict_user_interests(user_id, limit=10)
            
            if not recommendations:
                return {"status": "no_recommendations", "message": "No recommendations available"}
            
            # Format recommendations for display
            formatted_recs = []
            for rec in recommendations:
                formatted_rec = await self._format_recommendation_for_display(rec)
                formatted_recs.append(formatted_rec)
            
            # Generate recommendation message
            message = await self._build_recommendations_message(formatted_recs)
            
            return {
                "status": "success",
                "recommendations": formatted_recs,
                "message": message,
                "count": len(formatted_recs)
            }
            
        except Exception as e:
            log.error("Error generating personalized recommendations for user %d: %s", user_id, e)
            return {"status": "error", "message": str(e)}

    async def _calculate_urgency_with_ai(
        self, deal_quality: Dict, deal_prediction: Dict, current_data: Dict, watch: Watch
    ) -> str:
        """Calculate alert urgency enhanced with AI predictions."""
        try:
            base_urgency = await self._calculate_urgency(deal_quality, current_data, watch)
            
            # Enhance with AI prediction
            success_probability = deal_prediction.get("success_probability", 0.5)
            
            if success_probability >= 0.8:
                # AI predicts high success - increase urgency
                if base_urgency == "medium":
                    return "high"
                elif base_urgency == "low":
                    return "medium"
            elif success_probability <= 0.3:
                # AI predicts poor success - decrease urgency
                if base_urgency == "high":
                    return "medium"
                elif base_urgency == "medium":
                    return "low"
            
            return base_urgency
            
        except Exception as e:
            log.error("Error calculating AI-enhanced urgency: %s", e)
            return "medium"

    async def _build_inventory_alert_message(
        self, product, inventory_prediction: Dict, urgency: str
    ) -> Dict:
        """Build inventory alert message with AI insights."""
        urgency_emojis = {
            "low": "📊",
            "medium": "⚠️", 
            "high": "🚨",
            "critical": "🔥"
        }
        
        urgency_messages = {
            "low": "Stock levels are stable",
            "medium": "Stock levels need monitoring", 
            "high": "Stock may run out soon",
            "critical": "Stock-out imminent!"
        }
        
        emoji = urgency_emojis.get(urgency, "📊")
        base_message = urgency_messages.get(urgency, "Stock status update")
        
        stockout_prob = inventory_prediction.get("stockout_probability", 0)
        days_until = inventory_prediction.get("days_until_stockout")
        
        caption = f"{emoji} **Inventory Alert**\n\n"
        caption += f"**Product:** {product.title}\n"
        caption += f"**Status:** {base_message}\n"
        caption += f"**Stock-out Probability:** {stockout_prob:.1%}\n"
        
        if days_until:
            caption += f"**Estimated Time:** {days_until} days\n"
        
        caption += f"\n**AI Recommendation:** {inventory_prediction.get('recommendation', 'Monitor regularly')}"
        
        # Create keyboard with action buttons
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔍 Check Product", url=f"https://amazon.in/dp/{product.asin}"),
                InlineKeyboardButton("📊 View Details", callback_data=f"inventory_details:{product.asin}")
            ]
        ])
        
        return {
            "caption": caption,
            "keyboard": keyboard,
            "urgency": urgency
        }

    async def _format_recommendation_for_display(self, recommendation: Dict) -> Dict:
        """Format AI recommendation for user display."""
        return {
            "asin": recommendation.get("asin"),
            "title": recommendation.get("title", "Unknown Product"),
            "brand": recommendation.get("brand", "Unknown"),
            "category": recommendation.get("category", "General"),
            "confidence": recommendation.get("confidence_score", 0.5),
            "interest_level": recommendation.get("predicted_interest_level", "medium"),
            "explanation": recommendation.get("explanation", "Based on your preferences"),
            "source": recommendation.get("source", "ai_prediction")
        }

    async def _build_recommendations_message(self, recommendations: List[Dict]) -> Dict:
        """Build personalized recommendations message."""
        if not recommendations:
            return {"caption": "No recommendations available", "keyboard": None}
        
        caption = "🤖 **AI-Powered Recommendations**\n\n"
        caption += "Based on your browsing patterns, here are some products you might like:\n\n"
        
        # Show top 3 recommendations in detail
        for i, rec in enumerate(recommendations[:3], 1):
            confidence_emoji = "🔥" if rec["confidence"] > 0.8 else "⭐" if rec["confidence"] > 0.6 else "💡"
            
            caption += f"{confidence_emoji} **{i}. {rec['title'][:40]}{'...' if len(rec['title']) > 40 else ''}**\n"
            caption += f"   Brand: {rec['brand']} | Category: {rec['category']}\n"
            caption += f"   Why: {rec['explanation'][:60]}{'...' if len(rec['explanation']) > 60 else ''}\n\n"
        
        if len(recommendations) > 3:
            caption += f"_... and {len(recommendations) - 3} more personalized suggestions_\n\n"
        
        caption += "💡 Tap 'View All' to see complete recommendations with prices!"
        
        # Create keyboard
        keyboard_buttons = []
        
        # Add quick access buttons for top recommendations
        for i, rec in enumerate(recommendations[:2]):
            if rec["asin"] != "fallback":
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        f"🔍 View #{i+1}", 
                        url=f"https://amazon.in/dp/{rec['asin']}"
                    )
                ])
        
        # Add action buttons
        keyboard_buttons.append([
            InlineKeyboardButton("📋 View All Recommendations", callback_data="view_all_recommendations"),
            InlineKeyboardButton("⚙️ Preferences", callback_data="update_preferences")
        ])
        
        keyboard = InlineKeyboardMarkup(keyboard_buttons)
        
        return {
            "caption": caption,
            "keyboard": keyboard
        }
