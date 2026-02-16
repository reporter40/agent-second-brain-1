"""Voice message handler."""

import logging
from datetime import datetime

from aiogram import Bot, Router
from aiogram.types import Message

from d_brain.config import get_settings
from d_brain.services.session import SessionStore
from d_brain.services.storage import VaultStorage
from d_brain.services.transcription import DeepgramTranscriber
from d_brain.utils import handle_rate_limit, RateLimitException

router = Router(name="voice")
logger = logging.getLogger(__name__)


@router.message(lambda m: m.voice is not None)
async def handle_voice(message: Message, bot: Bot) -> None:
    """Handle voice messages."""
    if not message.voice or not message.from_user:
        return

    await message.chat.do(action="typing")

    settings = get_settings()
    storage = VaultStorage(settings.vault_path)
    transcriber = DeepgramTranscriber(settings.deepgram_api_key)

    try:
        file = await bot.get_file(message.voice.file_id)
        if not file.file_path:
            await message.answer("Failed to download voice message")
            return

        file_bytes = await bot.download_file(file.file_path)
        if not file_bytes:
            await message.answer("Failed to download voice message")
            return

        audio_bytes = file_bytes.read()
        
        # Handle potential rate limiting when transcribing
        try:
            transcript = await handle_rate_limit(transcriber.transcribe, audio_bytes)
        except RateLimitException as e:
            logger.error(f"Rate limit exceeded during transcription: {e}")
            await message.answer("⚠️ Слишком много запросов. Попробуйте немного позже.")
            return

        if not transcript:
            await message.answer("Could not transcribe audio")
            return

        timestamp = datetime.fromtimestamp(message.date.timestamp())
        storage.append_to_daily(transcript, timestamp, "[voice]")

        # Log to session
        session = SessionStore(settings.vault_path)
        session.append(
            message.from_user.id,
            "voice",
            text=transcript,
            duration=message.voice.duration,
            msg_id=message.message_id,
        )

        try:
            await message.answer(f"🎤 {transcript}\n\n✓ Сохранено")
        except Exception as e:
            if "429" in str(e).lower() or "rate limit" in str(e).lower():
                logger.warning("Rate limit hit when sending voice response")
            else:
                logger.error(f"Error sending response: {e}")
                
        logger.info("Voice message saved: %d chars", len(transcript))

    except Exception as e:
        logger.exception("Error processing voice message")
        try:
            await message.answer(f"Error: {e}")
        except Exception as response_error:
            if "429" in str(response_error).lower() or "rate limit" in str(response_error).lower():
                logger.warning("Rate limit hit when sending error response")
            else:
                logger.error(f"Error sending error response: {response_error}")
