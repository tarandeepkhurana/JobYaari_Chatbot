from uuid import UUID

from fastapi import APIRouter, Depends, UploadFile, File

from src.auth.dependencies import get_current_user_id
from src.services.resume.resume_upload_service import (
    process_resume_upload,
)
from src.db.resume_ops import get_resume_by_user
from src.services.resume.resume_storage import create_resume_signed_url

router = APIRouter(
    prefix="/pdf",
    tags=["PDF"],
)


@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),
    user_id: UUID = Depends(get_current_user_id),
):
    result = await process_resume_upload(
        user_id=str(user_id),
        file=file,
    )

    return result


@router.get("/current")
async def get_current_resume(
    user_id: UUID = Depends(get_current_user_id),
):
    resume = await get_resume_by_user(user_id)

    if not resume:
        return {
            "has_resume": False,
            "resume": None,
        }

    preview_url = await create_resume_signed_url(
        resume.get("storage_path")
    )
    thumbnail_path = None
    if resume.get("storage_path"):
        thumbnail_path = str(resume["storage_path"]).replace(
            "resume.pdf",
            "resume-thumbnail.png",
        )
    thumbnail_url = await create_resume_signed_url(thumbnail_path)

    return {
        "has_resume": True,
        "resume": {
            "id": resume.get("id"),
            "file_name": resume.get("file_name"),
            "file_mime_type": resume.get("file_mime_type"),
            "file_size_bytes": resume.get("file_size_bytes"),
            "storage_path": resume.get("storage_path"),
            "parsed_data": resume.get("parsed_data"),
            "updated_at": resume.get("updated_at"),
            "preview_url": preview_url,
            "thumbnail_url": thumbnail_url,
        },
    }
