import asyncio
import threading
import sys
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from bot.src.config.bot_token import TOKEN
from bot.src.domain.repositories.token_repositories import TokenRepository
from bot.src.domain.repositories.state_repository import StateRepository
from bot.src.application.email_oauth import OAuthService
from bot.src.application.gmail_client import GmailService
from bot.src.application.email_monitor_service import EmailMonitorService
from bot.src.handlers.telegram_handlers import TelegramHandlers
from bot.src.infrastructure.oauth_callback_app import OAuthCallbackApp


class BotApplication:
    def __init__(self):
        self.token_repo = TokenRepository()
        self.state_repo = StateRepository()
        self.oauth_service = OAuthService(self.token_repo)
        self.gmail_service = GmailService(self.token_repo)
        self.dp = Dispatcher()
        self.bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        self.handlers = TelegramHandlers(self.dp, self.oauth_service)
        self.monitor_service = EmailMonitorService(self.bot, self.token_repo, self.state_repo, self.gmail_service)
        self.callback_app = OAuthCallbackApp(self.oauth_service, self.gmail_service, self.state_repo)
        self.monitor_task = None

    async def start(self):
        flask_thread = threading.Thread(target=self.callback_app.run, kwargs={'debug': False})
        flask_thread.daemon = True
        flask_thread.start()

        self.monitor_task = asyncio.create_task(self.monitor_service.monitor_all_users())

        await self.dp.start_polling(self.bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    app = BotApplication()
    asyncio.run(app.start())
