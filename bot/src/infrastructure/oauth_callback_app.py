# from flask import Flask, request
# from bot.src.application.email_oauth import OAuthService
# from bot.src.application.gmail_client import GmailService
# from bot.src.domain.entities.user_state import UserState
# from bot.src.domain.repositories.state_repository import StateRepository
#
#
# class OAuthCallbackApp:
#     def __init__(self, oauth_service: OAuthService, gmail_service: GmailService, state_repo: StateRepository):
#         self.app = Flask(__name__)
#         self.oauth_service = oauth_service
#         self.gmail_service = gmail_service
#         self.state_repo = state_repo
#         self._register_routes()
#
#     def _register_routes(self):
#         @self.app.route("/oauth2callback")
#         def oauth_callback():
#             state = request.args.get("state")
#             user_id = int(state)
#             service = self.gmail_service.get_service(user_id)
#             profile = self.gmail_service.get_profile(service)
#             user_state = UserState(user_id, self.state_repo.tokens_dir)
#             user_state.save_last_history_id(profile['historyId'])
#             return "✅ Gmail успешно подключён. Можешь вернуться в Telegram."
#
#     def run(self, port: int = 5000, debug: bool = False):
#         self.app.run(port=port, debug=debug, use_reloader=False)


from flask import Flask, request
from bot.src.application.email_oauth import OAuthService
from bot.src.application.gmail_client import GmailService
from bot.src.domain.entities.user_state import UserState
from bot.src.domain.repositories.state_repository import StateRepository
import logging
import traceback

logger = logging.getLogger(__name__)


class OAuthCallbackApp:
    def __init__(self, oauth_service: OAuthService, gmail_service: GmailService, state_repo: StateRepository):
        self.app = Flask(__name__)
        self.oauth_service = oauth_service
        self.gmail_service = gmail_service
        self.state_repo = state_repo
        self._register_routes()

    def _register_routes(self):
        @self.app.route("/oauth2callback")
        def oauth_callback():
            try:
                # Логируем полученные параметры
                logger.debug(f"Получен callback с параметрами: {request.args}")

                # Получаем параметры
                code = request.args.get("code")
                state = request.args.get("state")
                error = request.args.get("error")

                if error:
                    logger.error(f"Ошибка авторизации: {error}")
                    return f"❌ Ошибка авторизации: {error}", 400

                if not code:
                    logger.error("Authorization code не получен")
                    return "❌ Authorization code не получен", 400

                if not state:
                    logger.error("State не получен")
                    return "❌ State не получен", 400

                # Преобразуем state в user_id
                try:
                    user_id = int(state)
                except (ValueError, TypeError) as e:
                    logger.error(f"Неверный state параметр: {state}, ошибка: {e}")
                    return "❌ Неверный state параметр", 400

                logger.info(f"Обработка OAuth callback для user_id: {user_id}")

                # 1. Получаем и сохраняем токен
                logger.debug("Получение и сохранение токена...")
                credentials = self.oauth_service.fetch_and_save_token(code, state)

                if not credentials:
                    logger.error("Не удалось получить токен")
                    return "❌ Не удалось получить токен", 500

                logger.info("Токен успешно получен и сохранен")

                # 2. Получаем сервис Gmail
                logger.debug("Создание Gmail сервиса...")
                service = self.gmail_service.get_service(user_id)

                if not service:
                    logger.error("Не удалось создать сервис Gmail")
                    return "❌ Не удалось создать сервис Gmail", 500

                # 3. Получаем профиль пользователя
                logger.debug("Получение профиля Gmail...")
                profile = service.users().getProfile(userId='me').execute()

                if not profile or 'historyId' not in profile:
                    logger.error(f"Не удалось получить профиль или historyId. Профиль: {profile}")
                    return "❌ Не удалось получить профиль Gmail", 500

                # 4. Сохраняем историю
                logger.debug(f"Сохранение historyId: {profile['historyId']}")
                user_state = UserState(user_id, self.state_repo.tokens_dir)
                user_state.save_last_history_id(profile['historyId'])

                logger.info(f"Успешная аутентификация для user_id: {user_id}")
                return """
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Успешная авторизация</title>
                    <style>
                        body {
                            font-family: Arial, sans-serif;
                            text-align: center;
                            padding: 50px;
                            background-color: #f5f5f5;
                        }
                        .success {
                            background-color: white;
                            padding: 30px;
                            border-radius: 10px;
                            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                            display: inline-block;
                        }
                        h1 {
                            color: #34A853;
                        }
                        .emoji {
                            font-size: 50px;
                        }
                    </style>
                </head>
                <body>
                    <div class="success">
                        <div class="emoji">✅</div>
                        <h1>Gmail успешно подключён!</h1>
                        <p>Можешь вернуться в Telegram и использовать все функции бота.</p>
                        <p><small>Это окно можно закрыть.</small></p>
                    </div>
                </body>
                </html>
                """

            except Exception as e:
                error_msg = f"Критическая ошибка в oauth_callback: {str(e)}"
                logger.error(f"{error_msg}\n{traceback.format_exc()}")
                return f"❌ Внутренняя ошибка сервера: {str(e)}", 500

        @self.app.route("/debug")
        def debug():
            return {
                "received_args": dict(request.args),
                "headers": dict(request.headers),
                "message": "Это debug endpoint"
            }, 200

    def run(self, port: int = 5000, debug: bool = False):
        # Настраиваем логирование
        logging.basicConfig(
            level=logging.DEBUG if debug else logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        logger.info(f"Запуск OAuthCallbackApp на порту {port}")
        self.app.run(host='0.0.0.0', port=port, debug=debug, use_reloader=False)
