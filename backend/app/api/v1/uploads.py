from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status

from app.api.deps import require_current_user
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
MAX_IMAGE_SIZE = 5 * 1024 * 1024
MAX_AVATAR_SIZE = 2 * 1024 * 1024


@router.post("/campaign-cover")
async def upload_campaign_cover(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(require_current_user),
) -> dict[str, str]:
    extension = ALLOWED_IMAGE_TYPES.get(file.content_type or "")
    if extension is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only JPG and PNG images are allowed")

    content = await file.read()
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Image is too large")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{extension}"
    path = UPLOAD_DIR / filename
    path.write_bytes(content)

    base_url = str(request.base_url).rstrip("/")
    return {"url": f"{base_url}/uploads/campaign-covers/{filename}"}


@router.post("/story-photo")
async def upload_story_photo(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(require_current_user),
) -> dict[str, str]:
    extension = ALLOWED_IMAGE_TYPES.get(file.content_type or "")
    if extension is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Допустимы только JPG, PNG и WebP")

    content = await file.read(MAX_IMAGE_SIZE + 1)
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Размер изображения не должен превышать 5 МБ")
    if not _matches_image_signature(content, extension):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Файл не соответствует заявленному формату изображения")

    STORY_PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{extension}"
    (STORY_PHOTO_DIR / filename).write_bytes(content)
    base_url = str(request.base_url).rstrip("/")
    return {"url": f"{base_url}/uploads/story-photos/{filename}"}


@router.post("/avatar")
async def upload_avatar(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(require_current_user),
) -> dict[str, str]:
    extension = ALLOWED_IMAGE_TYPES.get(file.content_type or "")
    if extension is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Допустимы только JPG, PNG и WebP")

    content = await file.read(MAX_AVATAR_SIZE + 1)
    if len(content) > MAX_AVATAR_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Размер аватара не должен превышать 2 МБ")
    if not _matches_image_signature(content, extension):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Файл не соответствует заявленному формату изображения")

    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{current_user.id}-{uuid4().hex}{extension}"
    (AVATAR_DIR / filename).write_bytes(content)
    base_url = str(request.base_url).rstrip("/")
    return {"url": f"{base_url}/uploads/avatars/{filename}"}


def _matches_image_signature(content: bytes, extension: str) -> bool:
    if extension == ".jpg":
        return content.startswith(b"\xff\xd8\xff")
    if extension == ".png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")
    if extension == ".webp":
        return len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP"
    return False
