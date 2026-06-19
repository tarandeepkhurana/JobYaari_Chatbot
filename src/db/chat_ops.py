from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import func, select
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    AIMessage,
)

from src.db.client import get_read_session, get_write_session   
from src.db.models import (
    Chat,
    Message,
    User,
)
from src.db.resume_ops import get_resume_by_user

import logging

logger = logging.getLogger("db.chat_ops")


def _has_vector(value) -> bool:
    if value is None:
        return False

    try:
        return len(value) > 0
    except TypeError:
        return True


async def create_chat_session(
    user_id: UUID,
    title: str = "New chat",
) -> dict:
    """Create a chat session for a user and return the new chat metadata."""

    clean_title = title.strip() or "New chat"

    async with get_write_session() as session:
        user = await session.get(User, user_id)
        if user is None:
            session.add(User(id=user_id))

        chat = Chat(
            user_id=user_id,
            title=clean_title,
        )
        session.add(chat)
        await session.flush()

        return {
            "chat_id": str(chat.id),
            "user_id": str(user_id),
            "title": chat.title,
        }


async def load_chat_state(
    chat_id: UUID,
    user_id: UUID,
) -> dict:
    """Load everything related to this chat from DB, and return as dict for agent state."""

    logger.info(f"Loading chat state for chat_id: {chat_id}, user_id: {user_id}")

    async with get_read_session() as session:

        # -------------------------
        # Chat
        # -------------------------

        chat_result = await session.execute(
            select(Chat).where(
                Chat.id == chat_id,
                Chat.user_id == user_id,
            )
        )

        chat = chat_result.scalar_one_or_none()

        if not chat:
            raise ValueError("Chat not found")

        # -------------------------
        # Messages after the rolling summary cutoff.
        # -------------------------

        messages_result = await session.execute(
            select(Message)
            .where(Message.chat_id == chat_id)
            .order_by(Message.created_at.asc())
            .offset(chat.summary_message_count or 0)   # start from after summary
        )

        db_messages = list(messages_result.scalars().all())

        messages = []

        for msg in db_messages:

            if msg.message_type == "user":

                messages.append(
                    HumanMessage(
                        content=msg.content
                    )
                )

            elif msg.message_type == "assistant":

                messages.append(
                    AIMessage(
                        content=msg.content
                    )
                )
        
        resume_data = await get_resume_by_user(user_id) or {}
        
        logger.info(
            "Loaded chat state: messages=%d, resume=%s, resume_intents=%d, resume_embedding=%s",
            len(messages),
            bool(resume_data),
            len(resume_data.get("intents") or []),
            _has_vector(resume_data.get("embedding")),
        )

        return {
            "user_id": str(user_id),
            "chat_id": str(chat_id),

            "messages": messages,

            "conversation_summary":
                chat.conversation_summary,

            "summary_message_count":
                chat.summary_message_count,

            "retrieved_jobs":
                chat.retrieved_jobs or [],

            "last_retrieval_query":
                chat.last_retrieval_query,

            "last_retrieval_filters":
                chat.last_retrieval_filters,

            "resume": resume_data,
        }
    
async def save_chat_turn(
    chat_id,
    user_query,
    assistant_response,
):
    """Save the user query and assistant response as messages in the DB after the turn is done."""

    logger.info(f"Saving chat turn for chat_id: {chat_id}. User query length: {len(user_query)}, Assistant response length: {len(assistant_response)}")

    async with get_write_session() as session:

        session.add(
            Message(
                chat_id=chat_id,
                message_type="user",
                content=user_query,
            )
        )

        session.add(
            Message(
                chat_id=chat_id,
                message_type="assistant",
                content=assistant_response,
            )
        )
    
    logger.info(f"Chat turn saved successfully for chat_id: {chat_id}")
    


async def update_chat_retrieved_jobs(
    chat_id,
    retrieved_jobs,
    last_retrieval_query=None,
    last_retrieval_filters=None,
):
    logger.info(f"Updating retrieved jobs for chat_id: {chat_id}. Number of jobs: {len(retrieved_jobs)}")
    
    async with get_write_session() as session:

        chat = await session.get(Chat, chat_id)
        if not chat:
            raise ValueError("Chat not found")

        chat.retrieved_jobs = retrieved_jobs
        chat.last_retrieval_query = last_retrieval_query
        chat.last_retrieval_filters = last_retrieval_filters
        chat.retrieval_updated_at = datetime.now(timezone.utc)

    logger.info(f"Retrieved jobs updated successfully for chat_id: {chat_id}")

async def update_chat_summary(
    chat_id: str,
    summary: str,
    summary_message_count: int,
):  
    """Update the conversation summary and summary_message_count for the chat in DB."""
    logger.info(f"Updating chat summary for chat_id: {chat_id}. Summary length: {len(summary)}, summary_message_count: {summary_message_count}")
    async with get_write_session() as session:
        chat = await session.get(Chat, chat_id)
        if chat:
            chat.conversation_summary = summary
            chat.summary_message_count = summary_message_count
            chat.summary_updated_at = datetime.now(timezone.utc)

    logger.info(f"Chat summary updated successfully for chat_id: {chat_id}")


async def get_total_message_count(chat_id: str) -> int:
    """Return total persisted messages for a chat."""

    async with get_read_session() as session:
        result = await session.execute(
            select(func.count(Message.id)).where(Message.chat_id == chat_id)
        )
        return result.scalar_one()


async def get_messages_range(
    chat_id: str,
    offset: int,
    limit: int,
) -> list[BaseMessage]:
    """Fetch a range of messages for the chat, used for summarization."""

    logger.info(f"Fetching messages for chat_id: {chat_id} with offset: {offset}, limit: {limit}")

    async with get_read_session() as session:
        result = await session.execute(
            select(Message)
            .where(Message.chat_id == chat_id)
            .order_by(Message.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        rows = result.scalars().all()
        messages = []
        for msg in rows:
            if msg.message_type == "user":
                messages.append(HumanMessage(content=msg.content))
            elif msg.message_type == "assistant":
                messages.append(AIMessage(content=msg.content))
        
        logger.info(f"Fetched {len(messages)} messages for chat_id: {chat_id} with offset: {offset}, limit: {limit}")
        
        return messages
