import pytest
import tempfile
import os
import json
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

sys.modules['pandas'] = MagicMock()
sys.modules['nltk'] = MagicMock()
sys.modules['joblib'] = MagicMock()

if 'nltk' in sys.modules:
    sys.modules['nltk'].download = Mock()
    sys.modules['nltk'].corpus = MagicMock()
    sys.modules['nltk'].corpus.stopwords = MagicMock()
    sys.modules['nltk'].corpus.stopwords.words = Mock(return_value=['the', 'is', 'and'])


@pytest.fixture
def temp_dir():
    """Создание временной директории для тестов"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_email_data():
    """Фикстура с примером данных email"""
    return {
        'id': '12345',
        'payload': {
            'headers': [
                {'name': 'From', 'value': 'test@example.com'},
                {'name': 'Subject', 'value': 'Test Subject'},
                {'name': 'Date', 'value': 'Mon, 1 Jan 2024 12:00:00 +0000'}
            ]
        },
        'snippet': 'This is a test email snippet'
    }


@pytest.fixture
def mock_token_repository():
    """Мок репозитория токенов"""
    repo = Mock()
    repo.load_credentials = Mock(return_value=None)
    repo.save_credentials = Mock()
    repo.tokens_dir = '/tmp/tokens'
    return repo


@pytest.fixture
def mock_state_repository():
    """Мок репозитория состояний"""
    repo = Mock()
    repo.get_state = Mock(return_value=None)
    repo.save_state = Mock()
    return repo


@pytest.fixture
def mock_bot():
    """Мок бота Telegram"""
    bot = Mock()
    bot.send_message = Mock()
    return bot


@pytest.fixture
def mock_gmail_service():
    """Мок сервиса Gmail"""
    service = Mock()
    service.users().getProfile = Mock(return_value={'emailAddress': 'test@example.com', 'historyId': '123'})
    return service