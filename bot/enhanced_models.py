"""Enhanced SQLModel classes for comprehensive PA-API data storage."""

from __future__ import annotations

import json
from datetime import datetime
from typing import List, Optional

from sqlmodel import Field, SQLModel


class Product(SQLModel, table=True):
    """Rich product information from PA-API."""

    asin: str = Field(primary_key=True)
    title: str
    brand: Optional[str] = None
    manufacturer: Optional[str] = None
    product_group: Optional[str] = None  # Electronics, Books, etc.
    binding: Optional[str] = None  # Paperback, Hardcover, etc.

    # ItemInfo.Features
    features: Optional[str] = None  # JSON array of features

    # ItemInfo.ProductInfo
    color: Optional[str] = None
    size: Optional[str] = None
    item_dimensions: Optional[str] = None  # JSON object
    item_weight: Optional[str] = None
    is_adult_product: bool = False

    # ItemInfo.TechnicalInfo
    technical_details: Optional[str] = None  # JSON object

    # External IDs
    ean: Optional[str] = None
    isbn: Optional[str] = None
    upc: Optional[str] = None

    # Content Info
    languages: Optional[str] = None  # JSON array
    page_count: Optional[int] = None
    publication_date: Optional[datetime] = None

    # Images
    small_image: Optional[str] = None
    medium_image: Optional[str] = None
    large_image: Optional[str] = None
    variant_images: Optional[str] = None  # JSON array

    # Last updated
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    @property
    def features_list(self) -> List[str]:
        """Get features as Python list."""
        if not self.features:
            return []
        try:
            return json.loads(self.features)
        except (json.JSONDecodeError, TypeError):
            return []

    @features_list.setter
    def features_list(self, value: List[str]) -> None:
        """Set features from Python list."""
        self.features = json.dumps(value) if value else None

    @property
    def languages_list(self) -> List[str]:
        """Get languages as Python list."""
        if not self.languages:
            return []
        try:
            return json.loads(self.languages)
        except (json.JSONDecodeError, TypeError):
            return []

    @languages_list.setter
    def languages_list(self, value: List[str]) -> None:
        """Set languages from Python list."""
        self.languages = json.dumps(value) if value else None

    @property
    def variant_images_list(self) -> List[str]:
        """Get variant images as Python list."""
        if not self.variant_images:
            return []
        try:
            return json.loads(self.variant_images)
        except (json.JSONDecodeError, TypeError):
            return []

    @variant_images_list.setter
    def variant_images_list(self, value: List[str]) -> None:
        """Set variant images from Python list."""
        self.variant_images = json.dumps(value) if value else None


class ProductOffers(SQLModel, table=True):
    """Detailed offer information."""

    id: int = Field(primary_key=True)
    asin: str = Field(foreign_key="product.asin")

    # Pricing
    price: int  # Current price in paise
    savings_amount: Optional[int] = None
    savings_percentage: Optional[int] = None
    list_price: Optional[int] = None  # Original/MRP price

    # Availability
    availability_type: Optional[str] = None  # InStock, OutOfStock, etc.
    availability_message: Optional[str] = None
    max_order_quantity: Optional[int] = None
    min_order_quantity: Optional[int] = None

    # Condition
    condition: str = "New"  # New, Used, Refurbished
    sub_condition: Optional[str] = None

    # Delivery
    is_amazon_fulfilled: bool = False
    is_prime_eligible: bool = False
    is_free_shipping_eligible: bool = False
    shipping_charges: Optional[int] = None

    # Merchant
    merchant_name: Optional[str] = None
    is_buy_box_winner: bool = False

    # Promotions
    promotions: Optional[str] = None  # JSON array

    # Program Eligibility
    is_prime_exclusive: bool = False
    is_prime_pantry: bool = False

    fetched_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def promotions_list(self) -> List[dict]:
        """Get promotions as Python list."""
        if not self.promotions:
            return []
        try:
            return json.loads(self.promotions)
        except (json.JSONDecodeError, TypeError):
            return []

    @promotions_list.setter
    def promotions_list(self, value: List[dict]) -> None:
        """Set promotions from Python list."""
        self.promotions = json.dumps(value) if value else None


class CustomerReviews(SQLModel, table=True):
    """Customer review data."""

    asin: str = Field(primary_key=True, foreign_key="product.asin")
    review_count: int = 0
    average_rating: Optional[float] = None  # 4.2 out of 5
    rating_distribution: Optional[str] = None  # JSON: {5: 120, 4: 45, ...}
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    @property
    def rating_distribution_dict(self) -> dict:
        """Get rating distribution as Python dict."""
        if not self.rating_distribution:
            return {}
        try:
            return json.loads(self.rating_distribution)
        except (json.JSONDecodeError, TypeError):
            return {}

    @rating_distribution_dict.setter
    def rating_distribution_dict(self, value: dict) -> None:
        """Set rating distribution from Python dict."""
        self.rating_distribution = json.dumps(value) if value else None


class BrowseNode(SQLModel, table=True):
    """Amazon category hierarchy."""

    id: int = Field(primary_key=True)
    name: str
    parent_id: Optional[int] = None
    sales_rank: Optional[int] = None
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class ProductBrowseNode(SQLModel, table=True):
    """Product-Category mapping."""

    product_asin: str = Field(foreign_key="product.asin", primary_key=True)
    browse_node_id: int = Field(foreign_key="browsenode.id", primary_key=True)


class ProductVariation(SQLModel, table=True):
    """Product variations (colors, sizes, etc.)."""

    id: int = Field(primary_key=True)
    parent_asin: str = Field(foreign_key="product.asin")
    child_asin: str = Field(foreign_key="product.asin")
    variation_type: str  # Color, Size, Storage, etc.
    variation_value: str  # Red, Large, 128GB, etc.


class PriceHistory(SQLModel, table=True):
    """Enhanced price tracking."""

    id: int = Field(primary_key=True)
    asin: str = Field(foreign_key="product.asin")
    price: int
    list_price: Optional[int] = None
    discount_percentage: Optional[int] = None
    availability: Optional[str] = None
    source: str = "paapi"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SearchQuery(SQLModel, table=True):
    """Track user search patterns."""

    id: int = Field(primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    query: str
    search_index: Optional[str] = None  # Category searched
    results_count: int = 0
    clicked_asin: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DealAlert(SQLModel, table=True):
    """Advanced deal notifications."""

    id: int = Field(primary_key=True)
    watch_id: int = Field(foreign_key="watch.id")
    asin: str
    alert_type: str  # price_drop, stock_alert, deal_quality, seasonal
    previous_price: Optional[int] = None
    current_price: int
    discount_percentage: Optional[int] = None
    deal_quality_score: Optional[float] = None  # 0-100
    sent_at: datetime = Field(default_factory=datetime.utcnow)
