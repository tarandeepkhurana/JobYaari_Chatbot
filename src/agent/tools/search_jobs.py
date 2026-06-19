from langchain_core.tools import tool
from typing import Literal
from uuid import UUID

from src.agent.state import AgentState
from src.db.job_ops import get_jobs_by_ids
from src.services.retrieval.retrieval_pipeline import retrieve_jobs


VALID_RETRIEVAL_MODES = {
    "normal",
    "augment_resume",
    "resume_only",
}


def resolve_retrieval_mode(
    llm_mode: str | None,
    use_resume_profile: bool,
) -> str:
    mode = llm_mode if llm_mode in VALID_RETRIEVAL_MODES else "normal"

    if mode == "normal" and use_resume_profile:
        return "augment_resume"

    return mode

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


@tool
async def get_job_details(
    job_ids: list[str],
) -> dict:
    """Fetch full job details for one or more job UUIDs.

    Use this after search_jobs when the user asks about the role details,
    responsibilities, eligibility, benefits, work functions, or wants a deeper
    explanation of specific retrieved listings. Returns only user-facing job
    details and intentionally does not truncate description or other long fields.
    """

    jobs = await get_jobs_by_ids(job_ids)

    return {
        "requested_job_ids": job_ids,
        "found_count": len(jobs),
        "jobs": jobs,
    }


def _is_uuid(value: str) -> bool:
    try:
        UUID(str(value))
    except ValueError:
        return False

    return True


def _resolve_job_ids_from_state(values: list[str], state: AgentState) -> list[str]:
    """Resolve UUIDs or known listing URLs/titles to job IDs from cached results."""

    resolved: list[str] = []
    cached_jobs = state.get("retrieved_jobs") or []

    for value in values:
        candidate = str(value or "").strip()
        if not candidate:
            continue

        if _is_uuid(candidate):
            resolved.append(candidate)
            continue

        candidate_lower = candidate.lower()
        for job in cached_jobs:
            if not isinstance(job, dict):
                continue

            job_id = job.get("id")
            if not job_id:
                continue

            match_values = [
                job.get("source_url"),
                job.get("application_url"),
                job.get("title"),
                job.get("org_name"),
            ]
            if any(
                str(item or "").strip().lower() == candidate_lower
                for item in match_values
            ):
                resolved.append(str(job_id))
                break

    return list(dict.fromkeys(resolved))


async def execute_get_job_details_tool(args: dict, state: AgentState) -> dict:
    """Execute get_job_details using cached jobs to resolve URLs/titles to IDs."""

    requested_values = args.get("job_ids") or []
    if isinstance(requested_values, str):
        requested_values = [requested_values]

    resolved_job_ids = _resolve_job_ids_from_state(requested_values, state)
    jobs = await get_jobs_by_ids(resolved_job_ids)

    return {
        "requested_values": requested_values,
        "resolved_job_ids": resolved_job_ids,
        "found_count": len(jobs),
        "jobs": jobs,
        "message": (
            None
            if jobs
            else "Could not resolve those listings from the current cached jobs."
        ),
    }


async def execute_search_jobs_tool(args: dict, state: AgentState) -> dict:
    """Execute the search_jobs tool with runtime state that the LLM cannot pass."""

    search_query = args.get("query") or state["current_query"]
    use_resume_profile = bool(state.get("use_resume_profile", False))
    retrieval_mode = resolve_retrieval_mode(
        args.get("retrieval_mode"),
        use_resume_profile,
    )

    if retrieval_mode != "normal" and not state.get("resume"):
        result = {
            "query": search_query,
            "parsed": {
                "use_resume_profile": retrieval_mode != "normal",
                "retrieval_mode": retrieval_mode,
                "resume_missing": True,
            },
            "results": [],
            "message": "No resume is uploaded for this user yet.",
        }
    else:
        result = await retrieve_jobs(
            search_query,
            resume=state.get("resume"),
            retrieval_mode=retrieval_mode,
        )

    result["_tool_runtime"] = {
        "query": search_query,
        "retrieval_mode": retrieval_mode,
        "use_resume_profile": use_resume_profile,
    }
    return result
