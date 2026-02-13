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

router = Router(name="process")
logger = logging.getLogger(__name__)


@router.message(Command("process"))
async def cmd_process(message: Message) -> None:
    """Handle /process command - trigger LLM processing."""
    user_id = message.from_user.id if message.from_user else "unknown"
    logger.info("Process command triggered by user %s", user_id)

    status_msg = await message.answer("⏳ Обрабатываю записи...")

    settings = get_settings()
    processor = ClaudeProcessor(
        settings.vault_path,
        settings.todoist_api_key,
        settings.groq_api_key,
    )
    git = VaultGit(settings.vault_path)

    try:
        report = await processor.process_daily(date.today())
    except Exception as e:
        logger.exception("Process failed")
        report = {"error": str(e), "processed_entries": 0}

    # Commit and push changes
    if "error" not in report:
        today = date.today().isoformat()
        await asyncio.to_thread(git.commit_and_push, f"chore: process daily {today}")

    # Format and send report
    formatted = format_process_report(report)
    try:
        await status_msg.edit_text(formatted)
    except Exception:
        await status_msg.edit_text(formatted, parse_mode=None)
