import json

import httpx
import pytest

from veriadd import (
    AsyncVeriaddClient,
    VeriaddClient,
    VeriaddError,
    awith_veriadd_retry,
    with_veriadd_retry,
)

OK_VERIFY = {
    "audit_id": "audit-1",
    "status": "verified",
    "confidence": 92,
    "reasons": ["postcode valid in NIPOST registry (+40)"],
    "postcode_canonical": "LA-11-W06-TC-10",
    "nipost": {"postcode": "LA-11-W06-TC-10", "valid": True},
    "identity": {"provider": "dojah", "bvn_valid": True},
    "billed_kobo": 5000,
    "billed_ngn": 50,
}


def envelope(body, status=200):
    return httpx.Response(status, json={"data": body})


def client_with(handler, **kwargs):
    transport = httpx.MockTransport(handler)
    kwargs.setdefault("http_client", httpx.Client(transport=transport))
    return VeriaddClient(api_key="vr_live_test", **kwargs)


def test_requires_api_key():
    with pytest.raises(ValueError):
        VeriaddClient(api_key="")


def test_verify_posts_payload_with_auth_headers():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["headers"] = dict(request.headers)
        seen["body"] = json.loads(request.content.decode())
        return envelope(OK_VERIFY)

    c = client_with(handler)
    try:
        res = c.verify_address(postcode="LA-11-W06-TC-10", level=3)
    finally:
        c.close()
    assert res.status == "verified"
    assert res.confidence == 92
    assert res.identity is not None and res.identity.bvn_valid is True
    assert seen["url"] == "https://api.veriadd.tech/api/v1/verify/address"
    assert seen["headers"]["x-api-key"] == "vr_live_test"
    assert seen["headers"]["x-request-id"]
    assert seen["body"] == {"postcode": "LA-11-W06-TC-10", "level": 3}


def test_base_url_override_trims_slashes():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return envelope({"postcode": "LA-11-W06-TC-10", "valid": True})

    c = client_with(handler, base_url="http://localhost:8080/")
    try:
        lookup = c.lookup("LA-11-W06-TC-10", 1)
    finally:
        c.close()
    assert lookup.valid is True
    assert seen["url"] == "http://localhost:8080/api/v1/lookup?code=LA-11-W06-TC-10&level=1"


def test_error_envelope_maps_to_veriadd_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            402,
            json={"error": {"code": "insufficient_credits", "message": "top up", "request_id": "req-1"}},
        )

    c = client_with(handler)
    try:
        with pytest.raises(VeriaddError) as exc:
            c.wallet()
    finally:
        c.close()
    assert exc.value.code == "insufficient_credits"
    assert exc.value.status == 402
    assert exc.value.request_id == "req-1"


def test_non_json_error_body():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, content=b"gateway exploded")

    c = client_with(handler)
    try:
        with pytest.raises(VeriaddError) as exc:
            c.wallet()
    finally:
        c.close()
    assert exc.value.status == 502


def test_timeout_exception_maps_to_timeout_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timed out", request=request)

    c = client_with(handler, timeout=0.02)
    assert c.timeout == 0.02
    try:
        with pytest.raises(VeriaddError) as exc:
            c.wallet()
    finally:
        c.close()
    assert exc.value.code == "timeout"


def test_create_key_posts_env():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content.decode())
        return httpx.Response(
            201,
            json={"data": {"api_key": "vr_live_x", "key_prefix": "vr_live_x", "warning": "once"}},
        )

    c = client_with(handler)
    try:
        key = c.create_key("test")
    finally:
        c.close()
    assert key["api_key"] == "vr_live_x"
    assert seen["body"] == {"env": "test"}


def test_retry_succeeds_after_retryable():
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise VeriaddError(code="rate_limited", status=429, message="slow down")
        return "ok"

    assert with_veriadd_retry(flaky, base_delay=0.001) == "ok"
    assert len(calls) == 3


def test_retry_bubbles_non_retryable_immediately():
    calls = []

    def bad():
        calls.append(1)
        raise VeriaddError(code="invalid_api_key", status=401, message="bad key")

    with pytest.raises(VeriaddError) as exc:
        with_veriadd_retry(bad, base_delay=0.001)
    assert exc.value.code == "invalid_api_key"
    assert len(calls) == 1


def test_retry_gives_up_after_max():
    calls = []

    def slow():
        calls.append(1)
        raise VeriaddError(code="nipost_rate_limited", status=429, message="slow")

    with pytest.raises(VeriaddError):
        with_veriadd_retry(slow, max_retries=2, base_delay=0.001)
    assert len(calls) == 3


@pytest.mark.asyncio
async def test_async_client_verify_and_status():
    seen = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        if request.url.path.endswith("/verify/address"):
            return envelope(OK_VERIFY)
        return envelope({"service": "veriadd", "version": "0.1.0"})

    transport = httpx.MockTransport(handler)
    async with AsyncVeriaddClient(
        api_key="k", http_client=httpx.AsyncClient(transport=transport)
    ) as c:
        res = await c.verify_address(postcode="LA-11-W06-TC-10", level=3)
        assert res.status == "verified"
        st = await c.status()
        assert st.service == "veriadd"
    assert seen["url"].endswith("/api/v1/status")
