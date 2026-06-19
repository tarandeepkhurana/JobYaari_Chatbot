import logging
import asyncio
from collections.abc import Awaitable
from typing import Literal

from src.services.retrieval.query_parser import parse_query
from src.services.retrieval.fts_search import fts_search
from src.services.retrieval.vector_search import (
    vector_search,
    vector_search_by_embedding,
)
from src.services.retrieval.hybrid_merge import (
    reciprocal_rank_fusion,
    reciprocal_rank_fusion_many,
)
from src.services.retrieval.reranker import rerank
from src.services.resume.resume_profile import (
    build_resume_search_profile,
    get_resume_intent_embedding,
    get_resume_search_intents,
    get_resume_embedding,
)

logger = logging.getLogger("retrieval.retrieval_pipeline")


RetrievalMode = Literal["normal", "augment_resume", "resume_only"]

QUERY_TOKEN_STOPWORDS = {
    "a",
    "an",
    "and",
    "for",
    "in",
    "internship",
    "internships",
    "job",
    "jobs",
    "me",
    "my",
    "of",
    "or",
    "paid",
    "remote",
    "role",
    "roles",
    "the",
    "to",
    "with",
}

GENERIC_RESUME_OVERLAP_TOKENS = {
    "java",
    "python",
    "sql",
}


async def _safe_search(stage_name: str, search: Awaitable[list[dict]]) -> list[dict]:
    try:
        return await search
    except Exception:
        logger.exception("%s failed; continuing with the other retrieval branch", stage_name)
        return []


def _build_filters(parsed: dict) -> dict:
    return {
        "remote": parsed.get("remote"),
        "work_mode": parsed.get("work_mode"),
        "is_paid": parsed.get("is_paid"),
        "skills": parsed.get("skills", []),
        "categories": parsed.get("categories", []),
        "cities": parsed.get("cities", []),
        "min_stipend": parsed.get("min_stipend"),
        "max_stipend": parsed.get("max_stipend"),
        "duration_months": parsed.get("duration_months"),
    }


def _compact_filters_for_log(filters: dict) -> dict:
    return {
        key: value
        for key, value in filters.items()
        if value not in (None, [], {})
    }


def _merge_branch_filters(base_filters: dict, branch_filters: dict) -> dict:
    # User-provided constraints stay hard across every branch. Resume-derived
    # terms can expand the query text, but should not loosen remote/city/pay/etc.
    merged = dict(branch_filters)

    for key in [
        "remote",
        "work_mode",
        "is_paid",
        "min_stipend",
        "max_stipend",
        "duration_months",
    ]:
        if base_filters.get(key) is not None:
            merged[key] = base_filters[key]

    for key in ["cities", "skills", "categories"]:
        base_values = base_filters.get(key) or []
        branch_values = branch_filters.get(key) or []
        merged[key] = list(dict.fromkeys([*base_values, *branch_values]))

    return merged


def _normalize_retrieval_mode(mode: str | None) -> RetrievalMode:
    if mode in {"augment_resume", "resume_only"}:
        return mode

    return "normal"


def _tokenize_for_overlap(text: str) -> set[str]:
    tokens = set()

    for raw_token in text.lower().replace("/", " ").replace("-", " ").split():
        token = raw_token.strip(".,:;()[]{}")

        if token and token not in QUERY_TOKEN_STOPWORDS:
            tokens.add(token)

    return tokens


def _select_overlapping_resume_intent(
    semantic_query: str,
    resume_intents: list[dict],
) -> dict | None:
    # In augment mode, resume should personalize a concrete user search without
    # hijacking it. Add at most one resume intent, and only when the user query
    # overlaps on meaningful terms beyond generic languages like "python".
    query_tokens = _tokenize_for_overlap(semantic_query)

    if not query_tokens:
        return resume_intents[0] if resume_intents else None

    scored_intents = []
    for intent in resume_intents:
        query = intent.get("query") or ""
        overlap = query_tokens & _tokenize_for_overlap(query)
        meaningful_overlap = overlap - GENERIC_RESUME_OVERLAP_TOKENS
        scored_intents.append((len(meaningful_overlap), len(overlap), intent))

    scored_intents.sort(key=lambda item: (item[0], item[1]), reverse=True)

    if scored_intents and scored_intents[0][0] > 0:
        return scored_intents[0][2]

    return None


async def _run_hybrid_branch(
    query: str,
    filters: dict,
    limit: int = 30,
    branch_name: str = "query",
) -> list[dict]:
    # One branch always means: lexical recall from FTS + semantic recall from
    # vectors, fused before the final reranker sees candidates.
    fts_results, vector_results = await asyncio.gather(
        _safe_search("FTS search", fts_search(query, filters, limit=limit)),
        _safe_search("Vector search", vector_search(query, filters, limit=limit)),
    )

    logger.info(
        "Branch %s | query='%s' | fts=%d | vector=%d",
        branch_name,
        query,
        len(fts_results),
        len(vector_results),
    )

    return reciprocal_rank_fusion(fts_results, vector_results)


async def _run_intent_branch(
    intent: dict,
    filters: dict,
    limit: int = 20,
) -> list[dict]:
    query = intent.get("query") or ""
    embedding = get_resume_intent_embedding(intent)

    if not query:
        return []

    fts_task = _safe_search(
        "Resume intent FTS search",
        fts_search(query, filters, limit=limit),
    )

    if embedding is not None:
        vector_task = _safe_search(
            "Resume intent vector search",
            vector_search_by_embedding(embedding, filters, limit=limit),
        )
    else:
        vector_task = _safe_search(
            "Resume intent vector search",
            vector_search(query, filters, limit=limit),
        )

    fts_results, vector_results = await asyncio.gather(
        fts_task,
        vector_task,
    )

    logger.info(
        "Branch resume_intent[%s] | embedding=%s | query='%s' | fts=%d | vector=%d",
        intent.get("label") or "intent",
        embedding is not None,
        query,
        len(fts_results),
        len(vector_results),
    )

    return reciprocal_rank_fusion(fts_results, vector_results)


