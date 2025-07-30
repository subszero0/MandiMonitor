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

            mock_parse.return_value = {
                "brand": "samsung",
                "max_price": None,
                "min_discount": None,
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
        mock_context.user_data = {
            "pending_watch": {
                "brand": "samsung",
                "max_price": None,
                "min_discount": None,
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
        mock_context.user_data = {
            "pending_watch": {
                "brand": "samsung",
                "max_price": None,
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
        # All possible combinations of brand, discount, price (present/missing)
        permutations = [
            # (brand, discount, price, expected_missing_fields)
            ("samsung", 10, 25000, []),  # All present
            ("samsung", 10, None, ["price"]),  # Missing price
            ("samsung", None, 25000, ["discount"]),  # Missing discount
            ("samsung", None, None, ["discount", "price"]),  # Missing both
            (None, 10, 25000, ["brand"]),  # Missing brand
            (None, 10, None, ["brand", "price"]),  # Missing brand & price
            (None, None, 25000, ["brand", "discount"]),  # Missing brand & discount
            (None, None, None, ["brand", "discount", "price"]),  # Missing all
        ]

        for brand, discount, price, expected_missing in permutations:
            parsed_data = {
                "brand": brand,
                "min_discount": discount,
                "max_price": price,
                "keywords": "test product",
                "asin": None,
            }

            # Add keys for fields that are explicitly set (including None for skipped)
            if discount is not None or brand is not None:
                parsed_data["min_discount"] = discount
            if price is not None or brand is not None:
                parsed_data["max_price"] = price

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
            ), f"Failed for {brand}, {discount}, {price}"
