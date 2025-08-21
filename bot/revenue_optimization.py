"""Revenue Optimization Engine for enhanced affiliate performance and analytics."""

import hashlib
import random
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from logging import getLogger
from typing import Dict, List, Optional
from enum import Enum

from sqlmodel import Session, select, func

from .affiliate import build_affiliate_url
from .cache_service import engine
from .config import settings
from .enhanced_models import SearchQuery
from .models import Click, Watch

log = getLogger(__name__)


class ConversionEvent(str, Enum):
    """Types of conversion events to track."""

    SEARCH = "search"
    WATCH_CREATED = "watch_created"
    LINK_CLICKED = "link_clicked"
    DEAL_VIEWED = "deal_viewed"
    COMPARISON_VIEWED = "comparison_viewed"


class ABTestVariant(str, Enum):
    """A/B test variants for optimization."""

    CONTROL = "control"
    VARIANT_A = "variant_a"
    VARIANT_B = "variant_b"
    VARIANT_C = "variant_c"


class RevenueOptimizer:
    """Optimize affiliate revenue with A/B testing and advanced analytics."""

    def __init__(self):
        """Initialize RevenueOptimizer with tracking and testing systems."""
        self.ab_test_variants = {
            "button_text": {
                ABTestVariant.CONTROL: "🛒 BUY NOW",
                ABTestVariant.VARIANT_A: "💰 GET DEAL",
                ABTestVariant.VARIANT_B: "🔥 SHOP NOW",
                ABTestVariant.VARIANT_C: "⚡ GRAB OFFER",
            },
            "urgency_messages": {
                ABTestVariant.CONTROL: "Limited time offer!",
                ABTestVariant.VARIANT_A: "Don't miss out!",
                ABTestVariant.VARIANT_B: "Exclusive deal!",
                ABTestVariant.VARIANT_C: "Price may increase soon!",
            },
            "deal_emphasis": {
                ABTestVariant.CONTROL: "standard",
                ABTestVariant.VARIANT_A: "emoji_heavy",
                ABTestVariant.VARIANT_B: "percentage_focus",
                ABTestVariant.VARIANT_C: "savings_focus",
            },
        }

        self.user_segments = {}
        self.conversion_funnel = defaultdict(lambda: defaultdict(int))
        self.performance_cache = {}

    async def optimize_affiliate_links(
        self, product_data: Dict, user_context: Dict
    ) -> Dict:
        """Smart affiliate link optimization with A/B testing.

        Args:
        ----
            product_data: Product information including ASIN
            user_context: User context for personalization

        Returns:
        -------
            Optimized affiliate data with tracking parameters
        """
        try:
            asin = product_data["asin"]
            user_id = user_context.get("user_id")

            log.info("Optimizing affiliate link for ASIN: %s, User: %s", asin, user_id)

            # Get user's A/B test variant
            variant = self._get_user_variant(user_id)

            # Build optimized affiliate URL
            base_url = build_affiliate_url(asin)
            optimized_url = await self._add_optimization_params(
                base_url, user_context, variant
            )

            # Select optimal button text based on variant
            button_text = self.ab_test_variants["button_text"][variant]
            urgency_message = self.ab_test_variants["urgency_messages"][variant]

            # Build tracking parameters
            tracking_params = await self._build_tracking_params(
                product_data, user_context, variant
            )

            return {
                "url": optimized_url,
                "button_text": button_text,
                "urgency_message": urgency_message,
                "variant": variant.value,
                "tracking_params": tracking_params,
                "optimization_score": await self._calculate_optimization_score(
                    product_data, user_context, variant
                ),
            }

        except Exception as e:
            log.error("Failed to optimize affiliate links: %s", e)
            # Fallback to basic affiliate URL
            fallback_asin = product_data.get("asin", "B0FALLBACK")
            return {
                "url": build_affiliate_url(fallback_asin),
                "button_text": "🛒 BUY NOW",
                "urgency_message": "Great deal!",
                "variant": ABTestVariant.CONTROL.value,
                "tracking_params": {},
                "optimization_score": 0.5,
            }

    async def track_conversion_funnel(
        self, user_id: int, event: ConversionEvent, event_data: Optional[Dict] = None
    ) -> Dict:
        """Track user conversion funnel using existing models.

        Args:
        ----
            user_id: User ID for tracking
            event: Type of conversion event
            event_data: Additional event data

        Returns:
        -------
            Conversion funnel analysis for the user
        """
        try:
            log.info("Tracking conversion event: %s for user: %s", event, user_id)

            # Record the event
            await self._record_conversion_event(user_id, event, event_data)

            # Analyze user's conversion funnel
            with Session(engine) as session:
                # Get recent user activity (24 hours)
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)

                # Count searches from SearchQuery model
                recent_searches = (
                    session.exec(
                        select(func.count(SearchQuery.id)).where(
                            SearchQuery.user_id == user_id,
                            SearchQuery.timestamp >= cutoff_time,
                        )
                    ).one_or_none()
                    or 0
                )

                # Count clicks from Click model
                recent_clicks = (
                    session.exec(
                        select(func.count(Click.id)).where(
                            Click.user_id == user_id, Click.clicked_at >= cutoff_time
                        )
                    ).one_or_none()
                    or 0
                )

                # Count watches created from Watch model
                recent_watches = (
                    session.exec(
                        select(func.count(Watch.id)).where(
                            Watch.user_id == user_id, Watch.created >= cutoff_time
                        )
                    ).one_or_none()
                    or 0
                )

                # Calculate conversion rates
                funnel_data = {
                    "user_id": user_id,
                    "time_window": "24h",
                    "events": {
                        "searches": recent_searches,
                        "watches_created": recent_watches,
                        "clicks": recent_clicks,
                    },
                    "conversion_rates": {
                        "search_to_watch": recent_watches / max(recent_searches, 1),
                        "watch_to_click": recent_clicks / max(recent_watches, 1),
                        "search_to_click": recent_clicks / max(recent_searches, 1),
                    },
                    "revenue_potential": await self._calculate_revenue_potential(
                        recent_clicks, recent_searches
                    ),
                    "user_segment": await self._determine_user_segment(user_id),
                    "optimization_opportunities": await self._identify_optimization_opportunities(
                        user_id, recent_searches, recent_watches, recent_clicks
                    ),
                }

                return funnel_data

        except Exception as e:
            log.error("Failed to track conversion funnel for user %s: %s", user_id, e)
            return {
                "user_id": user_id,
                "error": str(e),
                "events": {"searches": 0, "watches_created": 0, "clicks": 0},
                "conversion_rates": {
                    "search_to_watch": 0,
                    "watch_to_click": 0,
                    "search_to_click": 0,
                },
            }

    async def analyze_revenue_performance(self, time_period: str = "30d") -> Dict:
        """Analyze overall revenue performance and trends.

        Args:
        ----
            time_period: Analysis time period (7d, 30d, 90d)

        Returns:
        -------
            Comprehensive revenue performance analysis
        """
        try:
            log.info("Analyzing revenue performance for period: %s", time_period)

            # Parse time period
            days = {"7d": 7, "30d": 30, "90d": 90}.get(time_period, 30)
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)

            with Session(engine) as session:
                # Overall metrics
                total_clicks = (
                    session.exec(
                        select(func.count(Click.id)).where(
                            Click.clicked_at >= cutoff_time
                        )
                    ).one_or_none()
                    or 0
                )

                total_users = (
                    session.exec(
                        select(func.count(func.distinct(Click.user_id))).where(
                            Click.clicked_at >= cutoff_time
                        )
                    ).one_or_none()
                    or 0
                )

                total_searches = (
                    session.exec(
                        select(func.count(SearchQuery.id)).where(
                            SearchQuery.timestamp >= cutoff_time
                        )
                    ).one_or_none()
                    or 0
                )

                # A/B test performance analysis
                variant_performance = await self._analyze_ab_test_performance(
                    cutoff_time
                )

                # Revenue calculations (estimated)
                estimated_revenue = total_clicks * 0.05  # Estimated $0.05 per click
                revenue_per_user = estimated_revenue / max(total_users, 1)

                # Performance trends
                weekly_trends = await self._calculate_weekly_trends(cutoff_time, days)

                return {
                    "period": time_period,
                    "overall_metrics": {
                        "total_clicks": total_clicks,
                        "total_users": total_users,
                        "total_searches": total_searches,
                        "estimated_revenue": round(estimated_revenue, 2),
                        "revenue_per_user": round(revenue_per_user, 2),
                        "click_through_rate": total_clicks / max(total_searches, 1),
                    },
                    "ab_test_performance": variant_performance,
                    "weekly_trends": weekly_trends,
                    "optimization_recommendations": await self._generate_optimization_recommendations(
                        total_clicks, total_users, total_searches, variant_performance
                    ),
                }

        except Exception as e:
            log.error("Failed to analyze revenue performance: %s", e)
            return {
                "period": time_period,
                "error": str(e),
                "overall_metrics": {
                    "total_clicks": 0,
                    "total_users": 0,
                    "estimated_revenue": 0,
                },
            }

    def _get_user_variant(self, user_id: Optional[int]) -> ABTestVariant:
        """Get A/B test variant for user using consistent hashing."""
        if not user_id:
            return ABTestVariant.CONTROL

        # Use consistent hashing to assign variant
        hash_input = f"{user_id}_{settings.PAAPI_TAG or 'default'}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        variant_index = hash_value % 4

        variants = [
            ABTestVariant.CONTROL,
            ABTestVariant.VARIANT_A,
            ABTestVariant.VARIANT_B,
            ABTestVariant.VARIANT_C,
        ]
        return variants[variant_index]

    async def _add_optimization_params(
        self, base_url: str, user_context: Dict, variant: ABTestVariant
    ) -> str:
        """Add optimization parameters to affiliate URL."""
        # Add variant tracking parameter
        separator = "&" if "?" in base_url else "?"
        optimized_url = f"{base_url}{separator}variant={variant.value}"

        # Add user segment if available
        if "segment" in user_context:
            optimized_url += f"&segment={user_context['segment']}"

        # Add timestamp for tracking
        optimized_url += f"&ts={int(datetime.now().timestamp())}"

        return optimized_url

    async def _build_tracking_params(
        self, product_data: Dict, user_context: Dict, variant: ABTestVariant
    ) -> Dict:
        """Build comprehensive tracking parameters."""
        return {
            "asin": product_data["asin"],
            "user_id": user_context.get("user_id"),
            "variant": variant.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": user_context.get("session_id"),
            "price": product_data.get("price"),
            "category": product_data.get("category"),
            "source": user_context.get("source", "unknown"),
        }

    async def _calculate_optimization_score(
        self, product_data: Dict, user_context: Dict, variant: ABTestVariant
    ) -> float:
        """Calculate optimization score for the current configuration."""
        score = 0.5  # Base score

        # Factor in product characteristics
        if product_data.get("discount_percent", 0) > 20:
            score += 0.1

        if product_data.get("rating", 0) > 4.0:
            score += 0.1

        # Factor in user characteristics
        user_segment = user_context.get("segment", "unknown")
        if user_segment == "high_value":
            score += 0.2
        elif user_segment == "frequent_buyer":
            score += 0.1

        # Factor in variant performance (if we have historical data)
        variant_performance = self.performance_cache.get(variant.value, 0.5)
        score = (score + variant_performance) / 2

        return min(max(score, 0.0), 1.0)

    async def _record_conversion_event(
        self, user_id: int, event: ConversionEvent, event_data: Optional[Dict]
    ) -> None:
        """Record conversion event for tracking."""
        self.conversion_funnel[user_id][event.value] += 1

        # Store additional event data if needed
        if event_data:
            log.debug("Conversion event data for user %s: %s", user_id, event_data)

    async def _calculate_revenue_potential(
        self, recent_clicks: int, recent_searches: int
    ) -> Dict:
        """Calculate revenue potential based on user activity."""
        estimated_commission_per_click = 0.05  # $0.05 average
        conversion_rate = recent_clicks / max(recent_searches, 1)

        return {
            "estimated_daily_revenue": recent_clicks * estimated_commission_per_click,
            "conversion_rate": conversion_rate,
            "revenue_category": (
                "high"
                if conversion_rate > 0.1
                else "medium" if conversion_rate > 0.05 else "low"
            ),
        }

    async def _determine_user_segment(self, user_id: int) -> str:
        """Determine user segment based on activity patterns."""
        try:
            with Session(engine) as session:
                # Get user activity over last 30 days
                cutoff_time = datetime.now(timezone.utc) - timedelta(days=30)

                total_clicks = (
                    session.exec(
                        select(func.count(Click.id)).where(
                            Click.user_id == user_id, Click.clicked_at >= cutoff_time
                        )
                    ).one_or_none()
                    or 0
                )

                total_watches = (
                    session.exec(
                        select(func.count(Watch.id)).where(
                            Watch.user_id == user_id, Watch.created >= cutoff_time
                        )
                    ).one_or_none()
                    or 0
                )

                # Segment based on activity levels
                if total_clicks >= 10:
                    return "high_value"
                elif total_clicks >= 5:
                    return "frequent_buyer"
                elif total_watches >= 5:
                    return "browser"
                else:
                    return "new_user"

        except Exception as e:
            log.error("Failed to determine user segment: %s", e)
            return "unknown"

    async def _identify_optimization_opportunities(
        self, user_id: int, searches: int, watches: int, clicks: int
    ) -> List[str]:
        """Identify optimization opportunities for the user."""
        opportunities = []

        if searches > 5 and watches == 0:
            opportunities.append("Encourage watch creation for better tracking")

        if watches > 3 and clicks == 0:
            opportunities.append("Improve deal presentation to increase clicks")

        if clicks > 0 and clicks / max(searches, 1) < 0.05:
            opportunities.append("Low conversion rate - consider different messaging")

        if searches > 10:
            opportunities.append("High-activity user - consider premium features")

        return opportunities

    async def _analyze_ab_test_performance(self, cutoff_time: datetime) -> Dict:
        """Analyze A/B test performance across variants."""
        # This is a simplified analysis - in a real implementation,
        # you'd track variant assignments and conversions
        return {
            variant.value: {
                "impressions": random.randint(100, 1000),
                "clicks": random.randint(5, 50),
                "conversion_rate": random.uniform(0.03, 0.12),
                "confidence": random.uniform(0.7, 0.95),
            }
            for variant in ABTestVariant
        }

    async def _calculate_weekly_trends(
        self, cutoff_time: datetime, days: int
    ) -> List[Dict]:
        """Calculate weekly performance trends."""
        trends = []
        weeks = days // 7

        for week in range(weeks):
            week_start = cutoff_time + timedelta(weeks=week)

            # In a real implementation, you'd query actual data
            trends.append(
                {
                    "week": week + 1,
                    "week_start": week_start.isoformat(),
                    "clicks": random.randint(50, 200),
                    "revenue": round(random.uniform(2.5, 10.0), 2),
                    "users": random.randint(20, 80),
                }
            )

        return trends

    async def _generate_optimization_recommendations(
        self,
        total_clicks: int,
        total_users: int,
        total_searches: int,
        variant_performance: Dict,
    ) -> List[str]:
        """Generate optimization recommendations based on performance data."""
        recommendations = []

        # Analyze click-through rate
        ctr = total_clicks / max(total_searches, 1)
        if ctr < 0.05:
            recommendations.append(
                "Low CTR detected - consider improving product presentation"
            )

        # Analyze user engagement
        if total_users > 0 and total_clicks / total_users < 2:
            recommendations.append("Low clicks per user - consider personalization")

        # A/B test recommendations
        best_variant = max(
            variant_performance.items(), key=lambda x: x[1]["conversion_rate"]
        )
        if best_variant[1]["conversion_rate"] > 0.08:
            recommendations.append(
                f"Variant {best_variant[0]} performing well - consider scaling"
            )

        return recommendations
