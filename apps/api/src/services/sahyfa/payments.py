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


class JibitProvider:
    """Jibit payment adapter with configurable merchant API paths.

    Jibit deployments can expose different API versions. Keeping the paths
    configurable avoids baking a dashboard-specific version into the LMS.
    """

    def __init__(
        self,
        api_key: str,
        secret_key: str,
        *,
        base_url: str = "https://napi.jibit.ir",
        initiate_path: str = "/ppg/v3/payment/request",
        verify_path: str = "/ppg/v3/payment/verify",
        client: httpx.AsyncClient | None = None,
    ):
        self.api_key = api_key
        self.secret_key = secret_key
        self.base_url = base_url.rstrip("/")
        self.initiate_path = initiate_path
        self.verify_path = verify_path
        self._client = client

    async def create(self, request: PaymentRequest) -> PaymentSession:
        payload: dict[str, Any] = {
            "amount": request.amount,
            "callbackUrl": request.callback_url,
            "mobileNumber": request.mobile,
            "invoiceNumber": (request.metadata or {}).get("invoice_number"),
        }
        response = await self._request(self.initiate_path, payload)
        data = response.get("data") or response
        authority = data.get("paymentId") or data.get("token") or data.get("authority")
        if not authority:
            raise PaymentProviderError(self._error_message(response, "Jibit request failed"))
        payment_url = data.get("paymentUrl") or data.get("payment_url")
        if not payment_url:
            payment_url = f"{self.base_url}/ppg/v3/payment/start/{authority}"
        return PaymentSession(str(authority), payment_url)

    async def verify(self, authority: str, amount: int) -> VerifiedPayment:
        response = await self._request(
            self.verify_path,
            {"paymentId": authority, "amount": amount},
        )
        data = response.get("data") or response
        reference_id = data.get("referenceNumber") or data.get("referenceId") or data.get("refId")
        if not reference_id:
            raise PaymentProviderError(self._error_message(response, "Jibit verification failed"))
        return VerifiedPayment(str(authority), str(reference_id), data.get("cardNumber"), data.get("fee"))

    async def _request(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=20)
        try:
            response = await client.post(
                f"{self.base_url}{path}",
                json=payload,
                headers={"x-api-key": self.api_key, "x-secret-key": self.secret_key},
            )
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise PaymentProviderError("Jibit gateway request failed") from exc
        finally:
            if owns_client:
                await client.aclose()

    @staticmethod
    def _error_message(response: dict[str, Any], fallback: str) -> str:
        return str(response.get("message") or (response.get("errors") or {}).get("message") or fallback)
