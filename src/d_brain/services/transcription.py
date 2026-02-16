"""Deepgram transcription service."""

import logging

from deepgram import AsyncDeepgramClient

logger = logging.getLogger(__name__)


class RateLimitException(Exception):
    """Raised when API rate limit is exceeded."""
    pass


class DeepgramTranscriber:
    """Service for transcribing audio using Deepgram Nova-3."""

    def __init__(self, api_key: str) -> None:
        self.client = AsyncDeepgramClient(api_key=api_key)

    async def transcribe(self, audio_bytes: bytes) -> str:
        """Transcribe audio bytes to text.

        Args:
            audio_bytes: Audio file content

        Returns:
            Transcribed text

        Raises:
            Exception: If transcription fails
        """
        logger.info("Starting transcription, audio size: %d bytes", len(audio_bytes))

        try:
            response = await self.client.listen.v1.media.transcribe_file(
                request=audio_bytes,
                model="nova-3",
                language="ru",
                punctuate=True,
                smart_format=True,
            )

            transcript = (
                response.results.channels[0].alternatives[0].transcript
                if response.results
                and response.results.channels
                and response.results.channels[0].alternatives
                else ""
            )

            logger.info("Transcription complete: %d chars", len(transcript))
            return transcript
        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "rate limit" in error_str or "too many requests" in error_str:
                logger.error("Deepgram rate limit exceeded: %s", e)
                raise RateLimitException(f"Deepgram rate limit exceeded: {e}")
            else:
                logger.exception("Transcription failed")
                raise
