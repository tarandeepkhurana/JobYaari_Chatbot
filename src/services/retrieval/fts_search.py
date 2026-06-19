from sqlalchemy import text

from src.db.client import get_read_session
import logging

logger = logging.getLogger("retrieval.fts_search")

async def fts_search(
    query: str,
    filters: dict,
    limit: int = 30
) -> list[dict]:
    """Perform a full-text search on jobs with optional filters."""

    logger.debug("FTS search query='%s' limit=%d filters=%s", query, limit, filters)

    conditions = [
        "search_vector @@ websearch_to_tsquery('english', :query)",
        "is_active = true"
    ]

    params = {
        "query": query,
        "limit": limit
    }

    # work mode
    if filters.get("work_mode"):
        conditions.append("work_mode = :work_mode")
        params["work_mode"] = filters["work_mode"]

    # remote
    if filters.get("remote") is not None:
        conditions.append("remote = :remote")
        params["remote"] = filters["remote"]

    # paid/unpaid
    if filters.get("is_paid") is not None:
        conditions.append("is_paid = :is_paid")
        params["is_paid"] = filters["is_paid"]

    # stipend filters
    if filters.get("min_stipend") is not None:
        conditions.append("stipend_min >= :min_stipend")
        params["min_stipend"] = filters["min_stipend"]

    if filters.get("max_stipend") is not None:
        conditions.append("stipend_max <= :max_stipend")
        params["max_stipend"] = filters["max_stipend"]

    # duration
    if filters.get("duration_months") is not None:
        conditions.append("duration_display ILIKE :duration")
        params["duration"] = f"{filters['duration_months']} Month%"

    # cities overlap
    if filters.get("cities"):
        conditions.append("cities && :cities")
        params["cities"] = filters["cities"]

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

            ts_rank(
                search_vector,
                websearch_to_tsquery('english', :query)
            ) AS score

        FROM jobs

        WHERE {where_clause}

        ORDER BY score DESC

        LIMIT :limit
    """)

    async with get_read_session() as session:
        result = await session.execute(sql, params)
        rows = result.mappings().all()
        logger.debug("FTS search returned %d results", len(rows))
        return [dict(row) for row in rows]
