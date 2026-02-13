"""Weekly digest command handler."""

import asyncio
import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from d_brain.bot.formatters import format_process_report
from d_brain.config import get_settings
from d_brain.services.git import VaultGit
from d_brain.services.processor import ClaudeProcessor

router = Router(name="weekly")
logger = logging.getLogger(__name__)


@router.message(Command("weekly"))
async def cmd_weekly(message: Message) -> None:
    """Handle /weekly command - generate weekly digest."""
    user_id = message.from_user.id if message.from_user else "unknown"
    logger.info("Weekly digest triggered by user %s", user_id)

    status_msg = await message.answer("⏳ Генерирую недельный дайджест...")

    settings = get_settings()
    processor = ClaudeProcessor(
        settings.vault_path,
        settings.todoist_api_key,
        settings.groq_api_key,
    )
    git = VaultGit(settings.vault_path)

    try:
        report = await processor.generate_weekly()
    except Exception as e:
        logger.exception("Weekly digest failed")
        report = {"error": str(e), "processed_entries": 0}

    # Commit any changes
    if "error" not in report:
        await asyncio.to_thread(git.commit_and_push, "chore: weekly digest")

    formatted = format_process_report(report)
    try:
        await status_msg.edit_text(formatted)
    except Exception:
        await status_msg.edit_text(formatted, parse_mode=None)
