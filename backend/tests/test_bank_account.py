from decimal import Decimal

from app.models.bank_account_application import BankAccountApplication, BankAccountApplicationStatus
from tests.helpers import count_rows


async def test_bank_account_application_requires_five_confirmed_donations(client, user_factory, auth_headers):
    user = await user_factory()

    response = await client.post("/api/v1/bank-account/applications", headers=auth_headers(user))

    assert response.status_code == 403


async def test_bank_account_application_is_created_once(
    client, db_session, user_factory, campaign_factory, contribution_factory, auth_headers
):
    user = await user_factory()
    owner = await user_factory()
    campaign = await campaign_factory(owner, target_amount=Decimal("100000"))
    await contribution_factory(campaign, user=user, count=5)

    state_before = await client.get("/api/v1/bank-account/application", headers=auth_headers(user))
    assert state_before.status_code == 200
    assert state_before.json()["can_open_bank_account"] is True

    created = await client.post("/api/v1/bank-account/applications", headers=auth_headers(user))
    assert created.status_code == 201
    assert created.json()["status"] == BankAccountApplicationStatus.pending.value
    assert await count_rows(db_session, BankAccountApplication, BankAccountApplication.user_id == user.id) == 1

    state_after = await client.get("/api/v1/bank-account/application", headers=auth_headers(user))
    assert state_after.status_code == 200
    assert state_after.json()["can_open_bank_account"] is False
    assert state_after.json()["application_status"] == BankAccountApplicationStatus.pending.value

    duplicate = await client.post("/api/v1/bank-account/applications", headers=auth_headers(user))
    assert duplicate.status_code == 409
