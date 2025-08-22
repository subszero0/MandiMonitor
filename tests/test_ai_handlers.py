"""Tests for AI-powered handler functionality."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from telegram import Update, User as TgUser, Message, CallbackQuery
from telegram.ext import ContextTypes

from bot.handlers import recommendations_command, insights_command, ai_callback_handler
from bot.models import User


class TestAIHandlers:
    """Test cases for AI-powered Telegram handlers."""

    @pytest.fixture
    def mock_update(self):
        """Mock Telegram update for testing."""
        update = Mock(spec=Update)
        update.effective_user = Mock(spec=TgUser)
        update.effective_user.id = 12345
        update.message = Mock(spec=Message)
        update.message.reply_text = AsyncMock()
        return update

    @pytest.fixture
    def mock_context(self):
        """Mock Telegram context for testing."""
        return Mock(spec=ContextTypes.DEFAULT_TYPE)

    @pytest.fixture
    def mock_callback_query_update(self):
        """Mock Telegram callback query update for testing."""
        update = Mock(spec=Update)
        update.effective_user = Mock(spec=TgUser)
        update.effective_user.id = 12345
        update.callback_query = Mock(spec=CallbackQuery)
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        return update

    @pytest.mark.asyncio
    async def test_recommendations_command_new_user(self, mock_update, mock_context):
        """Test recommendations command for new user."""
        with patch('bot.handlers.Session') as mock_session:
            mock_session_instance = mock_session.return_value.__enter__.return_value
            
            # Mock no existing user
            mock_session_instance.exec.return_value.first.return_value = None
            
            # Mock user creation
            mock_session_instance.add = Mock()
            mock_session_instance.commit = Mock()
            mock_session_instance.refresh = Mock()
            
            with patch('bot.handlers.SmartAlertEngine') as mock_smart_alerts:
                mock_engine = mock_smart_alerts.return_value
                mock_engine.generate_personalized_recommendations.return_value = {
                    "status": "no_recommendations",
                    "message": "No data yet"
                }
                
                await recommendations_command(mock_update, mock_context)
                
                # Should create new user and show getting-to-know-you message
                mock_session_instance.add.assert_called_once()
                mock_update.message.reply_text.assert_called_once()
                
                # Check that the message contains guidance for new users
                call_args = mock_update.message.reply_text.call_args[0][0]
                assert "Getting to know you" in call_args
                assert "/watch" in call_args

    @pytest.mark.asyncio
    async def test_recommendations_command_existing_user_with_data(self, mock_update, mock_context):
        """Test recommendations command for existing user with recommendations."""
        with patch('bot.handlers.Session') as mock_session:
            mock_session_instance = mock_session.return_value.__enter__.return_value
            
            # Mock existing user
            mock_user = User(id=1, tg_user_id=12345)
            mock_session_instance.exec.return_value.first.return_value = mock_user
            
            with patch('bot.handlers.SmartAlertEngine') as mock_smart_alerts:
                mock_engine = mock_smart_alerts.return_value
                mock_engine.generate_personalized_recommendations.return_value = {
                    "status": "success",
                    "message": {
                        "caption": "🤖 AI Recommendations\n\nBased on your patterns...",
                        "keyboard": None
                    },
                    "count": 3
                }
                
                await recommendations_command(mock_update, mock_context)
                
                # Should generate and send recommendations
                mock_engine.generate_personalized_recommendations.assert_called_once_with(1)
                mock_update.message.reply_text.assert_called_once()
                
                # Check that recommendations are sent
                call_args = mock_update.message.reply_text.call_args
                assert "AI Recommendations" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_recommendations_command_error_handling(self, mock_update, mock_context):
        """Test recommendations command error handling."""
        with patch('bot.handlers.Session') as mock_session:
            mock_session.side_effect = Exception("Database error")
            
            await recommendations_command(mock_update, mock_context)
            
            # Should send error message
            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "Error generating recommendations" in call_args

    @pytest.mark.asyncio
    async def test_insights_command_success(self, mock_update, mock_context):
        """Test insights command successful execution."""
        await insights_command(mock_update, mock_context)
        
        # Should send insights message with keyboard
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        
        # Check message content
        assert "AI Market Insights" in call_args[0][0]
        assert "personalized deal predictions" in call_args[0][0].lower()
        
        # Check keyboard is provided
        assert "reply_markup" in call_args[1]
        assert call_args[1]["reply_markup"] is not None

    @pytest.mark.asyncio
    async def test_insights_command_error_handling(self, mock_update, mock_context):
        """Test insights command error handling."""
        # Mock an error in insights generation
        mock_update.message.reply_text.side_effect = [Exception("Send error"), None]
        
        await insights_command(mock_update, mock_context)
        
        # Should attempt to send insights and then error message
        assert mock_update.message.reply_text.call_count == 2

    @pytest.mark.asyncio
    async def test_ai_callback_handler_get_recommendations(self, mock_callback_query_update, mock_context):
        """Test AI callback handler for getting recommendations."""
        mock_callback_query_update.callback_query.data = "get_recommendations"
        
        with patch('bot.handlers.Session') as mock_session:
            mock_session_instance = mock_session.return_value.__enter__.return_value
            
            # Mock existing user
            mock_user = User(id=1, tg_user_id=12345)
            mock_session_instance.exec.return_value.first.return_value = mock_user
            
            with patch('bot.handlers.SmartAlertEngine') as mock_smart_alerts:
                mock_engine = mock_smart_alerts.return_value
                mock_engine.generate_personalized_recommendations.return_value = {
                    "status": "success",
                    "message": {
                        "caption": "Your recommendations...",
                        "keyboard": None
                    }
                }
                
                await ai_callback_handler(mock_callback_query_update, mock_context)
                
                # Should answer callback and edit message
                mock_callback_query_update.callback_query.answer.assert_called_once()
                mock_callback_query_update.callback_query.edit_message_text.assert_called_once()
                
                # Check edited message content
                call_args = mock_callback_query_update.callback_query.edit_message_text.call_args
                assert "Your recommendations" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_ai_callback_handler_get_recommendations_no_user(self, mock_callback_query_update, mock_context):
        """Test AI callback handler when user doesn't exist."""
        mock_callback_query_update.callback_query.data = "get_recommendations"
        
        with patch('bot.handlers.Session') as mock_session:
            mock_session_instance = mock_session.return_value.__enter__.return_value
            mock_session_instance.exec.return_value.first.return_value = None
            
            await ai_callback_handler(mock_callback_query_update, mock_context)
            
            # Should send initialization message
            mock_callback_query_update.callback_query.edit_message_text.assert_called_once()
            call_args = mock_callback_query_update.callback_query.edit_message_text.call_args
            assert "/start" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_ai_callback_handler_view_analytics(self, mock_callback_query_update, mock_context):
        """Test AI callback handler for viewing analytics."""
        mock_callback_query_update.callback_query.data = "view_analytics"
        
        await ai_callback_handler(mock_callback_query_update, mock_context)
        
        # Should show analytics coming soon message
        mock_callback_query_update.callback_query.edit_message_text.assert_called_once()
        call_args = mock_callback_query_update.callback_query.edit_message_text.call_args
        assert "Your Shopping Analytics" in call_args[0][0]
        assert "coming soon" in call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_ai_callback_handler_ai_preferences(self, mock_callback_query_update, mock_context):
        """Test AI callback handler for AI preferences."""
        mock_callback_query_update.callback_query.data = "ai_preferences"
        
        await ai_callback_handler(mock_callback_query_update, mock_context)
        
        # Should show preferences message
        mock_callback_query_update.callback_query.edit_message_text.assert_called_once()
        call_args = mock_callback_query_update.callback_query.edit_message_text.call_args
        assert "AI Preferences" in call_args[0][0]
        assert "Customize your AI experience" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_ai_callback_handler_learn_ai_features(self, mock_callback_query_update, mock_context):
        """Test AI callback handler for learning about AI features."""
        mock_callback_query_update.callback_query.data = "learn_ai_features"
        
        await ai_callback_handler(mock_callback_query_update, mock_context)
        
        # Should show AI features explanation
        mock_callback_query_update.callback_query.edit_message_text.assert_called_once()
        call_args = mock_callback_query_update.callback_query.edit_message_text.call_args
        assert "How AI Enhances Your Experience" in call_args[0][0]
        assert "Smart Learning" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_ai_callback_handler_unknown_action(self, mock_callback_query_update, mock_context):
        """Test AI callback handler for unknown action."""
        mock_callback_query_update.callback_query.data = "unknown_action"
        
        await ai_callback_handler(mock_callback_query_update, mock_context)
        
        # Should show unknown action message
        mock_callback_query_update.callback_query.edit_message_text.assert_called_once()
        call_args = mock_callback_query_update.callback_query.edit_message_text.call_args
        assert "Unknown action" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_ai_callback_handler_error_handling(self, mock_callback_query_update, mock_context):
        """Test AI callback handler error handling."""
        mock_callback_query_update.callback_query.data = "get_recommendations"
        
        with patch('bot.handlers.Session') as mock_session:
            mock_session.side_effect = Exception("Database error")
            
            await ai_callback_handler(mock_callback_query_update, mock_context)
            
            # Should send error message
            mock_callback_query_update.callback_query.edit_message_text.assert_called_once()
            call_args = mock_callback_query_update.callback_query.edit_message_text.call_args
            assert "Error processing request" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_recommendations_command_service_unavailable(self, mock_update, mock_context):
        """Test recommendations command when service is unavailable."""
        with patch('bot.handlers.Session') as mock_session:
            mock_session_instance = mock_session.return_value.__enter__.return_value
            
            # Mock existing user
            mock_user = User(id=1, tg_user_id=12345)
            mock_session_instance.exec.return_value.first.return_value = mock_user
            
            with patch('bot.handlers.SmartAlertEngine') as mock_smart_alerts:
                mock_engine = mock_smart_alerts.return_value
                mock_engine.generate_personalized_recommendations.return_value = {
                    "status": "error",
                    "message": "Service unavailable"
                }
                
                await recommendations_command(mock_update, mock_context)
                
                # Should send service unavailable message
                mock_update.message.reply_text.assert_called_once()
                call_args = mock_update.message.reply_text.call_args[0][0]
                assert "temporarily unavailable" in call_args

    @pytest.mark.asyncio
    async def test_ai_callback_handler_recommendations_no_data(self, mock_callback_query_update, mock_context):
        """Test AI callback handler when user has no recommendation data."""
        mock_callback_query_update.callback_query.data = "get_recommendations"
        
        with patch('bot.handlers.Session') as mock_session:
            mock_session_instance = mock_session.return_value.__enter__.return_value
            
            # Mock existing user
            mock_user = User(id=1, tg_user_id=12345)
            mock_session_instance.exec.return_value.first.return_value = mock_user
            
            with patch('bot.handlers.SmartAlertEngine') as mock_smart_alerts:
                mock_engine = mock_smart_alerts.return_value
                mock_engine.generate_personalized_recommendations.return_value = {
                    "status": "no_recommendations"
                }
                
                await ai_callback_handler(mock_callback_query_update, mock_context)
                
                # Should send need more data message
                mock_callback_query_update.callback_query.edit_message_text.assert_called_once()
                call_args = mock_callback_query_update.callback_query.edit_message_text.call_args
                assert "need more data" in call_args[0][0].lower()


@pytest.mark.integration
class TestAIHandlersIntegration:
    """Integration tests for AI handlers with real components."""
    
    @pytest.mark.asyncio
    async def test_full_recommendation_flow(self):
        """Test complete recommendation flow from command to response."""
        # This would test the full flow with real database and AI components
        # For now, we'll skip this as it requires full system setup
        pass

    @pytest.mark.asyncio
    async def test_ai_callback_flow_with_real_data(self):
        """Test AI callback flow with real user data."""
        # This would test callback handling with real user interactions
        # For now, we'll skip this as it requires real user data
        pass

    @pytest.mark.asyncio
    async def test_error_recovery_scenarios(self):
        """Test various error recovery scenarios in AI handlers."""
        # This would test error handling with various failure modes
        # For now, we'll skip this as it requires complex error simulation
        pass
