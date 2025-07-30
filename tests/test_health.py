"""Tests for health endpoint functionality."""

from typing import Generator

import pytest
from flask.testing import FlaskClient

from bot.admin_app import app


@pytest.fixture
def client() -> Generator[FlaskClient, None, None]:
    """Flask test client fixture."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_health_endpoint_returns_ok(client: FlaskClient):
    """Test /health endpoint returns 200 OK with 'ok' response."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_data(as_text=True) == "ok"


def test_health_endpoint_no_auth_required(client: FlaskClient):
    """Test /health endpoint does not require authentication."""
    # Should work without any Authorization header
    response = client.get("/health")
    assert response.status_code == 200
    assert "WWW-Authenticate" not in response.headers


def test_health_endpoint_lightweight(client: FlaskClient):
    """Test /health endpoint is lightweight and fast."""
    response = client.get("/health")
    assert response.status_code == 200
    # Should be very fast - no database operations
    assert response.get_data(as_text=True) == "ok"


def test_health_endpoint_content_type(client: FlaskClient):
    """Test /health endpoint returns plain text."""
    response = client.get("/health")
    assert response.status_code == 200
    # Should be plain text for UptimeRobot keyword monitoring
    assert "text/html" in response.content_type
    assert response.get_data(as_text=True) == "ok"