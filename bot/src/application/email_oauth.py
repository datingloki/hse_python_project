from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from bot.src.config.oauth_config import SCOPES, CLIENT_SECRET_FILE, REDIRECT_URI
from bot.src.domain.repositories.token_repositories import TokenRepository


class OAuthService:
    def __init__(self, token_repo: TokenRepository):
        self.token_repo = token_repo

    def generate_auth_url(self, user_id: int) -> str:
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRET_FILE,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI,
        )
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
            state=str(user_id),
        )
        return auth_url

    def fetch_and_save_token(self, code: str, state: str) -> Credentials:
        user_id = int(state)
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRET_FILE,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI,
        )
        flow.fetch_token(code=code)
        creds = flow.credentials
        self.token_repo.save_credentials(user_id, creds)
        return creds
