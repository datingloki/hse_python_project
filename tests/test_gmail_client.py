import pytest
from unittest.mock import Mock, patch, MagicMock
from google.oauth2.credentials import Credentials
from bot.src.application.gmail_client import GmailService


class TestGmailService:
    """Тесты для GmailService"""

    @pytest.fixture
    def mock_token_repository(self):
        """Фикстура для мок-репозитория токенов"""
        return Mock()

    @pytest.fixture
    def gmail_service(self, mock_token_repository):
        """Фикстура для создания экземпляра GmailService"""
        return GmailService(token_repository=mock_token_repository)

