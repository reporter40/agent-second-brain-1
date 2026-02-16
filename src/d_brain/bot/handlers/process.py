"""Process command handler."""

import asyncio
import logging
from datetime import date

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from d_brain.bot.formatters import format_process_report
from d_brain.config import get_settings
from d_brain.services.git import VaultGit
from d_brain.services.processor import ClaudeProcessor
from d_brain.utils import handle_rate_limit, RateLimitException

router = Router(name="process")
logger = logging.getLogger(__name__)


@router.message(Command("process"))
async def cmd_process(message: Message) -> None:
    """Handle /process command - trigger LLM processing."""
    user_id = message.from_user.id if message.from_user else "unknown"
    logger.info("Process command triggered by user %s", user_id)

    try:
        status_msg = await message.answer("⏳ Обрабатываю записи...")
    except Exception as e:
        logger.exception("Error sending initial processing message")
        if "429" in str(e).lower() or "rate limit" in str(e).lower():
            await message.answer("⚠️ Слишком много запросов. Попробуйте чуть позже.")
            return
        else:
            raise

    settings = get_settings()
    processor = ClaudeProcessor(
        settings.vault_path,
        settings.todoist_api_key,
        settings.groq_api_key,
    )
    git = VaultGit(settings.vault_path)

    try:
        report = await handle_rate_limit(
            processor.process_daily, 
            date.today(),
            delay=2.0,
            max_retries=3
        )
    except Exception as e:
        logger.exception("Process failed")
        error_str = str(e).lower()
        if "429" in error_str or "rate limit" in error_str:
            report = {"error": "⚠️ Превышен лимит запросов. Попробуйте позже.", "processed_entries": 0}
        else:
            report = {"error": str(e), "processed_entries": 0}

    # Commit and push changes
    if "error" not in report:
        today = date.today().isoformat()
        await asyncio.to_thread(git.commit_and_push, f"chore: process daily {today}")

    # Format and send report
    formatted = format_process_report(report)
    try:
        await status_msg.edit_text(formatted)
    except Exception as e:
        if "429" in str(e).lower() or "rate limit" in str(e).lower():
            # If can't edit due to rate limit, send new message
            try:
                await asyncio.sleep(1)
                await message.answer(formatted)
            except:
                await message.answer("Обработка завершена, но не удалось обновить сообщение.")
        else:
            await status_msg.edit_text(formatted, parse_mode=None)