async def _retrieve_normal(
    user_query: str,
    parsed: dict,
    top_n: int,
) -> dict:
    semantic_query = parsed.get("semantic_query") or user_query
    filters = _build_filters(parsed)
    logger.info(
        "Retrieval start | mode=normal | query='%s' | semantic='%s' | filters=%s",
        user_query,
        semantic_query,
        _compact_filters_for_log(filters),
    )
    merged = await _run_hybrid_branch(
        semantic_query,
        filters,
        branch_name="user_query",
    )
    logger.info("Retrieval merge | branches=1 | candidates=%d", len(merged))

    final = await rerank(semantic_query, merged, top_n=top_n)
    logger.info("Retrieval done | mode=normal | final=%d", len(final))

    return {
        "query": user_query,
        "parsed": parsed,
        "results": final,
    }


async def _retrieve_with_resume(
    user_query: str,
    parsed: dict,
    resume: dict,
    top_n: int,
    retrieval_mode: RetrievalMode,
) -> dict:
    semantic_query = parsed.get("semantic_query") or user_query
    base_filters = _build_filters(parsed)
    resume_profile = build_resume_search_profile(resume)
    resume_intents = get_resume_search_intents(resume)
    resume_embedding = get_resume_embedding(resume)
    ranked_lists = []
    used_resume_intents = []

    logger.info(
        "Retrieval start | mode=%s | query='%s' | semantic='%s' | filters=%s | resume_embedding=%s | stored_intents=%d | intent_embeddings=%d",
        retrieval_mode,
        user_query,
        semantic_query,
        _compact_filters_for_log(base_filters),
        resume_embedding is not None,
        len(resume_intents),
        sum(
            1
            for intent in resume_intents
            if get_resume_intent_embedding(intent) is not None
        ),
    )

    if retrieval_mode == "augment_resume":
        # Mixed/normal search with resume enabled:
        # keep the user's query as the primary candidate source, then add only
        # targeted resume signals so recall improves without drifting too far.
        base_results = await _run_hybrid_branch(
            semantic_query,
            base_filters,
            branch_name="user_query",
        )
        ranked_lists.append(base_results)

        selected_intent = _select_overlapping_resume_intent(
            semantic_query,
            resume_intents,
        )
        if selected_intent:
            used_resume_intents.append(selected_intent)

    else:
        # Pure resume search:
        # "jobs matching my resume" is not a useful standalone search query, so
        # use resume-derived intents plus the resume embedding instead.
        used_resume_intents = resume_intents

    for intent in used_resume_intents:
        intent_query = intent.get("query") or ""
        intent_parsed = await parse_query(intent_query)
        intent_query = intent_parsed.get("semantic_query") or intent_query
        intent_filters = _merge_branch_filters(
            base_filters,
            _build_filters(intent_parsed),
        )
        ranked_lists.append(
            await _run_intent_branch(
                {
                    **intent,
                    "query": intent_query,
                },
                intent_filters,
                limit=20,
            )
        )

    if resume_embedding is not None:
        # The resume embedding represents the overall profile. It is an extra
        # candidate source, not a replacement for query/intent retrieval.
        resume_embedding_results = await _safe_search(
            "Resume embedding vector search",
            vector_search_by_embedding(resume_embedding, base_filters, limit=30),
        )
        logger.info(
            "Branch resume_embedding | embedding=True | vector=%d",
            len(resume_embedding_results),
        )
        ranked_lists.append(resume_embedding_results)

    merged = reciprocal_rank_fusion_many(ranked_lists)
    logger.info(
        "Retrieval merge | mode=%s | branches=%d | candidates=%d | rerank_input=%d",
        retrieval_mode,
        len(ranked_lists),
        len(merged),
        min(len(merged), 20),
    )

    # The reranker is the final precision layer. It sees the user's query,
    # candidate jobs, and compact resume profile, then chooses the top matches.
    final = await rerank(
        semantic_query,
        merged,
        top_n=top_n,
        resume_context=resume_profile,
    )
    logger.info(
        "Retrieval done | mode=%s | final=%d | top_titles=%s",
        retrieval_mode,
        len(final),
        [
            job.get("title")
            for job in final[:5]
            if isinstance(job, dict)
        ],
    )

    return {
        "query": user_query,
        "parsed": {
            **parsed,
            "use_resume_profile": True,
            "retrieval_mode": retrieval_mode,
            "resume_search_intents": [
                intent.get("query")
                for intent in used_resume_intents
            ],
        },
        "results": final,
    }


async def retrieve_jobs(
    user_query: str,
    top_n: int = 10,
    resume: dict | None = None,
    retrieval_mode: str = "normal",
) -> dict:
    parsed = await parse_query(user_query)

    mode = _normalize_retrieval_mode(retrieval_mode)

    if mode != "normal" and resume:
        return await _retrieve_with_resume(
            user_query=user_query,
            parsed=parsed,
            resume=resume,
            top_n=top_n,
            retrieval_mode=mode,
        )

    return await _retrieve_normal(
        user_query=user_query,
        parsed=parsed,
        top_n=top_n,
    )
