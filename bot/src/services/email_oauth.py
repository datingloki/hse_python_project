# работа с Gmail API
from google_auth_oauthlib.flow import Flow
from bot.src.config.oauth_config import SCOPES, CLIENT_SECRET_FILE, REDIRECT_URI, TOKENS_DIR


def generate_oauth_url(telegram_user_id: int) -> str:
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRET_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )

    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=str(telegram_user_id),  # 🔑 ключ к пользователю
    )

    return auth_url
