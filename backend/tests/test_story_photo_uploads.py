from app.api.v1 import uploads
from app.core.config import settings


async def test_story_photo_upload_accepts_image(client, user_factory, auth_headers, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "public_web_url", "https://test.digitalgardens.online")
    user = await user_factory()
    monkeypatch.setattr(uploads, "STORY_PHOTO_DIR", tmp_path)
    response = await client.post(
        "/api/v1/uploads/story-photo",
        files={"file": ("result.png", b"\x89PNG\r\n\x1a\n" + b"x" * 32, "image/png")},
        headers=auth_headers(user),
    )
    assert response.status_code == 200
    assert response.json()["url"].startswith("https://test.digitalgardens.online/uploads/story-photos/")
    assert response.json()["url"].endswith(".png")
    assert len(list(tmp_path.iterdir())) == 1


async def test_story_photo_upload_rejects_fake_and_oversized_files(
    client, user_factory, auth_headers, tmp_path, monkeypatch
):
    user = await user_factory()
    monkeypatch.setattr(uploads, "STORY_PHOTO_DIR", tmp_path)
    fake = await client.post(
        "/api/v1/uploads/story-photo",
        files={"file": ("fake.png", b"not-an-image", "image/png")},
        headers=auth_headers(user),
    )
    oversized = await client.post(
        "/api/v1/uploads/story-photo",
        files={"file": ("large.jpg", b"\xff\xd8\xff" + b"x" * uploads.MAX_IMAGE_SIZE, "image/jpeg")},
        headers=auth_headers(user),
    )
    assert fake.status_code == 400
    assert oversized.status_code == 413
    assert oversized.json()["detail"] == "Фото слишком большое. Максимальный размер — 10 МБ."


async def test_avatar_upload_accepts_image(client, user_factory, auth_headers, tmp_path, monkeypatch):
    user = await user_factory()
    monkeypatch.setattr(uploads, "AVATAR_DIR", tmp_path)
    response = await client.post(
        "/api/v1/uploads/avatar",
        files={"file": ("avatar.webp", b"RIFF" + b"x" * 4 + b"WEBP" + b"x" * 16, "image/webp")},
        headers=auth_headers(user),
    )
    assert response.status_code == 200
    assert response.json()["url"].endswith(".webp")
    assert len(list(tmp_path.iterdir())) == 1


async def test_avatar_upload_rejects_fake_and_oversized_files(client, user_factory, auth_headers, tmp_path, monkeypatch):
    user = await user_factory()
    monkeypatch.setattr(uploads, "AVATAR_DIR", tmp_path)
    fake = await client.post(
        "/api/v1/uploads/avatar",
        files={"file": ("fake.png", b"not-an-image", "image/png")},
        headers=auth_headers(user),
    )
    oversized = await client.post(
        "/api/v1/uploads/avatar",
        files={"file": ("large.jpg", b"\xff\xd8\xff" + b"x" * uploads.MAX_IMAGE_SIZE, "image/jpeg")},
        headers=auth_headers(user),
    )
    assert fake.status_code == 400
    assert oversized.status_code == 413


async def test_campaign_cover_uses_shared_image_validation(client, user_factory, auth_headers, tmp_path, monkeypatch):
    user = await user_factory()
    monkeypatch.setattr(uploads, "UPLOAD_DIR", tmp_path)

    accepted = await client.post(
        "/api/v1/uploads/campaign-cover",
        files={"file": ("cover.webp", b"RIFF" + b"x" * 4 + b"WEBP" + b"x" * 16, "image/webp")},
        headers=auth_headers(user),
    )
    fake = await client.post(
        "/api/v1/uploads/campaign-cover",
        files={"file": ("fake.png", b"not-an-image", "image/png")},
        headers=auth_headers(user),
    )

    assert accepted.status_code == 200
    assert accepted.json()["url"].endswith(".webp")
    assert fake.status_code == 400
