from googleapiclient.discovery import build, Resource
from typing import Dict
from bot.src.config.oauth_config import SCOPES
from bot.src.domain.repositories.token_repositories import TokenRepository


class GmailService:
    def __init__(self, token_repo: TokenRepository):
        self.token_repo = token_repo

    def get_service(self, user_id: int) -> Resource | None:
        creds = self.token_repo.load_credentials(user_id, SCOPES)
        if creds:
            return build("gmail", "v1", credentials=creds)
        return None

    def get_profile(self, service: Resource) -> Dict:
        return service.users().getProfile(userId='me').execute()

    def get_history(self, service: Resource, start_history_id: str) -> Dict:
        return service.users().history().list(
            userId='me',
            startHistoryId=start_history_id,
            historyTypes=['messageAdded']
        ).execute()

    def get_message(self, service: Resource, msg_id: str) -> Dict:
        return service.users().messages().get(
            userId='me',
            id=msg_id,
            format='metadata'
        ).execute()
