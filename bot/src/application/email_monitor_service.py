import asyncio
import logging
import sys
import importlib
import importlib.util
from pathlib import Path
import logging
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

# --- Надёжный импорт EmailClassifier с поиском пути к ML ---
def _find_predictor_path() -> Path | None:
    """Ищет файл predictor.py в родительских директориях и в ~/hse_python_project."""
    cur = Path(__file__).resolve()
    # подняться до 6 уровней вверх и проверить наличие ML/classifier/predictor.py
    for _ in range(7):
        candidate = cur.parent / "ML" / "classifier" / "predictor.py"
        if candidate.exists():
            return candidate
        cur = cur.parent
    # проверить домашнюю папку как fallback
    home_candidate = Path.home() / "hse_python_project" / "ML" / "classifier" / "predictor.py"
    if home_candidate.exists():
        return home_candidate
    return None

def _import_email_classifier():
    predictor_path = _find_predictor_path()
    if predictor_path is None:
        logging.getLogger(__name__).warning(
            "Не удалось найти ML/classifier/predictor.py в проекте и в ~/hse_python_project. "
            "Проверь путь к ML."
        )
        return None, None

    # попробуем добавить корень проекта (папку, содержащую ML) в sys.path
    ml_root = predictor_path.parents[1]  # .../ML
    project_root = ml_root.parent        # одна папка выше ML
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    try:
        # сначала пробуем обычный импорт по пакету ML.classifier.predictor
        module = importlib.import_module("ML.classifier.predictor")
    except Exception:
        # fallback: импортировать напрямую по пути
        try:
            spec = importlib.util.spec_from_file_location("predictor_from_path", str(predictor_path))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)  # type: ignore
        except Exception as e:
            logging.getLogger(__name__).error(f"Не удалось импортировать predictor.py: {e}")
            return None, None

    # получить класс EmailClassifier из модуля
    EmailClassifier = getattr(module, "EmailClassifier", None)
    if EmailClassifier is None:
        logging.getLogger(__name__).error("В predictor.py не найден класс EmailClassifier")
        return None, None

    # определить model_dir ( ML/models рядом с predictor.py или fallback в ~/hse_python_project/ML/models )
    candidate_models_dir = ml_root / "models"
    if candidate_models_dir.exists():
        model_dir = str(candidate_models_dir)
    else:
        fallback = Path.home() / "hse_python_project" / "ML" / "models"
        model_dir = str(fallback) if fallback.exists() else None

    return EmailClassifier, model_dir

# вызов импорта (сразу при загрузке модуля)
_EMAIL_CLASSIFIER_CLS, _EMAIL_CLASSIFIER_MODEL_DIR = _import_email_classifier()
if _EMAIL_CLASSIFIER_CLS is None:
    logging.getLogger(__name__).warning("EmailClassifier не импортирован — классификация будет отключена.")
else:
    logging.getLogger(__name__).info(f"EmailClassifier импортирован. model_dir: {_EMAIL_CLASSIFIER_MODEL_DIR}")


class EmailMonitorService:
    def __init__(self, bot: Bot, token_repo: TokenRepository, state_repo: StateRepository, gmail_service: GmailService):
        self.bot = bot
        self.token_repo = token_repo
        self.state_repo = state_repo
        self.gmail_service = gmail_service
        # Попытка загрузить классификатор (если он доступен)
        self.classifier = None
        if _EMAIL_CLASSIFIER_CLS is not None:
            try:
                if _EMAIL_CLASSIFIER_MODEL_DIR:
                    # передаём model_dir явно (если найден)
                    self.classifier = _EMAIL_CLASSIFIER_CLS(model_dir=_EMAIL_CLASSIFIER_MODEL_DIR)
                else:
                    # иначе полагаемся на поведение конструктора по умолчанию
                    self.classifier = _EMAIL_CLASSIFIER_CLS()
            except FileNotFoundError as e:
                logging.getLogger(__name__).error(f"Файлы модели не найдены: {e}")
                self.classifier = None
            except Exception as e:
                logging.getLogger(__name__).error(f"Не удалось инициализировать EmailClassifier: {e}")
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