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

