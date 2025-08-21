"""Migration 001: Enhanced Models for PA-API Integration.

This migration adds enhanced models while preserving existing data.
It creates new tables for rich product information without breaking
existing Cache, User, Watch, Price, and Click tables.
"""

import asyncio
from logging import getLogger

from sqlmodel import Session, select

from ..cache_service import engine
from ..models import Price
from ..enhanced_models import (
    Product,
    ProductOffers,
    CustomerReviews,
    BrowseNode,
    ProductBrowseNode,
    ProductVariation,
    PriceHistory,
    SearchQuery,
    DealAlert,
)

log = getLogger(__name__)


class Migration001:
    """Migration to add enhanced models."""

    def __init__(self):
        self.engine = engine

    async def upgrade(self) -> bool:
        """Apply the migration (create new tables)."""
        try:
            log.info("Starting Migration 001: Enhanced Models")

            # Create new enhanced tables
            await self._create_enhanced_tables()

            # Migrate existing price data to PriceHistory
            await self._migrate_price_data()

            log.info("Migration 001 completed successfully")
            return True

        except Exception as e:
            log.error("Migration 001 failed: %s", e)
            return False

    async def downgrade(self) -> bool:
        """Rollback the migration (drop new tables)."""
        try:
            log.info("Rolling back Migration 001: Enhanced Models")

            # Drop enhanced tables (existing tables remain untouched)
            enhanced_tables = [
                DealAlert,
                SearchQuery,
                PriceHistory,
                ProductVariation,
                ProductBrowseNode,
                BrowseNode,
                CustomerReviews,
                ProductOffers,
                Product,
            ]

            for table in enhanced_tables:
                try:
                    table.__table__.drop(self.engine, checkfirst=True)
                    log.info("Dropped table: %s", table.__tablename__)
                except Exception as e:
                    log.warning("Failed to drop table %s: %s", table.__tablename__, e)

            log.info("Migration 001 rollback completed")
            return True

        except Exception as e:
            log.error("Migration 001 rollback failed: %s", e)
            return False

    async def _create_enhanced_tables(self) -> None:
        """Create all enhanced model tables."""
        # Create enhanced tables
        enhanced_tables = [
            Product,
            ProductOffers,
            CustomerReviews,
            BrowseNode,
            ProductBrowseNode,
            ProductVariation,
            PriceHistory,
            SearchQuery,
            DealAlert,
        ]

        for table in enhanced_tables:
            try:
                table.__table__.create(self.engine, checkfirst=True)
                log.info("Created table: %s", table.__tablename__)
            except Exception as e:
                log.warning(
                    "Table %s already exists or creation failed: %s",
                    table.__tablename__,
                    e,
                )

    async def _migrate_price_data(self) -> None:
        """Migrate existing Price data to PriceHistory table."""
        with Session(self.engine) as session:
            try:
                # Get all existing price records
                statement = select(Price)
                existing_prices = session.exec(statement).all()

                migrated_count = 0
                for price_record in existing_prices:
                    # Create corresponding PriceHistory record
                    price_history = PriceHistory(
                        asin=price_record.asin,
                        price=price_record.price,
                        source=price_record.source,
                        timestamp=price_record.fetched_at,
                    )

                    session.add(price_history)
                    migrated_count += 1

                session.commit()
                log.info("Migrated %d price records to PriceHistory", migrated_count)

            except Exception as e:
                session.rollback()
                log.error("Failed to migrate price data: %s", e)
                raise


async def run_migration_001():
    """Run Migration 001."""
    migration = Migration001()
    success = await migration.upgrade()
    if not success:
        raise RuntimeError("Migration 001 failed")


async def rollback_migration_001():
    """Rollback Migration 001."""
    migration = Migration001()
    success = await migration.downgrade()
    if not success:
        raise RuntimeError("Migration 001 rollback failed")


if __name__ == "__main__":
    # Run migration when executed directly
    asyncio.run(run_migration_001())
