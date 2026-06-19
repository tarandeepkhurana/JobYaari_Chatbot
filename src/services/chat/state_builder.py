import logging
from uuid import UUID

from langchain_core.messages import HumanMessage

from src.db.chat_ops import load_chat_state


logger = logging.getLogger("chat.state_builder")


async def build_initial_state(
    chat_id: UUID,
    user_id: UUID,
    user_query: str,
    use_resume_profile: bool = False,
) -> dict:
    """Build the per-request AgentState from persisted chat data."""

    logger.info(
        "Building initial state for chat_id=%s, user_id=%s",
        chat_id,
        user_id,
    )

    db_state = await load_chat_state(chat_id, user_id)
    messages = db_state["messages"]

    if not (
        messages
        and messages[-1].type == "human"
        and messages[-1].content.strip() == user_query.strip()
    ):
        messages = messages + [HumanMessage(content=user_query)]

    return {
        "user_id": db_state["user_id"],
        "chat_id": db_state["chat_id"],
        "current_query": user_query,
        "use_resume_profile": use_resume_profile,
        "messages": messages,
        "conversation_summary": db_state["conversation_summary"],
        "summary_message_count": db_state["summary_message_count"],
        "retrieved_jobs": db_state["retrieved_jobs"],
        "last_retrieval_query": db_state["last_retrieval_query"],
        "last_retrieval_filters": db_state["last_retrieval_filters"],
        "retrieval_decision": None,
        "retrieval_reason": None,
        "resume": db_state["resume"],
    }
