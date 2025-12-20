import os
from bot.src.config.oauth_config import TOKENS_DIR


class StateRepository:
    def __init__(self, tokens_dir: str = TOKENS_DIR):
        self.tokens_dir = tokens_dir

    def get_state_path(self, user_id: int) -> str:
        return os.path.join(self.tokens_dir, f"{user_id}_state.json")

    def exists(self, user_id: int) -> bool:
        return os.path.exists(self.get_state_path(user_id))
