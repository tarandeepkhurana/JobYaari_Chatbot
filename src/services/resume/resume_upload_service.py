import logging
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from src.services.resume.resume_reader import (
    extract_text_from_pdf,
)
from src.services.resume.resume_embedding import (
    generate_resume_embedding,
    generate_resume_intent_embeddings,
)
from src.services.resume.resume_parser import (
    parse_resume,
)

from src.db.resume_ops import replace_resume_intents, upsert_resume
from src.services.resume.resume_storage import (
    create_resume_signed_url,
    upload_resume_thumbnail,
    upload_resume_pdf,
)

logger = logging.getLogger("resume.resume_upload_service")

UPLOAD_DIR = Path("src/uploaded_pdfs")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE_MB = 5
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


async def process_resume_upload(
    user_id: str,
    file: UploadFile,
) -> dict:

    # -------------------------
    # Validate content type
    # -------------------------
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed",
        )

    # -------------------------
    # Read file
    # -------------------------
    content = await file.read()

    # -------------------------
    # Validate size
    # -------------------------
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"PDF size must be less than {MAX_FILE_SIZE_MB} MB",
        )

    # -------------------------
    # Save PDF
    # -------------------------
    filename = f"{uuid4()}.pdf"

    file_path = UPLOAD_DIR / filename

    with open(file_path, "wb") as f:
        f.write(content)

    logger.info(f"Resume uploaded: {filename}")

    # -------------------------
    # Extract text
    # -------------------------
    resume_text = await extract_text_from_pdf(file_path)

    if not resume_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Could not extract text from PDF",
        )

    # -------------------------
    # Parse resume using LLM
    # -------------------------
    parsed_data = await parse_resume(resume_text)

    # -------------------------
    # Generate embedding
    # -------------------------
    embedding = await generate_resume_embedding(
        parsed_data
    )

    # -------------------------
    # Generate per-intent embeddings
    # -------------------------
    target_role_intents = parsed_data.get(
        "target_role_intents",
        [],
    )
    embedded_intents = await generate_resume_intent_embeddings(
        target_role_intents
    )

    # -------------------------
    # Upload durable PDF copy
    # -------------------------
    storage_metadata = await upload_resume_pdf(
        user_id=user_id,
        content=content,
        content_type=file.content_type or "application/pdf",
    )
    thumbnail_metadata = await upload_resume_thumbnail(
        user_id=user_id,
        pdf_content=content,
    )

    # -------------------------
    # Store in DB
    # -------------------------
    resume_id = await upsert_resume(
        user_id=user_id,
        resume_text=resume_text,
        parsed_data=parsed_data,
        embedding=embedding,
        file_name=file.filename,
        file_mime_type=file.content_type,
        file_size_bytes=len(content),
        storage_bucket=storage_metadata["storage_bucket"],
        storage_path=storage_metadata["storage_path"],
    )

    await replace_resume_intents(
        user_id=user_id,
        resume_id=resume_id,
        intents=embedded_intents,
    )

    logger.info(f"Resume processed for user: {user_id}")
    preview_url = await create_resume_signed_url(
        storage_metadata["storage_path"]
    )
    thumbnail_url = await create_resume_signed_url(
        thumbnail_metadata["thumbnail_storage_path"]
    )

    return {
        "message": "Resume uploaded successfully",
        "filename": filename,
        "original_filename": file.filename,
        "preview_url": preview_url,
        "thumbnail_url": thumbnail_url,
        "storage_path": storage_metadata["storage_path"],
        "parsed_data": parsed_data,
    }
