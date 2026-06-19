# src/db/job_ops.py
import logging
from uuid import UUID
from datetime import datetime, timezone, timedelta
from sqlalchemy import delete, text
from sqlalchemy.dialects.postgresql import insert
from src.db.client import get_read_session, get_write_session
from src.db.models import Job

logger = logging.getLogger("db.job_ops")


async def upsert_jobs(jobs: list[dict]):
    """Insert or update jobs by dedupe_key."""

    fetched_count = len(jobs)
    logger.info(f"Preparing to upsert {fetched_count} fetched jobs")

    if not jobs:
        return
    
    # Deduplicate by dedupe_key
    unique_jobs = {}

    for job in jobs:
        unique_jobs[job["dedupe_key"]] = job

    jobs = list(unique_jobs.values())
    logger.info(
        "Unique jobs after dedupe: %d (removed %d duplicates)",
        len(jobs),
        fetched_count - len(jobs),
    )
    
    now = datetime.now(timezone.utc)

    async with get_write_session() as session:
        stmt = insert(Job).values(jobs)
        stmt = stmt.on_conflict_do_update(
            index_elements=["dedupe_key"],
            set_={
                "source_url": stmt.excluded.source_url,
                "application_url": stmt.excluded.application_url,
                "title": stmt.excluded.title,
                "description": stmt.excluded.description,
                "job_type": stmt.excluded.job_type,
                "work_mode": stmt.excluded.work_mode,
                "remote": stmt.excluded.remote,
                "org_name": stmt.excluded.org_name,
                "org_logo_url": stmt.excluded.org_logo_url,
                "org_size": stmt.excluded.org_size,
                "cities": stmt.excluded.cities,
                "state": stmt.excluded.state,
                "country": stmt.excluded.country,
                "salary_min": stmt.excluded.salary_min,
                "salary_max": stmt.excluded.salary_max,
                "salary_currency": stmt.excluded.salary_currency,
                "salary_period": stmt.excluded.salary_period,
                "salary_display": stmt.excluded.salary_display,
                "is_paid": stmt.excluded.is_paid,
                "stipend_min": stmt.excluded.stipend_min,
                "stipend_max": stmt.excluded.stipend_max,
                "stipend_display": stmt.excluded.stipend_display,
                "experience_min_years": stmt.excluded.experience_min_years,
                "experience_max_years": stmt.excluded.experience_max_years,
                "experience_label": stmt.excluded.experience_label,
                "duration_display": stmt.excluded.duration_display,
                "duration_days": stmt.excluded.duration_days,
                "skills": stmt.excluded.skills,
                "categories": stmt.excluded.categories,
                "eligibility": stmt.excluded.eligibility,
                "benefits": stmt.excluded.benefits,
                "work_functions": stmt.excluded.work_functions,
                "posted_at": stmt.excluded.posted_at,
                "expires_at": stmt.excluded.expires_at,
                "scraped_at": now,
                "status": stmt.excluded.status,
                "embedding_text": stmt.excluded.embedding_text,
                "embedding": stmt.excluded.embedding,
                "embedding_model": stmt.excluded.embedding_model,
                "raw_payload": stmt.excluded.raw_payload,
                "extra_metadata": stmt.excluded.extra_metadata,
                "is_active": stmt.excluded.is_active,
                "last_updated_at": now,
            }
        )
        await session.execute(stmt)
        logger.info(f"Upserted {len(jobs)} unique jobs")


async def remove_old_jobs(days: int = 30):
    """Delete jobs that have not been seen by the scraper for `days` days."""
    
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    async with get_write_session() as session:
        result = await session.execute(
            delete(Job).where(Job.scraped_at < cutoff)
        )
        logger.info(f"Deleted {result.rowcount or 0} jobs older than {days} days")


async def list_jobs(
    query: str | None = None,
    work_mode: str | None = None,
    categories: list[str] | None = None,
    is_paid: bool | None = None,
    limit: int = 60,
) -> list[dict]:
    """Return active jobs for the UI jobs browser with lightweight filters."""

    conditions = ["is_active = true"]
    params = {"limit": min(max(limit, 1), 100)}

    if query:
        conditions.append(
            """
            (
                title ILIKE :query
                OR org_name ILIKE :query
                OR description ILIKE :query
                OR EXISTS (
                    SELECT 1 FROM unnest(skills) AS skill
                    WHERE skill ILIKE :query
                )
                OR EXISTS (
                    SELECT 1 FROM unnest(categories) AS category
                    WHERE category ILIKE :query
                )
            )
            """
        )
        params["query"] = f"%{query.strip()}%"

    if work_mode:
        conditions.append("work_mode = :work_mode")
        params["work_mode"] = work_mode

    clean_categories = [
        category.strip().lower()
        for category in categories or []
        if category and category.strip()
    ]
    if clean_categories:
        conditions.append("categories && :categories")
        params["categories"] = clean_categories

    if is_paid is not None:
        conditions.append("is_paid = :is_paid")
        params["is_paid"] = is_paid

    where_clause = " AND ".join(conditions)

    sql = text(f"""
        SELECT
            id::text,
            source,
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
            posted_at::text AS posted_at,
            scraped_at::text AS scraped_at
        FROM jobs
        WHERE {where_clause}
        ORDER BY
            COALESCE(posted_at, scraped_at, last_updated_at) DESC NULLS LAST,
            title ASC
        LIMIT :limit
    """)

    async with get_read_session() as session:
        result = await session.execute(sql, params)
        rows = result.mappings().all()

    return [dict(row) for row in rows]


async def get_jobs_by_ids(job_ids: list[str | UUID]) -> list[dict]:
    """Return full active job details for the provided job UUIDs."""

    clean_ids: list[UUID] = []
    for job_id in job_ids:
        if not job_id:
            continue

        try:
            clean_ids.append(job_id if isinstance(job_id, UUID) else UUID(str(job_id)))
        except ValueError:
            logger.warning("Skipping invalid job UUID for full details: %s", job_id)

    if not clean_ids:
        return []

    sql = text("""
        SELECT
            id::text,
            application_url,
            title,
            description,
            work_mode,
            org_name,
            cities,
            country,
            salary_display,
            stipend_display,
            duration_display,
            skills,
            eligibility,
            benefits,
            work_functions
        FROM jobs
        WHERE id = ANY(:job_ids)
          AND is_active = true
    """)

    async with get_read_session() as session:
        result = await session.execute(sql, {"job_ids": clean_ids})
        rows = result.mappings().all()

    jobs_by_id = {str(row["id"]): dict(row) for row in rows}
    return [jobs_by_id[str(job_id)] for job_id in clean_ids if str(job_id) in jobs_by_id]
