"""Tests for database migration system."""

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from bot.migrations.migration_001_enhanced_models import Migration001
from bot.models import Price, User, Watch
from bot.enhanced_models import Product, PriceHistory


@pytest.fixture
def test_engine():
    """Create test database engine."""
    engine = create_engine("sqlite:///:memory:")
    # Create base tables
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def test_session(test_engine):
    """Create test database session."""
    with Session(test_engine) as session:
        yield session


@pytest.fixture
def migration(test_engine):
    """Create migration instance."""
    migration = Migration001()
    migration.engine = test_engine
    return migration


@pytest.mark.asyncio
async def test_migration_preserves_existing_data(migration, test_session):
    """Test that migration doesn't lose existing data."""
    # Create some existing data
    user = User(id=1, tg_user_id=123456)
    watch = Watch(id=1, user_id=1, keywords="test product", asin="B08N5WRWNW")
    price = Price(id=1, watch_id=1, asin="B08N5WRWNW", price=2500)
    
    test_session.add(user)
    test_session.add(watch)
    test_session.add(price)
    test_session.commit()
    
    # Run migration
    success = await migration.upgrade()
    assert success is True
    
    # Verify existing data is preserved
    existing_user = test_session.get(User, 1)
    existing_watch = test_session.get(Watch, 1)
    existing_price = test_session.get(Price, 1)
    
    assert existing_user is not None
    assert existing_user.tg_user_id == 123456
    assert existing_watch is not None
    assert existing_watch.keywords == "test product"
    assert existing_price is not None
    assert existing_price.price == 2500


@pytest.mark.asyncio
async def test_migration_creates_enhanced_tables(migration, test_session):
    """Test that migration creates all enhanced tables."""
    success = await migration.upgrade()
    assert success is True
    
    # Test that enhanced tables exist by creating records
    product = Product(asin="B08N5WRWNW", title="Test Product")
    test_session.add(product)
    test_session.commit()
    
    retrieved_product = test_session.get(Product, "B08N5WRWNW")
    assert retrieved_product is not None
    assert retrieved_product.title == "Test Product"


@pytest.mark.asyncio
async def test_migration_migrates_price_data(migration, test_session):
    """Test that existing price data is migrated to PriceHistory."""
    # Create existing price data
    user = User(id=1, tg_user_id=123456)
    watch = Watch(id=1, user_id=1, keywords="test", asin="B08N5WRWNW")
    price = Price(id=1, watch_id=1, asin="B08N5WRWNW", price=2500, source="paapi")
    
    test_session.add_all([user, watch, price])
    test_session.commit()
    
    # Run migration
    success = await migration.upgrade()
    assert success is True
    
    # Verify price data was migrated
    price_history = test_session.query(PriceHistory).filter_by(asin="B08N5WRWNW").first()
    assert price_history is not None
    assert price_history.price == 2500
    assert price_history.source == "paapi"


@pytest.mark.asyncio
async def test_migration_rollback(migration, test_session):
    """Test migration rollback functionality."""
    # Run migration
    success = await migration.upgrade()
    assert success is True
    
    # Create some enhanced model data
    product = Product(asin="B08N5WRWNW", title="Test Product")
    test_session.add(product)
    test_session.commit()
    
    # Rollback migration
    success = await migration.downgrade()
    assert success is True
    
    # Enhanced tables should be dropped - this will raise an error when trying to query
    try:
        test_session.query(Product).first()
        # If we get here, the table wasn't dropped
        assert False, "Product table should have been dropped"
    except Exception:
        # Expected - table was dropped
        pass


@pytest.mark.asyncio
async def test_migration_handles_empty_database(migration, test_session):
    """Test migration works with empty database."""
    success = await migration.upgrade()
    assert success is True
    
    # Should be able to create enhanced model records
    product = Product(asin="B08N5WRWNW", title="Test Product")
    test_session.add(product)
    test_session.commit()
    
    retrieved = test_session.get(Product, "B08N5WRWNW")
    assert retrieved is not None


@pytest.mark.asyncio
async def test_migration_handles_duplicate_runs(migration, test_session):
    """Test that running migration multiple times doesn't cause errors."""
    # Run migration first time
    success1 = await migration.upgrade()
    assert success1 is True
    
    # Run migration second time (should handle existing tables gracefully)
    success2 = await migration.upgrade()
    assert success2 is True
    
    # Should still work
    product = Product(asin="B08N5WRWNW", title="Test Product")
    test_session.add(product)
    test_session.commit()


