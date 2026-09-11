"""Provider-neutral Iranian payment boundary for Sahyfa."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import httpx


class PaymentProviderError(RuntimeError):
    """A gateway rejected or could not complete an operation."""


@dataclass(frozen=True)
class PaymentRequest:
    amount: int
    callback_url: str
    description: str
    mobile: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class PaymentSession:
    authority: str
    payment_url: str


@dataclass(frozen=True)
class VerifiedPayment:
    authority: str
    reference_id: str
    card_pan: str | None = None
    fee: int | None = None


class PaymentProvider(Protocol):
    async def create(self, request: PaymentRequest) -> PaymentSession: ...

    async def verify(self, authority: str, amount: int) -> VerifiedPayment: ...


class ZarinPalProvider:
    """ZarinPal REST API client using the current merchant API contract."""

    def __init__(self, merchant_id: str, *, sandbox: bool = False, client: httpx.AsyncClient | None = None):
        self.merchant_id = merchant_id
        self.base_url = "https://sandbox.zarinpal.com/pg/v4/payment" if sandbox else "https://payment.zarinpal.com/pg/v4/payment"
        self._client = client

    async def create(self, request: PaymentRequest) -> PaymentSession:
        payload: dict[str, Any] = {
            "merchant_id": self.merchant_id,
            "amount": request.amount,
            "callback_url": request.callback_url,
            "description": request.description,
        }
        if request.mobile or request.metadata:
            payload["metadata"] = {**({"mobile": request.mobile} if request.mobile else {}), **(request.metadata or {})}
        response = await self._request("/request.json", payload)
        data = response.get("data") or {}
        authority = data.get("authority")
        if not authority:
            raise PaymentProviderError(self._error_message(response, "ZarinPal request failed"))
        return PaymentSession(str(authority), f"https://www.zarinpal.com/pg/StartPay/{authority}")

    async def verify(self, authority: str, amount: int) -> VerifiedPayment:
        response = await self._request("/verify.json", {"merchant_id": self.merchant_id, "amount": amount, "authority": authority})
        data = response.get("data") or {}
        reference_id = data.get("ref_id")
        if not reference_id:
            raise PaymentProviderError(self._error_message(response, "ZarinPal verification failed"))
        return VerifiedPayment(str(authority), str(reference_id), data.get("card_pan"), data.get("fee"))

    async def _request(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=20)
        try:
            response = await client.post(f"{self.base_url}{path}", json=payload)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise PaymentProviderError("ZarinPal gateway request failed") from exc
        finally:
            if owns_client:
                await client.aclose()

    @staticmethod
    def _error_message(response: dict[str, Any], fallback: str) -> str:
        return str((response.get("errors") or {}).get("message") or fallback)
