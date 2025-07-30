"""Tests for admin Flask app functionality."""

import base64
from datetime import datetime
from typing import Generator

import pytest
from flask.testing import FlaskClient
from sqlmodel import Session, create_engine

from bot.admin_app import app
from bot.models import SQLModel, User, Watch, Price, Click


@pytest.fixture
def client() -> Generator[FlaskClient, None, None]:
    """Flask test client fixture."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def in_memory_db():
    """In-memory database fixture for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    
    # Patch the admin app to use test database
    import bot.admin_app
    original_engine = bot.admin_app.engine
    bot.admin_app.engine = engine
    
    yield engine
    
    # Restore original engine
    bot.admin_app.engine = original_engine


@pytest.fixture
def auth_headers():
    """HTTP Basic Auth headers for admin:changeme."""
    credentials = base64.b64encode(b"admin:changeme").decode("utf-8")
    return {"Authorization": f"Basic {credentials}"}


@pytest.fixture
def sample_data(in_memory_db):
    """Create sample data for testing."""
    with Session(in_memory_db) as session:
        # Create users
        user1 = User(id=1, tg_user_id=12345)
        user2 = User(id=2, tg_user_id=67890)
        session.add(user1)
        session.add(user2)
        
        # Create watches for user1 only (user2 is explorer without watches)
        watch1 = Watch(
            id=1, 
            user_id=1, 
            keywords="Samsung monitor", 
            asin="B123456789"
        )
        watch2 = Watch(
            id=2, 
            user_id=1, 
            keywords="Gaming laptop", 
            asin="B987654321"
        )
        session.add(watch1)
        session.add(watch2)
        
        # Create price history with different sources
        price1 = Price(
            id=1, 
            watch_id=1, 
            asin="B123456789", 
            price=2500000, 
            source="paapi"
        )
        price2 = Price(
            id=2, 
            watch_id=1, 
            asin="B123456789", 
            price=2400000, 
            source="scraper"
        )
        price3 = Price(
            id=3, 
            watch_id=2, 
            asin="B987654321", 
            price=8500000, 
            source="paapi"
        )
        session.add(price1)
        session.add(price2)
        session.add(price3)
        
        # Create click records
        click1 = Click(id=1, watch_id=1, asin="B123456789")
        click2 = Click(id=2, watch_id=2, asin="B987654321")
        session.add(click1)
        session.add(click2)
        
        session.commit()


def test_admin_endpoint_without_auth(client: FlaskClient):
    """Test /admin endpoint returns 401 without authentication."""
    response = client.get("/admin")
    assert response.status_code == 401
    assert "Auth required" in response.get_data(as_text=True)
    assert "WWW-Authenticate" in response.headers
    assert 'Basic realm="Admin"' in response.headers["WWW-Authenticate"]


def test_admin_endpoint_with_wrong_auth(client: FlaskClient):
    """Test /admin endpoint returns 401 with wrong credentials."""
    wrong_credentials = base64.b64encode(b"wrong:credentials").decode("utf-8")
    headers = {"Authorization": f"Basic {wrong_credentials}"}
    
    response = client.get("/admin", headers=headers)
    assert response.status_code == 401


def test_admin_endpoint_with_correct_auth(
    client: FlaskClient, 
    auth_headers: dict, 
    sample_data
):
    """Test /admin endpoint returns correct metrics with valid auth."""
    response = client.get("/admin", headers=auth_headers)
    assert response.status_code == 200
    
    data = response.get_json()
    assert isinstance(data, dict)
    
    # Check all required metric keys are present
    required_keys = [
        "explorers", 
        "watch_creators", 
        "live_watches", 
        "click_outs", 
        "scraper_fallbacks"
    ]
    for key in required_keys:
        assert key in data
        assert isinstance(data[key], int)
    
    # Verify metric values based on sample data
    assert data["explorers"] == 2  # 2 total users
    assert data["watch_creators"] == 1  # Only user1 has watches
    assert data["live_watches"] == 2  # 2 watches created
    assert data["click_outs"] == 2  # 2 clicks recorded
    assert data["scraper_fallbacks"] == 1  # 1 price from scraper


def test_prices_csv_without_auth(client: FlaskClient):
    """Test /admin/prices.csv returns 401 without authentication."""
    response = client.get("/admin/prices.csv")
    assert response.status_code == 401


def test_prices_csv_with_auth(
    client: FlaskClient, 
    auth_headers: dict, 
    sample_data
):
    """Test /admin/prices.csv returns CSV data with valid auth."""
    response = client.get("/admin/prices.csv", headers=auth_headers)
    assert response.status_code == 200
    assert response.content_type == "text/csv; charset=utf-8"
    
    csv_data = response.get_data(as_text=True)
    lines = csv_data.strip().split("\n")
    
    # Check CSV header
    assert lines[0] == "id,watch_id,asin,price,source,fetched_at"
    
    # Check we have 3 data rows (from sample_data)
    assert len(lines) == 4  # header + 3 data rows
    
    # Verify first data row structure
    first_row = lines[1].split(",")
    assert len(first_row) == 6  # id,watch_id,asin,price,source,fetched_at
    assert first_row[0] == "1"  # id
    assert first_row[1] == "1"  # watch_id
    assert first_row[2] == "B123456789"  # asin
    assert first_row[3] == "2500000"  # price
    assert first_row[4] == "paapi"  # source


def test_admin_endpoint_with_malformed_auth(client: FlaskClient):
    """Test /admin endpoint with malformed Authorization header."""
    # Test without "Basic " prefix
    headers = {"Authorization": "InvalidHeader"}
    response = client.get("/admin", headers=headers)
    assert response.status_code == 401
    
    # Test with invalid base64
    headers = {"Authorization": "Basic InvalidBase64"}
    response = client.get("/admin", headers=headers)
    assert response.status_code == 401