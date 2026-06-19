from pgvector.sqlalchemy import Vector
from sqlalchemy import bindparam, text

from src.db.client import get_read_session
from src.utils.embeddings import generate_embedding
import logging

logger = logging.getLogger("retrieval.vector_search")

async def _vector_search_with_embedding(
    embedding: list[float],
    filters: dict,
    limit: int = 30,
    log_label: str = "query",
) -> list[dict]:

    logger.debug(
        "Performing vector search with %s embedding and filters: %s",
        log_label,
        filters,
    )

    conditions = [
        "is_active = true",
        "embedding IS NOT NULL"
    ]

    params = {
        "embedding": embedding,
        "limit": limit
    }

    # ---------------------------------------------------------
    # Work mode
    # ---------------------------------------------------------

    if filters.get("work_mode"):
        conditions.append("work_mode = :work_mode")
        params["work_mode"] = filters["work_mode"]

    # ---------------------------------------------------------
    # Remote
    # ---------------------------------------------------------

    if filters.get("remote") is not None:
        conditions.append("remote = :remote")
        params["remote"] = filters["remote"]

    # ---------------------------------------------------------
    # Paid / unpaid
    # ---------------------------------------------------------

    if filters.get("is_paid") is not None:
        conditions.append("is_paid = :is_paid")
        params["is_paid"] = filters["is_paid"]

    # ---------------------------------------------------------
    # Minimum stipend
    # ---------------------------------------------------------

    if filters.get("min_stipend") is not None:
        conditions.append("stipend_min >= :min_stipend")
        params["min_stipend"] = filters["min_stipend"]

    # ---------------------------------------------------------
    # Maximum stipend
    # ---------------------------------------------------------

    if filters.get("max_stipend") is not None:
        conditions.append("stipend_max <= :max_stipend")
        params["max_stipend"] = filters["max_stipend"]

    # ---------------------------------------------------------
    # Duration
    # Example:
    # "6 Months"
    # ---------------------------------------------------------

    if filters.get("duration_months") is not None:
        conditions.append(
            "duration_display ILIKE :duration_display"
        )

        params["duration_display"] = (
            f"{filters['duration_months']} Month%"
        )

    # ---------------------------------------------------------
    # Cities overlap
    # ---------------------------------------------------------

    if filters.get("cities"):
        conditions.append("cities && :cities")
        params["cities"] = filters["cities"]

    # ---------------------------------------------------------
    # Final WHERE clause
    # ---------------------------------------------------------

    where_clause = " AND ".join(conditions)

    sql = text(f"""
        SELECT
            id::text,
            title,
            org_name,
            cities,
            remote,
            work_mode,
            is_paid,

            stipend_display,
            salary_display,
            duration_display,

            skills,
            categories,

            source_url,
            description,
            posted_at::text AS posted_at,

            1 - (
                embedding <=> :embedding
            ) AS score

        FROM jobs

        WHERE {where_clause}

        ORDER BY embedding <=> :embedding

        LIMIT :limit
    """).bindparams(
        bindparam("embedding", type_=Vector(1536))
    )

    async with get_read_session() as session:
        result = await session.execute(
            sql,
            params
        )
        rows = result.mappings().all()
        logger.debug("Vector search returned %d results", len(rows))

        return [dict(row) for row in rows]


async def vector_search(
    query: str,
    filters: dict,
    limit: int = 30
) -> list[dict]:
    
    logger.debug("Vector search query='%s' limit=%d filters=%s", query, limit, filters)

    embedding = await generate_embedding(query)

    return await _vector_search_with_embedding(
        embedding=embedding,
        filters=filters,
        limit=limit,
        log_label="query",
    )


async def vector_search_by_embedding(
    embedding: list[float],
    filters: dict,
    limit: int = 30,
) -> list[dict]:
    """Perform vector search using a precomputed embedding."""

    return await _vector_search_with_embedding(
        embedding=embedding,
        filters=filters,
        limit=limit,
        log_label="resume",
    )
