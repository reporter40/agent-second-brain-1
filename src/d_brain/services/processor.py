"""LLM processing service using Groq API."""

import logging
from datetime import date
from pathlib import Path
from typing import Any

import httpx

from d_brain.services.session import SessionStore

logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"
DEFAULT_TIMEOUT = 120  # seconds


class ClaudeProcessor:
    """Service for LLM processing via Groq API.

    Note: Class keeps the name ClaudeProcessor for backward compatibility
    with existing handler imports.
    """

    def __init__(self, vault_path: Path, todoist_api_key: str = "", groq_api_key: str = "") -> None:
        self.vault_path = Path(vault_path)
        self.todoist_api_key = todoist_api_key
        self.groq_api_key = groq_api_key
        # We initialize storage internally to ensure consistent path logic
        from d_brain.services.storage import VaultStorage
        self.storage = VaultStorage(self.vault_path)

    async def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Call Groq API for chat completion.

        Args:
            system_prompt: System instructions for the model
            user_prompt: User's message/request

        Returns:
            Model response text
        """
        if not self.groq_api_key:
            return "❌ GROQ_API_KEY не настроен. Добавьте ключ в переменные окружения."

        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 2000,
        }

        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            try:
                response = await client.post(GROQ_API_URL, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except httpx.HTTPStatusError as e:
                # Re-raise with specific message for 429 to be caught by handle_rate_limit
                if e.response.status_code == 429:
                    raise  # Will be caught by handle_rate_limit mechanism
                raise

    def _get_session_context(self, user_id: int) -> str:
        """Get today's session context."""
        if user_id == 0:
            return ""

        session = SessionStore(self.vault_path)
        today_entries = session.get_today(user_id)
        if not today_entries:
            return ""

        lines = ["=== СЕГОДНЯШНИЕ ЗАПИСИ ==="]
        for entry in today_entries[-10:]:
            ts = entry.get("ts", "")[11:16]
            entry_type = entry.get("type", "unknown")
            text = entry.get("text", "")[:80]
            if text:
                lines.append(f"{ts} [{entry_type}] {text}")
        lines.append("=== КОНЕЦ ЗАПИСЕЙ ===\n")
        return "\n".join(lines)

    def _html_to_markdown(self, html: str) -> str:
        """Convert Telegram HTML to Obsidian Markdown."""
        import re

        text = html
        text = re.sub(r"<b>(.*?)</b>", r"**\1**", text)
        text = re.sub(r"<i>(.*?)</i>", r"*\1*", text)
        text = re.sub(r"<code>(.*?)</code>", r"`\1`", text)
        text = re.sub(r"<s>(.*?)</s>", r"~~\1~~", text)
        text = re.sub(r"</?u>", "", text)
        text = re.sub(r'<a href="([^"]+)">([^<]+)</a>', r"[\2](\1)", text)
        return text

    def _save_weekly_summary(self, report_html: str, week_date: date) -> Path:
        """Save weekly summary to vault/summaries/."""
        year, week, _ = week_date.isocalendar()
        filename = f"{year}-W{week:02d}-summary.md"
        summary_dir = self.vault_path / "summaries"
        summary_dir.mkdir(parents=True, exist_ok=True)
        summary_path = summary_dir / filename

        content = self._html_to_markdown(report_html)
        frontmatter = f"""---
date: {week_date.isoformat()}
type: weekly-summary
week: {year}-W{week:02d}
---

"""
        summary_path.write_text(frontmatter + content)
        logger.info("Weekly summary saved to %s", summary_path)
        return summary_path

    async def process_daily(self, day: date | None = None) -> dict[str, Any]:
        """Process daily file with LLM."""
        if day is None:
            day = date.today()

        # Use Storage service to read file - ensures consistency with /status
        daily_content = self.storage.read_daily(day)

        if not daily_content:
            logger.warning("No daily content found for %s via Storage", day)
            # Try debugging: does the file exist on disk?
            fpath = self.storage.get_daily_file(day)
            logger.info("Checked path: %s (exists=%s)", fpath.absolute(), fpath.exists())
            return {"error": f"Нет записей за {day}", "processed_entries": 0}

        system_prompt = """Ты — персональный ассистент d-brain. Твоя задача — обработать дневные записи пользователя.

ПРАВИЛА:
1. Проанализируй все записи за день
2. Выдели ключевые мысли и идеи
3. Найди задачи (явные и неявные)
4. Определи эмоциональный фон
5. Предложи действия

ФОРМАТ ОТВЕТА:
- Используй ТОЛЬКО HTML-теги для Telegram: <b>, <i>, <code>
- НЕ используй markdown (**, ##, ```)
- Начни с: 📊 <b>Обработка за ДАТУ</b>
- Будь кратким — лимит Telegram 4096 символов
- Пиши на русском языке"""

        user_prompt = f"""Сегодня {day}. Обработай записи за день:

{daily_content}"""

        output = await self._call_llm(system_prompt, user_prompt)
        return {"report": output, "processed_entries": 1}

    async def execute_prompt(self, user_prompt: str, user_id: int = 0) -> dict[str, Any]:
        """Execute arbitrary prompt with LLM."""
        today = date.today()
        session_context = self._get_session_context(user_id)

        system_prompt = f"""Ты — персональный ассистент d-brain.

КОНТЕКСТ:
- Дата: {today}
- Vault: {self.vault_path}

{session_context}

ПРАВИЛА:
- Отвечай кратко и по делу
- Используй ТОЛЬКО HTML-теги для Telegram: <b>, <i>, <code>
- НЕ используй markdown (**, ##, ```)
- Начни с emoji и <b>заголовка</b>
- Лимит 4096 символов
- Пиши на русском языке"""

        output = await self._call_llm(system_prompt, user_prompt)
        return {"report": output, "processed_entries": 1}

    async def generate_weekly(self) -> dict[str, Any]:
        """Generate weekly digest with LLM."""
        today = date.today()

        # Collect daily files for the last 7 days
        week_content = []
        for i in range(7):
            from datetime import timedelta
            day = today - timedelta(days=i)
            # Use Storage service
            content = self.storage.read_daily(day)
            if content:
                week_content.append(f"--- {day} ---\n{content}")

        if not week_content:
            return {"error": "Нет записей за последнюю неделю", "processed_entries": 0}

        all_content = "\n\n".join(week_content)

        system_prompt = """Ты — персональный ассистент d-brain. Сгенерируй недельный дайджест.

ПРАВИЛА:
1. Проанализируй записи за неделю
2. Выдели главные темы и тренды
3. Отметь победы и достижения
4. Определи вызовы и проблемы
5. Предложи фокус на следующую неделю

ФОРМАТ ОТВЕТА:
- Используй ТОЛЬКО HTML-теги для Telegram: <b>, <i>, <code>
- НЕ используй markdown
- Начни с: 📅 <b>Недельный дайджест</b>
- Будь кратким — лимит 4096 символов
- Пиши на русском языке"""

        user_prompt = f"""Сегодня {today}. Вот записи за неделю:

{all_content}"""

        output = await self._call_llm(system_prompt, user_prompt)

        # Save to summaries/
        try:
            self._save_weekly_summary(output, today)
        except Exception as e:
            logger.warning("Failed to save weekly summary: %s", e)

        return {"report": output, "processed_entries": 1}
