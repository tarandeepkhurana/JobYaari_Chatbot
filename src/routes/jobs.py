from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from src.db.job_ops import get_jobs_by_ids, list_jobs


router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("")
async def get_jobs(
    q: str | None = Query(default=None, max_length=120),
    work_mode: Literal["remote", "hybrid", "onsite"] | None = None,
    category: list[str] = Query(default=[]),
    paid: Literal["paid", "unpaid"] | None = None,
    limit: int = Query(default=60, ge=1, le=100),
):
    jobs = await list_jobs(
        query=q,
        work_mode=work_mode,
        categories=category,
        is_paid=True if paid == "paid" else False if paid == "unpaid" else None,
        limit=limit,
    )

    return {
        "jobs": jobs,
        "count": len(jobs),
    }


@router.get("/{job_id}")
async def get_job_details(job_id: str):
    jobs = await get_jobs_by_ids([job_id])

    if not jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    return {"job": jobs[0]}
