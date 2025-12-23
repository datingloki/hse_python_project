from ML.classifier.preprocessor import clean_email_text
import joblib
import pickle
import os
import asyncio
import logging
import html
import json
from typing import List, Set, Dict
from googleapiclient.errors import HttpError
from aiogram import Bot
from email.utils import parsedate_to_datetime
from bot.src.domain.entities.user_state import UserState
from bot.src.domain.entities.email_message_class import EmailMessage
from bot.src.domain.repositories.token_repositories import TokenRepository
from bot.src.domain.repositories.state_repository import StateRepository
from bot.src.application.gmail_client import GmailService
from ML.classifier.predictor import EmailClassifier


class EmailMonitorService:
    def __init__(self, bot: Bot, token_repo: TokenRepository, state_repo: StateRepository,
                 gmail_service: GmailService, classifier: EmailClassifier):
        self.bot = bot
        self.token_repo = token_repo
        self.state_repo = state_repo
        self.gmail_service = gmail_service
        self.classifier = classifier
        self.user_categories_file = "user_categories.json"
        self.user_categories = self._load_user_categories()

    def _load_user_categories(self) -> Dict[int, Set[str]]:
        if os.path.exists(self.user_categories_file):
            try:
                with open(self.user_categories_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    result = {}
                    for user_id_str, categories in data.items():
                        result[int(user_id_str)] = set(categories)
                    return result
            except Exception as e:
                logging.error(f"Ошибка загрузки категорий: {e}")
                return {}
        return {}

    def _get_user_categories(self, user_id: int) -> Set[str]:
        return self.user_categories.get(user_id, set())

    async def monitor_all_users(self):
        while True:
            await asyncio.sleep(60)
            self.user_categories = self._load_user_categories()
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

        user_categories = self._get_user_categories(user_id)
        if not user_categories:
            logging.info(f"Пользователь {user_id} не выбрал категории для уведомлений")
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

                    predicted_category = await self._predict_email_category(email)

                    if not self._should_notify_user(user_categories, predicted_category):
                        continue

                    await self._send_email_notification(user_id, email, predicted_category)

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

    async def _predict_email_category(self, email: EmailMessage) -> Dict:
        try:
            email_text = email.body if hasattr(email, 'body') else email.snippet
            if not email_text:
                email_text = f"{email.subject or ''} {email.snippet or ''}"

            prediction = self.classifier.predict(email_text)
            logging.info(
                f"Предсказана категория: {prediction['category']} с уверенностью {prediction['confidence']:.2f}")
            return prediction
        except Exception as e:
            logging.error(f"Ошибка при классификации письма: {e}")
            return {
                'category': 'unknown',
                'confidence': 0.0,
                'probabilities': {},
                'clean_text': ''
            }

    def _should_notify_user(self, user_categories: Set[str], prediction: Dict) -> bool:
        if not user_categories:
            return False

        predicted_category = prediction.get('category', 'unknown')
        confidence = prediction.get('confidence', 0.0)

        category_mapping = {
            'forum': 'forum',
            'promotions': 'promotions',
            'social': 'social',
            'spam': 'spam',
            'updates': 'updates',
            'verify': 'verify'
        }

        predicted_category_key = category_mapping.get(predicted_category, predicted_category)

        if predicted_category_key in user_categories and confidence > 0.5:
            return True

        return False

    async def _send_email_notification(self, user_id: int, email: EmailMessage, prediction: Dict):
        try:
            date_str = email.headers.get('Date', '')
            try:
                date_obj = parsedate_to_datetime(date_str)
                formatted_date = date_obj.strftime("%d %b %Y, %H:%M")
            except:
                formatted_date = date_str

            confidence = prediction.get('confidence', 0.0)
            category = prediction.get('category', 'unknown')

            category_emojis = {
                'forum': '🗣️',
                'promotions': '🛒',
                'social': '📱',
                'spam': '⚠️',
                'updates': '🔄',
                'verify': '🔐',
                'unknown': '📧'
            }

            category_emoji = category_emojis.get(category, '📧')

            notification = f"""
            {category_emoji} *НОВОЕ ПИСЬМО* ({category.upper()})

            👤 *От:* {email.from_}
            📅 *Дата:* {formatted_date}
            📌 *Тема:* {email.subject}
            🎯 *Уверенность:* {confidence:.0%}

            📄 *Содержание:*
            {email.snippet}

            ━━━━━━━━━━━━━━━━━━━━
            """

            await self.bot.send_message(
                user_id,
                notification,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )

        except Exception as e:
            logging.error(f"Ошибка при отправке уведомления пользователю {user_id}: {e}")