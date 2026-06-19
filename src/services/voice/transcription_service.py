from io import BytesIO
import logging

from fastapi import HTTPException, UploadFile, status
from openai import AsyncOpenAI

from src.config import settings


logger = logging.getLogger("voice.transcription")

MAX_AUDIO_BYTES = 15 * 1024 * 1024


async def transcribe_audio(file: UploadFile) -> str:
    """Transcribe a short user-recorded audio clip into text."""

    if not file.content_type or not file.content_type.startswith("audio/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be an audio file",
        )

    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audio file is empty",
        )

    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Audio file is too large",
        )

    audio_file = BytesIO(audio_bytes)
    audio_file.name = file.filename or "voice-input.webm"

    logger.info(
        "Transcribing voice input | filename=%s | content_type=%s | bytes=%d",
        audio_file.name,
        file.content_type,
        len(audio_bytes),
    )

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    transcript = await client.audio.transcriptions.create(
        model=settings.OPENAI_TRANSCRIPTION_MODEL,
        file=audio_file,
    )

    text = getattr(transcript, "text", "") or ""
    return text.strip()
