import pytest
from unittest.mock import Mock, patch
from flask.testing import FlaskClient
from bot.src.infrastructure.oauth_callback_app import OAuthCallbackApp


class TestOAuthCallbackApp:
    @pytest.fixture
    def mock_oauth_service(self):
        """Мок OAuth сервиса"""
        service = Mock()
        service.fetch_and_save_token = Mock(return_value=Mock())
        return service
    
    @pytest.fixture
    def mock_gmail_service(self):
        """Мок Gmail сервиса"""
        service = Mock()
        service.get_service = Mock(return_value=Mock())
        return service
    
    @pytest.fixture
    def mock_state_repo(self):
        """Мок репозитория состояний"""
        repo = Mock()
        repo.tokens_dir = '/tmp'
        return repo
    
    @pytest.fixture
    def callback_app(self, mock_oauth_service, mock_gmail_service, mock_state_repo):
        """Создание экземпляра OAuthCallbackApp"""
        return OAuthCallbackApp(mock_oauth_service, mock_gmail_service, mock_state_repo)
    
    def test_init(self, callback_app):
        """Тест инициализации приложения"""
        assert callback_app is not None
        assert callback_app.app is not None
    
    def test_oauth_callback_success(self, callback_app, mock_oauth_service):
        """Тест успешного OAuth коллбека"""
        with callback_app.app.test_client() as client:
            # Настраиваем моки
            mock_credentials = Mock()
            mock_oauth_service.fetch_and_save_token.return_value = mock_credentials
            
            mock_service = Mock()
            mock_gmail_service = Mock()
            mock_gmail_service.get_service.return_value = mock_service
            callback_app.gmail_service = mock_gmail_service
            
            mock_profile = {'historyId': '123'}
            mock_service.users().getProfile().execute.return_value = mock_profile
            
            # Вызываем callback
            response = client.get('/oauth2callback?code=auth_code&state=123')
            
            assert response.status_code == 200
            assert 'Gmail успешно подключён' in response.get_data(as_text=True)
    
    def test_oauth_callback_missing_code(self, callback_app):
        """Тест коллбека без кода авторизации"""
        with callback_app.app.test_client() as client:
            response = client.get('/oauth2callback?state=123')
            
            assert response.status_code == 400
            assert 'Authorization code не получен' in response.get_data(as_text=True)
    
    def test_oauth_callback_missing_state(self, callback_app):
        """Тест коллбека без state"""
        with callback_app.app.test_client() as client:
            response = client.get('/oauth2callback?code=auth_code')
            
            assert response.status_code == 400
            assert 'State не получен' in response.get_data(as_text=True)
    
    def test_debug_endpoint(self, callback_app):
        """Тест debug endpoint"""
        with callback_app.app.test_client() as client:
            response = client.get('/debug')
            
            assert response.status_code == 200
            data = response.get_json()
            assert 'received_args' in data
            assert 'message' in data