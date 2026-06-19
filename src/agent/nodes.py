import json
import logging
from typing import Literal
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langchain_core.tools import tool
from src.agent.state import AgentState
from src.factories.llm_factory import LLMFactory
from src.services.retrieval.retrieval_pipeline import retrieve_jobs
from src.services.llm.prompts import JOBLENS_AGENT_SYSTEM_PROMPT

logger = logging.getLogger("agent.nodes")


LOG_CONTENT_PREVIEW_CHARS = 300


@tool
async def search_jobs(
    query: str,
    retrieval_mode: Literal[
        "normal",
        "augment_resume",
        "resume_only",
    ] = "normal",
) -> dict:
    """Search jobs using normal, resume-augmented, or resume-only mode."""

    return await retrieve_jobs(query)


def _format_job_location(job: dict) -> str:
    if job.get("remote"):
        return "Remote"

    cities = job.get("cities") or []
    if cities:
        return ", ".join(cities)

    return "NA"


def _truncate_for_log(text: str, limit: int = LOG_CONTENT_PREVIEW_CHARS) -> str:
    text = text.replace("\n", "\\n")

    if len(text) <= limit:
        return text

    return f"{text[:limit]}... [truncated {len(text) - limit} chars]"


def _get_message_role(message) -> str:
    if isinstance(message, dict):
        return message.get("role") or "unknown"

    return getattr(message, "type", "unknown")


def _get_message_content(message) -> str:
    if isinstance(message, dict):
        return str(message.get("content", ""))

    return str(getattr(message, "content", ""))


def _preview_messages_for_log(messages: list[BaseMessage]) -> list[dict]:
    previews = []

    for index, message in enumerate(messages):
        content = _get_message_content(message)
        previews.append({
            "index": index,
            "role": _get_message_role(message),
            "content_length": len(content),
            "content_preview": _truncate_for_log(content),
        })

    return previews


def _summarize_state_for_log(state: AgentState) -> dict:
    resume = state.get("resume") or {}
    retrieved_jobs = state.get("retrieved_jobs") or []
    messages = state.get("messages") or []

    return {
        "user_id": state.get("user_id"),
        "chat_id": state.get("chat_id"),
        "current_query": _truncate_for_log(
            str(state.get("current_query") or ""),
            limit=120,
        ),
        "messages_count": len(messages),
        "message_roles": [_get_message_role(message) for message in messages[-5:]],
        "conversation_summary_length": len(state.get("conversation_summary") or ""),
        "summary_message_count": state.get("summary_message_count", 0),
        "resume_uploaded": bool(resume),
        "resume_updated_at": resume.get("updated_at"),
        "retrieved_jobs_count": len(retrieved_jobs),
        "retrieved_job_titles": [
            job.get("title")
            for job in retrieved_jobs[:5]
            if isinstance(job, dict)
        ],
        "last_retrieval_query": state.get("last_retrieval_query"),
        "use_resume_profile": state.get("use_resume_profile", False),
    }


def _format_prompt_list(values) -> str:
    if not values:
        return "Not available"

    if isinstance(values, list):
        return ", ".join(str(value) for value in values[:12]) or "Not available"

    return str(values)


def _extract_response_text(content) -> str:
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts = []

        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(block.get("text", ""))

        return "".join(text_parts)

    return str(content or "")


def _compact_job_for_tool(job: dict) -> dict:
    return {
        "id": job.get("id"),
        "title": job.get("title"),
        "company": job.get("org_name"),
        "location": _format_job_location(job),
        "work_mode": job.get("work_mode"),
        "compensation": job.get("stipend_display") or job.get("salary_display"),
        "duration": job.get("duration_display"),
        "skills": job.get("skills") or [],
        "application_url": job.get("source_url"),
        "rerank_score": job.get("rerank_score"),
    }


def _compact_retrieval_result_for_tool(result: dict) -> dict:
    jobs = result.get("results", [])

    return {
        "query": result.get("query"),
        "parsed": result.get("parsed"),
        "message": result.get("message"),
        "results": [_compact_job_for_tool(job) for job in jobs],
    }


def _get_tool_calls(response: AIMessage) -> list[dict]:
    return getattr(response, "tool_calls", None) or []


def _get_tool_call_id(tool_call: dict) -> str:
    return tool_call.get("id") or tool_call.get("tool_call_id") or ""


def _get_tool_call_name(tool_call: dict) -> str:
    return tool_call.get("name") or ""


def _get_tool_call_args(tool_call: dict) -> dict:
    args = tool_call.get("args") or {}

    if isinstance(args, str):
        try:
            return json.loads(args)
        except json.JSONDecodeError:
            return {"query": args}

    return args


