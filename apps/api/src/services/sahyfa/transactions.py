from datetime import datetime, timezone

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.sahyfa_payments import SahyfaPaymentTransaction
from src.services.sahyfa.payments import PaymentProvider, PaymentRequest, PaymentSession, VerifiedPayment


async def create_pending_transaction(
    session: AsyncSession,
    *,
    org_id: int,
    user_id: int,
    provider_name: str,
    request: PaymentRequest,
    provider: PaymentProvider,
) -> tuple[SahyfaPaymentTransaction, PaymentSession]:
    payment = await provider.create(request)
    transaction = SahyfaPaymentTransaction(
        org_id=org_id,
        user_id=user_id,
        provider=provider_name,
        authority=payment.authority,
        amount=request.amount,
        description=request.description,
        callback_url=request.callback_url,
        provider_data=request.metadata,
    )
    session.add(transaction)
    await session.commit()
    await session.refresh(transaction)
    return transaction, payment


async def verify_transaction(
    session: AsyncSession,
    *,
    authority: str,
    provider: PaymentProvider,
) -> tuple[SahyfaPaymentTransaction, VerifiedPayment | None]:
    result = await session.exec(
        select(SahyfaPaymentTransaction).where(SahyfaPaymentTransaction.authority == authority)
    )
    transaction = result.one_or_none()
    if transaction is None:
        raise LookupError("Payment transaction was not found")
    if transaction.status == "verified":
        return transaction, None
    if transaction.status != "pending":
        raise ValueError(f"Payment transaction is {transaction.status}")

    try:
        verified = await provider.verify(authority, transaction.amount)
    except Exception:
        transaction.status = "failed"
        await session.commit()
        raise

    transaction.status = "verified"
    transaction.reference_id = verified.reference_id
    transaction.verified_at = datetime.now(timezone.utc)
    transaction.provider_data = {
        **(transaction.provider_data or {}),
        "card_pan": verified.card_pan,
        "fee": verified.fee,
    }
    await session.commit()
    await session.refresh(transaction)
    return transaction, verified
