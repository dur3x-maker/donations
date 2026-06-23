import pytest


@pytest.mark.parametrize(
    ("payload", "status_code"),
    [
        ({"email": "bad", "username": "valid_user", "password": "password123"}, 422),
        ({"email": "hsfna@aaa", "username": "valid_user", "password": "password123"}, 422),
        ({"email": "a@example.com", "username": "", "password": "password123"}, 422),
        ({"email": "a@example.com", "username": "valid_user", "password": ""}, 422),
        ({"email": "a@example.com", "username": "x" * 25, "password": "password123"}, 422),
    ],
)
async def test_registration_validation(client, payload, status_code):
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == status_code


async def test_register_and_login(client):
    payload = {"email": "Donor@Example.com", "username": "Donor-One", "password": "password123"}
    registered = await client.post("/api/v1/auth/register", json=payload)
    assert registered.status_code == 200
    assert registered.json()["user"]["email"] == "donor@example.com"
    assert registered.json()["user"]["username"] == "donor-one"

    logged_in = await client.post(
        "/api/v1/auth/login",
        json={"email": "DONOR@example.com", "password": "password123"},
    )
    assert logged_in.status_code == 200
    assert logged_in.json()["access_token"]
    assert logged_in.json()["refresh_token"]


@pytest.mark.parametrize(
    "username",
    ["admin", "root", "support", "moderator", "system", "null", "undefined", "api", "test"],
)
async def test_reserved_usernames_are_rejected_case_insensitively(client, username):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"{username}@example.com",
            "username": username.upper(),
            "password": "password123",
        },
    )
    assert response.status_code == 422


async def test_wrong_password_and_unknown_user_have_same_status(client, user_factory):
    await user_factory(email="known@example.com")
    wrong = await client.post("/api/v1/auth/login", json={"email": "known@example.com", "password": "wrong"})
    unknown = await client.post("/api/v1/auth/login", json={"email": "missing@example.com", "password": "wrong"})
    assert wrong.status_code == unknown.status_code == 401


async def test_duplicate_registration(client):
    payload = {"email": "same@example.com", "username": "same_user", "password": "password123"}
    assert (await client.post("/api/v1/auth/register", json=payload)).status_code == 200
    assert (await client.post("/api/v1/auth/register", json=payload)).status_code == 409


async def test_duplicate_email_and_username_are_rejected_independently(client):
    original = {"email": "one@example.com", "username": "one_user", "password": "password123"}
    await client.post("/api/v1/auth/register", json=original)
    duplicate_email = {**original, "username": "other_user"}
    duplicate_username = {**original, "email": "other@example.com"}
    assert (await client.post("/api/v1/auth/register", json=duplicate_email)).status_code == 409
    assert (await client.post("/api/v1/auth/register", json=duplicate_username)).status_code == 409


async def test_protected_endpoint_requires_valid_access_token(client):
    assert (await client.get("/api/v1/me")).status_code == 401
    response = await client.get("/api/v1/me", headers={"Authorization": "Bearer invalid"})
    assert response.status_code == 401