def _build_resume_context_for_prompt(state: AgentState) -> str:
    resume = state.get("resume")

    if not resume:
        return "Status: not_uploaded\nNo resume has been uploaded for this user yet."

    parsed = resume.get("parsed_data") or {}
    resume_text = resume.get("resume_text") or ""

    lines = [
        "Status: uploaded",
        f"Updated at: {resume.get('updated_at') or 'Not available'}",
        f"Summary: {parsed.get('summary') or resume_text[:600] or 'Not available'}",
        f"Skills: {_format_prompt_list(parsed.get('skills'))}",
        f"Technologies: {_format_prompt_list(parsed.get('technologies'))}",
        f"Domains: {_format_prompt_list(parsed.get('domains'))}",
        f"Experience years: {parsed.get('experience_years') if parsed.get('experience_years') is not None else 'Not available'}",
    ]

    projects = parsed.get("projects") or []
    if projects:
        project_lines = []
        for project in projects[:3]:
            if not isinstance(project, dict):
                continue

            project_lines.append(
                f"{project.get('name') or 'Unnamed project'}"
                f" ({_format_prompt_list(project.get('technologies'))})"
            )

        if project_lines:
            lines.append(f"Projects: {'; '.join(project_lines)}")

    experience = parsed.get("experience") or []
    if experience:
        experience_lines = []
        for item in experience[:3]:
            if not isinstance(item, dict):
                continue

            experience_lines.append(
                f"{item.get('role') or 'Role'} at {item.get('company') or 'Company'}"
            )

        if experience_lines:
            lines.append(f"Experience: {'; '.join(experience_lines)}")

    return "\n".join(lines)


def _build_retrieved_jobs_context_for_prompt(state: AgentState) -> str:
    jobs = state.get("retrieved_jobs") or []

    if not jobs:
        return "Status: none\nNo retrieved jobs are currently cached for this chat."

    lines = [
        "Status: available",
        f"Last retrieval query: {state.get('last_retrieval_query') or 'Not available'}",
        "Last filters: "
        + json.dumps(state.get("last_retrieval_filters") or {}, default=str),
        "Cached listings:",
    ]

    for index, job in enumerate(jobs[:10], 1):
        lines.append(
            f"{index}. {job.get('title') or 'Untitled'} @ "
            f"{job.get('org_name') or 'Unknown company'} | "
            f"{_format_job_location(job)} | "
            f"{job.get('stipend_display') or job.get('salary_display') or 'NA'} | "
            f"{job.get('duration_display') or 'Duration NA'} | "
            f"Skills: {_format_prompt_list(job.get('skills'))} | "
            f"Apply: {job.get('source_url') or 'NA'}"
        )

    if len(jobs) > 10:
        lines.append(f"... {len(jobs) - 10} more cached listings not shown.")

    return "\n".join(lines)


def _build_openai_messages(state: AgentState) -> list[BaseMessage]:
    """Construct messages with system prompt, state context, and chat history."""

    logger.info(
        "Building OpenAI messages for answer_node: %s",
        _summarize_state_for_log(state),
    )

    system_prompt = JOBLENS_AGENT_SYSTEM_PROMPT.format(
        resume_context=_build_resume_context_for_prompt(state),
        retrieved_jobs_context=_build_retrieved_jobs_context_for_prompt(state),
    )

    messages: list[BaseMessage] = [SystemMessage(content=system_prompt)]

    if state.get("conversation_summary"):
        messages.append(
            SystemMessage(
                content=(
                    "<conversation_summary>\n"
                    "This is a summary of older messages not included in full below.\n"
                    f"{state['conversation_summary']}\n"
                    "</conversation_summary>"
                )
            )
        )

    for m in state["messages"]:
        messages.append(m)
    
    logger.info(
        "Constructed %d OpenAI messages: %s",
        len(messages),
        _preview_messages_for_log(messages),
    )

    return messages


async def answer_node(state: AgentState) -> dict:
    """Compatibility non-streaming answer node.

    The /chat/stream endpoint uses src.agent.streaming_agent.run_agent_stream
    for the full streaming tool loop.
    """

    logger.info(
        "Running answer_node: %s",
        _summarize_state_for_log(state),
    )

    openai_messages = _build_openai_messages(state)
    llm = LLMFactory.get_chat_llm()
    response = await llm.ainvoke(openai_messages)
    reply = _extract_response_text(response.content)

    logger.info("answer_node generated reply: %s", _truncate_for_log(reply))

    return {"messages": [AIMessage(content=reply)]}


