import pytest
import os
import json
import tempfile
from bot.src.domain.entities.user_state import UserState


class TestUserState:
    """Тесты для UserState"""
    
    @pytest.fixture
    def temp_dir(self):
        """Фикстура для временной директории"""
        with tempfile.TemporaryDirectory() as tmpdirname:
            yield tmpdirname
    
    

