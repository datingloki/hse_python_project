from flask import Flask, request
from bot.src.application.email_oauth import OAuthService
from bot.src.application.gmail_client import GmailService
from bot.src.domain.entities.user_state import UserState
from bot.src.domain.repositories.state_repository import StateRepository


class OAuthCallbackApp:
    def __init__(self, oauth_service: OAuthService, gmail_service: GmailService, state_repo: StateRepository):
        self.app = Flask(__name__)
        self.oauth_service = oauth_service
        self.gmail_service = gmail_service
        self.state_repo = state_repo
        self._register_routes()

    def _register_routes(self):
        @self.app.route("/oauth2callback", methods=["GET"])
        def oauth_callback():
            code = request.args.get("code")
            state = request.args.get("state")
            error = request.args.get("error")

            if error:
                return f"Ошибка авторизации: {error}", 400

            if not code or not state:
                return "Неверный запрос (нет code или state)", 400

            try:
                user_id = int(state)
                self.oauth_service.fetch_and_save_token(code, state)

                service = self.gmail_service.get_service(user_id)
                if service:
                    profile = self.gmail_service.get_profile(service)
                    user_state = UserState(user_id, self.state_repo.tokens_dir)
                    user_state.save_last_history_id(profile['historyId'])

                return "✅ Gmail успешно подключён. Можешь вернуться в Telegram."
            except Exception as e:
                return f"Ошибка при сохранении токена: {str(e)}", 500

    def run(self, port: int = 5000, debug: bool = False):
        self.app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=False)
