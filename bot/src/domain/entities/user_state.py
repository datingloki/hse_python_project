import json
import os
from bot.src.config.oauth_config import TOKENS_DIR


class UserState:
    def __init__(self, user_id: int, tokens_dir: str = TOKENS_DIR):
        self.user_id = user_id
        self.state_path = os.path.join(tokens_dir, f"{user_id}_state.json")
        self.last_history_id = self._load_last_history_id()

    def _load_last_history_id(self) -> str | None:
        if os.path.exists(self.state_path):
            with open(self.state_path, 'r') as f:
                state = json.load(f)
                return state.get('last_history_id')
        return None

    def save_last_history_id(self, history_id: str):
        state = {'last_history_id': history_id}
        with open(self.state_path, 'w') as f:
            json.dump(state, f)
