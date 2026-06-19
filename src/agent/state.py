from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    # Chat identity loaded from DB.
    user_id: str
    chat_id: str

    # Current user turn.
    current_query: str
    use_resume_profile: bool

    # Recent messages after the rolling summary cutoff.
    messages: Annotated[list, add_messages]

    # Long-running conversation memory.
    conversation_summary: str | None
    summary_message_count: int

    # Retrieval cache used by the job search tool loop.
    retrieved_jobs: list
    last_retrieval_query: str | None
    last_retrieval_filters: dict | None

    # Optional routing/debug metadata retained for compatibility.
    retrieval_decision: str | None
    retrieval_reason: str | None

    # Parsed resume/profile context for answer generation.
    resume: dict | None
