import json
import re
from managers.dataBase import DataBaseManager
from dotenv import load_dotenv
from datetime import datetime

import requests
import os

load_dotenv()

db = DataBaseManager()

YANDEX_API_KEY = os.getenv('YANDEX_API_KEY')
YANDEX_GPT_URL = os.getenv('YANDEX_GPT_URL')


class ManagerYandexGPT:
    def __init__(self):
        # «Контекст» текущего вызова — кто спрашивает и по какой теме.
        # Ставится в боте через set_context(tg_id, topic) перед парсингом.
        self._current_tg_id = None
        self._current_topic = None

    # ---------- публичный метод для бота ----------
    def set_context(self, tg_id, topic):
        """Вызывается в боте один раз перед parser_response_gpt."""
        self._current_tg_id = tg_id
        self._current_topic = topic

    # ---------- парсинг ответа YandexGPT ----------
    def parser_response_gpt(self, response) -> str:
        """Возвращает чистый ответ пользователю.
        Побочный эффект: если в тексте найден resume — сохраняет его в БД.
        """
        # Удаляем лишние пробелы и переносы в начале/конце
        response = response.strip()

        # Проверяем баланс скобок (быстрый тест на валидность JSON)
        if response.count('{') != response.count('}'):
            raise ValueError("Несбалансированные скобки в JSON")

        # Экранируем только настоящие переносы, не трогая \\n
        fixed_response = re.sub(r'(?<!\\)\n', r'\\n', response)

        try:
            data = json.loads(fixed_response)
        except json.JSONDecodeError as e:
            if "Extra data" in str(e):
                last_brace = fixed_response.rfind('}')
                if last_brace != -1:
                    fixed_response = fixed_response[:last_brace + 1]
            try:
                data = json.loads(fixed_response)
            except json.JSONDecodeError as final_error:
                error_pos = final_error.pos
                raise ValueError(
                    f"Не удалось распарсить JSON. Ошибка: {final_error}\n"
                    f"Проблемный участок: {fixed_response[max(0, error_pos - 50):error_pos + 50]}"
                ) from None

        if 'error' in data:
            return (
                "❌Произошла ошибка с выводом ответа от ИИ. Вероятно, вы отправили "
                "пустой запрос. Если это не так, то напишите в /support и подробно "
                "опишите ситуацию."
            )

        text = data["result"]["alternatives"][0]["message"]["text"]

        # --- отделяем resume от ответа ---
        answer, resume = self._split_answer_and_resume(text)

        # --- тихо сохраняем resume в БД, если есть контекст ---
        if resume and self._current_tg_id is not None and self._current_topic:
            try:
                self._save_resume(self._current_tg_id, self._current_topic, resume)
            except Exception as e:
                print(f"[parser_response_gpt] Не удалось сохранить resume: {e}")

        return answer
    def _get_summary(self):
        """Возвращает сохранённый summary для текущего (tg_id, topic) или ''."""
        if self._current_tg_id is None or not self._current_topic:
            return ""
        try:
            row = db.query_database(
                "SELECT cs.summary FROM chat_sessions cs "
                "JOIN users u ON u.user_id = cs.user_id "
                "WHERE u.tg_id=%s AND cs.topic=%s",
                (self._current_tg_id, self._current_topic)
            )
            if row and row[0][0]:
                return row[0][0]
        except Exception as e:
            print(f"[_get_summary] {e}")
        return ""


    # ---------- вспомогательные ----------
    def _split_answer_and_resume(self, text: str):
        """Делит текст на (answer, resume). Если resume нет — вернёт (text, '')."""
        if not text:
            return text, ""

        patterns = [
            r'resume\s*:\s*\{(.*)\}\s*$',
            r'резюме\s*:\s*\{(.*)\}\s*$',
            r'resume\s*:\s*\{(.*)\}',
            r'резюме\s*:\s*\{(.*)\}',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
            if match:
                resume = match.group(1).strip()[:500]
                answer = (text[:match.start()] + text[match.end():]).strip()
                if not answer:
                    answer = text.strip()
                return answer, resume

        return text.strip(), ""
    
    def _save_resume(self, tg_id: int, topic: str, resume: str):
        """Сохраняет resume в chat_sessions. Создаёт сессию, если её нет."""
        # tg_id -> user_id
        row = db.query_database(
            "SELECT user_id FROM users WHERE tg_id=%s", (tg_id,)
        )
        if not row:
            return
        user_id = row[0][0]

        # ищем сессию
        sess = db.query_database(
            "SELECT id FROM chat_sessions WHERE user_id=%s AND topic=%s",
            (user_id, topic)
        )

        if sess:
            session_id = sess[0][0]
            db.query_database(
                "UPDATE chat_sessions SET summary=%s, updated_at=NOW() WHERE id=%s",
                (resume, session_id), reg=True
            )
        else:
            db.query_database(
                "INSERT INTO chat_sessions (user_id, topic, summary) VALUES (%s, %s, %s)",
                (user_id, topic, resume), reg=True
            )
            print("вставлено")


    
    # ---------- запрос к YandexGPT ----------
    def ask_yandex_gpt(self, request: str, system_message: str) -> str:
        try:
            headers = {
                "Authorization": f'Api-Key {YANDEX_API_KEY}'
            }

            system_with_resume = (
                re.sub(r'\b[A-Za-z]+\d+\b', '', system_message.replace(' ', '').replace('\n', ''))
                + "\n\nВАЖНО: в самом конце ответа, ПОСЛЕ основного текста, добавь ровно одну строку:\n"
                + "resume: {краткий конспект диалога, 3-4 предложения}\n"
                + "Требования к resume: с фигурными скобкам вкоруг сути;"
                + "пользователь и что обсудили; без пояснений и мета-текста." 
                + "ограничивай символами не больше 50, чтобы следующие запросы выполнялись"
            )
            summary = self._get_summary()
            if summary:
                full_request = f"[Контекст прошлого диалога]\n{summary}\n\n[Текущий вопрос]\n{request}"
            else:
                full_request = request
            
            promt = {
                "modelUri": "gpt://b1gmotqp93hmcr4jnin8/yandexgpt",
                "completionOptions": {
                    "stream": False,
                    "temperature": 0.6,
                    "maxTokens": "2000",
                    "reasoningOptions": {
                        "mode": "DISABLED"
                    }
                },
                "messages": [
                    {
                        "role": "system",
                        "text": system_with_resume
                    },
                    {
                        "role": "user",
                        "text": full_request
                    }
                ]
            }

            response = requests.post(YANDEX_GPT_URL, headers=headers, json=promt, timeout=60)
            result = response.text
            print(result)
            return result, False
        except Exception as e:
            return f"❌ Ошибка при исполнении: {e}. Передайте ее в /support. ", True