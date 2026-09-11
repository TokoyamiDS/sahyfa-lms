import httpx
import pytest

from src.services.sahyfa.payments import JibitProvider, PaymentProviderError, PaymentRequest, ZarinPalProvider


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


@pytest.mark.asyncio
async def test_jibit_create_and_verify_use_provider_contract():
    calls = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.url.path.endswith("/request"):
            return httpx.Response(200, json={"paymentId": "J123", "paymentUrl": "https://jibit.test/J123"})
        return httpx.Response(200, json={"referenceNumber": "R123"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = JibitProvider("api", "secret", initiate_path="/request", verify_path="/verify", client=client)
    session = await provider.create(PaymentRequest(50_000, "https://sahyfa.test/callback", "Course"))
    verified = await provider.verify(session.authority, 50_000)

    assert session.payment_url == "https://jibit.test/J123"
    assert verified.reference_id == "R123"
    assert calls[0].headers["x-api-key"] == "api"
    await client.aclose()
