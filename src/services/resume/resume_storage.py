import logging
from io import BytesIO
from urllib.parse import quote

import httpx
import pypdfium2 as pdfium

from src.config import settings


logger = logging.getLogger("resume.resume_storage")


SIGNED_URL_EXPIRES_SECONDS = 30 * 60


def build_resume_storage_path(user_id: str) -> str:
    return f"users/{user_id}/resume.pdf"


def build_resume_thumbnail_storage_path(user_id: str) -> str:
    return f"users/{user_id}/resume-thumbnail.png"


def _storage_headers(content_type: str | None = None) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
        "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
    }

    if content_type:
        headers["Content-Type"] = content_type

    return headers


def _quote_storage_path(path: str) -> str:
    return "/".join(quote(part, safe="") for part in path.split("/"))


async def upload_resume_pdf(
    *,
    user_id: str,
    content: bytes,
    content_type: str,
) -> dict:
    bucket = settings.SUPABASE_RESUME_BUCKET
    storage_path = build_resume_storage_path(user_id)
    quoted_path = _quote_storage_path(storage_path)
    url = (
        f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/"
        f"{bucket}/{quoted_path}"
    )

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            url,
            params={"upsert": "true"},
            headers={
                **_storage_headers(content_type),
                "x-upsert": "true",
            },
            content=content,
        )
        response.raise_for_status()

    logger.info("Uploaded resume PDF to Supabase Storage: %s", storage_path)

    return {
        "storage_bucket": bucket,
        "storage_path": storage_path,
    }


def render_resume_thumbnail(content: bytes, width: int = 420) -> bytes:
    pdf = pdfium.PdfDocument(content)
    page = pdf[0]
    page_width, _page_height = page.get_size()
    scale = width / page_width
    bitmap = page.render(scale=scale)
    image = bitmap.to_pil()

    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()


async def upload_resume_thumbnail(
    *,
    user_id: str,
    pdf_content: bytes,
) -> dict:
    thumbnail = render_resume_thumbnail(pdf_content)
    bucket = settings.SUPABASE_RESUME_BUCKET
    storage_path = build_resume_thumbnail_storage_path(user_id)
    quoted_path = _quote_storage_path(storage_path)
    url = (
        f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/"
        f"{bucket}/{quoted_path}"
    )

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            url,
            params={"upsert": "true"},
            headers={
                **_storage_headers("image/png"),
                "x-upsert": "true",
            },
            content=thumbnail,
        )
        response.raise_for_status()

    logger.info("Uploaded resume thumbnail to Supabase Storage: %s", storage_path)

    return {
        "storage_bucket": bucket,
        "thumbnail_storage_path": storage_path,
    }


async def create_resume_signed_url(
    storage_path: str,
    expires_in: int = SIGNED_URL_EXPIRES_SECONDS,
) -> str | None:
    if not storage_path:
        return None

    bucket = settings.SUPABASE_RESUME_BUCKET
    quoted_path = _quote_storage_path(storage_path)
    url = (
        f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/sign/"
        f"{bucket}/{quoted_path}"
    )

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            url,
            headers={
                **_storage_headers("application/json"),
            },
            json={"expiresIn": expires_in},
        )

        if response.status_code >= 400:
            logger.warning(
                "Could not create signed URL for storage path: %s",
                storage_path,
            )
            return None

    signed_url = response.json().get("signedURL")
    if not signed_url:
        return None

    if signed_url.startswith("http"):
        return signed_url

    return f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1{signed_url}"
