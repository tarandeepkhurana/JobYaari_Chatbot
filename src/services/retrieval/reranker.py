from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from src.factories.llm_factory import LLMFactory
from src.services.llm.prompts import RERANK_PROMPT
import logging

logger = logging.getLogger("retrieval.reranker")


RERANK_CANDIDATE_LIMIT = 20


class RerankScore(BaseModel):
    job_id: str = Field(description="Job id from the candidate list.")
    score: float = Field(ge=0.0, le=1.0)
    reason: str = Field(default="")


class RerankResult(BaseModel):
    rankings: list[RerankScore] = Field(default_factory=list)


def build_job_text(job: dict) -> str:
    """Convert a job dict into a compact textual description for LLM input."""

    logger.debug(f"Building job text for job_id: {job.get('id')}")

    location = (
        ", ".join(job.get("cities") or [])
        if job.get("cities")
        else (
            "Remote"
            if job.get("remote")
            else "Unknown"
        )
    )

    compensation = (
        job.get("stipend_display")
        or job.get("salary_display")
        or "Not specified"
    )

    skills = ", ".join(job.get("skills") or [])

    categories = ", ".join(job.get("categories") or [])

    description = (
        (job.get("description") or "")[:450]
    )
    
    logger.debug(f"Job text for job_id {job.get('id')}: {description}")

    return f"""
Job ID: {job.get("id")}

Title: {job.get("title")}

Company: {job.get("org_name")}

Location: {location}

Work Mode: {job.get("work_mode")}

Remote: {job.get("remote")}

Compensation: {compensation}

Duration: {job.get("duration_display")}

Skills: {skills}

Categories: {categories}

Description:
{description}
"""


def _build_rerank_payload(candidates: list[dict]) -> str:
    job_cards = []

    for index, job in enumerate(candidates, start=1):
        job_cards.append(
            f"Candidate {index}\n{build_job_text(job)}"
        )

    return "\n---\n".join(job_cards)


async def rerank_batch(
    query: str,
    candidates: list[dict],
    resume_context: str | None = None,
) -> dict[str, RerankScore]:
    """Use one structured LLM call to score all rerank candidates."""

    llm = LLMFactory.get_reranker_llm().with_structured_output(RerankResult)
    candidate_text = _build_rerank_payload(candidates)
    resume_section = (
        f"""
Resume Profile:
{resume_context}
"""
        if resume_context
        else ""
    )
    
    messages = [
        SystemMessage(content=RERANK_PROMPT),
        HumanMessage(
            content=f"""
User Query:
{query}

{resume_section}
Candidate Jobs:
{candidate_text}
"""
        )
    ]

    try:
        response = await llm.ainvoke(messages)
        rankings = response.rankings
        return {
            str(ranking.job_id): ranking
            for ranking in rankings
        }
    except Exception:
        logger.exception("Batch reranking failed")
        return {}


async def rerank(
    query: str,
    candidates: list[dict],
    top_n: int = 10,
    resume_context: str | None = None,
) -> list[dict]:
    
    logger.info(f"Starting reranking of {len(candidates)} candidates for query: {query}")

    rerank_candidates = candidates[:RERANK_CANDIDATE_LIMIT]
    scores_by_id = await rerank_batch(
        query=query,
        candidates=rerank_candidates,
        resume_context=resume_context,
    )

    for job in rerank_candidates:
        ranking = scores_by_id.get(str(job.get("id")))
        job["rerank_score"] = ranking.score if ranking else 0.0
        job["rerank_reason"] = ranking.reason if ranking else ""

    reranked_results = sorted(
        rerank_candidates,
        key=lambda x: x["rerank_score"],
        reverse=True
    )
    
    logger.info(f"Reranking completed. Top reranked job ID: {reranked_results[0].get('id') if reranked_results else 'N/A'} with score: {reranked_results[0].get('rerank_score') if reranked_results else 'N/A'}")
    
    return reranked_results[:top_n]
