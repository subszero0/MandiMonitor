"""Enhanced scheduler for data enrichment and analytics."""

import asyncio
from logging import getLogger

from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlmodel import Session, select

from .cache_service import engine
from .config import settings
from .data_enrichment import ProductEnrichmentService
from .models import Watch, Price
from .scheduler import scheduler

log = getLogger(__name__)


class EnrichmentScheduler:
    """Background enrichment respecting API limits."""

    def __init__(self):
        """Initialize enrichment scheduler."""
        self.enrichment_service = ProductEnrichmentService()
        self.is_running = False

    def schedule_enrichment_jobs(self) -> None:
        """Schedule enrichment jobs with proper API rate limiting."""
        if self.is_running:
            return

        # High priority: Active watches enrichment (every 2 hours)
        scheduler.add_job(
            self._run_async_job,
            IntervalTrigger(hours=2),
            args=[self._enrich_active_watches],
            id="enrich_active_watches",
            replace_existing=True,
            max_instances=1,
        )

        # Medium priority: Historical price analysis (daily at 3 AM IST)
        scheduler.add_job(
            self._run_async_job,
            CronTrigger(hour=3, minute=0),
            args=[self._daily_price_analysis],
            id="daily_price_analysis",
            replace_existing=True,
            max_instances=1,
        )

        # Low priority: Bulk enrichment of new products (daily at 4 AM IST)
        scheduler.add_job(
            self._run_async_job,
            CronTrigger(hour=4, minute=0),
            args=[self._bulk_enrichment],
            id="bulk_enrichment",
            replace_existing=True,
            max_instances=1,
        )

        # Weekly trend analysis (Sunday at 5 AM IST)
        scheduler.add_job(
            self._run_async_job,
            CronTrigger(day_of_week=0, hour=5, minute=0),
            args=[self._weekly_trend_analysis],
            id="weekly_trends",
            replace_existing=True,
            max_instances=1,
        )

        self.is_running = True
        log.info("Enrichment scheduler jobs configured")

    def _run_async_job(self, async_func):
        """Run async function in the scheduler context."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(async_func())
            loop.close()
        except Exception as e:
            log.error("Async job failed: %s", e)

    async def _enrich_active_watches(self) -> None:
        """Enrich products from active watches with high priority."""
        try:
            log.info("Starting active watches enrichment")

            with Session(engine) as session:
                # Get ASINs from active watches
                statement = select(Watch).where(Watch.asin.is_not(None))
                active_watches = session.exec(statement).all()

                asins_to_enrich = list(
                    set(watch.asin for watch in active_watches if watch.asin)
                )

                if not asins_to_enrich:
                    log.info("No active watches with ASINs found")
                    return

                log.info("Enriching %d ASINs from active watches", len(asins_to_enrich))

                # Enrich with high priority and rate limiting
                enriched_count = 0
                for asin in asins_to_enrich:
                    try:
                        success = await self.enrichment_service.enrich_product_data(
                            asin, priority="high"
                        )
                        if success:
                            enriched_count += 1

                        # Rate limiting: wait between requests
                        await asyncio.sleep(1.2)  # Slightly over 1 second for safety

                    except Exception as e:
                        log.warning("Failed to enrich ASIN %s: %s", asin, e)
                        continue

                log.info(
                    "Active watches enrichment completed: %d/%d successful",
                    enriched_count,
                    len(asins_to_enrich),
                )

        except Exception as e:
            log.error("Active watches enrichment failed: %s", e)

    async def _daily_price_analysis(self) -> None:
        """Perform daily price analysis and pattern detection."""
        try:
            log.info("Starting daily price analysis")

            with Session(engine) as session:
                # Get ASINs with recent price data
                statement = select(Price.asin).distinct()
                recent_asins = session.exec(statement).all()

                if not recent_asins:
                    log.info("No ASINs with price data found")
                    return

                analysis_count = 0
                for asin in recent_asins:
                    try:
                        # Calculate deal quality score
                        score = (
                            await self.enrichment_service.calculate_deal_quality_score(
                                asin
                            )
                        )

                        # Detect price patterns
                        patterns = await self.enrichment_service.detect_price_patterns(
                            asin
                        )

                        if score > 0 or not patterns.get("error"):
                            analysis_count += 1

                        # Log high-quality deals
                        if score > 80:
                            log.info(
                                "High-quality deal detected: ASIN %s, score %.1f",
                                asin,
                                score,
                            )

                        # Rate limiting
                        await asyncio.sleep(0.1)  # Short delay for DB operations

                    except Exception as e:
                        log.warning("Failed to analyze ASIN %s: %s", asin, e)
                        continue

                log.info(
                    "Daily price analysis completed: %d ASINs analyzed", analysis_count
                )

        except Exception as e:
            log.error("Daily price analysis failed: %s", e)

    async def _bulk_enrichment(self) -> None:
        """Perform bulk enrichment of products with low priority."""
        try:
            log.info("Starting bulk enrichment")

            with Session(engine) as session:
                # Find ASINs that need enrichment (exist in Price but not in Product)
                from .enhanced_models import Product

                price_statement = select(Price.asin).distinct()
                product_statement = select(Product.asin)

                price_asins = set(session.exec(price_statement).all())
                existing_product_asins = set(session.exec(product_statement).all())

                asins_to_enrich = list(price_asins - existing_product_asins)

                if not asins_to_enrich:
                    log.info("No ASINs need bulk enrichment")
                    return

                # Limit bulk enrichment to avoid quota exhaustion
                max_bulk_items = min(
                    len(asins_to_enrich), settings.ENRICHMENT_BATCH_SIZE * 2
                )
                asins_to_enrich = asins_to_enrich[:max_bulk_items]

                log.info("Bulk enriching %d ASINs", len(asins_to_enrich))

                enriched_count = 0
                for asin in asins_to_enrich:
                    try:
                        success = await self.enrichment_service.enrich_product_data(
                            asin, priority="low"
                        )
                        if success:
                            enriched_count += 1

                        # Longer rate limiting for bulk operations
                        await asyncio.sleep(2.0)

                    except Exception as e:
                        log.warning("Failed to bulk enrich ASIN %s: %s", asin, e)
                        continue

                log.info(
                    "Bulk enrichment completed: %d/%d successful",
                    enriched_count,
                    len(asins_to_enrich),
                )

        except Exception as e:
            log.error("Bulk enrichment failed: %s", e)

    async def _weekly_trend_analysis(self) -> None:
        """Perform weekly trend analysis across all products."""
        try:
            log.info("Starting weekly trend analysis")

            with Session(engine) as session:
                from .enhanced_models import Product

                # Get all products for trend analysis
                statement = select(Product.asin)
                product_asins = session.exec(statement).all()

                if not product_asins:
                    log.info("No products found for trend analysis")
                    return

                trends_analyzed = 0
                high_volatility_products = []

                for asin in product_asins:
                    try:
                        patterns = await self.enrichment_service.detect_price_patterns(
                            asin, days=30
                        )

                        if not patterns.get("error"):
                            trends_analyzed += 1

                            # Identify high volatility products
                            volatility = patterns.get("price_volatility", 0)
                            if volatility > 1000:  # High volatility threshold (₹10)
                                high_volatility_products.append(
                                    {
                                        "asin": asin,
                                        "volatility": volatility,
                                        "trend": patterns.get("trend"),
                                    }
                                )

                        # Rate limiting for analysis
                        await asyncio.sleep(0.2)

                    except Exception as e:
                        log.warning("Failed to analyze trends for ASIN %s: %s", asin, e)
                        continue

                log.info(
                    "Weekly trend analysis completed: %d ASINs analyzed",
                    trends_analyzed,
                )

                if high_volatility_products:
                    log.info(
                        "High volatility products detected: %d",
                        len(high_volatility_products),
                    )
                    for product in high_volatility_products[:5]:  # Log top 5
                        log.info(
                            "High volatility: ASIN %s, volatility %.2f, trend %s",
                            product["asin"],
                            product["volatility"],
                            product["trend"],
                        )

        except Exception as e:
            log.error("Weekly trend analysis failed: %s", e)


# Global enrichment scheduler instance
_enrichment_scheduler = None


def get_enrichment_scheduler() -> EnrichmentScheduler:
    """Get the global enrichment scheduler instance."""
    global _enrichment_scheduler
    if _enrichment_scheduler is None:
        _enrichment_scheduler = EnrichmentScheduler()
    return _enrichment_scheduler


def initialize_enrichment_scheduler() -> None:
    """Initialize and start enrichment scheduling."""
    if settings.ENABLE_ENHANCED_MODELS:
        enrichment_scheduler = get_enrichment_scheduler()
        enrichment_scheduler.schedule_enrichment_jobs()
        log.info("Enrichment scheduler initialized")
    else:
        log.info("Enhanced models disabled, skipping enrichment scheduler")
