import asyncio
import json
import os
import logging
import html

from googleapiclient.errors import HttpError
from bot.src.services.gmail_client import get_gmail_service
from bot.src.config.oauth_config import TOKENS_DIR

async def monitor_emails(bot):
    while True:
        await asyncio.sleep(60)
        if not os.path.exists(TOKENS_DIR):
            os.makedirs(TOKENS_DIR, exist_ok=True)
            continue

        for file in os.listdir(TOKENS_DIR):
            if file.endswith('.json') and not file.endswith('_state.json'):
                user_id_str = file[:-5]

                try:
                    user_id = int(user_id_str)
                except ValueError:
                    continue

                state_path = os.path.join(TOKENS_DIR, f"{user_id}_state.json")
                token_path = os.path.join(TOKENS_DIR, file)
                if not os.path.exists(state_path) or not os.path.exists(token_path):
                    continue
                with open(state_path, 'r') as f:
                    state = json.load(f)

                last_history_id = state.get('last_history_id')
                if not last_history_id:
                    continue

                service = get_gmail_service(user_id)
                if not service:
                    continue
                try:
                    history_response = service.users().history().list(
                        userId='me',
                        startHistoryId=last_history_id,
                        historyTypes=['messageAdded']
                    ).execute()

                    histories = history_response.get('history', [])
                    new_history_id = history_response.get('historyId') or last_history_id

                    for hist in histories:
                        for msg_added in hist.get('messagesAdded', []):
                            msg = msg_added['message']
                            msg_id = msg['id']
                            full_msg = service.users().messages().get(
                                userId='me',
                                id=msg_id,
                                format='metadata'
                            ).execute()

                            headers = {h['name']: h['value'] for h in full_msg['payload']['headers']}
                            from_ = html.escape(headers.get('From', 'Unknown'))
                            subject = html.escape(headers.get('Subject', 'No Subject'))
                            snippet = html.escape(full_msg.get('snippet', ''))
                            notification = f"New email:\nFrom: {from_}\nSubject: {subject}\nSnippet: {snippet}"
                            await bot.send_message(user_id, notification)

                    if new_history_id != last_history_id:
                        state['last_history_id'] = new_history_id
                        with open(state_path, 'w') as f:
                            json.dump(state, f)

                except HttpError as e:
                    if e.resp.status == 404:
                        profile = service.users().getProfile(userId='me').execute()
                        state['last_history_id'] = profile['historyId']

                        with open(state_path, 'w') as f:
                            json.dump(state, f)
                    else:
                        logging.error(f"HttpError processing email for user {user_id}: {str(e)}")
                except Exception as e:
                    logging.error(f"Error processing email for user {user_id}: {str(e)}")