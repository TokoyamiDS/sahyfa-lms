import httpx
import pytest

from src.services.sahyfa.payments import PaymentProviderError, PaymentRequest, ZarinPalProvider


@pytest.mark.asyncio
async def test_zarinpal_create_returns_payment_session():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": {"authority": "A123"}})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    session = await ZarinPalProvider("merchant", sandbox=True, client=client).create(
        PaymentRequest(100_000, "https://sahyfa.test/callback", "Course")
    )
    assert session.authority == "A123"
    assert session.payment_url.endswith("/A123")
    await client.aclose()


@pytest.mark.asyncio
async def test_zarinpal_verify_returns_reference_id():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": {"ref_id": 987654, "card_pan": "6037"}})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    verified = await ZarinPalProvider("merchant", client=client).verify("A123", 100_000)
    assert verified.reference_id == "987654"
    assert verified.card_pan == "6037"
    await client.aclose()


@pytest.mark.asyncio
async def test_zarinpal_errors_are_provider_errors():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": {}, "errors": {"message": "bad amount"}})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    with pytest.raises(PaymentProviderError, match="bad amount"):
        await ZarinPalProvider("merchant", client=client).create(PaymentRequest(1, "https://sahyfa.test/callback", "Course"))
    await client.aclose()
