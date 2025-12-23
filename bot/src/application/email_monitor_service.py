import asyncio
import logging
import html
import os
from typing import List
from googleapiclient.errors import HttpError
from aiogram import Bot
from email.utils import parsedate_to_datetime
from bot.src.domain.entities.user_state import UserState
from bot.src.domain.entities.email_message_class import EmailMessage
from bot.src.domain.repositories.token_repositories import TokenRepository
from bot.src.domain.repositories.state_repository import StateRepository
from bot.src.application.gmail_client import GmailService


class EmailMonitorService:
    def __init__(self, bot: Bot, token_repo: TokenRepository, state_repo: StateRepository, gmail_service: GmailService):
        self.bot = bot
        self.token_repo = token_repo
        self.state_repo = state_repo
        self.gmail_service = gmail_service

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
                    except:
                        formatted_date = date_str

                    safe_from = html.escape(email.from_)
                    safe_subject = html.escape(email.subject)
                    safe_snippet = html.escape(email.snippet)

                    notification = (
                        "📬 <b>НОВОЕ ПИСЬМО</b>\n\n"
                        f"👤 <b>От:</b> {safe_from}\n"
                        f"📅 <b>Дата:</b> {formatted_date}\n"
                        f"📌 <b>Тема:</b> {safe_subject}\n\n"
                        f"📄 <b>Содержание:</b>\n"
                        f"{safe_snippet}\n\n"
                        "━━━━━━━━━━━━━━━━━━━━"
                    )

                    await self.bot.send_message(
                        user_id,
                        notification,
                        parse_mode='HTML',
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