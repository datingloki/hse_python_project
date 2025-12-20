# import asyncio
# import json
# import os
# import logging
# import html
#
# from googleapiclient.errors import HttpError
# from application.services.gmail_client import get_gmail_service
# from bot.src.config.oauth_config import TOKENS_DIR
#
# async def monitor_emails(bot):
#     while True:
#         await asyncio.sleep(60)
#         if not os.path.exists(TOKENS_DIR):
#             os.makedirs(TOKENS_DIR, exist_ok=True)
#             continue
#
#         for file in os.listdir(TOKENS_DIR):
#             if file.endswith('.json') and not file.endswith('_state.json'):
#                 user_id_str = file[:-5]
#
#                 try:
#                     user_id = int(user_id_str)
#                 except ValueError:
#                     continue
#
#                 state_path = os.path.join(TOKENS_DIR, f"{user_id}_state.json")
#                 token_path = os.path.join(TOKENS_DIR, file)
#                 if not os.path.exists(state_path) or not os.path.exists(token_path):
#                     continue
#                 with open(state_path, 'r') as f:
#                     state = json.load(f)
#
#                 last_history_id = state.get('last_history_id')
#                 if not last_history_id:
#                     continue
#
#                 service = get_gmail_service(user_id)
#                 if not service:
#                     continue
#                 try:
#                     history_response = service.users().history().list(
#                         userId='me',
#                         startHistoryId=last_history_id,
#                         historyTypes=['messageAdded']
#                     ).execute()
#
#                     histories = history_response.get('history', [])
#                     new_history_id = history_response.get('historyId') or last_history_id
#
#                     for hist in histories:
#                         for msg_added in hist.get('messagesAdded', []):
#                             msg = msg_added['message']
#                             msg_id = msg['id']
#                             full_msg = service.users().messages().get(
#                                 userId='me',
#                                 id=msg_id,
#                                 format='metadata'
#                             ).execute()
#
#                             headers = {h['name']: h['value'] for h in full_msg['payload']['headers']}
#                             from_ = html.escape(headers.get('From', 'Unknown'))
#                             subject = html.escape(headers.get('Subject', 'No Subject'))
#                             snippet = html.escape(full_msg.get('snippet', ''))
#                             notification = f"New email:\nFrom: {from_}\nSubject: {subject}\nSnippet: {snippet}"
#                             await bot.send_message(user_id, notification)
#
#                     if new_history_id != last_history_id:
#                         state['last_history_id'] = new_history_id
#                         with open(state_path, 'w') as f:
#                             json.dump(state, f)
#
#                 except HttpError as e:
#                     if e.resp.status == 404:
#                         profile = service.users().getProfile(userId='me').execute()
#                         state['last_history_id'] = profile['historyId']
#
#                         with open(state_path, 'w') as f:
#                             json.dump(state, f)
#                     else:
#                         logging.error(f"HttpError processing email for user {user_id}: {str(e)}")
#                 except Exception as e:
#                     logging.error(f"Error processing email for user {user_id}: {str(e)}")

import asyncio
import logging
import html
import os
from typing import List
from googleapiclient.errors import HttpError
from aiogram import Bot
from bot.src.domain.entities.user_state import UserState
from bot.src.domain.entities.email_message_class import EmailMessage
from bot.src.domain.repositories.token_repositories import TokenRepository
from bot.src.domain.repositories.state_repository import StateRepository
from application.gmail_client import GmailService


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
                    notification = f"New email:\nFrom: {html.escape(email.from_)}\nSubject: {html.escape(email.subject)}\nSnippet: {html.escape(email.snippet)}"
                    await self.bot.send_message(user_id, notification)

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