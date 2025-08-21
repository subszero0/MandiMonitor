"""Data enrichment service for comprehensive product information."""

import statistics
from datetime import datetime, timedelta
from logging import getLogger
from typing import Dict, List

from sqlmodel import Session, select

from .cache_service import engine
from .config import settings
from .enhanced_models import (
    Product,
    ProductOffers,
    CustomerReviews,
    BrowseNode,
    ProductBrowseNode,
    PriceHistory,
)
from .errors import QuotaExceededError
from .paapi_enhanced import get_item_detailed, get_resources_for_context

log = getLogger(__name__)


class ProductEnrichmentService:
    """Service to enrich product data respecting API limits."""

    def __init__(self):
        """Initialize enrichment service."""
        self.batch_size = settings.ENRICHMENT_BATCH_SIZE

    async def enrich_product_data(self, asin: str, priority: str = "normal") -> bool:
        """Enrich product data with comprehensive PA-API information.

        Args:
        ----
            asin: Product ASIN to enrich
            priority: Request priority ("high", "normal", "low")

        Returns:
        -------
            True if enrichment successful, False otherwise
        """
        try:
            log.info("Starting product enrichment for ASIN: %s", asin)

            # Get comprehensive data from PA-API
            resources = get_resources_for_context("data_enrichment")
            product_data = await get_item_detailed(asin, resources, priority)

            # Store enriched data in database
            await self._store_enriched_data(asin, product_data)

            log.info("Product enrichment completed for ASIN: %s", asin)
            return True

        except QuotaExceededError:
            log.warning("Quota exceeded during enrichment for %s", asin)
            await self._schedule_delayed_enrichment(asin, priority)
            return False
        except Exception as e:
            log.error("Enrichment failed for ASIN %s: %s", asin, e)
            return False

    async def _store_enriched_data(self, asin: str, product_data: Dict) -> None:
        """Store enriched product data in database."""
        with Session(engine) as session:
            try:
                # Store/update Product record
                await self._store_product_record(session, asin, product_data)

                # Store/update ProductOffers record
                await self._store_product_offers(session, asin, product_data)

                # Store/update CustomerReviews record
                await self._store_customer_reviews(session, asin, product_data)

                # Store browse node relationships
                await self._store_browse_node_relationships(session, asin, product_data)

                # Store price history
                await self._store_price_history(session, asin, product_data)

                session.commit()
                log.debug("Stored enriched data for ASIN: %s", asin)

            except Exception as e:
                session.rollback()
                log.error("Failed to store enriched data for ASIN %s: %s", asin, e)
                raise

    async def _store_product_record(
        self, session: Session, asin: str, data: Dict
    ) -> None:
        """Store or update Product record."""
        # Check if product exists
        statement = select(Product).where(Product.asin == asin)
        existing_product = session.exec(statement).first()

        if existing_product:
            # Update existing product
            existing_product.title = data.get("title", existing_product.title)
            existing_product.brand = data.get("brand")
            existing_product.manufacturer = data.get("manufacturer")
            existing_product.product_group = data.get("product_group")
            existing_product.binding = data.get("binding")
            existing_product.features_list = data.get("features", [])
            existing_product.color = data.get("color")
            existing_product.size = data.get("size")
            existing_product.is_adult_product = data.get("is_adult_product", False)
            existing_product.ean = data.get("ean")
            existing_product.isbn = data.get("isbn")
            existing_product.upc = data.get("upc")
            existing_product.languages_list = data.get("languages", [])
            existing_product.page_count = data.get("page_count")
            existing_product.small_image = data.get("images", {}).get("small")
            existing_product.medium_image = data.get("images", {}).get("medium")
            existing_product.large_image = data.get("images", {}).get("large")
            existing_product.variant_images_list = data.get("images", {}).get(
                "variants", []
            )
            existing_product.last_updated = datetime.utcnow()
        else:
            # Create new product
            product = Product(
                asin=asin,
                title=data.get("title", ""),
                brand=data.get("brand"),
                manufacturer=data.get("manufacturer"),
                product_group=data.get("product_group"),
                binding=data.get("binding"),
                color=data.get("color"),
                size=data.get("size"),
                is_adult_product=data.get("is_adult_product", False),
                ean=data.get("ean"),
                isbn=data.get("isbn"),
                upc=data.get("upc"),
                page_count=data.get("page_count"),
                small_image=data.get("images", {}).get("small"),
                medium_image=data.get("images", {}).get("medium"),
                large_image=data.get("images", {}).get("large"),
            )
            product.features_list = data.get("features", [])
            product.languages_list = data.get("languages", [])
            product.variant_images_list = data.get("images", {}).get("variants", [])

            session.add(product)

    async def _store_product_offers(
        self, session: Session, asin: str, data: Dict
    ) -> None:
        """Store or update ProductOffers record."""
        offers_data = data.get("offers", {})

        if not offers_data.get("price"):
            return  # No pricing information available

        # Create new offer record (we store historical offers)
        offer = ProductOffers(
            asin=asin,
            price=offers_data["price"],
            list_price=offers_data.get("list_price"),
            savings_amount=offers_data.get("savings_amount"),
            savings_percentage=offers_data.get("savings_percentage"),
            availability_type=offers_data.get("availability_type"),
            availability_message=offers_data.get("availability_message"),
            condition=offers_data.get("condition", "New"),
            is_prime_eligible=offers_data.get("is_prime_eligible", False),
            is_amazon_fulfilled=offers_data.get("is_amazon_fulfilled", False),
            merchant_name=offers_data.get("merchant_name"),
        )
        offer.promotions_list = offers_data.get("promotions", [])

        session.add(offer)

    async def _store_customer_reviews(
        self, session: Session, asin: str, data: Dict
    ) -> None:
        """Store or update CustomerReviews record."""
        reviews_data = data.get("reviews", {})

        if not reviews_data.get("count"):
            return  # No review information

        # Check if reviews record exists
        statement = select(CustomerReviews).where(CustomerReviews.asin == asin)
        existing_reviews = session.exec(statement).first()

        if existing_reviews:
            # Update existing reviews
            existing_reviews.review_count = reviews_data["count"]
            existing_reviews.average_rating = reviews_data.get("average_rating")
            existing_reviews.last_updated = datetime.utcnow()
        else:
            # Create new reviews record
            reviews = CustomerReviews(
                asin=asin,
                review_count=reviews_data["count"],
                average_rating=reviews_data.get("average_rating"),
            )
            session.add(reviews)

    async def _store_browse_node_relationships(
        self, session: Session, asin: str, data: Dict
    ) -> None:
        """Store browse node relationships."""
        browse_nodes = data.get("browse_nodes", [])

        for node_data in browse_nodes:
            node_id = node_data.get("id")
            if not node_id:
                continue

            # Store/update browse node
            statement = select(BrowseNode).where(BrowseNode.id == node_id)
            existing_node = session.exec(statement).first()

            if not existing_node:
                browse_node = BrowseNode(
                    id=node_id,
                    name=node_data.get("name", ""),
                    sales_rank=node_data.get("sales_rank"),
                )
                session.add(browse_node)

            # Store product-browse node relationship
            statement = select(ProductBrowseNode).where(
                ProductBrowseNode.product_asin == asin,
                ProductBrowseNode.browse_node_id == node_id,
            )
            existing_relationship = session.exec(statement).first()

            if not existing_relationship:
                relationship = ProductBrowseNode(
                    product_asin=asin, browse_node_id=node_id
                )
                session.add(relationship)

    async def _store_price_history(
        self, session: Session, asin: str, data: Dict
    ) -> None:
        """Store price history record."""
        offers_data = data.get("offers", {})

        if not offers_data.get("price"):
            return

        price_history = PriceHistory(
            asin=asin,
            price=offers_data["price"],
            list_price=offers_data.get("list_price"),
            discount_percentage=offers_data.get("savings_percentage"),
            availability=offers_data.get("availability_type"),
            source="paapi",
        )

        session.add(price_history)

    async def _schedule_delayed_enrichment(self, asin: str, priority: str) -> None:
        """Schedule enrichment for later when quota is available."""
        # This would integrate with the scheduler to retry later
        # For now, just log the delay
        delay_minutes = 60 if priority == "low" else 30 if priority == "normal" else 10
        log.info(
            "Scheduling delayed enrichment for %s in %d minutes", asin, delay_minutes
        )

    async def calculate_deal_quality_score(self, asin: str) -> float:
        """Calculate deal quality score (0-100) based on multiple factors.

        Args:
        ----
            asin: Product ASIN to analyze

        Returns:
        -------
            Deal quality score from 0-100
        """
        with Session(engine) as session:
            try:
                # Get product and price history
                product = session.get(Product, asin)
                if not product:
                    return 0.0

                # Get current offer
                offer_statement = (
                    select(ProductOffers)
                    .where(ProductOffers.asin == asin)
                    .order_by(ProductOffers.fetched_at.desc())
                )
                current_offer = session.exec(offer_statement).first()

                if not current_offer:
                    return 0.0

                score = 0.0

                # Historical price factor (40%)
                price_score = await self._calculate_price_score(
                    session, asin, current_offer.price
                )
                score += price_score * 0.4

                # Review quality factor (30%)
                review_score = await self._calculate_review_score(session, asin)
                score += review_score * 0.3

                # Availability factor (20%)
                availability_score = await self._calculate_availability_score(
                    current_offer
                )
                score += availability_score * 0.2

                # Discount factor (10%)
                discount_score = await self._calculate_discount_score(current_offer)
                score += discount_score * 0.1

                return min(100.0, max(0.0, score))

            except Exception as e:
                log.error("Failed to calculate deal quality for %s: %s", asin, e)
                return 0.0

    async def _calculate_price_score(
        self, session: Session, asin: str, current_price: int
    ) -> float:
        """Calculate price score based on historical data."""
        try:
            # Get price history for last 90 days
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=90)

            statement = select(PriceHistory).where(
                PriceHistory.asin == asin, PriceHistory.timestamp >= start_date
            )
            price_history = session.exec(statement).all()

            if not price_history:
                return 50.0  # Neutral score if no history

            prices = [p.price for p in price_history]

            # Calculate percentile of current price (lower price = higher score)
            if len(prices) >= 2:
                percentile = sum(1 for p in prices if p > current_price) / len(prices)
                return percentile * 100

            return 50.0

        except Exception as e:
            log.error("Failed to calculate price score: %s", e)
            return 50.0

    async def _calculate_review_score(self, session: Session, asin: str) -> float:
        """Calculate review quality score."""
        try:
            reviews = session.get(CustomerReviews, asin)
            if not reviews or not reviews.average_rating:
                return 50.0  # Neutral score if no reviews

            # Score based on rating (1-5 scale)
            rating_score = (reviews.average_rating / 5.0) * 100

            # Boost for high review count
            if reviews.review_count > 100:
                rating_score *= 1.1
            elif reviews.review_count > 1000:
                rating_score *= 1.2

            return min(100.0, rating_score)

        except Exception as e:
            log.error("Failed to calculate review score: %s", e)
            return 50.0

    async def _calculate_availability_score(self, offer: ProductOffers) -> float:
        """Calculate availability score."""
        try:
            if offer.availability_type == "InStock":
                score = 100.0
            elif offer.availability_type == "OutOfStock":
                score = 0.0
            else:
                score = 50.0  # Unknown availability

            # Boost for Prime eligibility
            if offer.is_prime_eligible:
                score *= 1.1

            # Boost for Amazon fulfillment
            if offer.is_amazon_fulfilled:
                score *= 1.05

            return min(100.0, score)

        except Exception as e:
            log.error("Failed to calculate availability score: %s", e)
            return 50.0

    async def _calculate_discount_score(self, offer: ProductOffers) -> float:
        """Calculate discount score."""
        try:
            if not offer.savings_percentage:
                return 0.0

            # Score based on discount percentage
            if offer.savings_percentage >= 50:
                return 100.0
            elif offer.savings_percentage >= 30:
                return 80.0
            elif offer.savings_percentage >= 20:
                return 60.0
            elif offer.savings_percentage >= 10:
                return 40.0
            else:
                return 20.0

        except Exception as e:
            log.error("Failed to calculate discount score: %s", e)
            return 0.0

    async def detect_price_patterns(self, asin: str, days: int = 90) -> Dict:
        """Analyze price trends and patterns.

        Args:
        ----
            asin: Product ASIN to analyze
            days: Number of days to analyze

        Returns:
        -------
            Dict with price pattern analysis
        """
        with Session(engine) as session:
            try:
                # Get price history
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=days)

                statement = (
                    select(PriceHistory)
                    .where(
                        PriceHistory.asin == asin, PriceHistory.timestamp >= start_date
                    )
                    .order_by(PriceHistory.timestamp)
                )

                price_history = session.exec(statement).all()

                if len(price_history) < 2:
                    return {"error": "Insufficient price history"}

                prices = [p.price for p in price_history]

                # Calculate trend metrics
                current_price = prices[-1]
                min_price = min(prices)
                max_price = max(prices)
                avg_price = statistics.mean(prices)
                price_volatility = statistics.stdev(prices) if len(prices) > 1 else 0

                # Detect trend direction
                if len(prices) >= 10:
                    recent_avg = statistics.mean(prices[-5:])
                    older_avg = statistics.mean(prices[-10:-5])
                    trend = (
                        "increasing"
                        if recent_avg > older_avg
                        else "decreasing" if recent_avg < older_avg else "stable"
                    )
                else:
                    trend = "insufficient_data"

                # Calculate drop probability
                drop_probability = await self._calculate_drop_probability(prices)

                return {
                    "current_price": current_price,
                    "min_price": min_price,
                    "max_price": max_price,
                    "average_price": avg_price,
                    "price_volatility": price_volatility,
                    "trend": trend,
                    "drop_probability": drop_probability,
                    "price_percentile": (
                        sum(1 for p in prices if p > current_price) / len(prices)
                    )
                    * 100,
                    "analysis_period": f"{days} days",
                    "data_points": len(price_history),
                }

            except Exception as e:
                log.error("Failed to detect price patterns for %s: %s", asin, e)
                return {"error": str(e)}

    async def _calculate_drop_probability(self, prices: List[int]) -> float:
        """Calculate probability of price drop based on historical patterns."""
        try:
            if len(prices) < 10:
                return 0.5  # Neutral probability

            current_price = prices[-1]

            # Count how many times price dropped from similar levels
            drops = 0
            total_comparisons = 0

            for i in range(len(prices) - 1):
                if abs(prices[i] - current_price) / current_price < 0.05:  # Within 5%
                    total_comparisons += 1
                    if i + 1 < len(prices) and prices[i + 1] < prices[i]:
                        drops += 1

            if total_comparisons > 0:
                return drops / total_comparisons

            return 0.5

        except Exception as e:
            log.error("Failed to calculate drop probability: %s", e)
            return 0.5
