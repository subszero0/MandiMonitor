"""Tests for health endpoint."""

from bot.health import app


def test_health():
    """Test health endpoint returns correct response."""
    with app.test_client() as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json == {"status": "ok"}
