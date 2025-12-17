import asyncio
import threading
import sys
from os import getenv
import logging

from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from bot.src.services.email_oauth import generate_oauth_url
from utils.oauth_callback import app as flask_app
from services.scheduler import monitor_emails

TOKEN = "8204410947:AAHZuxncIITudP1OYSag3u5_CNbW_c3xgGE"


dp = Dispatcher()


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    This handler receives messages with `/start` command
    """
    await message.answer(
        f"👋 <b>Привет, {html.bold(message.from_user.full_name)}!</b>\n\n"
        f"Я — бот для уведомлений о важных письмах из твоей почты 📬\n"
        f"Я подключаюсь к <b>Gmail</b>, отслеживаю новые письма и сообщаю тебе в Telegram "
        f"только о действительно важных событиях.\n\n"
        f"<b>Что я умею:</b>\n"
        f"• 🔐 Подключать почту через безопасную авторизацию Gmail\n"
        f"• ⚙️ Настраивать фильтры важности:\n"
        f"  — по ключевым словам\n"
        f"  — по отправителю\n"
        f"  — по теме письма\n"
        f"• 🚨 Присылать мгновенные уведомления о важных письмах\n"
        f"• ✂️ Показывать краткую выжимку письма\n\n"
        f"<b>С чего начать:</b>\n"
        f"1️⃣ Подключи почту командой /auth\n"
        f"2️⃣ Настрой фильтры через /filters\n"
        f"3️⃣ Получай уведомления автоматически ✨\n\n"
        f"Если понадобится помощь — напиши /help 😊"
    )


@dp.message(Command('help'))
async def command_help_handler(message: Message) -> None:
    """
    This handler receives messages with `/help` command
    """
    await message.answer(
        "<b>ℹ️ Помощь</b>\n\n"
        "Я — бот для уведомлений о важных письмах из Gmail 📬\n"
        "Помогаю отслеживать новые письма и присылаю в Telegram только то, что действительно важно.\n\n"
        "<b>Доступные команды:</b>\n"
        "/start — начать работу с ботом\n"
        "/auth — подключить Gmail-почту\n"
        "/filters — настроить фильтры важности писем\n"
        "/help — показать это сообщение\n\n"
        "<b>Как это работает:</b>\n"
        "1️⃣ Ты подключаешь почту Gmail\n"
        "2️⃣ Настраиваешь правила (ключевые слова, отправители, темы)\n"
        "3️⃣ Я автоматически проверяю новые письма\n"
        "4️⃣ Если письмо важно — присылаю уведомление ✨\n\n"
        "<b>Поддержка:</b>\n"
        "Если возникли вопросы или проблемы, напиши 👉 @datingloki"
    )

@dp.message(Command('auth'))
async def connect_handler(message: Message):
    telegram_user_id = message.from_user.id

    auth_url = generate_oauth_url(telegram_user_id)

    await message.answer(
        "🔐 <b>Подключение Gmail</b>\n\n"
        "Чтобы подключить почту, перейди по ссылке ниже 👇\n"
        "Авторизация происходит через Google и безопасна.\n\n"
        f"👉 {auth_url}\n\n"
        "После завершения авторизации я автоматически начну отслеживать письма.",
    )

@dp.message()
async def echo_handler(message: Message) -> None: #ловим любые другие сообщения
    """
    Handler will forward receive a message back to the sender

    By default, message handler will handle all message types (like a text, photo, sticker etc.)
    """
    try:
        # Send a copy of the received message
        await message.send_copy(chat_id=message.chat.id)
    except TypeError:
        # But not all the types is supported to be copied so need to handle it
        await message.answer("Nice try!")


# ВСЕ КОМАНДЫ НУЖНО В /handlers потом запихнуть


async def main() -> None:
    # Initialize Bot instance with default bot properties which will be passed to all API calls
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    flask_thread = threading.Thread(target=flask_app.run, kwargs={'debug': False, 'use_reloader': False, 'port': 5000})
    flask_thread.daemon = True
    flask_thread.start()

    asyncio.create_task(monitor_emails(bot))

    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())