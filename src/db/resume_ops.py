import logging
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.sql import func

from src.db.client import get_read_session, get_write_session
from src.db.models import Resume, ResumeIntent, User


logger = logging.getLogger("db.resume_ops")


def _normalize_embedding(embedding):
    if embedding is None:
        return None

    try:
        if len(embedding) == 0:
            return None
    except TypeError:
        return None

    return embedding


def _parse_user_id(user_id: str | UUID) -> UUID:
    return user_id if isinstance(user_id, UUID) else UUID(str(user_id))


async def get_resume_by_user(user_id: str | UUID) -> dict | None:
    """Fetch the latest stored resume for a user."""

    user_uuid = _parse_user_id(user_id)

    logger.info("Fetching resume for user_id: %s", user_uuid)

    async with get_read_session() as session:
        result = await session.execute(
            select(Resume).where(Resume.user_id == user_uuid)
        )
        resume = result.scalar_one_or_none()

        if not resume:
            logger.info("Resume not found for user_id: %s", user_uuid)
            return None

        logger.info("Resume fetched successfully for user_id: %s", user_uuid)

        intents_result = await session.execute(
            select(ResumeIntent)
            .where(ResumeIntent.resume_id == resume.id)
            .order_by(ResumeIntent.position)
        )
        intents = intents_result.scalars().all()

        return {
            "id": str(resume.id),
            "resume_text": resume.resume_text,
            "parsed_data": resume.parsed_data,
            "embedding": resume.embedding,
            "file_name": resume.file_name,
            "file_mime_type": resume.file_mime_type,
            "file_size_bytes": resume.file_size_bytes,
            "storage_bucket": resume.storage_bucket,
            "storage_path": resume.storage_path,
            "intents": [
                {
                    "id": str(intent.id),
                    "label": intent.label,
                    "query": intent.query,
                    "evidence": intent.evidence or [],
                    "embedding": intent.embedding,
                    "position": intent.position,
                }
                for intent in intents
            ],
            "updated_at": resume.updated_at.isoformat() if resume.updated_at else None,
        }


async def upsert_resume(
    user_id: str | UUID,
    resume_text: str,
    parsed_data: dict,
    embedding: list[float] | None,
    file_name: str | None = None,
    file_mime_type: str | None = None,
    file_size_bytes: int | None = None,
    storage_bucket: str | None = None,
    storage_path: str | None = None,
) -> UUID:
    """Insert or update the single resume stored for a user."""

    user_uuid = _parse_user_id(user_id)
    clean_embedding = _normalize_embedding(embedding)

    logger.info("Upserting resume for user_id: %s", user_uuid)

    async with get_write_session() as session:
        user = await session.get(User, user_uuid)
        if user is None:
            session.add(User(id=user_uuid))

        stmt = insert(Resume).values(
            user_id=user_uuid,
            resume_text=resume_text,
            parsed_data=parsed_data,
            embedding=clean_embedding,
            file_name=file_name,
            file_mime_type=file_mime_type,
            file_size_bytes=file_size_bytes,
            storage_bucket=storage_bucket,
            storage_path=storage_path,
        )

        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id"],
            set_={
                "resume_text": stmt.excluded.resume_text,
                "parsed_data": stmt.excluded.parsed_data,
                "embedding": stmt.excluded.embedding,
                "file_name": stmt.excluded.file_name,
                "file_mime_type": stmt.excluded.file_mime_type,
                "file_size_bytes": stmt.excluded.file_size_bytes,
                "storage_bucket": stmt.excluded.storage_bucket,
                "storage_path": stmt.excluded.storage_path,
                "updated_at": func.now(),
            },
        )

        result = await session.execute(
            stmt.returning(Resume.id)
        )
        resume_id = result.scalar_one()

    logger.info("Resume upserted successfully for user_id: %s", user_uuid)
    return resume_id


async def replace_resume_intents(
    user_id: str | UUID,
    resume_id: str | UUID,
    intents: list[dict],
) -> None:
    """Replace stored role intents for a resume."""

    user_uuid = _parse_user_id(user_id)
    resume_uuid = _parse_user_id(resume_id)

    logger.info(
        "Replacing %d resume intents for user_id: %s",
        len(intents),
        user_uuid,
    )

    async with get_write_session() as session:
        await session.execute(
            delete(ResumeIntent).where(ResumeIntent.resume_id == resume_uuid)
        )
        await session.flush()

        for position, intent in enumerate(intents[:5], start=1):
            session.add(
                ResumeIntent(
                    resume_id=resume_uuid,
                    user_id=user_uuid,
                    position=position,
                    label=intent.get("label") or intent.get("query") or "Role intent",
                    query=intent.get("query") or "",
                    evidence=intent.get("evidence") or [],
                    embedding=_normalize_embedding(intent.get("embedding")),
                )
            )

    logger.info("Resume intents replaced successfully for user_id: %s", user_uuid)
