from uuid import UUID
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from src.auth.dependencies import get_current_user_id
from src.services.streaming.chat_stream_service import stream_chat_response
from src.db.chat_ops import create_chat_session

router = APIRouter(prefix="/chat", tags=["Chat"])


class CreateChatRequest(BaseModel):
    title: Optional[str] = None


class ChatRequest(BaseModel):
    query: str
    chat_id: UUID
    use_resume_profile: bool = False


@router.post("/sessions")
async def create_session(
    request: CreateChatRequest,
    user_id: UUID = Depends(get_current_user_id),
):
    return await create_chat_session(
        user_id=user_id,
        title=request.title or "New chat",
    )


@router.post("/stream")
async def stream_chat(
    request: ChatRequest,
    user_id: UUID = Depends(get_current_user_id),
):
    return StreamingResponse(
        stream_chat_response(
            query=request.query,
            user_id=user_id,
            chat_id=request.chat_id,
            use_resume_profile=request.use_resume_profile,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
