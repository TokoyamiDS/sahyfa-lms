from datetime import datetime

import pytest

from src.db.sahyfa_payments import SahyfaPaymentTransaction
from src.services.sahyfa.payments import PaymentSession, PaymentRequest, VerifiedPayment
from src.services.sahyfa.transactions import verify_transaction


class FakeResult:
    def __init__(self, value):
        self.value = value

    def one_or_none(self):
        return self.value


class FakeSession:
    def __init__(self, transaction):
        self.transaction = transaction
        self.commits = 0

    async def exec(self, query):
        return FakeResult(self.transaction)

    async def commit(self):
        self.commits += 1

    async def refresh(self, transaction):
        return None


class FakeProvider:
    def __init__(self):
        self.calls = 0

    async def verify(self, authority, amount):
        self.calls += 1
        return VerifiedPayment(authority, "REF-1")


@pytest.mark.asyncio
async def test_verified_transaction_is_idempotent():
    transaction = SahyfaPaymentTransaction(
        org_id=1, user_id=2, provider="zarinpal", authority="A1", amount=100, status="verified"
    )
    provider = FakeProvider()

    result, verified = await verify_transaction(FakeSession(transaction), authority="A1", provider=provider)

    assert result is transaction
    assert verified is None
    assert provider.calls == 0


@pytest.mark.asyncio
async def test_pending_transaction_is_verified_once():
    transaction = SahyfaPaymentTransaction(
        org_id=1, user_id=2, provider="zarinpal", authority="A1", amount=100, status="pending"
    )
    provider = FakeProvider()
    session = FakeSession(transaction)

    result, verified = await verify_transaction(session, authority="A1", provider=provider)

    assert result.status == "verified"
    assert verified.reference_id == "REF-1"
    assert isinstance(result.verified_at, datetime)
    assert provider.calls == 1
    assert session.commits == 1
