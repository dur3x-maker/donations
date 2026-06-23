from decimal import Decimal

from sqlalchemy import select

from app.models.contribution import Contribution, ContributionStatus
from app.models.payment import Payment, PaymentStatus
from app.services.payment_service import fail_payment


async def test_failed_payment_rejects_pending_contribution(
    db_session, user_factory, campaign_factory
):
    owner = await user_factory()
    donor = await user_factory()
    campaign = await campaign_factory(owner)
    contribution = Contribution(
        campaign_id=campaign.id,
        user_id=donor.id,
        amount=Decimal("100"),
        status=ContributionStatus.pending,
    )
    db_session.add(contribution)
    await db_session.flush()
    payment = Payment(
        contribution_id=contribution.id,
        provider="test",
        amount=contribution.amount,
        currency="RUB",
        status=PaymentStatus.pending,
    )
    db_session.add(payment)
    await db_session.flush()

    assert await fail_payment(db_session, payment) is True
    assert payment.status == PaymentStatus.failed
    assert contribution.status == ContributionStatus.rejected


async def test_succeeded_payment_cannot_be_failed(
    db_session, user_factory, campaign_factory, contribution_factory
):
    owner = await user_factory()
    donor = await user_factory()
    campaign = await campaign_factory(owner)
    contribution = (await contribution_factory(campaign, user=donor))[0]
    payment = await db_session.scalar(select(Payment).where(Payment.contribution_id == contribution.id))
    assert await fail_payment(db_session, payment) is False
    assert payment.status == PaymentStatus.succeeded
