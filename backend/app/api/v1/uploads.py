from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.deps import require_current_user
from app.core.public_urls import build_public_web_url
from app.models.user import User

router = APIRouter(prefix="/uploads", tags=["uploads"])

UPLOAD_DIR = Path("uploads/campaign-covers")
STORY_PHOTO_DIR = Path("uploads/story-photos")
AVATAR_DIR = Path("uploads/avatars")
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_IMAGE_SIZE = 10 * 1024 * 1024


@router.post("/campaign-cover")
async def upload_campaign_cover(
    file: UploadFile = File(...),
    current_user: User = Depends(require_current_user),
) -> dict[str, str]:
    extension, content = await _read_valid_image(file)

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{extension}"
    path = UPLOAD_DIR / filename
    path.write_bytes(content)

    return {"url": build_public_web_url(f"/uploads/campaign-covers/{filename}")}


@router.post("/story-photo")
async def upload_story_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(require_current_user),
) -> dict[str, str]:
    extension, content = await _read_valid_image(file)

    STORY_PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{extension}"
    (STORY_PHOTO_DIR / filename).write_bytes(content)
    return {"url": build_public_web_url(f"/uploads/story-photos/{filename}")}


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(require_current_user),
) -> dict[str, str]:
    extension, content = await _read_valid_image(file)

    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{current_user.id}-{uuid4().hex}{extension}"
    (AVATAR_DIR / filename).write_bytes(content)
    return {"url": build_public_web_url(f"/uploads/avatars/{filename}")}


async def _read_valid_image(file: UploadFile) -> tuple[str, bytes]:
    extension = ALLOWED_IMAGE_TYPES.get(file.content_type or "")
    if extension is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Допустимы только JPG, PNG и WebP.",
        )

    content = await file.read(MAX_IMAGE_SIZE + 1)
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Фото слишком большое. Максимальный размер — 10 МБ.",
        )
    if not _matches_image_signature(content, extension):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Файл не соответствует заявленному формату изображения.",
        )
    return extension, content


def _matches_image_signature(content: bytes, extension: str) -> bool:
    if extension == ".jpg":
        return content.startswith(b"\xff\xd8\xff")
    if extension == ".png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")
    if extension == ".webp":
        return len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP"
    return False
