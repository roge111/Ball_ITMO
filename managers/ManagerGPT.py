# -*- coding: utf-8 -*-
import json
import re
import requests
import os
from dotenv import load_dotenv

from managers.dataBase import DataBaseManager
from managers.logger import log

load_dotenv()

db = DataBaseManager()

YANDEX_API_KEY = os.getenv('YANDEX_API_KEY')
YANDEX_GPT_URL = os.getenv('YANDEX_GPT_URL')

RESUME_INSTRUCTION = (
    "\n\nВАЖНО: в самом конце ответа, ПОСЛЕ основного текста, добавь ровно одну строку:\n"
    + "resume: {краткий конспект диалога, 3-4 предложения}\n"
    + "Требования к resume: с фигурными скобками вокруг сути;"
    + "пользователь и что обсудили; без пояснений и мета-текста."
    + "ограничивай символами не больше 50, чтобы следующие запросы выполнялись"
)


class ManagerYandexGPT:
    def __init__(self):
        # «Контекст» текущего вызова — кто спрашивает и по какой теме.
        self._current_tg_id = None
        self._current_topic = None

    # ---------- контекст ----------
    def set_context(self, tg_id, topic):
        """Вызывается в боте один раз перед parser_response_gpt."""
        self._current_tg_id = tg_id
        self._current_topic = topic

    # ---------- работа с summary ----------
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
            log("ManagerGPT", f"[_get_summary] {e}")
        return ""

    def _save_resume(self, tg_id: int, topic: str, resume: str):
        """Сохраняет resume в chat_sessions. Создаёт сессию, если её нет."""
        row = db.query_database(
            "SELECT user_id FROM users WHERE tg_id=%s", (tg_id,)
        )
        if not row:
            return
        user_id = row[0][0]

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
            log("ManagerGPT", "chat_sessions: вставлено")

    # ---------- парсинг ответа ----------
    def parser_response_gpt(self, response) -> str:
        """Возвращает чистый ответ пользователю.
        Побочный эффект: если найден resume — сохраняет его в БД.
        """
        response = response.strip()

        if response.count('{') != response.count('}'):
            raise ValueError("Несбалансированные скобки в JSON")

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

        answer, resume = self._split_answer_and_resume(text)

        if resume and self._current_tg_id is not None and self._current_topic:
            try:
                self._save_resume(self._current_tg_id, self._current_topic, resume)
            except Exception as e:
                log("ManagerGPT", f"[parser_response_gpt] Не удалось сохранить resume: {e}")

        return answer

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

    # ---------- сборка system-сообщения ----------
    def _build_system(self, base_system: str, summary: str = "") -> str:
        """Собирает system-сообщение — как в оригинале, с replace(' ','').replace('\\n','')."""
        cleaned = re.sub(
            r'\b[A-Za-z]+\d+\b', '',
            base_system.replace(' ', '').replace('\n', '')
        )
        text = cleaned + RESUME_INSTRUCTION
        if summary:
            text += f"Контекст: {summary}"
        text += "Отвечай быстро, можешь использовать и из интернета."
        return text

    # ---------- сам запрос ----------
    def _call_gpt(self, system_text: str, user_text: str, timeout: int):
        """Делает один запрос к YandexGPT. Возвращает (result, ok)."""
        headers = {"Authorization": f'Api-Key {YANDEX_API_KEY}'}

        prompt = {
            "modelUri": "gpt://b1gmotqp93hmcr4jnin8/yandexgpt",
            "completionOptions": {
                "stream": False,
                "temperature": 0.6,
                "maxTokens": "4000",
                "reasoningOptions": {"mode": "DISABLED"}
            },
            "messages": [
                {"role": "system", "text": system_text},
                {"role": "user", "text": user_text + 'Кратко'},
            ]
        }

        log("ManagerGPT", system_text)
        log("ManagerGPT", len(system_text.replace(' ', '').replace('\n', '')))

        response = requests.post(YANDEX_GPT_URL, headers=headers, json=prompt, timeout=timeout)
        return response.text, False

    def ask_yandex_gpt(self, request: str, system_message: str):
        """
        1) Если есть summary — сначала пробуем с ним, таймаут 40 секунд.
        2) Если не успел — повторяем БЕЗ summary, таймаут 60 секунд.
        3) Если и это не удалось — возвращаем ошибку.
        """
        summary = self._get_summary()

        # ---- Попытка 1: с summary (если есть), таймаут 40 сек ----
        if summary:
            system_text = self._build_system(system_message, summary)
            log("ManagerGPT", f"[ask] Попытка 1 (с summary), длина: {len(system_text)}")
            try:
                result, err = self._call_gpt(system_text, request, timeout=40)
                if not err:
                    log("ManagerGPT", "[ask] Попытка 1: успешно")
                    return result, False
            except requests.exceptions.Timeout:
                log("ManagerGPT", "[ask] Попытка 1: timeout 40s, пробуем без summary")
            except Exception as e:
                log("ManagerGPT", f"[ask] Попытка 1: ошибка — {e}. Пробуем без summary")

        # ---- Попытка 2: без summary, таймаут 60 сек ----
        system_text = self._build_system(system_message, summary="")
        log("ManagerGPT", f"[ask] Попытка 2 (без summary), длина: {len(system_text)}")
        try:
            result, err = self._call_gpt(system_text, request, timeout=60)
            if not err:
                log("ManagerGPT", "[ask] Попытка 2: успешно")
                return result, False
        except requests.exceptions.Timeout:
            log("ManagerGPT", "[ask] Попытка 2: timeout 60s")
            return "❌ YandexGPT не ответил вовремя. Попробуйте позже.", True
        except Exception as e:
            log("ManagerGPT", f"[ask] Попытка 2: ошибка — {e}")
            return f"❌ Ошибка при исполнении: {e}. Передайте в /support.", True

        return "❌ YandexGPT вернул пустой ответ.", True