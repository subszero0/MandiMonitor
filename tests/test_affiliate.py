"""Tests for affiliate URL generation and click tracking."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from bot.affiliate import build_affiliate_url
from bot.handlers import click_handler
from bot.models import Click


def test_build_affiliate_url():
    """Test affiliate URL generation with default tag."""
    url = build_affiliate_url("B01234XYZ")
    assert url.startswith("https://www.amazon.in/dp/B01234XYZ?tag=")
    assert "&linkCode=ogi&th=1&psc=1" in url


def test_build_affiliate_url_with_custom_tag():
    """Test affiliate URL generation with custom PAAPI_TAG."""
    with patch("bot.affiliate.settings") as mock_settings:
        mock_settings.PAAPI_TAG = "customtag-21"
        url = build_affiliate_url("B09ABC123")
        assert (
            url
            == "https://www.amazon.in/dp/B09ABC123?tag=customtag-21&linkCode=ogi&th=1&psc=1"
        )


def test_build_affiliate_url_fallback():
    """Test affiliate URL generation with None PAAPI_TAG falls back to default."""
    with patch("bot.affiliate.settings") as mock_settings:
        mock_settings.PAAPI_TAG = None
        url = build_affiliate_url("B12345DEF")
        assert (
            url
            == "https://www.amazon.in/dp/B12345DEF?tag=YOURTAG-21&linkCode=ogi&th=1&psc=1"
        )


@pytest.mark.asyncio
async def test_click_logged():
    """Test that click handler logs clicks and redirects."""
    # Create mock update and context
    mock_update = MagicMock()
    mock_context = MagicMock()
    mock_query = MagicMock()
    mock_update.callback_query = mock_query
    mock_query.data = "click:123:B01234ABC"
    mock_query.answer = AsyncMock()

    # Mock session and database
    with patch("sqlmodel.Session") as mock_session, patch(
        "bot.affiliate.build_affiliate_url"
    ) as mock_build_url:

        mock_session_instance = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_session_instance
        mock_build_url.return_value = (
            "https://amazon.in/dp/B01234ABC?tag=test-21&linkCode=ogi&th=1&psc=1"
        )

        # Call the handler
        await click_handler(mock_update, mock_context)

        # Verify click was logged
        mock_session_instance.add.assert_called_once()
        click_obj = mock_session_instance.add.call_args[0][0]
        assert isinstance(click_obj, Click)
        assert click_obj.watch_id == 123
        assert click_obj.asin == "B01234ABC"
        mock_session_instance.commit.assert_called_once()

        # Verify redirect with cache_time=0
        mock_query.answer.assert_called_with(
            url="https://amazon.in/dp/B01234ABC?tag=test-21&linkCode=ogi&th=1&psc=1",
            cache_time=0,
        )


@pytest.mark.asyncio
async def test_click_handler_invalid_data():
    """Test click handler with invalid callback data."""
    mock_update = MagicMock()
    mock_context = MagicMock()
    mock_query = MagicMock()
    mock_update.callback_query = mock_query
    mock_query.data = "invalid:data"
    mock_query.answer = AsyncMock()
    mock_query.edit_message_text = AsyncMock()

    await click_handler(mock_update, mock_context)

    # Should show error message
    mock_query.edit_message_text.assert_called_once_with(
        "❌ Invalid link. Please try again."
    )
    mock_query.answer.assert_called_once_with()
