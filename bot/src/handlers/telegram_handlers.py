from aiogram import Dispatcher, html
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest
from bot.src.application.email_oauth import OAuthService


class TelegramHandlers:
    def __init__(self, dp: Dispatcher, oauth_service: OAuthService):
        self.dp = dp
        self.oauth_service = oauth_service
        self._register_handlers()
        self.keyboard = self.inline_keyboard_construction()

    def _register_handlers(self):
        self.dp.message(CommandStart())(self.command_start_handler)
        self.dp.message(Command('help'))(self.command_help_handler)
        self.dp.message(Command('auth'))(self.command_auth_handler)
        self.dp.message(Command('filters'))(self.command_filter_handler)
        self.dp.callback_query()(self.callback_query_handler)
        self.dp.message()(self.echo_handler)

    @staticmethod
    def inline_keyboard_construction() -> InlineKeyboardMarkup:
        keyboard_builder = InlineKeyboardBuilder()
        keyboard_builder.button(text="Фильтр 1", callback_data="filter1")
        keyboard_builder.button(text="Фильтр 2", callback_data="filter2")
        keyboard_builder.button(text="Дополнительные настройки", callback_data="advanced_settings")
        keyboard_builder.button(text="Сбросить все фильтры", callback_data="reset_filters")
        keyboard = keyboard_builder.as_markup(row_width=2)
        return keyboard

    async def command_start_handler(self, message: Message):  # Убрать @staticmethod
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

    async def command_help_handler(self, message: Message):  # Убрать @staticmethod
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

    async def command_auth_handler(self, message: Message):
        user_id = message.from_user.id
        auth_url = self.oauth_service.generate_auth_url(user_id)  # Убрать self
        await message.answer(
            "🔐 <b>Подключение Gmail</b>\n\n"
            "Чтобы подключить почту, перейди по ссылке ниже 👇\n"
            "Авторизация происходит через Google и безопасна.\n\n"
            f"👉 {auth_url}\n\n"
            "После завершения авторизации я автоматически начну отслеживать письма.",
        )

    async def command_filter_handler(self, message: Message):
        await message.answer(
            "<b>Настройка фильтров</b>\n\n"
            "Выберите желаемые фильтры на клавиатуре под этим сообщением",
            reply_markup=self.keyboard
        )

    async def callback_query_handler(self, callback_query: CallbackQuery):
        """Маршрутизатор callback запросов"""
        data = callback_query.data

        try:
            await callback_query.answer()

            if data.startswith("filter"):
                await self._handle_filter_callback(callback_query)
            elif data.startswith("configure"):
                await self._handle_configure_callback(callback_query)
            elif data.startswith("save"):
                await self._handle_save_callback(callback_query)
            elif data == "back_to_filters":
                await self._show_filters_menu(callback_query.message)
            else:
                await self._handle_unknown_callback(callback_query)
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                # Игнорируем ошибку, если сообщение не изменилось
                pass
            else:
                raise

    async def _handle_filter_callback(self, callback_query: CallbackQuery):
        """Обработка выбора фильтра"""
        data = callback_query.data

        if data == "filter1":
            await self._show_filter1_configuration(callback_query)
        elif data == "filter2":
            await self._show_filter2_configuration(callback_query)
        else:
            await callback_query.answer(f"Фильтр {data} не найден")

    async def _show_filter1_configuration(self, callback_query: CallbackQuery):
        """Показать настройки для фильтра 1"""
        await callback_query.message.edit_text(
            "🔧 <b>Настройка Фильтра 1</b>\n\n"
            "📌 <b>Текущие настройки:</b>\n"
            "• Ключевые слова: важное, срочно, ASAP\n"
            "• Приоритет: высокий\n"
            "• Отправители: все\n\n"
            "Выберите действие:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="Изменить ключевые слова",
                                         callback_data="configure_keywords_filter1"),
                    InlineKeyboardButton(text="Изменить приоритет",
                                         callback_data="configure_priority_filter1")
                ],
                [
                    InlineKeyboardButton(text="Сохранить", callback_data="save_filter1"),
                    InlineKeyboardButton(text="Назад к фильтрам",
                                         callback_data="back_to_filters")
                ]
            ])
        )

    async def _show_filter2_configuration(self, callback_query: CallbackQuery):
        """Показать настройки для фильтра 2"""
        await callback_query.message.edit_text(
            "🔧 <b>Настройка Фильтра 2</b>\n\n"
            "📌 <b>Текущие настройки:</b>\n"
            "• Ключевые слова: отчет, итоги, результаты\n"
            "• Приоритет: средний\n"
            "• Отправители: выбранные\n\n"
            "Выберите действие:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="Изменить ключевые слова",
                                         callback_data="configure_keywords_filter2"),
                    InlineKeyboardButton(text="Выбрать отправителей",
                                         callback_data="configure_senders_filter2")
                ],
                [
                    InlineKeyboardButton(text="Сохранить", callback_data="save_filter2"),
                    InlineKeyboardButton(text="Назад к фильтрам",
                                         callback_data="back_to_filters")
                ]
            ])
        )

    async def _handle_configure_callback(self, callback_query: CallbackQuery):
        """Обработка настроек фильтров"""
        data = callback_query.data

        if "keywords" in data:
            filter_num = data.replace("configure_keywords_filter", "")
            await self._configure_keywords(callback_query, filter_num)
        elif "priority" in data:
            filter_num = data.replace("configure_priority_filter", "")
            await self._configure_priority(callback_query, filter_num)
        elif "senders" in data:
            filter_num = data.replace("configure_senders_filter", "")
            await self._configure_senders(callback_query, filter_num)
        else:
            await callback_query.answer("Неизвестная команда настройки")

    async def _configure_keywords(self, callback_query: CallbackQuery, filter_num: str):
        """Настройка ключевых слов"""
        await callback_query.message.edit_text(
            f"✏️ <b>Настройка ключевых слов для фильтра {filter_num}</b>\n\n"
            "Введите ключевые слова через запятую:\n"
            "<i>Пример: важное, срочно, ASAP, отчет</i>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Отмена", callback_data=f"filter{filter_num}")]
            ])
        )
        # Здесь можно сохранить состояние для ожидания ввода пользователя
        # Например, используя FSM (Finite State Machine)

    async def _configure_priority(self, callback_query: CallbackQuery, filter_num: str):
        """Настройка приоритета"""
        await callback_query.message.edit_text(
            f"⚡ <b>Настройка приоритета для фильтра {filter_num}</b>\n\n"
            "Выберите уровень приоритета:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="Высокий",
                                         callback_data=f"set_priority_high_filter{filter_num}"),
                    InlineKeyboardButton(text="Средний",
                                         callback_data=f"set_priority_medium_filter{filter_num}")
                ],
                [
                    InlineKeyboardButton(text="Низкий",
                                         callback_data=f"set_priority_low_filter{filter_num}"),
                    InlineKeyboardButton(text="Отмена",
                                         callback_data=f"filter{filter_num}")
                ]
            ])
        )

    async def _configure_senders(self, callback_query: CallbackQuery, filter_num: str):
        """Настройка отправителей"""
        await callback_query.message.edit_text(
            f"👤 <b>Настройка отправителей для фильтра {filter_num}</b>\n\n"
            "Выберите отправителей для фильтра:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="Все отправители",
                                         callback_data=f"set_senders_all_filter{filter_num}"),
                    InlineKeyboardButton(text="Выбранные",
                                         callback_data=f"set_senders_selected_filter{filter_num}")
                ],
                [
                    InlineKeyboardButton(text="Добавить отправителя",
                                         callback_data=f"add_sender_filter{filter_num}"),
                    InlineKeyboardButton(text="Отмена",
                                         callback_data=f"filter{filter_num}")
                ]
            ])
        )

    async def _handle_save_callback(self, callback_query: CallbackQuery):
        """Обработка сохранения настроек"""
        data = callback_query.data

        if data == "save_filter1":
            # Здесь логика сохранения настроек фильтра 1
            # Например, в базу данных
            await self._save_filter_settings(callback_query, 1)
        elif data == "save_filter2":
            await self._save_filter_settings(callback_query, 2)
        elif data.startswith("set_priority_"):
            # Обработка установки приоритета
            filter_num = data.split("_")[-1].replace("filter", "")
            priority = data.split("_")[2]  # high, medium, low
            await self._save_priority_setting(callback_query, filter_num, priority)
        elif data.startswith("set_senders_"):
            # Обработка установки отправителей
            filter_num = data.split("_")[-1].replace("filter", "")
            senders_type = data.split("_")[2]  # all, selected
            await self._save_senders_setting(callback_query, filter_num, senders_type)

    async def _save_filter_settings(self, callback_query: CallbackQuery, filter_num: int):
        """Сохранить настройки фильтра"""
        # Реальная логика сохранения в БД
        # filter_settings = get_filter_settings_from_message(callback_query.message)
        # save_to_database(callback_query.from_user.id, filter_num, filter_settings)

        await callback_query.message.edit_text(
            f"✅ <b>Фильтр {filter_num} успешно сохранен!</b>\n\n"
            "Настройки применены и будут использоваться для фильтрации писем.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Вернуться к фильтрам",
                                      callback_data="back_to_filters")]
            ])
        )

    async def _save_priority_setting(self, callback_query: CallbackQuery, filter_num: str, priority: str):
        """Сохранить настройку приоритета"""
        priority_names = {
            "high": "высокий",
            "medium": "средний",
            "low": "низкий"
        }

        await callback_query.answer(f"Приоритет установлен: {priority_names.get(priority, priority)}")
        # Возвращаемся к настройкам фильтра
        if filter_num == "1":
            await self._show_filter1_configuration(callback_query)
        else:
            await self._show_filter2_configuration(callback_query)

    async def _save_senders_setting(self, callback_query: CallbackQuery, filter_num: str, senders_type: str):
        """Сохранить настройку отправителей"""
        senders_names = {
            "all": "все отправители",
            "selected": "выбранные отправители"
        }

        await callback_query.answer(f"Тип отправителей: {senders_names.get(senders_type, senders_type)}")
        # Возвращаемся к настройкам фильтра
        if filter_num == "1":
            await self._show_filter1_configuration(callback_query)
        else:
            await self._show_filter2_configuration(callback_query)

    async def _show_filters_menu(self, message: Message):
        """Показать меню фильтров"""
        try:
            await message.edit_text(
                "<b>Настройка фильтров</b>\n\n"
                "Выберите желаемые фильтры на клавиатуре под этим сообщением",
                reply_markup=self.keyboard
            )
        except TelegramBadRequest:
            # Если сообщение нельзя отредактировать (например, отправлено другим ботом),
            # отправляем новое сообщение
            await message.answer(
                "<b>Настройка фильтров</b>\n\n"
                "Выберите желаемые фильтры на клавиатуре под этим сообщением",
                reply_markup=self.keyboard
            )

    async def _handle_unknown_callback(self, callback_query: CallbackQuery):
        """Обработка неизвестного callback"""
        await callback_query.answer("Неизвестная команда")
        await callback_query.message.answer(
            "❌ <b>Неизвестная команда</b>\n\n"
            "Пожалуйста, используйте команды из меню бота или начните заново с /start",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Вернуться к фильтрам",
                                      callback_data="back_to_filters")]
            ])
        )

    @staticmethod
    async def echo_handler(message: Message):  # Убрать self из параметров
        try:
            await message.send_copy(chat_id=message.chat.id)
        except TypeError:
            await message.answer("Nice try!")