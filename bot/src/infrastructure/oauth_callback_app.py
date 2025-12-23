from flask import Flask, request
from bot.src.application.email_oauth import OAuthService
from bot.src.application.gmail_client import GmailService
from bot.src.domain.entities.user_state import UserState
from bot.src.domain.repositories.state_repository import StateRepository
import logging
import traceback
import datetime
from flask import make_response

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
                logger.debug(f"Получен callback с параметрами: {request.args}")
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

                try:
                    user_id = int(state)
                except (ValueError, TypeError) as e:
                    logger.error(f"Неверный state параметр: {state}, ошибка: {e}")
                    return "❌ Неверный state параметр", 400

                logger.info(f"Обработка OAuth callback для user_id: {user_id}")

                logger.debug("Получение и сохранение токена...")
                credentials = self.oauth_service.fetch_and_save_token(code, state)

                if not credentials:
                    logger.error("Не удалось получить токен")
                    return "❌ Не удалось получить токен", 500

                logger.info("Токен успешно получен и сохранен")

                logger.debug("Создание Gmail сервиса...")
                service = self.gmail_service.get_service(user_id)

                if not service:
                    logger.error("Не удалось создать сервис Gmail")
                    return "❌ Не удалось создать сервис Gmail", 500

                logger.debug("Получение профиля Gmail...")
                profile = service.users().getProfile(userId='me').execute()

                if not profile or 'historyId' not in profile:
                    logger.error(f"Не удалось получить профиль или historyId. Профиль: {profile}")
                    return "❌ Не удалось получить профиль Gmail", 500

                logger.debug(f"Сохранение historyId: {profile['historyId']}")
                user_state = UserState(user_id, self.state_repo.tokens_dir)
                user_state.save_last_history_id(profile['historyId'])

                logger.info(f"Успешная аутентификация для user_id: {user_id}")
                html_content = """
                <!DOCTYPE html>
                <html lang="ru">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>Успешная авторизация</title>
                    <style>
                        * {
                            margin: 0;
                            padding: 0;
                            box-sizing: border-box;
                        }

                        body {
                            font-family: 'Arial', 'Segoe UI', sans-serif;
                            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                            min-height: 100vh;
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            padding: 20px;
                        }

                        .success-container {
                            width: 100%;
                            max-width: 800px;
                            background: white;
                            border-radius: 25px;
                            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
                            overflow: hidden;
                            animation: fadeIn 0.6s ease-out;
                        }

                        .header {
                            background: linear-gradient(135deg, #34A853 0%, #2E8B47 100%);
                            color: white;
                            padding: 60px 40px;
                            text-align: center;
                            position: relative;
                        }

                        .header::after {
                            content: '';
                            position: absolute;
                            bottom: -50px;
                            left: 50%;
                            transform: translateX(-50%);
                            width: 100px;
                            height: 100px;
                            background: #34A853;
                            border-radius: 50%;
                            z-index: 1;
                        }

                        .emoji {
                            font-size: 120px;
                            margin-bottom: 30px;
                            display: block;
                            animation: bounce 1s ease infinite alternate;
                        }

                        h1 {
                            font-size: 48px;
                            font-weight: 700;
                            margin-bottom: 20px;
                            letter-spacing: 0.5px;
                            text-shadow: 0 2px 4px rgba(0,0,0,0.1);
                        }

                        .subtitle {
                            font-size: 26px;
                            opacity: 0.95;
                            font-weight: 300;
                        }

                        .content {
                            padding: 80px 50px 60px;
                            text-align: center;
                        }

                        .message {
                            font-size: 32px;
                            line-height: 1.6;
                            color: #333;
                            margin-bottom: 40px;
                            padding: 0 20px;
                        }

                        .steps {
                            background: #f8f9fa;
                            border-radius: 20px;
                            padding: 40px;
                            margin: 40px auto;
                            text-align: left;
                            max-width: 600px;
                        }

                        .steps h2 {
                            font-size: 28px;
                            color: #2E8B47;
                            margin-bottom: 25px;
                            text-align: center;
                        }

                        .step {
                            display: flex;
                            align-items: center;
                            margin-bottom: 25px;
                            font-size: 22px;
                        }

                        .step-number {
                            background: #34A853;
                            color: white;
                            width: 50px;
                            height: 50px;
                            border-radius: 50%;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            font-weight: bold;
                            font-size: 24px;
                            margin-right: 20px;
                            flex-shrink: 0;
                        }

                        .note {
                            font-size: 22px;
                            color: #666;
                            line-height: 1.5;
                            margin-top: 40px;
                            padding: 30px;
                            background: #fff8e1;
                            border-radius: 15px;
                            border-left: 6px solid #ffc107;
                        }

                        .telegram-icon {
                            display: inline-block;
                            vertical-align: middle;
                            margin: 0 10px;
                            font-size: 28px;
                        }

                        .footer {
                            margin-top: 50px;
                            padding-top: 30px;
                            border-top: 2px dashed #e0e0e0;
                            font-size: 20px;
                            color: #888;
                        }

                        @keyframes fadeIn {
                            from { opacity: 0; transform: translateY(30px); }
                            to { opacity: 1; transform: translateY(0); }
                        }

                        @keyframes bounce {
                            from { transform: translateY(0); }
                            to { transform: translateY(-20px); }
                        }

                        @media (max-width: 768px) {
                            .header {
                                padding: 40px 20px;
                            }

                            .emoji {
                                font-size: 80px;
                            }

                            h1 {
                                font-size: 36px;
                            }

                            .subtitle {
                                font-size: 22px;
                            }

                            .content {
                                padding: 60px 20px 40px;
                            }

                            .message {
                                font-size: 26px;
                            }

                            .steps {
                                padding: 30px 20px;
                            }

                            .step {
                                font-size: 18px;
                            }

                            .note {
                                font-size: 18px;
                                padding: 20px;
                            }
                        }

                        @media (max-width: 480px) {
                            h1 {
                                font-size: 28px;
                            }

                            .message {
                                font-size: 22px;
                            }

                            .step {
                                font-size: 16px;
                            }
                        }
                    </style>
                    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
                </head>
                <body>
                    <div class="success-container">
                        <div class="header">
                            <span class="emoji">✅</span>
                            <h1>Gmail успешно подключён!</h1>
                            <p class="subtitle">Почтовый ящик интегрирован с Telegram ботом</p>
                        </div>

                        <div class="content">
                            <div class="message">
                                Теперь вы можете вернуться в Telegram и пользоваться всеми функциями бота
                            </div>

                            <div class="steps">
                                <h2>Что дальше?</h2>
                                <div class="step">
                                    <div class="step-number">1</div>
                                    <div>Вернитесь в Telegram-бот</div>
                                </div>
                                <div class="step">
                                    <div class="step-number">2</div>
                                    <div>Используйте команду /help для просмотра доступных функций</div>
                                </div>
                                <div class="step">
                                    <div class="step-number">3</div>
                                    <div>Настройте уведомления о новых письмах в настройках бота</div>
                                </div>
                                <div class="step">
                                    <div class="step-number">4</div>
                                    <div>Начните управлять почтой прямо из Telegram</div>
                                </div>
                            </div>

                            <div class="note">
                                <i class="fas fa-info-circle" style="margin-right: 10px;"></i>
                                <strong>Важно:</strong> Авторизация сохраняется автоматически. 
                                Вы можете управлять доступом в настройках Google Аккаунта.
                            </div>

                            <div class="footer">
                                <p>
                                    <i class="fab fa-telegram telegram-icon" style="color: #0088cc;"></i>
                                    Это окно можно закрыть
                                </p>
                                <p style="margin-top: 10px; font-size: 18px;">
                                    Бот продолжит работу в Telegram
                                </p>
                            </div>
                        </div>
                    </div>
                </body>
                </html>
                """

                response = make_response(html_content)
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
                response.headers['Last-Modified'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')
                return response

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

    def run(self, port: int = 8083, debug: bool = False):
        logging.basicConfig(
            level=logging.DEBUG if debug else logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        logger.info(f"Запуск OAuthCallbackApp на порту {port}")
        self.app.run(host='0.0.0.0', port=port, debug=debug, use_reloader=False)
