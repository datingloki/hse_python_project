import pytest
from bot.src.domain.entities.email_message_class import EmailMessage


class TestEmailMessage:
    def test_email_message_creation(self, sample_email_data):
        """Тест создания объекта EmailMessage"""
        email = EmailMessage(sample_email_data)
        
        assert email.id == '12345'
        assert email.from_ == 'test@example.com'
        assert email.subject == 'Test Subject'
        assert email.snippet == 'This is a test email snippet'
        
    def test_email_message_without_headers(self):
        """Тест создания EmailMessage без некоторых заголовков"""
        data = {
            'id': '123',
            'payload': {'headers': []},
            'snippet': 'Test'
        }
        email = EmailMessage(data)
        
        assert email.id == '123'
        assert email.from_ == 'Unknown'
        assert email.subject == 'No Subject'
        assert email.snippet == 'Test'
        
    def test_email_message_without_snippet(self):
        """Тест создания EmailMessage без сниппета"""
        data = {
            'id': '123',
            'payload': {
                'headers': [
                    {'name': 'From', 'value': 'sender@example.com'}
                ]
            }
        }
        email = EmailMessage(data)
        
        assert email.snippet == ''
        
    def test_headers_dict(self, sample_email_data):
        """Тест преобразования заголовков в словарь"""
        email = EmailMessage(sample_email_data)
        
        assert isinstance(email.headers, dict)
        assert email.headers['From'] == 'test@example.com'
        assert email.headers['Subject'] == 'Test Subject'
