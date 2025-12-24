from aiogram import Dispatcher, html, Router
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest
from bot.src.application.email_oauth import OAuthService
import json
import os


class TelegramHandlers:
    def __init__(self, dp: Dispatcher, oauth_service: OAuthService):
        self.dp = dp
        self.oauth_service = oauth_service
        self.router = Router()
        self.data_file = "user_categories.json"

        self.user_categories = self._load_user_categories()

        self.categories = {
            "forum": {
                "name": "Форумы",
                "emoji": "🗣️",
                "description": "Сообщения с форумов, обсуждения и уведомления от сообществ",
            },
            "promotions": {
                "name": "Реклама",
                "emoji": "🛒",
                "description": "Маркетинговые письма, акции, скидки и рекламные предложения",
            },
            "social_media": {
                "name": "Соцсети",
                "emoji": "📱",
                "description": "Уведомления из социальных сетей и платформ",
            },
            "updates": {
                "name": "Обновления",
                "emoji": "🔄",
                "description": "Системные уведомления, обновления безопасности и технические сообщения",
            },
            "verify_code": {
                "name": "Коды верификации",
                "emoji": "🔐",
                "description": "Письма с кодами подтверждения, паролями и проверочными кодами",
            }
        }

        self._register_handlers()
        self.dp.include_router(self.router)

    def _load_user_categories(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    result = {}
                    for user_id_str, categories in data.items():
                        result[int(user_id_str)] = set(categories)
                    return result
            except Exception:
                return {}
        return {}

    def _save_user_categories(self):
        try:
            data_to_save = {}
            for user_id, categories_set in self.user_categories.items():
                data_to_save[str(user_id)] = list(categories_set)

            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка при сохранении категорий: {e}")

    def _register_handlers(self):
        self.router.message.register(self.command_start_handler, CommandStart())
        self.router.message.register(self.command_help_handler, Command('help'))
        self.router.message.register(self.command_auth_handler, Command('auth'))
        self.router.message.register(self.command_filter_handler, Command('filters'))
        self.router.message.register(self.command_my_filters_handler, Command('my_filters'))
        self.router.callback_query.register(self.callback_query_handler)
        self.router.message.register(self.echo_handler)

    def inline_keyboard_categories(self, user_id: int = None) -> InlineKeyboardMarkup:
        keyboard_builder = InlineKeyboardBuilder()

        for category_id, category_info in self.categories.items():
            is_selected = False
            if user_id and user_id in self.user_categories:
                is_selected = category_id in self.user_categories[user_id]

            status_emoji = "✅ " if is_selected else ""
            button_text = f"{status_emoji}{category_info['emoji']} {category_info['name']}"

            keyboard_builder.button(
                text=button_text,
                callback_data=f"category_{category_id}"
            )

        keyboard_builder.button(text="📋 Мои фильтры", callback_data="show_my_filters")
        keyboard_builder.button(text="🔄 Сбросить все", callback_data="reset_all_categories")
        keyboard_builder.button(text="💾 Сохранить", callback_data="save_categories")

        keyboard_builder.adjust(2, 2, 2, 3)
        return keyboard_builder.as_markup()

    def inline_keyboard_category_detail(self, category_id: str, is_selected: bool = False) -> InlineKeyboardMarkup:
        keyboard_builder = InlineKeyboardBuilder()

        if is_selected:
            keyboard_builder.button(
                text="❌ Отключить",
                callback_data=f"toggle_{category_id}"
            )
        else:
            keyboard_builder.button(
                text="✅ Включить",
                callback_data=f"toggle_{category_id}"
            )

        keyboard_builder.button(
            text="⬅️ Назад",
            callback_data="back_to_categories"
        )
        keyboard_builder.button(
            text="📋 Мои фильтры",
            callback_data="show_my_filters"
        )

        keyboard_builder.adjust(1, 2)
        return keyboard_builder.as_markup()

    async def command_start_handler(self, message: Message):
        await message.answer(
            f"👋 <b>Привет, {html.bold(message.from_user.full_name)}!</b>\n\n"
            f"Я — бот для уведомлений о важных письмах из твоей почты 📬\n"
            f"Я подключаюсь к <b>Gmail</b>, отслеживаю новые письма и сообщаю тебе в Telegram "
            f"только о действительно важных событиях.\n\n"
            f"<b>Что я умею:</b>\n"
            f"• 🔐 Подключать почту через безопасную авторизацию Gmail\n"
            f"• ⚙️ Настраивать фильтры по категориям писем\n"
            f"• 🚨 Присылать мгновенные уведомления о важных письмах\n"
            f"• ✂️ Показывать краткую выжимку письма\n\n"
            f"<b>С чего начать:</b>\n"
            f"1️⃣ Подключи почту командой /auth\n"
            f"2️⃣ Настрой фильтры через /filters\n"
            f"3️⃣ Получай уведомления автоматически ✨\n\n"
            f"Если понадобится помощь — напиши /help 😊"
        )

    async def command_help_handler(self, message: Message):
        await message.answer(
            "<b>ℹ️ Помощь</b>\n\n"
            "Я — бот для уведомлений о важных письмах из Gmail 📬\n"
            "Помогаю отслеживать новые письма и присылаю в Telegram только то, что действительно важно.\n\n"
            "<b>Доступные команды:</b>\n"
            "/start — начать работу с ботом\n"
            "/auth — подключить Gmail-почту\n"
            "/filters — настроить фильтры по категориям\n"
            "/my_filters — показать выбранные категории\n"
            "/help — показать это сообщение\n\n"
            "<b>Как это работает:</b>\n"
            "1️⃣ Ты подключаешь почту Gmail\n"
            "2️⃣ Выбираешь категории писем, о которых хочешь получать уведомления\n"
            "3️⃣ Я автоматически проверяю новые письма\n"
            "4️⃣ Если письмо попадает в выбранные категории — присылаю уведомление ✨\n\n"
            "<b>Поддержка:</b>\n"
            "Если возникли вопросы или проблемы, напиши 👉 @datingloki"
        )

    async def command_auth_handler(self, message: Message):
        user_id = message.from_user.id
        auth_url = self.oauth_service.generate_auth_url(user_id)
        await message.answer(
            "🔐 <b>Подключение Gmail</b>\n\n"
            "Чтобы подключить почту, перейди по ссылке ниже 👇\n"
            "Авторизация происходит через Google и безопасна.\n\n"
            f"👉 {auth_url}\n\n"
            "После завершения авторизации я автоматически начну отслеживать письма.",
        )

    async def command_filter_handler(self, message: Message):
        user_id = message.from_user.id

        if user_id not in self.user_categories:
            self.user_categories[user_id] = set()

        selected_count = len(self.user_categories.get(user_id, set()))

        await message.answer(
            f"<b>🎯 Настройка фильтров по категориям</b>\n\n"
            f"✅ <b>Выбрано: {selected_count} из {len(self.categories)}</b>\n\n"
            "Выберите категорию, чтобы увидеть подробности и настроить:\n\n"
            "<i>Нажмите на любую категорию ниже для просмотра подробностей и включения/выключения</i>",
            reply_markup=self.inline_keyboard_categories(user_id)
        )

    async def command_my_filters_handler(self, message: Message):
        user_id = message.from_user.id

        if user_id not in self.user_categories or not self.user_categories[user_id]:
            await message.answer(
                "📭 <b>У вас пока нет выбранных категорий</b>\n\n"
                "Используйте команду /filters, чтобы выбрать категории писем для уведомлений."
            )
        else:
            selected_categories = []
            for category_id in self.user_categories[user_id]:
                category = self.categories.get(category_id, {})
                selected_categories.append(
                    f"{category.get('emoji', '📧')} {category.get('name', 'Неизвестная категория')}"
                )

            await message.answer(
                f"✅ <b>Ваши выбранные категории ({len(selected_categories)}):</b>\n\n"
                + "\n".join(selected_categories) + "\n\n"
                                                   "Изменить выбор можно командой /filters"
            )

    async def callback_query_handler(self, callback_query: CallbackQuery):
        data = callback_query.data

        try:
            await callback_query.answer()

            if data.startswith("category_"):
                await self._handle_category_detail(callback_query)
            elif data.startswith("toggle_"):
                await self._handle_toggle_category(callback_query)
            elif data == "show_my_filters":
                await self._show_my_filters(callback_query)
            elif data == "back_to_categories":
                await self._show_categories_list(callback_query)
            elif data == "reset_all_categories":
                await self._reset_all_categories(callback_query)
            elif data == "save_categories":
                await self._save_categories(callback_query)
            else:
                await self._handle_unknown_callback(callback_query)

        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                pass
            else:
                raise
        except Exception as e:
            print(f"Error in callback handler: {e}")
            await callback_query.answer(f"Произошла ошибка: {str(e)}")

    async def _handle_category_detail(self, callback_query: CallbackQuery):
        category_id = callback_query.data.replace("category_", "")
        category = self.categories.get(category_id)

        if not category:
            await callback_query.answer("Категория не найдена")
            return

        user_id = callback_query.from_user.id

        if user_id not in self.user_categories:
            self.user_categories[user_id] = set()

        is_selected = category_id in self.user_categories[user_id]

        status = "✅ <b>Включена</b>" if is_selected else "❌ <b>Выключена</b>"

        await callback_query.message.edit_text(
            f"{category['emoji']} <b>{category['name']}</b>\n\n"
            f"📝 <b>Описание:</b> {category['description']}\n\n"
            f"<b>Статус:</b> {status}\n\n"
            f"<i>Нажмите кнопку ниже, чтобы {'отключить' if is_selected else 'включить'} эту категорию</i>",
            reply_markup=self.inline_keyboard_category_detail(category_id, is_selected)
        )

    async def _handle_toggle_category(self, callback_query: CallbackQuery):
        category_id = callback_query.data.replace("toggle_", "")

        if category_id not in self.categories:
            await callback_query.answer("Категория не найдена")
            return

        user_id = callback_query.from_user.id

        if user_id not in self.user_categories:
            self.user_categories[user_id] = set()

        if category_id in self.user_categories[user_id]:
            self.user_categories[user_id].remove(category_id)
            action = "отключена"
        else:
            self.user_categories[user_id].add(category_id)
            action = "включена"

        category = self.categories[category_id]
        await callback_query.answer(f"Категория «{category['name']}» {action}")

        self._save_user_categories()

        is_selected = category_id in self.user_categories[user_id]
        status = "✅ <b>Включена</b>" if is_selected else "❌ <b>Выключена</b>"

        await callback_query.message.edit_text(
            f"{category['emoji']} <b>{category['name']}</b>\n\n"
            f"📝 <b>Описание:</b> {category['description']}\n\n"
            f"<b>Статус:</b> {status}\n\n"
            f"<i>Нажмите кнопку ниже, чтобы {'отключить' if is_selected else 'включить'} эту категорию</i>",
            reply_markup=self.inline_keyboard_category_detail(category_id, is_selected)
        )

    async def _show_my_filters(self, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id

        if user_id not in self.user_categories or not self.user_categories[user_id]:
            await callback_query.message.edit_text(
                "📭 <b>У вас пока нет выбранных категорий</b>\n\n"
                "Выберите категории, нажав кнопки ниже:",
                reply_markup=self.inline_keyboard_categories(user_id)
            )
        else:
            selected_categories = []
            for category_id in self.user_categories[user_id]:
                category = self.categories.get(category_id, {})
                selected_categories.append(
                    f"{category.get('emoji', '📧')} {category.get('name', 'Неизвестная категория')}"
                )

            await callback_query.message.edit_text(
                f"✅ <b>Ваши выбранные категории ({len(selected_categories)}):</b>\n\n"
                + "\n".join(selected_categories) + "\n\n"
                                                   "Изменить выбор можно кнопками ниже:",
                reply_markup=self.inline_keyboard_categories(user_id)
            )

    async def _show_categories_list(self, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id

        if user_id not in self.user_categories:
            self.user_categories[user_id] = set()

        selected_count = len(self.user_categories.get(user_id, set()))

        await callback_query.message.edit_text(
            f"<b>🎯 Настройка фильтров по категориям</b>\n\n"
            f"✅ <b>Выбрано: {selected_count} из {len(self.categories)}</b>\n\n"
            "Выберите категорию, чтобы увидеть подробности и настроить:\n\n"
            "<i>Нажмите на любую категорию ниже для просмотра подробностей и включения/выключения</i>",
            reply_markup=self.inline_keyboard_categories(user_id)
        )

    async def _reset_all_categories(self, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id

        if user_id in self.user_categories:
            count = len(self.user_categories[user_id])
            self.user_categories[user_id] = set()
            await callback_query.answer(f"Сброшено {count} категорий")
        else:
            await callback_query.answer("Нет выбранных категорий для сброса")

        self._save_user_categories()

        await self._show_categories_list(callback_query)

    async def _save_categories(self, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        selected_count = len(self.user_categories.get(user_id, set()))

        self._save_user_categories()

        await callback_query.answer(f"Сохранено {selected_count} категорий")

        await callback_query.message.edit_text(
            f"💾 <b>Настройки сохранены!</b>\n\n"
            f"✅ <b>Выбрано категорий:</b> {selected_count}\n\n"
            "Я буду присылать уведомления только о письмах из выбранных категорий.\n\n"
            "Изменить настройки можно в любое время через /filters",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад к фильтрам", callback_data="back_to_categories")]
            ])
        )

    async def _handle_unknown_callback(self, callback_query: CallbackQuery):
        await callback_query.answer("Неизвестная команда")
        await callback_query.message.answer(
            "❌ <b>Неизвестная команда</b>\n\n"
            "Пожалуйста, используйте команды из меню бота или начните заново с /start"
        )

    @staticmethod
    async def echo_handler(message: Message):
        try:
            await message.send_copy(chat_id=message.chat.id)
        except TypeError:
            await message.answer("Nice try!")