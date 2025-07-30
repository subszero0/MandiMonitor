"""Comprehensive tests for watch creation flow scenarios."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, Message, User, CallbackQuery
from telegram.ext import ContextTypes

from bot.watch_flow import start_watch, handle_callback


class TestWatchFlow:
    """Test various watch creation flow permutations."""

    @pytest.fixture
    def mock_update(self):
        """Create a mock Telegram update object."""
        update = MagicMock(spec=Update)
        update.effective_user = MagicMock(spec=User)
        update.effective_user.id = 12345
        update.message = MagicMock(spec=Message)
        update.message.message_id = 1
        update.message.reply_text = AsyncMock()
        update.effective_message = update.message
        return update

    @pytest.fixture
    def mock_context(self):
        """Create a mock context object."""
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        context.args = []
        context.user_data = {}
        return context

    @pytest.fixture
    def mock_callback_update(self, mock_update):
        """Create a mock update for callback query."""
        mock_update.callback_query = MagicMock(spec=CallbackQuery)
        mock_update.callback_query.answer = AsyncMock()
        mock_update.callback_query.edit_message_text = AsyncMock()
        mock_update.callback_query.data = "test:value"
        mock_update.effective_message = MagicMock()
        mock_update.effective_message.reply_text = AsyncMock()
        return mock_update

    @pytest.mark.asyncio
    async def test_watch_command_no_args(self, mock_update, mock_context):
        """Test /watch command without arguments shows help text."""
        await start_watch(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Add a Watch" in call_args
        assert "Examples:" in call_args

    @pytest.mark.asyncio
    async def test_watch_with_complete_input(self, mock_update, mock_context):
        """Test watch creation with complete input (brand + price + discount)."""
        mock_context.args = [
            "Samsung",
            "Galaxy",
            "S24",
            "under",
            "50000",
            "with",
            "20%",
            "discount",
        ]

        with patch("bot.watch_flow.parse_watch") as mock_parse, patch(
            "bot.watch_flow.validate_watch_data"
        ) as mock_validate, patch("bot.watch_flow._finalize_watch") as mock_finalize:

            mock_parse.return_value = {
                "brand": "samsung",
                "max_price": 50000,
                "min_discount": 20,
                "keywords": "Samsung Galaxy S24 under 50000 with 20% discount",
                "asin": None,
            }
            mock_validate.return_value = {}

            await start_watch(mock_update, mock_context)

            # Should finalize immediately since all fields are present
            mock_finalize.assert_called_once()

    @pytest.mark.asyncio
    async def test_watch_missing_discount_and_price(self, mock_update, mock_context):
        """Test watch creation missing discount and price."""
        mock_context.args = ["Samsung", "mobile"]

        with patch("bot.watch_flow.parse_watch") as mock_parse, patch(
            "bot.watch_flow.validate_watch_data"
        ) as mock_validate, patch("bot.watch_flow._ask_for_missing_field") as mock_ask:

            # Return parsed data that's missing discount and price (keys not present)
            mock_parse.return_value = {
                "brand": "samsung",
                "keywords": "Samsung mobile", 
                "asin": None,
            }
            mock_validate.return_value = {}

            await start_watch(mock_update, mock_context)

            # Should ask for the first missing field (discount)
            mock_ask.assert_called_once_with(mock_update, mock_context, "discount")

    @pytest.mark.asyncio
    async def test_callback_discount_selection(
        self, mock_callback_update, mock_context
    ):
        """Test discount selection callback."""
        mock_callback_update.callback_query.data = "disc:15"
        # Set up context with missing price only 
        mock_context.user_data = {
            "pending_watch": {
                "brand": "samsung",
                "keywords": "Samsung mobile",
                "asin": None,
            }
        }

        with patch("bot.watch_flow._ask_for_missing_field") as mock_ask:
            await handle_callback(mock_callback_update, mock_context)

            # Should update discount and ask for price
            assert mock_context.user_data["pending_watch"]["min_discount"] == 15
            mock_ask.assert_called_once_with(
                mock_callback_update, mock_context, "price", edit=True
            )

    @pytest.mark.asyncio
    async def test_callback_discount_skip(self, mock_callback_update, mock_context):
        """Test skipping discount selection."""
        mock_callback_update.callback_query.data = "disc:skip"
        # Set up context with missing price only
        mock_context.user_data = {
            "pending_watch": {
                "brand": "samsung", 
                "keywords": "Samsung mobile",
                "asin": None,
            }
        }

        with patch("bot.watch_flow._ask_for_missing_field") as mock_ask:
            await handle_callback(mock_callback_update, mock_context)

            # Should set discount to None and ask for price
            assert mock_context.user_data["pending_watch"]["min_discount"] is None
            assert "min_discount" in mock_context.user_data["pending_watch"]
            mock_ask.assert_called_once_with(
                mock_callback_update, mock_context, "price", edit=True
            )

    @pytest.mark.asyncio
    async def test_callback_price_selection(self, mock_callback_update, mock_context):
        """Test price selection callback."""
        mock_callback_update.callback_query.data = "price:25000"
        mock_context.user_data = {
            "pending_watch": {
                "brand": "samsung",
                "min_discount": 10,
                "max_price": None,
                "keywords": "Samsung mobile",
                "asin": None,
            }
        }

        with patch("bot.watch_flow._finalize_watch") as mock_finalize:
            await handle_callback(mock_callback_update, mock_context)

            # Should update price and finalize
            assert mock_context.user_data["pending_watch"]["max_price"] == 25000
            mock_finalize.assert_called_once()

    @pytest.mark.asyncio
    async def test_callback_price_skip(self, mock_callback_update, mock_context):
        """Test skipping price selection."""
        mock_callback_update.callback_query.data = "price:skip"
        mock_context.user_data = {
            "pending_watch": {
                "brand": "samsung",
                "min_discount": 10,
                "keywords": "Samsung mobile",
                "asin": None,
            }
        }

        with patch("bot.watch_flow._finalize_watch") as mock_finalize:
            await handle_callback(mock_callback_update, mock_context)

            # Should set price to None and finalize
            assert mock_context.user_data["pending_watch"]["max_price"] is None
            assert "max_price" in mock_context.user_data["pending_watch"]
            mock_finalize.assert_called_once()

    @pytest.mark.asyncio
    async def test_callback_both_skip(self, mock_callback_update, mock_context):
        """Test complete flow with both discount and price skipped."""
        # First callback - skip discount
        mock_callback_update.callback_query.data = "disc:skip"
        mock_context.user_data = {
            "pending_watch": {
                "brand": "samsung",
                "keywords": "Samsung mobile",
                "asin": None,
            }
        }

        with patch("bot.watch_flow._ask_for_missing_field") as mock_ask:
            await handle_callback(mock_callback_update, mock_context)
            mock_ask.assert_called_once_with(
                mock_callback_update, mock_context, "price", edit=True
            )

        # Second callback - skip price
        mock_callback_update.callback_query.data = "price:skip"
        mock_context.user_data["pending_watch"][
            "max_price"
        ] = None  # Simulate skipped price

        with patch("bot.watch_flow._finalize_watch") as mock_finalize:
            await handle_callback(mock_callback_update, mock_context)
            mock_finalize.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_expired_callback(self, mock_callback_update, mock_context):
        """Test callback when session has expired."""
        mock_callback_update.callback_query.data = "disc:10"
        mock_context.user_data = {}  # No pending watch data

        await handle_callback(mock_callback_update, mock_context)

        mock_callback_update.callback_query.edit_message_text.assert_called_once_with(
            "❌ Session expired. Please start a new /watch command."
        )

    @pytest.mark.asyncio
    async def test_invalid_callback_data(self, mock_callback_update, mock_context):
        """Test callback with invalid data."""
        mock_callback_update.callback_query.data = "invalid:data"
        mock_context.user_data = {
            "pending_watch": {
                "brand": "samsung",
                "keywords": "Samsung mobile",
                "asin": None,
            }
        }

        await handle_callback(mock_callback_update, mock_context)

        mock_callback_update.callback_query.edit_message_text.assert_called_once_with(
            "❌ Unknown option selected."
        )

    def test_permutation_matrix(self):
        """Test all possible field combinations for completeness."""
        # Test scenarios: value=present, None=explicitly skipped, missing=not in dict
        test_cases = [
            # (parsed_data, expected_missing_fields)
            (
                {"brand": "samsung", "min_discount": 10, "max_price": 25000, "keywords": "test", "asin": None},
                []  # All present
            ),
            (
                {"brand": "samsung", "min_discount": 10, "keywords": "test", "asin": None}, 
                ["price"]  # Missing max_price key
            ),
            (
                {"brand": "samsung", "max_price": 25000, "keywords": "test", "asin": None},
                ["discount"]  # Missing min_discount key  
            ),
            (
                {"brand": "samsung", "keywords": "test", "asin": None},
                ["discount", "price"]  # Missing both keys
            ),
            (
                {"min_discount": 10, "max_price": 25000, "keywords": "test", "asin": None},
                ["brand"]  # Missing brand key
            ),
            (
                {"brand": "samsung", "min_discount": None, "max_price": 25000, "keywords": "test", "asin": None},
                []  # discount explicitly skipped (None but key present)
            ),
            (
                {"brand": "samsung", "min_discount": 10, "max_price": None, "keywords": "test", "asin": None},
                []  # price explicitly skipped (None but key present) 
            ),
        ]

        for parsed_data, expected_missing in test_cases:
            missing_fields = []
            if parsed_data.get("brand") is None and "brand" not in parsed_data:
                missing_fields.append("brand")
            if (
                parsed_data.get("min_discount") is None
                and "min_discount" not in parsed_data
            ):
                missing_fields.append("discount")
            if parsed_data.get("max_price") is None and "max_price" not in parsed_data:
                missing_fields.append("price")

            assert (
                missing_fields == expected_missing
            ), f"Failed for {parsed_data}: expected {expected_missing}, got {missing_fields}"
