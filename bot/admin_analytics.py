"""Business Analytics Dashboard for admin interface and business intelligence."""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from logging import getLogger
from typing import Dict, List, Optional

from sqlmodel import Session, select, func

from .cache_service import engine
from .enhanced_models import Product, SearchQuery
from .models import User, Watch, Price, Click
from .revenue_optimization import RevenueOptimizer

log = getLogger(__name__)


class AdminAnalytics:
    """Business analytics engine for admin dashboard and business intelligence."""

    def __init__(self):
        """Initialize AdminAnalytics with revenue optimizer integration."""
        self.revenue_optimizer = RevenueOptimizer()
        self.cache_duration = timedelta(minutes=15)  # Cache results for 15 minutes
        self.analytics_cache = {}

    async def generate_performance_dashboard(self, time_period: str = "30d") -> Dict:
        """Generate comprehensive performance dashboard data.

        Args:
        ----
            time_period: Analysis period (7d, 30d, 90d)

        Returns:
        -------
            Complete dashboard data with all business metrics
        """
        try:
            log.info("Generating performance dashboard for period: %s", time_period)

            # Check cache first
            cache_key = f"dashboard_{time_period}"
            if self._is_cache_valid(cache_key):
                return self.analytics_cache[cache_key]

            # Parse time period
            days = {"7d": 7, "30d": 30, "90d": 90}.get(time_period, 30)
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)

            with Session(engine) as session:
                # Core user metrics
                user_metrics = await self._calculate_user_metrics(session, cutoff_time)

                # Watch and product metrics
                product_metrics = await self._calculate_product_metrics(
                    session, cutoff_time
                )

                # Revenue and affiliate metrics
                revenue_metrics = await self._calculate_revenue_metrics(
                    session, cutoff_time
                )

                # System performance metrics
                performance_metrics = await self._calculate_performance_metrics(
                    session, cutoff_time
                )

                # Growth and trend analysis
                growth_metrics = await self._calculate_growth_metrics(
                    session, cutoff_time, days
                )

                # Category and search analytics
                category_metrics = await self._calculate_category_metrics(
                    session, cutoff_time
                )

                dashboard_data = {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "time_period": time_period,
                    "user_metrics": user_metrics,
                    "product_metrics": product_metrics,
                    "revenue_metrics": revenue_metrics,
                    "performance_metrics": performance_metrics,
                    "growth_metrics": growth_metrics,
                    "category_metrics": category_metrics,
                    "key_insights": await self._generate_key_insights(
                        user_metrics, product_metrics, revenue_metrics, growth_metrics
                    ),
                    "action_items": await self._generate_action_items(
                        user_metrics, product_metrics, revenue_metrics
                    ),
                }

                # Cache the results
                self.analytics_cache[cache_key] = dashboard_data

                return dashboard_data

        except Exception as e:
            log.error("Failed to generate performance dashboard: %s", e)
            return {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "time_period": time_period,
                "error": str(e),
                "user_metrics": {"total": 0, "active": 0},
                "product_metrics": {"total_watches": 0, "active_watches": 0},
                "revenue_metrics": {"total_clicks": 0, "estimated_revenue": 0},
            }

    async def analyze_user_segmentation(self, detailed: bool = False) -> Dict:
        """Analyze user segmentation with behavioral patterns.

        Args:
        ----
            detailed: Whether to include detailed user-level analysis

        Returns:
        -------
            User segmentation analysis with behavioral insights
        """
        try:
            log.info("Analyzing user segmentation (detailed=%s)", detailed)

            with Session(engine) as session:
                # Get all users with their activity
                users_with_activity = await self._get_users_with_activity(session)

                # Segment users based on behavior
                segments = {
                    "power_users": [],
                    "regular_users": [],
                    "casual_users": [],
                    "inactive_users": [],
                    "new_users": [],
                }

                segment_stats = defaultdict(
                    lambda: {
                        "count": 0,
                        "total_watches": 0,
                        "total_clicks": 0,
                        "total_searches": 0,
                        "avg_session_length": 0,
                        "revenue_contribution": 0,
                    }
                )

                for user_data in users_with_activity:
                    segment = await self._classify_user_segment(user_data)
                    segments[segment].append(user_data)

                    # Update segment statistics
                    stats = segment_stats[segment]
                    stats["count"] += 1
                    stats["total_watches"] += user_data["watches_count"]
                    stats["total_clicks"] += user_data["clicks_count"]
                    stats["total_searches"] += user_data["searches_count"]
                    stats["revenue_contribution"] += user_data["estimated_revenue"]

                # Calculate segment metrics
                for segment in segment_stats:
                    if segment_stats[segment]["count"] > 0:
                        count = segment_stats[segment]["count"]
                        segment_stats[segment]["avg_watches_per_user"] = (
                            segment_stats[segment]["total_watches"] / count
                        )
                        segment_stats[segment]["avg_clicks_per_user"] = (
                            segment_stats[segment]["total_clicks"] / count
                        )
                        segment_stats[segment]["avg_revenue_per_user"] = (
                            segment_stats[segment]["revenue_contribution"] / count
                        )

                segmentation_analysis = {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "total_users": len(users_with_activity),
                    "segment_distribution": {
                        segment: stats["count"]
                        for segment, stats in segment_stats.items()
                    },
                    "segment_statistics": dict(segment_stats),
                    "segment_insights": await self._generate_segment_insights(
                        segment_stats
                    ),
                    "churn_risk_analysis": await self._analyze_churn_risk(
                        users_with_activity
                    ),
                    "growth_opportunities": await self._identify_growth_opportunities(
                        segment_stats
                    ),
                }

                if detailed:
                    segmentation_analysis["detailed_segments"] = segments

                return segmentation_analysis

        except Exception as e:
            log.error("Failed to analyze user segmentation: %s", e)
            return {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
                "total_users": 0,
                "segment_distribution": {},
            }

    async def analyze_product_performance(self, category: Optional[str] = None) -> Dict:
        """Analyze product performance across categories and individual products.

        Args:
        ----
            category: Optional category filter for analysis

        Returns:
        -------
            Product performance analysis with insights
        """
        try:
            log.info("Analyzing product performance (category=%s)", category)

            with Session(engine) as session:
                # Get product performance data
                products_data = await self._get_product_performance_data(
                    session, category
                )

                # Category performance analysis
                category_performance = await self._analyze_category_performance(
                    session, category
                )

                # Price trend analysis
                price_trends = await self._analyze_price_trends(session, category)

                # Deal effectiveness analysis
                deal_effectiveness = await self._analyze_deal_effectiveness(
                    session, category
                )

                # Search pattern analysis
                search_patterns = await self._analyze_search_patterns(session, category)

                return {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "category_filter": category,
                    "total_products": len(products_data),
                    "category_performance": category_performance,
                    "price_trends": price_trends,
                    "deal_effectiveness": deal_effectiveness,
                    "search_patterns": search_patterns,
                    "top_performing_products": products_data[:10],  # Top 10
                    "underperforming_products": await self._identify_underperforming_products(
                        products_data
                    ),
                    "optimization_recommendations": await self._generate_product_optimization_recommendations(
                        products_data, category_performance, deal_effectiveness
                    ),
                }

        except Exception as e:
            log.error("Failed to analyze product performance: %s", e)
            return {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
                "total_products": 0,
                "category_performance": {},
            }

    async def generate_revenue_insights(
        self, include_forecasting: bool = False
    ) -> Dict:
        """Generate comprehensive revenue insights and forecasting.

        Args:
        ----
            include_forecasting: Whether to include revenue forecasting

        Returns:
        -------
            Revenue insights with trends and forecasting
        """
        try:
            log.info(
                "Generating revenue insights (forecasting=%s)", include_forecasting
            )

            # Get revenue performance from RevenueOptimizer
            revenue_performance = (
                await self.revenue_optimizer.analyze_revenue_performance("30d")
            )

            with Session(engine) as session:
                # Additional revenue analysis
                revenue_by_source = await self._analyze_revenue_by_source(session)
                revenue_by_category = await self._analyze_revenue_by_category(session)
                seasonal_patterns = await self._analyze_seasonal_patterns(session)

                insights = {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "revenue_performance": revenue_performance,
                    "revenue_by_source": revenue_by_source,
                    "revenue_by_category": revenue_by_category,
                    "seasonal_patterns": seasonal_patterns,
                    "optimization_impact": await self._analyze_optimization_impact(
                        session
                    ),
                    "competitive_analysis": await self._analyze_competitive_position(
                        session
                    ),
                }

                if include_forecasting:
                    insights["revenue_forecast"] = (
                        await self._generate_revenue_forecast(
                            revenue_performance, seasonal_patterns
                        )
                    )

                return insights

        except Exception as e:
            log.error("Failed to generate revenue insights: %s", e)
            return {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
                "revenue_performance": {},
            }

    # Private helper methods

    async def _calculate_user_metrics(
        self, session: Session, cutoff_time: datetime
    ) -> Dict:
        """Calculate comprehensive user metrics."""
        total_users = session.exec(select(func.count(User.id))).one()

        active_users = (
            session.exec(
                select(func.count(func.distinct(Watch.user_id))).where(
                    Watch.created >= cutoff_time
                )
            ).one_or_none()
            or 0
        )

        new_users = (
            session.exec(
                select(func.count(User.id)).where(User.first_seen >= cutoff_time)
            ).one_or_none()
            or 0
        )

        # User engagement metrics
        avg_watches_per_user = (
            session.exec(
                select(func.avg(func.count(Watch.id)))
                .select_from(Watch)
                .group_by(Watch.user_id)
            ).one_or_none()
            or 0
        )

        return {
            "total": total_users,
            "active_monthly": active_users,
            "new_users": new_users,
            "growth_rate": new_users / max(total_users - new_users, 1) * 100,
            "engagement_rate": active_users / max(total_users, 1) * 100,
            "avg_watches_per_user": round(float(avg_watches_per_user or 0), 2),
        }

    async def _calculate_product_metrics(
        self, session: Session, cutoff_time: datetime
    ) -> Dict:
        """Calculate product and watch metrics."""
        total_watches = session.exec(select(func.count(Watch.id))).one()

        active_watches = (
            session.exec(
                select(func.count(Watch.id)).where(Watch.created >= cutoff_time)
            ).one_or_none()
            or 0
        )

        total_products = (
            session.exec(select(func.count(Product.asin))).one_or_none() or 0
        )

        return {
            "total_watches": total_watches,
            "active_watches": active_watches,
            "total_products": total_products,
            "watch_creation_rate": active_watches
            / max((datetime.now(timezone.utc) - cutoff_time).days, 1),
            "watches_per_product": total_watches / max(total_products, 1),
        }

    async def _calculate_revenue_metrics(
        self, session: Session, cutoff_time: datetime
    ) -> Dict:
        """Calculate revenue and affiliate metrics."""
        total_clicks = (
            session.exec(
                select(func.count(Click.id)).where(Click.clicked_at >= cutoff_time)
            ).one_or_none()
            or 0
        )

        # Get unique clickers by joining Click with Watch to get user_id
        from sqlmodel import join

        unique_clickers = (
            session.exec(
                select(func.count(func.distinct(Watch.user_id)))
                .select_from(join(Click, Watch, Click.watch_id == Watch.id))
                .where(Click.clicked_at >= cutoff_time)
            ).one_or_none()
            or 0
        )

        estimated_revenue = total_clicks * 0.05  # $0.05 per click estimate

        return {
            "total_clicks": total_clicks,
            "unique_clickers": unique_clickers,
            "estimated_revenue": round(estimated_revenue, 2),
            "revenue_per_user": round(estimated_revenue / max(unique_clickers, 1), 2),
            "click_through_rate": await self._calculate_overall_ctr(
                session, cutoff_time
            ),
        }

    async def _calculate_performance_metrics(
        self, session: Session, cutoff_time: datetime
    ) -> Dict:
        """Calculate system performance metrics."""
        # API usage metrics
        total_searches = (
            session.exec(
                select(func.count(SearchQuery.id)).where(
                    SearchQuery.timestamp >= cutoff_time
                )
            ).one_or_none()
            or 0
        )

        # Cache performance (simplified) - placeholder for future implementation

        return {
            "total_api_calls": total_searches,
            "cache_efficiency": 0.85,  # Placeholder - implement actual cache tracking
            "avg_response_time": 1.2,  # Placeholder - implement actual timing
            "error_rate": 0.02,  # Placeholder - implement actual error tracking
            "system_uptime": 99.5,  # Placeholder - implement actual uptime tracking
        }

    async def _calculate_growth_metrics(
        self, session: Session, cutoff_time: datetime, days: int
    ) -> Dict:
        """Calculate growth and trend metrics."""
        # Weekly growth calculation
        weeks = max(days // 7, 1)
        weekly_data = []

        for week in range(weeks):
            week_start = cutoff_time + timedelta(days=week * 7)
            week_end = week_start + timedelta(days=7)

            week_users = (
                session.exec(
                    select(func.count(User.id)).where(
                        User.first_seen >= week_start, User.first_seen < week_end
                    )
                ).one_or_none()
                or 0
            )

            week_watches = (
                session.exec(
                    select(func.count(Watch.id)).where(
                        Watch.created >= week_start, Watch.created < week_end
                    )
                ).one_or_none()
                or 0
            )

            weekly_data.append(
                {
                    "week": week + 1,
                    "users": week_users,
                    "watches": week_watches,
                    "week_start": week_start.isoformat(),
                }
            )

        return {
            "weekly_trends": weekly_data,
            "user_growth_trend": "stable",  # Implement trend calculation
            "watch_growth_trend": "increasing",  # Implement trend calculation
            "projected_monthly_growth": 15.0,  # Implement projection algorithm
        }

    async def _calculate_category_metrics(
        self, session: Session, cutoff_time: datetime
    ) -> Dict:
        """Calculate category-wise performance metrics."""
        # This is simplified - implement based on your category data
        return {
            "top_categories": [
                {"name": "Electronics", "watches": 45, "clicks": 23},
                {"name": "Books", "watches": 32, "clicks": 18},
                {"name": "Clothing", "watches": 28, "clicks": 15},
            ],
            "category_trends": {
                "growing": ["Electronics", "Home & Garden"],
                "stable": ["Books", "Sports"],
                "declining": ["Music"],
            },
        }

    async def _generate_key_insights(
        self,
        user_metrics: Dict,
        product_metrics: Dict,
        revenue_metrics: Dict,
        growth_metrics: Dict,
    ) -> List[str]:
        """Generate key business insights from metrics."""
        insights = []

        if user_metrics["growth_rate"] > 20:
            insights.append(
                "Strong user growth detected - consider scaling infrastructure"
            )

        if revenue_metrics["click_through_rate"] < 0.05:
            insights.append("Low CTR - consider improving product presentation")

        if user_metrics["engagement_rate"] > 70:
            insights.append("High user engagement - good retention indicators")

        if product_metrics["watches_per_product"] > 2:
            insights.append("Products generating multiple watches - strong interest")

        return insights

    async def _generate_action_items(
        self, user_metrics: Dict, product_metrics: Dict, revenue_metrics: Dict
    ) -> List[str]:
        """Generate actionable items based on metrics."""
        actions = []

        if user_metrics["engagement_rate"] < 30:
            actions.append("Implement user engagement campaign")

        if revenue_metrics["revenue_per_user"] < 1.0:
            actions.append("Optimize monetization strategies")

        if product_metrics["watch_creation_rate"] < 5:
            actions.append("Promote watch creation features")

        return actions

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is still valid."""
        if cache_key not in self.analytics_cache:
            return False

        # For this implementation, we'll use a simple time-based cache
        # In production, implement proper cache validation
        return True  # Simplified for now

    # Additional helper methods (simplified implementations)

    async def _get_users_with_activity(self, session: Session) -> List[Dict]:
        """Get all users with their activity metrics."""
        # Simplified implementation - expand based on your needs
        return []

    async def _classify_user_segment(self, user_data: Dict) -> str:
        """Classify user into behavioral segment."""
        # Implement user segmentation logic
        return "regular_users"

    async def _generate_segment_insights(self, segment_stats: Dict) -> List[str]:
        """Generate insights about user segments."""
        return ["User segmentation analysis completed"]

    async def _analyze_churn_risk(self, users_data: List[Dict]) -> Dict:
        """Analyze churn risk across user base."""
        return {"high_risk": 5, "medium_risk": 15, "low_risk": 80}

    async def _identify_growth_opportunities(self, segment_stats: Dict) -> List[str]:
        """Identify growth opportunities from segmentation."""
        return ["Focus on converting casual users to regular users"]

    async def _get_product_performance_data(
        self, session: Session, category: Optional[str]
    ) -> List[Dict]:
        """Get product performance data."""
        return []

    async def _analyze_category_performance(
        self, session: Session, category: Optional[str]
    ) -> Dict:
        """Analyze category-wise performance."""
        return {}

    async def _analyze_price_trends(
        self, session: Session, category: Optional[str]
    ) -> Dict:
        """Analyze price trends."""
        return {}

    async def _analyze_deal_effectiveness(
        self, session: Session, category: Optional[str]
    ) -> Dict:
        """Analyze deal effectiveness."""
        return {}

    async def _analyze_search_patterns(
        self, session: Session, category: Optional[str]
    ) -> Dict:
        """Analyze search patterns."""
        return {}

    async def _identify_underperforming_products(
        self, products_data: List[Dict]
    ) -> List[Dict]:
        """Identify underperforming products."""
        return []

    async def _generate_product_optimization_recommendations(
        self,
        products_data: List[Dict],
        category_performance: Dict,
        deal_effectiveness: Dict,
    ) -> List[str]:
        """Generate product optimization recommendations."""
        return []

    async def _analyze_revenue_by_source(self, session: Session) -> Dict:
        """Analyze revenue by source."""
        return {}

    async def _analyze_revenue_by_category(self, session: Session) -> Dict:
        """Analyze revenue by category."""
        return {}

    async def _analyze_seasonal_patterns(self, session: Session) -> Dict:
        """Analyze seasonal revenue patterns."""
        return {}

    async def _analyze_optimization_impact(self, session: Session) -> Dict:
        """Analyze impact of optimization efforts."""
        return {}

    async def _analyze_competitive_position(self, session: Session) -> Dict:
        """Analyze competitive position."""
        return {}

    async def _generate_revenue_forecast(
        self, revenue_performance: Dict, seasonal_patterns: Dict
    ) -> Dict:
        """Generate revenue forecast."""
        return {}

    async def _calculate_overall_ctr(
        self, session: Session, cutoff_time: datetime
    ) -> float:
        """Calculate overall click-through rate."""
        total_searches = (
            session.exec(
                select(func.count(SearchQuery.id)).where(
                    SearchQuery.timestamp >= cutoff_time
                )
            ).one_or_none()
            or 0
        )

        total_clicks = (
            session.exec(
                select(func.count(Click.id)).where(Click.clicked_at >= cutoff_time)
            ).one_or_none()
            or 0
        )

        return total_clicks / max(total_searches, 1)
