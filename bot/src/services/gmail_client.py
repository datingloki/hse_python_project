# services/gmail_service.py
import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from config.oauth_config import SCOPES, TOKENS_DIR


def get_gmail_service(telegram_user_id: int):
    token_path = os.path.join(TOKENS_DIR, f"{telegram_user_id}.json")

    if not os.path.exists(token_path):
        return None  # почта не подключена

    creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    return build("gmail", "v1", credentials=creds)
