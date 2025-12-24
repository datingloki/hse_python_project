import asyncio
import logging
import html
import os
import json
from typing import List
from googleapiclient.errors import HttpError
from aiogram import Bot
from email.utils import parsedate_to_datetime
from bot.src.domain.entities.user_state import UserState
from bot.src.domain.entities.email_message_class import EmailMessage
from bot.src.domain.repositories.token_repositories import TokenRepository
from bot.src.domain.repositories.state_repository import StateRepository
from bot.src.application.gmail_client import GmailService
USER_CATEGORIES_PATH = "bot/src/handlers/user_categories.json"

try:
    from ML.classifier.predictor import EmailClassifier
except Exception:
    EmailClassifier = None
    logging.getLogger(__name__).warning("Не удалось импортировать EmailClassifier (ML.classifier.predictor).")


class EmailMonitorService:
    def __init__(self, bot: Bot, token_repo: TokenRepository, state_repo: StateRepository, gmail_service: GmailService):
        self.bot = bot
        self.token_repo = token_repo
        self.state_repo = state_repo
        self.gmail_service = gmail_service
        self.classifier = None
        if EmailClassifier is not None:
            try:
                self.classifier = EmailClassifier()
            except Exception as e:
                logging.getLogger(__name__).error(f"Не удалось загрузить классификатор: {e}")
                self.classifier = None

    def _load_user_categories_file(self):
        """
        Возвращает dict: {user_id: set(category_id, ...), ...}
        Если файл не найден или ошибка — возвращает {}.
        """
        try:
            if not os.path.exists(USER_CATEGORIES_PATH):
                return {}
            with open(USER_CATEGORIES_PATH, 'r', encoding='utf-8') as f:
                raw = json.load(f)
            result = {}
            for user_id_str, categories in raw.items():
                try:
                    result[int(user_id_str)] = set(categories)
                except Exception:
                    # если ключ не число — игнорируем
                    continue
            return result
        except Exception as e:
            logging.getLogger(__name__).error(f"Ошибка при чтении {USER_CATEGORIES_PATH}: {e}")
            return {}

    async def monitor_all_users(self):
        while True:
            await asyncio.sleep(60)
            for user_id in self._get_connected_users():
                await self._process_user_emails(user_id)

    def _get_connected_users(self) -> List[int]:
        return [
            int(file[:-5]) for file in os.listdir(self.token_repo.tokens_dir)
            if file.endswith('.json') and not file.endswith('_state.json')
        ]

    async def _process_user_emails(self, user_id: int):
        if not self.token_repo.exists(user_id) or not self.state_repo.exists(user_id):
            return

        user_state = UserState(user_id, self.token_repo.tokens_dir)
        if not user_state.last_history_id:
            return

        service = self.gmail_service.get_service(user_id)
        if not service:
            return

        try:
            history_response = self.gmail_service.get_history(service, user_state.last_history_id)
            histories = history_response.get('history', [])
            new_history_id = history_response.get('historyId') or user_state.last_history_id

            for hist in histories:
                for msg_added in hist.get('messagesAdded', []):
                    msg = msg_added['message']
                    full_msg = self.gmail_service.get_message(service, msg['id'])
                    email = EmailMessage(full_msg)
                    date_str = email.headers.get('Date', '')
                    try:
                        date_obj = parsedate_to_datetime(date_str)
                        formatted_date = date_obj.strftime("%d %b %Y, %H:%M")
                    except Exception:
                        formatted_date = date_str

                    # подготовка текста для классификации
                    text_for_classification = None
                    # пробуем несколько полей, которые могут содержать текст письма
                    for attr in ("full_text", "body", "plain_text", "snippet"):
                        if hasattr(email, attr):
                            value = getattr(email, attr)
                            if value:
                                text_for_classification = value
                                break
                    if not text_for_classification:
                        text_for_classification = (email.subject or "") + "\n" + (email.snippet or "")

                    category = None
                    confidence = None
                    top_probs_str = None
                    if self.classifier:
                        try:
                            result = self.classifier.predict(text_for_classification)
                            category = result.get('category')
                            confidence = result.get('confidence')
                            probs = result.get('probabilities', {})

                            sorted_probs = sorted(probs.items(), key=lambda x: -x[1])[:3]
                            top_probs_str = ", ".join([f"{k}: {v * 100:.1f}%" for k, v in sorted_probs])

                        except Exception as e:
                            logging.getLogger(__name__).error(f"Ошибка классификации письма {msg['id']}: {e}")
                            category = None

                    user_categories_map = self._load_user_categories_file()

                    if self.classifier is None:
                        logging.getLogger(__name__).info("Классификатор не загружен — пропускаем отправку уведомления")
                        continue


                    if not category:
                        logging.getLogger(__name__).info(f"Письмо {msg['id']} пропущено: категория не определена")
                        continue

                    selected_for_user = user_categories_map.get(user_id, set())
                    if not selected_for_user:
                        logging.getLogger(__name__).info(
                            f"Письмо {msg['id']} пропущено для пользователя {user_id}: нет выбранных категорий")
                        continue

                    if category not in selected_for_user:
                        logging.getLogger(__name__).info(
                            f"Письмо {msg['id']} пропущено: категория '{category}' не выбрана пользователем {user_id}"
                        )
                        continue

                    notification_lines = [
                        "📬 *НОВОЕ ПИСЬМО*",
                        "",
                        f"👤 *От:* {email.from_}",
                        f"📅 *Дата:* {formatted_date}",
                        f"📌 *Тема:* {email.subject}",
                        ""
                    ]

                    if category is not None:
                        notification_lines.append(f"📂 *Категория:* {category} ({(confidence * 100):.1f}%)")
                        if top_probs_str:
                            notification_lines.append(f"🔢 *Вероятности:* {top_probs_str}")
                        notification_lines.append("")

                    notification_lines.extend([
                        "📄 *Содержание:*",
                        f"{email.snippet}",
                        "",
                        "━━━━━━━━━━━━━━━━━━━━"
                    ])

                    notification = "\n".join(notification_lines)

                    await self.bot.send_message(
                        user_id,
                        notification,
                        parse_mode='Markdown',
                        disable_web_page_preview=True
                    )

            if new_history_id != user_state.last_history_id:
                user_state.save_last_history_id(new_history_id)

        except HttpError as e:
            if e.resp.status == 404:
                profile = self.gmail_service.get_profile(service)
                user_state.save_last_history_id(profile['historyId'])
            else:
                logging.error(f"HttpError processing email for user {user_id}: {str(e)}")
        except Exception as e:
            logging.error(f"Error processing email for user {user_id}: {str(e)}")