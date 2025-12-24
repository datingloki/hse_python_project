import pytest
import os
import json
from unittest.mock import Mock, patch, AsyncMock
from aiogram.types import Message, User, CallbackQuery
from bot.src.handlers.telegram_handlers import TelegramHandlers


class TestTelegramHandlers:
    """Тесты для TelegramHandlers"""
    
    @pytest.fixture
    def telegram_handlers(self):
        """Фикстура для создания экземпляра TelegramHandlers"""
        mock_oauth_service = Mock()
        return TelegramHandlers(oauth_service=mock_oauth_service)
    
    @pytest.fixture
    def mock_oauth_service(self):
        """Фикстура для мок-сервиса OAuth"""
        return Mock()