import json
import logging
from typing import AsyncGenerator

from langchain_core.messages import AIMessage, ToolMessage, BaseMessage, SystemMessage

from src.agent.state import AgentState
from src.agent.tools.search_jobs import (
    execute_get_job_details_tool,
    execute_search_jobs_tool,
    get_job_details,
    resolve_retrieval_mode,
    search_jobs,
)
from src.agent.tool_calling import (
    get_tool_call_args,
    get_tool_call_id,
    get_tool_call_name,
    merge_tool_call_chunk,
    normalize_streamed_tool_calls,
)
from src.db.chat_ops import update_chat_retrieved_jobs
from src.factories.llm_factory import LLMFactory
from src.services.llm.prompts import JOBLENS_AGENT_SYSTEM_PROMPT

logger = logging.getLogger("agent.streaming_agent")

MAX_AGENT_ITERATIONS = 3
LOG_CONTENT_PREVIEW_CHARS = 300

def _extract_text_part(content) -> str:
    if isinstance(content, list):
        text = ""

        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text += block.get("text", "")

        return text

    if isinstance(content, str):
        return content

    return ""


def _extract_reasoning_part(additional_kwargs: dict) -> str:
    reasoning_data = additional_kwargs.get("reasoning", {})
    reasoning_summary = reasoning_data.get("summary", [])
    text = ""

    for item in reasoning_summary:
        if item.get("type") == "summary_text":
            text += item.get("text", "")

    return text


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

def _truncate_for_log(text: str, limit: int = LOG_CONTENT_PREVIEW_CHARS) -> str:
    text = text.replace("\n", "\\n")

    if len(text) <= limit:
        return text

    return f"{text[:limit]}... [truncated {len(text) - limit} chars]"

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

def _format_job_location(job: dict) -> str:
    if job.get("remote"):
        return "Remote"

    cities = job.get("cities") or []
    if cities:
        return ", ".join(cities)

    return "NA"

def _format_prompt_list(values) -> str:
    if not values:
        return "Not available"

    if isinstance(values, list):
        return ", ".join(str(value) for value in values[:12]) or "Not available"

    return str(values)

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
        "Building OpenAI messages for streaming agent"
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

async def _stream_llm_iteration(
    llm_with_tools,
    messages: list,
) -> AsyncGenerator[dict, None]:
    tool_calls_by_index: dict[int, dict] = {}
    accumulated_text = ""

    async for chunk in llm_with_tools.astream(messages):
        content = chunk.content if hasattr(chunk, "content") else None
        additional_kwargs = getattr(chunk, "additional_kwargs", {})

        reasoning_part = _extract_reasoning_part(additional_kwargs)
        if reasoning_part:
            yield {
                "event": "thinking",
                "data": {"text": reasoning_part},
            }

        text_part = _extract_text_part(content)
        if text_part:
            accumulated_text += text_part
            yield {
                "event": "token",
                "data": {"text": text_part},
            }

        for tool_chunk in getattr(chunk, "tool_call_chunks", []) or []:
            index = tool_chunk.get("index", 0)
            current = tool_calls_by_index.setdefault(
                index,
                {
                    "id": "",
                    "name": "",
                    "args": "",
                    "parsed_args": {},
                },
            )
            merge_tool_call_chunk(current, tool_chunk)

        for tool_call in getattr(chunk, "tool_calls", []) or []:
            index = tool_call.get("index", len(tool_calls_by_index))
            if index not in tool_calls_by_index:
                tool_calls_by_index[index] = {
                    "id": tool_call.get("id") or "",
                    "name": tool_call.get("name") or "",
                    "args": tool_call.get("args") or {},
                    "parsed_args": {},
                }

    yield {
        "event": "iteration_end",
        "data": {
            "text": accumulated_text,
            "tool_calls": normalize_streamed_tool_calls(tool_calls_by_index),
        },
    }


