from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile

from src.auth.dependencies import get_current_user_id
from src.services.voice.transcription_service import transcribe_audio


router = APIRouter(prefix="/voice", tags=["Voice"])


@router.post("/transcribe")
async def transcribe_voice_input(
    file: UploadFile = File(...),
    user_id: UUID = Depends(get_current_user_id),
):
    """Transcribe a user-recorded audio clip for the chat composer."""

    text = await transcribe_audio(file)
    return {
        "text": text,
    }
