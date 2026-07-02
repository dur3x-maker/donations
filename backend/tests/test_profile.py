async def test_empty_impact_profile(client, user_factory, auth_headers):
    user = await user_factory()
    response = await client.get("/api/v1/me/profile-impact", headers=auth_headers(user))
    assert response.status_code == 200
    assert response.json()["confirmed_contributions_count"] == 0
    assert response.json()["is_patron"] is False
    assert response.json()["patron_since"] is None


async def test_profile_counts_confirmed_contributions(
    client, user_factory, campaign_factory, contribution_factory, auth_headers
):
    owner = await user_factory()
    donor = await user_factory()
    campaign = await campaign_factory(owner, target_amount=100000)
    await contribution_factory(campaign, user=donor, count=5)
    response = await client.get("/api/v1/me/profile-summary", headers=auth_headers(donor))
    assert response.status_code == 200
    assert response.json()["confirmed_contributions_count"] == 5
    assert response.json()["can_create_campaign"] is True
    assert response.json()["supported_campaigns_count"] == 1
    assert all("copy" in item for item in response.json()["achievements"])


async def test_public_profile_does_not_expose_email(client, user_factory):
    user = await user_factory(username="public_user", email="private@example.com")
    response = await client.get(f"/api/v1/users/{user.username}")
    assert response.status_code == 200
    assert "email" not in response.json()


async def test_update_profile_fields_are_visible_publicly(client, user_factory, auth_headers):
    user = await user_factory(username="old_name")
    updated = await client.patch(
        "/api/v1/me",
        json={
            "username": "new_name",
            "first_name": "Никита",
            "last_name": "Иванов",
            "bio": "Помогаю историям, которые понимаю.",
            "city": "Нижний Новгород",
            "avatar_url": "http://testserver/uploads/avatars/avatar.png",
        },
        headers=auth_headers(user),
    )
    assert updated.status_code == 200
    assert updated.json()["username"] == "new_name"
    assert updated.json()["bio"] == "Помогаю историям, которые понимаю."

    public = await client.get("/api/v1/users/new_name")
    assert public.status_code == 200
    assert public.json()["first_name"] == "Никита"
    assert public.json()["last_name"] == "Иванов"
    assert public.json()["city"] == "Нижний Новгород"
    assert public.json()["avatar_url"].endswith("/uploads/avatars/avatar.png")


async def test_update_profile_rejects_duplicate_username(client, user_factory, auth_headers):
    existing = await user_factory(username="taken_name")
    user = await user_factory(username="free_name")
    response = await client.patch(
        "/api/v1/me",
        json={"username": existing.username},
        headers=auth_headers(user),
    )
    assert response.status_code == 409
