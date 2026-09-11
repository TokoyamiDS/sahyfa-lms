import os
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, HttpUrl
from sqlmodel.ext.asyncio.session import AsyncSession

from src.core.events.database import get_db_session
from src.db.users import PublicUser
from src.services.sahyfa.payments import JibitProvider, PaymentProvider, PaymentProviderError, PaymentRequest, ZarinPalProvider
from src.services.sahyfa.transactions import create_pending_transaction, verify_transaction
from src.security.auth import get_authenticated_user


router = APIRouter(prefix="/sahyfa/payments", tags=["sahyfa-payments"])


class PaymentStartRequest(BaseModel):
    provider: Literal["zarinpal", "jibit"]
    org_id: int
    amount: int
    callback_url: HttpUrl
    description: str
    mobile: str | None = None
    invoice_number: str | None = None


def get_provider(name: str) -> PaymentProvider:
    if name == "zarinpal":
        merchant_id = os.environ.get("SAHYFA_ZARINPAL_MERCHANT_ID")
        if not merchant_id:
            raise HTTPException(status_code=503, detail="ZarinPal is not configured")
        return ZarinPalProvider(
            merchant_id,
            sandbox=os.environ.get("SAHYFA_ZARINPAL_SANDBOX", "false").lower() in {"1", "true", "yes"},
        )
    api_key = os.environ.get("SAHYFA_JIBIT_API_KEY")
    secret_key = os.environ.get("SAHYFA_JIBIT_SECRET_KEY")
    if not api_key or not secret_key:
        raise HTTPException(status_code=503, detail="Jibit is not configured")
    return JibitProvider(
        api_key,
        secret_key,
        base_url=os.environ.get("SAHYFA_JIBIT_BASE_URL", "https://napi.jibit.ir"),
        initiate_path=os.environ.get("SAHYFA_JIBIT_INITIATE_PATH", "/ppg/v3/payment/request"),
        verify_path=os.environ.get("SAHYFA_JIBIT_VERIFY_PATH", "/ppg/v3/payment/verify"),
    )


@router.post("/start")
async def start_payment(
    payload: PaymentStartRequest,
    current_user: PublicUser = Depends(get_authenticated_user),
    db_session: AsyncSession = Depends(get_db_session),
):
    if payload.amount <= 0:
        raise HTTPException(status_code=422, detail="Amount must be positive")
    provider = get_provider(payload.provider)
    try:
        transaction, payment = await create_pending_transaction(
            db_session,
            org_id=payload.org_id,
            user_id=current_user.id,
            provider_name=payload.provider,
            request=PaymentRequest(
                amount=payload.amount,
                callback_url=str(payload.callback_url),
                description=payload.description,
                mobile=payload.mobile,
                metadata={"invoice_number": payload.invoice_number} if payload.invoice_number else None,
            ),
            provider=provider,
        )
    except PaymentProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"transaction_id": transaction.id, "authority": payment.authority, "payment_url": payment.payment_url}


@router.get("/callback")
async def payment_callback(
    provider_name: Literal["zarinpal", "jibit"] = Query(alias="provider"),
    authority: str = Query(min_length=1),
    db_session: AsyncSession = Depends(get_db_session),
):
    provider = get_provider(provider_name)
    try:
        # The transaction service looks up the amount by authority, so the callback
        # never trusts an amount supplied by the browser/gateway query string.
        transaction, verified = await verify_transaction(db_session, authority=authority, provider=provider)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (PaymentProviderError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "status": transaction.status,
        "transaction_id": transaction.id,
        "reference_id": transaction.reference_id,
        "verified_now": verified is not None,
        "access_grant": "pending_product_mapping",
    }
