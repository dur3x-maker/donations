from app.api.v1 import uploads


async def test_story_photo_upload_accepts_image(client, user_factory, auth_headers, tmp_path, monkeypatch):
    user = await user_factory()
    monkeypatch.setattr(uploads, "STORY_PHOTO_DIR", tmp_path)
    response = await client.post(
        "/api/v1/uploads/story-photo",
        files={"file": ("result.png", b"\x89PNG\r\n\x1a\n" + b"x" * 32, "image/png")},
        headers=auth_headers(user),
    )
    assert response.status_code == 200
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
        files={"file": ("large.jpg", b"\xff\xd8\xff" + b"x" * uploads.MAX_AVATAR_SIZE, "image/jpeg")},
        headers=auth_headers(user),
    )
    assert fake.status_code == 400
    assert oversized.status_code == 413
