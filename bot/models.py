"""SQLModel ORM classes for MandiMonitor Bot."""

from datetime import datetime

from sqlmodel import Field, SQLModel


class Cache(SQLModel, table=True):
    """Cache model for 24h price caching."""

    asin: str = Field(primary_key=True)
    price: int
    fetched_at: datetime = Field(default_factory=datetime.utcnow)


class User(SQLModel, table=True):
    """User model for bot users."""

    id: int = Field(primary_key=True)
    tg_user_id: int = Field(unique=True)
    first_seen: datetime = Field(default_factory=datetime.utcnow)


class Watch(SQLModel, table=True):
    """Watch model for price monitoring requests."""

    id: int = Field(primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    asin: str | None = None
    keywords: str
    brand: str | None = None
    max_price: int | None = None
    min_discount: int | None = None
    mode: str = Field(default="daily")  # "daily" or "rt" for real-time
    created: datetime = Field(default_factory=datetime.utcnow)


class Price(SQLModel, table=True):
    """Price model for storing price history."""

    id: int = Field(primary_key=True)
    watch_id: int = Field(foreign_key="watch.id")
    asin: str
    price: int
    source: str = Field(default="paapi")  # "paapi" or "scraper"
    fetched_at: datetime = Field(default_factory=datetime.utcnow)


class Click(SQLModel, table=True):
    """Click model for tracking affiliate link clicks."""

    id: int = Field(primary_key=True)
    watch_id: int = Field(foreign_key="watch.id")
    asin: str
    clicked_at: datetime = Field(default_factory=datetime.utcnow)
