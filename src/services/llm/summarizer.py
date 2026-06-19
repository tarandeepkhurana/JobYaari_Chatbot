from typing import Optional
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from src.factories.llm_factory import LLMFactory
from src.db.chat_ops import update_chat_summary
from src.services.llm.prompts import (
    SUMMARIZATION_SYSTEM_PROMPT,
    SUMMARIZATION_USER_PROMPT,
)
import logging

logger = logging.getLogger("summarizer")

SUMMARY_THRESHOLD = 8      # summarize after 8 new messages
KEEP_FRESH_MESSAGES = 8     # always keep last 8 messages as full context


def _truncate_for_log(text: str, limit: int = 300) -> str:
    text = str(text or "").replace("\n", "\\n")

    if len(text) <= limit:
        return text

    return f"{text[:limit]}... [truncated {len(text) - limit} chars]"


def _extract_text(content) -> str:
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts = []

        for block in content:
            if isinstance(block, dict):
                if block.get("type") in {"text", "summary_text"}:
                    text_parts.append(str(block.get("text", "")))
                elif "text" in block:
                    text_parts.append(str(block.get("text", "")))
            else:
                text_parts.append(str(block))

        return "".join(text_parts)

    return str(content or "")


def _format_messages(messages: list[BaseMessage]) -> str:
    lines = []
    for m in messages:
        role = "User" if m.type == "human" else "Assistant"
        lines.append(f"{role}: {_extract_text(m.content)[:300]}")
    return "\n".join(lines)


async def generate_summary(
    messages: list[BaseMessage],
    existing_summary: Optional[str] = None,
) -> str:
    """Generate an updated summary based on new messages and existing summary."""

    logger.info(f"Generating summary. Existing summary length: {len(existing_summary) if existing_summary else 0}, new messages count: {len(messages)}")
    if not messages:
        return existing_summary or ""

    try:
        prompt = SUMMARIZATION_USER_PROMPT.format(
            existing_summary=existing_summary or "No existing summary yet.",
            messages=_format_messages(messages),
        )

        llm = LLMFactory.get_chat_llm()  # gpt-5-mini, cheap enough

        response = await llm.ainvoke([
            SystemMessage(content=SUMMARIZATION_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ])
        summary = _extract_text(response.content).strip()
        logger.info(
            "Generated summary length=%d preview=%s",
            len(summary),
            _truncate_for_log(summary),
        )
        return summary

    except Exception as e:
        logger.error(f"[SUMMARIZER] Failed: {e}")
        return existing_summary or ""


async def maybe_summarize_from_db(
    chat_id: str,
    current_summary: Optional[str] = None,
    summary_message_count: int = 0,
) -> None:
    """Check if we should generate a new summary based on message count, and update DB if so."""
    
    logger.info(f"Checking if summarization needed for chat_id: {chat_id}. Current summary length: {len(current_summary) if current_summary else 0}, summary_message_count: {summary_message_count}")

    from src.db.chat_ops import get_total_message_count, get_messages_range

    total = await get_total_message_count(chat_id)
    new_count = total - summary_message_count

    if new_count < SUMMARY_THRESHOLD:
        return

    summarize_up_to = total - KEEP_FRESH_MESSAGES
    if summarize_up_to % 2 != 0:
        summarize_up_to -= 1

    if summarize_up_to <= summary_message_count:
        return  # nothing new to summarize

    # KEY: only fetch NEW messages since last summary
    new_messages = await get_messages_range(
        chat_id,
        offset=summary_message_count,       # start from where we left off
        limit=summarize_up_to - summary_message_count,
    )

    if not new_messages:
        return

    new_summary = await generate_summary(
        new_messages,
        existing_summary=current_summary,   # rolling: build on top
    )

    if new_summary:
        await update_chat_summary(
            chat_id=chat_id,
            summary=new_summary,
            summary_message_count=summarize_up_to,
        )

