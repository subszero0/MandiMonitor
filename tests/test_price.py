"""Tests for price fetching system."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from sqlmodel import Session, create_engine

from bot.cache_service import get_price
from bot.models import Cache
from bot.errors import QuotaExceededError


@pytest.fixture
def in_memory_db():
    """Create in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )

    # Patch the engine in cache_service
    with patch("bot.cache_service.engine", engine):
        # Initialize tables
        from bot.models import SQLModel

        SQLModel.metadata.create_all(engine)
        yield engine


def test_get_price_from_paapi(in_memory_db):
    """Test price fetching from PA-API."""
    mock_item_data = {
        "price": 12300,  # 123.00 rupees in paise
        "title": "Test Product",
        "image": "https://example.com/image.jpg",
    }

    with patch(
        "bot.cache_service.get_item", new=AsyncMock(return_value=mock_item_data)
    ):
        price = get_price("B0ABC123")
        assert price == 12300


def test_get_price_fallback_to_scraper(in_memory_db):
    """Test fallback to scraper when PA-API fails."""
    with patch(
        "bot.cache_service.get_item", new=AsyncMock(side_effect=QuotaExceededError())
    ):
        with patch("bot.cache_service.scrape_price", return_value=15600):
            price = get_price("B0ABC123")
            assert price == 15600


def test_get_price_from_cache(in_memory_db):
    """Test price retrieval from cache."""
    # Insert cached entry
    with Session(in_memory_db) as session:
        cache_entry = Cache(
            asin="B0CACHED",
            price=20000,
            fetched_at=datetime.utcnow() - timedelta(hours=1),  # 1 hour ago
        )
        session.add(cache_entry)
        session.commit()

    # Mock to ensure PA-API is not called
    with patch("bot.cache_service.get_item", new=AsyncMock()) as mock_paapi:
        price = get_price("B0CACHED")
        assert price == 20000
        mock_paapi.assert_not_called()


def test_get_price_cache_expired(in_memory_db):
    """Test price fetching when cache is expired."""
    # Insert expired cache entry
    with Session(in_memory_db) as session:
        cache_entry = Cache(
            asin="B0EXPIRED",
            price=18000,
            fetched_at=datetime.utcnow() - timedelta(hours=25),  # 25 hours ago
        )
        session.add(cache_entry)
        session.commit()

    mock_item_data = {"price": 19000, "title": "Updated Product", "image": "url"}

    with patch(
        "bot.cache_service.get_item", new=AsyncMock(return_value=mock_item_data)
    ):
        price = get_price("B0EXPIRED")
        assert price == 19000


def test_get_price_all_sources_fail_with_stale_cache(in_memory_db):
    """Test using stale cache when all sources fail."""
    # Insert stale cache entry
    with Session(in_memory_db) as session:
        cache_entry = Cache(
            asin="B0STALE",
            price=25000,
            fetched_at=datetime.utcnow() - timedelta(hours=30),
        )
        session.add(cache_entry)
        session.commit()

    with patch(
        "bot.cache_service.get_item",
        new=AsyncMock(side_effect=Exception("PA-API down")),
    ):
        with patch(
            "bot.cache_service.scrape_price", side_effect=Exception("Scraper failed")
        ):
            price = get_price("B0STALE")
            assert price == 25000


def test_get_price_all_sources_fail_no_cache(in_memory_db):
    """Test error when all sources fail and no cache exists."""
    with patch(
        "bot.cache_service.get_item",
        new=AsyncMock(side_effect=Exception("PA-API down")),
    ):
        with patch(
            "bot.cache_service.scrape_price", side_effect=Exception("Scraper failed")
        ):
            with pytest.raises(ValueError, match="Could not fetch price"):
                get_price("B0NOTFOUND")