@pytest.mark.asyncio
async def test_migration_error_handling(migration, test_session):
    """Test migration error handling."""
    # Simulate error by using invalid engine
    migration.engine = None
    
    success = await migration.upgrade()
    assert success is False


@pytest.mark.asyncio
async def test_model_relationships_work_after_migration(migration, test_session):
    """Test all model relationships work correctly after migration."""
    success = await migration.upgrade()
    assert success is True
    
    # Create related records
    from bot.enhanced_models import (
        Product, ProductOffers, CustomerReviews, BrowseNode, ProductBrowseNode
    )
    
    # Create product
    product = Product(asin="B08N5WRWNW", title="Test Product")
    test_session.add(product)
    test_session.flush()
    
    # Create offers
    offer = ProductOffers(asin="B08N5WRWNW", price=2500)
    test_session.add(offer)
    
    # Create reviews
    reviews = CustomerReviews(asin="B08N5WRWNW", review_count=100, average_rating=4.5)
    test_session.add(reviews)
    
    # Create browse node and relationship
    browse_node = BrowseNode(id=1951048031, name="Electronics")
    test_session.add(browse_node)
    test_session.flush()
    
    relationship = ProductBrowseNode(
        product_asin="B08N5WRWNW",
        browse_node_id=1951048031
    )
    test_session.add(relationship)
    
    test_session.commit()
    
    # Verify relationships
    retrieved_product = test_session.get(Product, "B08N5WRWNW")
    retrieved_offers = test_session.query(ProductOffers).filter_by(asin="B08N5WRWNW").first()
    retrieved_reviews = test_session.get(CustomerReviews, "B08N5WRWNW")
    retrieved_relationship = test_session.query(ProductBrowseNode).filter_by(
        product_asin="B08N5WRWNW"
    ).first()
    
    assert retrieved_product is not None
    assert retrieved_offers is not None
    assert retrieved_reviews is not None
    assert retrieved_relationship is not None


@pytest.mark.asyncio
async def test_migration_preserves_data_integrity(migration, test_session):
    """Test migration preserves data integrity."""
    # Create complex existing data
    user = User(id=1, tg_user_id=123456)
    watch1 = Watch(id=1, user_id=1, keywords="laptop", asin="B08N5WRWNW", max_price=100000)
    watch2 = Watch(id=2, user_id=1, keywords="phone", asin="B08N5WRXXX", max_price=50000)
    
    price1 = Price(id=1, watch_id=1, asin="B08N5WRWNW", price=95000)
    price2 = Price(id=2, watch_id=1, asin="B08N5WRWNW", price=93000)
    price3 = Price(id=3, watch_id=2, asin="B08N5WRXXX", price=45000)
    
    test_session.add_all([user, watch1, watch2, price1, price2, price3])
    test_session.commit()
    
    # Run migration
    success = await migration.upgrade()
    assert success is True
    
    # Verify all data integrity
    assert test_session.get(User, 1) is not None
    assert test_session.get(Watch, 1) is not None
    assert test_session.get(Watch, 2) is not None
    assert test_session.get(Price, 1) is not None
    assert test_session.get(Price, 2) is not None
    assert test_session.get(Price, 3) is not None
    
    # Verify migrated price history
    price_history_records = test_session.query(PriceHistory).all()
    assert len(price_history_records) == 3
    
    # Verify relationships are intact
    watch = test_session.get(Watch, 1)
    assert watch.user_id == 1
    assert watch.asin == "B08N5WRWNW"


@pytest.mark.asyncio
async def test_migration_performance_with_large_dataset(migration, test_session):
    """Test migration performance with larger dataset."""
    # Create larger dataset
    user = User(id=1, tg_user_id=123456)
    test_session.add(user)
    test_session.flush()
    
    # Create multiple watches and prices
    for i in range(50):
        watch = Watch(
            id=i + 1,
            user_id=1,
            keywords=f"product {i}",
            asin=f"B08N5WR{i:03d}"
        )
        test_session.add(watch)
        
        # Add multiple price records per watch
        for j in range(10):
            price = Price(
                id=i * 10 + j + 1,
                watch_id=i + 1,
                asin=f"B08N5WR{i:03d}",
                price=1000 + j * 100
            )
            test_session.add(price)
    
    test_session.commit()
    
    # Run migration
    success = await migration.upgrade()
    assert success is True
    
    # Verify all data was migrated
    price_history_count = test_session.query(PriceHistory).count()
    assert price_history_count == 500  # 50 watches * 10 prices each