async def run_agent_stream(
    state: AgentState,
) -> AsyncGenerator[dict, None]:
    """Run the chat agent as a streaming tool loop."""

    logger.info(
        "Running streaming agent: %s",
        _summarize_state_for_log(state),
    )

    llm = LLMFactory.get_chat_llm()
    llm_with_tools = llm.bind_tools(
        [search_jobs, get_job_details],
        parallel_tool_calls=False,
    )
    messages = _build_openai_messages(state)
    final_answer = ""
    retrieved_jobs = None
    retrieval_query = None
    retrieval_filters = None

    for iteration in range(1, MAX_AGENT_ITERATIONS + 1):
        logger.info(
            "Streaming agent iteration %d/%d",
            iteration,
            MAX_AGENT_ITERATIONS,
        )
        yield {
            "event": "status",
            "data": {
                "text": (
                    "Understanding your request..."
                    if iteration == 1
                    else "Processing results..."
                )
            },
        }

        iteration_result = None

        async for event in _stream_llm_iteration(llm_with_tools, messages):
            if event.get("event") in {"token", "thinking"}:
                yield event
            elif event.get("event") == "iteration_end":
                iteration_result = event.get("data", {})

        if iteration_result is None:
            iteration_result = {
                "text": "",
                "tool_calls": [],
            }

        message_text = iteration_result.get("text", "")
        tool_calls = iteration_result.get("tool_calls", [])

        if not tool_calls:
            final_answer += message_text
            if not final_answer:
                final_answer = (
                    "I could not generate a response for that. Please try again."
                )
                yield {
                    "event": "token",
                    "data": {"text": final_answer},
                }

            logger.info(
                "Streaming agent final answer: %s",
                _truncate_for_log(final_answer),
            )
            yield {
                "event": "done",
                "data": {
                    "final_answer": final_answer,
                    "retrieved_jobs": retrieved_jobs,
                    "last_retrieval_query": retrieval_query,
                    "last_retrieval_filters": retrieval_filters,
                },
            }
            return

        final_answer += message_text
        messages.append(
            AIMessage(
                content=message_text,
                tool_calls=tool_calls,
            )
        )

        for tool_call in tool_calls:
            tool_name = get_tool_call_name(tool_call)

            if tool_name == "get_job_details":
                args = get_tool_call_args(tool_call)
                logger.info(
                    "Tool call | name=%s | args=%s",
                    tool_name,
                    args,
                )
                yield {
                    "event": "status",
                    "data": {"text": "Reading full job details..."},
                }

                result = await execute_get_job_details_tool(args, state)
                logger.info(
                    "Tool result | name=%s | jobs=%d",
                    tool_name,
                    len(result.get("jobs", [])),
                )
                messages.append(
                    ToolMessage(
                        content=json.dumps(result, default=str),
                        tool_call_id=get_tool_call_id(tool_call),
                    )
                )
                continue

            if tool_name != "search_jobs":
                continue

            args = get_tool_call_args(tool_call)
            logger.info(
                "Tool call | name=%s | args=%s",
                tool_name,
                args,
            )
            display_mode = resolve_retrieval_mode(
                args.get("retrieval_mode"),
                bool(state.get("use_resume_profile", False)),
            )
            yield {
                "event": "status",
                "data": {
                    "text": (
                        "Matching jobs to your resume..."
                        if display_mode != "normal"
                        else "Searching for jobs..."
                    )
                },
            }

            result = await execute_search_jobs_tool(args, state)
            tool_runtime = result.get("_tool_runtime", {})
            search_query = (
                tool_runtime.get("query")
                or args.get("query")
                or state["current_query"]
            )
            retrieval_mode = tool_runtime.get("retrieval_mode") or display_mode

            compact_result = _compact_retrieval_result_for_tool(result)

            retrieved_jobs = result.get("results", [])
            retrieval_query = search_query
            retrieval_filters = result.get("parsed")
            state["retrieved_jobs"] = retrieved_jobs
            state["last_retrieval_query"] = retrieval_query
            state["last_retrieval_filters"] = retrieval_filters

            await update_chat_retrieved_jobs(
                chat_id=state["chat_id"],
                retrieved_jobs=retrieved_jobs,
                last_retrieval_query=retrieval_query,
                last_retrieval_filters=retrieval_filters,
            )

            logger.info(
                "Tool result | name=%s | jobs=%d | query=%s | mode=%s | top_titles=%s",
                tool_name,
                len(retrieved_jobs),
                search_query,
                retrieval_mode,
                [
                    job.get("title")
                    for job in retrieved_jobs[:5]
                    if isinstance(job, dict)
                ],
            )

            yield {
                "event": "jobs",
                "data": {"jobs": retrieved_jobs},
            }
            messages.append(
                ToolMessage(
                    content=json.dumps(compact_result, default=str),
                    tool_call_id=get_tool_call_id(tool_call),
                )
            )

    fallback = (
        "I searched through the available context, but I could not complete the "
        "request cleanly. Please try rephrasing your request once."
    )
    if not final_answer:
        final_answer = fallback
        yield {
            "event": "token",
            "data": {"text": fallback},
        }
    yield {
        "event": "done",
        "data": {
            "final_answer": final_answer,
            "retrieved_jobs": retrieved_jobs,
            "last_retrieval_query": retrieval_query,
            "last_retrieval_filters": retrieval_filters,
        },
    }
