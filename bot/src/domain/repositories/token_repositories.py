import os
from bot.src.config.oauth_config import TOKENS_DIR
from google.oauth2.credentials import Credentials


class TokenRepository:
    def __init__(self, tokens_dir: str = TOKENS_DIR):
        self.tokens_dir = tokens_dir
        os.makedirs(self.tokens_dir, exist_ok=True)

    def get_token_path(self, user_id: int) -> str:
        return os.path.join(self.tokens_dir, f"{user_id}.json")

    def exists(self, user_id: int) -> bool:
        return os.path.exists(self.get_token_path(user_id))

    def save_credentials(self, user_id: int, creds: Credentials):
        with open(self.get_token_path(user_id), 'w') as f:
            f.write(creds.to_json())

    def load_credentials(self, user_id: int, scopes: list[str]) -> Credentials | None:
        token_path = self.get_token_path(user_id)
        if os.path.exists(token_path):
            return Credentials.from_authorized_user_file(token_path, scopes)
        return None
