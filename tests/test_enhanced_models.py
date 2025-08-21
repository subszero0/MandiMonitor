"""Tests for enhanced SQLModel classes."""

import json
from datetime import datetime

import pytest
from sqlmodel import Session, SQLModel, create_engine

from bot.enhanced_models import (
    Product, ProductOffers, CustomerReviews, BrowseNode,
    ProductBrowseNode, ProductVariation, PriceHistory,
    SearchQuery, DealAlert
)


@pytest.fixture
def test_engine():
    """Create test database engine."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def test_session(test_engine):
    """Create test database session."""
    with Session(test_engine) as session:
        yield session


def test_product_model_creation(test_session):
    """Test Product model with all fields."""
    product = Product(
        asin="B08N5WRWNW",
        title="Test Product",
        brand="Test Brand",
        manufacturer="Test Manufacturer",
        product_group="Electronics",
        binding="Paperback",
        color="Red",
        size="Large",
        is_adult_product=False,
        ean="1234567890123",
        isbn="978-0123456789",
        upc="012345678901",
        page_count=200,
        small_image="https://example.com/small.jpg",
        medium_image="https://example.com/medium.jpg",
        large_image="https://example.com/large.jpg"
    )
    
    # Test JSON field setters
    product.features_list = ["Feature 1", "Feature 2", "Feature 3"]
    product.languages_list = ["English", "Hindi"]
    product.variant_images_list = ["https://example.com/var1.jpg", "https://example.com/var2.jpg"]
    
    test_session.add(product)
    test_session.commit()
    
    # Retrieve and verify
    retrieved = test_session.get(Product, "B08N5WRWNW")
    assert retrieved is not None
    assert retrieved.title == "Test Product"
    assert retrieved.brand == "Test Brand"
    assert retrieved.features_list == ["Feature 1", "Feature 2", "Feature 3"]
    assert retrieved.languages_list == ["English", "Hindi"]
    assert len(retrieved.variant_images_list) == 2


def test_product_features_serialization(test_session):
    """Test JSON field serialization/deserialization."""
    product = Product(
        asin="B08N5WRWNW",
        title="Test Product"
    )
    
    # Test empty features
    assert product.features_list == []
    
    # Test setting features
    features = ["Wireless", "Bluetooth", "USB-C"]
    product.features_list = features
    
    # Verify JSON serialization
    assert product.features is not None
    assert json.loads(product.features) == features
    
    # Test setting to None
    product.features_list = []
    assert product.features is None or product.features == "[]"


def test_product_offers_relationship(test_session):
    """Test Product-ProductOffers relationship."""
    # Create product
    product = Product(
        asin="B08N5WRWNW",
        title="Test Product"
    )
    test_session.add(product)
    test_session.flush()
    
    # Create offer
    offer = ProductOffers(
        asin="B08N5WRWNW",
        price=2500,  # ₹25.00 in paise
        list_price=3000,
        savings_amount=500,
        savings_percentage=17,
        availability_type="InStock",
        condition="New",
        is_prime_eligible=True,
        is_amazon_fulfilled=True,
        merchant_name="Amazon"
    )
    
    # Test promotions JSON field
    offer.promotions_list = [
        {"type": "discount", "display_name": "20% off"},
        {"type": "coupon", "display_name": "Extra ₹5 off"}
    ]
    
    test_session.add(offer)
    test_session.commit()
    
    # Verify
    retrieved_offer = test_session.query(ProductOffers).filter_by(asin="B08N5WRWNW").first()
    assert retrieved_offer is not None
    assert retrieved_offer.price == 2500
    assert retrieved_offer.savings_percentage == 17
    assert len(retrieved_offer.promotions_list) == 2


def test_customer_reviews_model(test_session):
    """Test CustomerReviews model."""
    # Create product first
    product = Product(asin="B08N5WRWNW", title="Test Product")
    test_session.add(product)
    test_session.flush()
    
    # Create reviews
    reviews = CustomerReviews(
        asin="B08N5WRWNW",
        review_count=150,
        average_rating=4.3
    )
    
    # Test rating distribution
    reviews.rating_distribution_dict = {
        "5": 80,
        "4": 40,
        "3": 20,
        "2": 7,
        "1": 3
    }
    
    test_session.add(reviews)
    test_session.commit()
    
    # Verify
    retrieved = test_session.get(CustomerReviews, "B08N5WRWNW")
    assert retrieved is not None
    assert retrieved.review_count == 150
    assert retrieved.average_rating == 4.3
    assert retrieved.rating_distribution_dict["5"] == 80


def test_browse_node_hierarchy(test_session):
    """Test BrowseNode hierarchy."""
    # Create parent node
    parent_node = BrowseNode(
        id=1951048031,
        name="Electronics",
        sales_rank=1
    )
    test_session.add(parent_node)
    test_session.flush()
    
    # Create child node
    child_node = BrowseNode(
        id=1951049031,
        name="Computers & Accessories",
        parent_id=1951048031,
        sales_rank=2
    )
    test_session.add(child_node)
    test_session.commit()
    
    # Verify
    retrieved_child = test_session.get(BrowseNode, 1951049031)
    assert retrieved_child is not None
    assert retrieved_child.parent_id == 1951048031


def test_product_browse_node_mapping(test_session):
    """Test Product-BrowseNode mapping."""
    # Create product and browse node
    product = Product(asin="B08N5WRWNW", title="Test Product")
    browse_node = BrowseNode(id=1951048031, name="Electronics")
    
    test_session.add(product)
    test_session.add(browse_node)
    test_session.flush()
    
    # Create mapping
    mapping = ProductBrowseNode(
        product_asin="B08N5WRWNW",
        browse_node_id=1951048031
    )
    test_session.add(mapping)
    test_session.commit()
    
    # Verify
    retrieved = test_session.query(ProductBrowseNode).filter_by(
        product_asin="B08N5WRWNW"
    ).first()
    assert retrieved is not None
    assert retrieved.browse_node_id == 1951048031


def test_price_history_aggregation(test_session):
    """Test price history calculations."""
    # Create product
    product = Product(asin="B08N5WRWNW", title="Test Product")
    test_session.add(product)
    test_session.flush()
    
    # Create price history entries
    prices = [2500, 2300, 2100, 2400, 2200]
    for i, price in enumerate(prices):
        price_history = PriceHistory(
            asin="B08N5WRWNW",
            price=price,
            list_price=3000,
            discount_percentage=int((3000 - price) / 3000 * 100),
            availability="InStock",
            source="paapi"
        )
        test_session.add(price_history)
    
    test_session.commit()
    
    # Verify aggregation
    history_records = test_session.query(PriceHistory).filter_by(asin="B08N5WRWNW").all()
    assert len(history_records) == 5
    
    # Calculate statistics
    price_values = [record.price for record in history_records]
    min_price = min(price_values)
    max_price = max(price_values)
    avg_price = sum(price_values) / len(price_values)
    
    assert min_price == 2100
    assert max_price == 2500
    assert avg_price == 2300


def test_search_query_tracking(test_session):
    """Test SearchQuery model for user search patterns."""
    search_query = SearchQuery(
        user_id=123,
        query="gaming laptop",
        search_index="Electronics",
        results_count=25,
        clicked_asin="B08N5WRWNW"
    )
    
    test_session.add(search_query)
    test_session.commit()
    
    # Verify
    retrieved = test_session.query(SearchQuery).filter_by(user_id=123).first()
    assert retrieved is not None
    assert retrieved.query == "gaming laptop"
    assert retrieved.results_count == 25


def test_deal_alert_model(test_session):
    """Test DealAlert model."""
    deal_alert = DealAlert(
        watch_id=1,
        asin="B08N5WRWNW",
        alert_type="price_drop",
        previous_price=2500,
        current_price=2100,
        discount_percentage=16,
        deal_quality_score=85.5
    )
    
    test_session.add(deal_alert)
    test_session.commit()
    
    # Verify
    retrieved = test_session.query(DealAlert).filter_by(watch_id=1).first()
    assert retrieved is not None
    assert retrieved.alert_type == "price_drop"
    assert retrieved.deal_quality_score == 85.5


def test_product_variation_model(test_session):
    """Test ProductVariation model."""
    # Create parent and child products
    parent = Product(asin="B08N5WRWNW", title="Parent Product")
    child = Product(asin="B08N5WRXXX", title="Child Product")
    
    test_session.add(parent)
    test_session.add(child)
    test_session.flush()
    
    # Create variation
    variation = ProductVariation(
        parent_asin="B08N5WRWNW",
        child_asin="B08N5WRXXX",
        variation_type="Color",
        variation_value="Red"
    )
    
    test_session.add(variation)
    test_session.commit()
    
    # Verify
    retrieved = test_session.query(ProductVariation).filter_by(
        parent_asin="B08N5WRWNW"
    ).first()
    assert retrieved is not None
    assert retrieved.variation_type == "Color"
    assert retrieved.variation_value == "Red"


def test_model_timestamps(test_session):
    """Test that timestamps are set correctly."""
    product = Product(asin="B08N5WRWNW", title="Test Product")
    test_session.add(product)
    test_session.commit()
    
    # Verify timestamp is set
    assert product.last_updated is not None
    assert isinstance(product.last_updated, datetime)
    
    # Verify timestamp is recent (within last minute)
    time_diff = datetime.utcnow() - product.last_updated
    assert time_diff.total_seconds() < 60


def test_json_field_error_handling():
    """Test JSON field error handling for invalid data."""
    product = Product(asin="B08N5WRWNW", title="Test Product")
    
    # Set invalid JSON data directly
    product.features = "invalid json"
    
    # Should return empty list for invalid JSON
    assert product.features_list == []
    
    # Test None handling
    product.features = None
    assert product.features_list == []
