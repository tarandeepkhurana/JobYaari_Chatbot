import asyncio
import json
import logging
from typing import AsyncGenerator
from uuid import UUID

from src.agent.streaming_agent import run_agent_stream
from src.db.chat_ops import save_chat_turn
from src.services.chat.state_builder import build_initial_state
from src.services.llm.summarizer import maybe_summarize_from_db


logger = logging.getLogger("chat_stream_service")


def sse_event(event: str, data: dict) -> str:
    """Encode one server-sent event."""

    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


async def stream_chat_response(
    query: str,
    user_id: UUID,
    chat_id: UUID,
    use_resume_profile: bool = False,
) -> AsyncGenerator[str, None]:

    try:
        state = await build_initial_state(
            chat_id=chat_id,
            user_id=user_id,
            user_query=query,
            use_resume_profile=use_resume_profile,
        )
    except ValueError as e:
        yield sse_event("error", {"message": str(e)})
        return

    final_answer = ""

    try:
        async for agent_event in run_agent_stream(state):
            event_name = agent_event.get("event")
            data = agent_event.get("data", {})

            if event_name == "done":
                final_answer = data.get("final_answer", "")
                break

            if event_name in {"status", "thinking", "token", "jobs", "error"}:
                yield sse_event(event_name, data)

            if event_name == "error":
                return

    except Exception:
        logger.exception("Chat stream failed")
        yield sse_event("error", {"message": "Chat stream failed"})
        return

    await save_chat_turn(
        chat_id=chat_id,
        user_query=query,
        assistant_response=final_answer,
    )

    asyncio.create_task(
        maybe_summarize_from_db(
            chat_id=str(chat_id),
            current_summary=state.get("conversation_summary"),
            summary_message_count=state.get("summary_message_count", 0),
        )
    )

    yield sse_event("done", {"final_answer": final_answer})
