"""Synchronous and asynchronous clients for the Veriadd address KYC API."""

import time
import uuid
from typing import Any, Awaitable, Callable, Dict, List, Optional, TypeVar

import httpx

from .errors import VeriaddError
from .models import (
    VeriaddCreatedKey,
    VeriaddKYB,
    VeriaddKeyInfo,
    VeriaddNipostLookup,
    VeriaddStatus,
    VeriaddTopupInit,
    VeriaddTopupVerify,
    VeriaddUsageRow,
    VeriaddVerifyResult,
    VeriaddWallet,
)

#: Default production host. Override with ``base_url`` for self-hosted
#: backends or local development.
VERIADD_DEFAULT_BASE_URL = "https://api.veriadd.tech"

#: Error codes worth retrying with backoff (transient upstream/rate states).
VERIADD_RETRYABLE_CODES = frozenset(
    {"rate_limited", "provider_unavailable", "nipost_rate_limited"}
)

T = TypeVar("T")


def _error_from_response(status: int, body: Any) -> VeriaddError:
    err: Dict[str, Any] = {}
    if isinstance(body, dict):
        nested = body.get("error")
        if isinstance(nested, dict):
            err = nested
    code = str(err.get("code") or f"http_{status}")
    message = str(err.get("message") or f"Request failed ({status})")
    request_id = err.get("request_id")
    return VeriaddError(
        code=code,
        status=status,
        message=message,
        request_id=str(request_id) if request_id is not None else None,
    )


def _unwrap(body: Any) -> Any:
    if isinstance(body, dict) and "data" in body:
        return body["data"]
    return body


def _as_map(payload: Any) -> Dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    raise VeriaddError(
        code="bad_response",
        status=0,
        message="Unexpected response shape from the Veriadd API",
    )


class VeriaddClient:
    """Official client for the Veriadd address KYC API.

    .. code-block:: python

        from veriadd import VeriaddClient

        client = VeriaddClient(api_key=os.environ["VERIADD_KEY"])
        result = client.verify_address(
            postcode="LA-11-W06-TC-10", state="LAGOS", bvn="22233344455", level=3,
        )
        if result.status == "verified" and result.confidence >= 80:
            pass  # proceed to onboarding; result.audit_id is your CBN trail
    """

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        timeout: float = 15.0,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        if not api_key:
            raise ValueError("VeriaddClient requires an api_key")
        self.api_key = api_key
        self.base_url = (base_url or VERIADD_DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        self._http = http_client or httpx.Client(timeout=timeout)
        self._owns_http = http_client is None

    def close(self) -> None:
        """Release resources if this client created its own HTTP client."""
        if self._owns_http:
            self._http.close()

    def __enter__(self) -> "VeriaddClient":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, str]] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Any:
        try:
            res = self._http.request(
                method,
                self.base_url + path,
                params=params,
                json=payload,
                headers={
                    "X-API-Key": self.api_key,
                    "X-Request-ID": uuid.uuid4().hex,
                },
            )
        except httpx.TimeoutException as exc:
            raise VeriaddError(
                code="timeout",
                status=0,
                message=f"Request timed out after {self.timeout:g}s",
            ) from exc
        except httpx.HTTPError as exc:
            raise VeriaddError(code="network_error", status=0, message=str(exc)) from exc
        try:
            body = res.json()
        except ValueError:
            body = {}
        if res.status_code < 200 or res.status_code >= 300:
            raise _error_from_response(res.status_code, body)
        return _unwrap(body)

    # -- primary endpoints -------------------------------------------------

    def verify_address(self, **kwargs: Any) -> VeriaddVerifyResult:
        """Verify an address + optional identity cross-checks. The money endpoint."""
        return VeriaddVerifyResult.from_dict(
            _as_map(self._request("POST", "/api/v1/verify/address", payload=kwargs))
        )

    def lookup(self, code: str, level: int = 1) -> VeriaddNipostLookup:
        """Direct NIPOST postcode lookup. L1 is free."""
        return VeriaddNipostLookup.from_dict(
            _as_map(
                self._request(
                    "GET", "/api/v1/lookup", params={"code": code, "level": str(level)}
                )
            )
        )

    def autocomplete(self, q: str) -> Any:
        """Segment-aware postcode typeahead."""
        return self._request("GET", "/api/v1/search/autocomplete", params={"q": q})

    def nearby(self, lat: float, lng: float, radius: Optional[float] = None) -> Any:
        """Postcodes within a radius (metres, default 300) of a coordinate."""
        params = {"lat": str(lat), "lng": str(lng)}
        if radius is not None:
            params["radius"] = str(radius)
        return self._request("GET", "/api/v1/search/nearby", params=params)

    def reverse(self, lat: float, lng: float, max_distance_m: Optional[float] = None) -> Any:
        """Resolve a coordinate to the nearest postcode."""
        params = {"lat": str(lat), "lng": str(lng)}
        if max_distance_m is not None:
            params["max_distance_m"] = str(max_distance_m)
        return self._request("GET", "/api/v1/search/reverse", params=params)

    def disassemble(self, code: str) -> Any:
        """Parse a postcode into segments (native NIPOST shape)."""
        return self._request(
            "GET", "/api/v1/assembly/disassemble", params={"code": code}
        )

    def assemble(
        self, state: str, lga: str, district: str, area: str, unit: str
    ) -> Any:
        """Assemble segments into a canonical postcode."""
        return self._request(
            "POST",
            "/api/v1/assembly/assemble",
            payload={
                "state": state,
                "lga": lga,
                "district": district,
                "area": area,
                "unit": unit,
            },
        )

    def wallet(self) -> VeriaddWallet:
        """Wallet balance + pricing for this key."""
        return VeriaddWallet.from_dict(_as_map(self._request("GET", "/api/v1/wallet")))

    def usage(self, limit: int = 50) -> List[VeriaddUsageRow]:
        """Metered call history (1–200, default 50)."""
        data = self._request("GET", "/api/v1/usage", params={"limit": str(limit)})
        if not isinstance(data, list):
            return []
        return [VeriaddUsageRow.from_dict(e) for e in data if isinstance(e, dict)]

    def topup_init(
        self, amount_kobo: int, email: str, callback_url: Optional[str] = None
    ) -> VeriaddTopupInit:
        """Start a Bachs wallet top-up; redirect the user to `authorization_url`."""
        payload: Dict[str, Any] = {"amount_kobo": amount_kobo, "email": email}
        if callback_url is not None:
            payload["callback_url"] = callback_url
        return VeriaddTopupInit.from_dict(
            _as_map(self._request("POST", "/api/v1/wallet/topup/initialize", payload=payload))
        )

    def topup_verify(self, reference: str) -> VeriaddTopupVerify:
        """Verify a top-up reference and credit the wallet (idempotent)."""
        return VeriaddTopupVerify.from_dict(
            _as_map(
                self._request(
                    "GET", "/api/v1/wallet/topup/verify", params={"reference": reference}
                )
            )
        )

    def kyb_get(self) -> Optional[VeriaddKYB]:
        """Current workspace KYB submission (None when never submitted)."""
        data = self._request("GET", "/api/v1/kyb")
        if data is None:
            return None
        return VeriaddKYB.from_dict(_as_map(data))

    def kyb_submit(self, **kwargs: Any) -> VeriaddKYB:
        """Submit (or resubmit) KYB business details."""
        return VeriaddKYB.from_dict(
            _as_map(self._request("POST", "/api/v1/kyb", payload=kwargs))
        )

    def status(self) -> VeriaddStatus:
        """Live dependency status (public — key is harmless if set)."""
        return VeriaddStatus.from_dict(
            _as_map(self._request("GET", "/api/v1/status"))
        )

    def list_keys(self) -> List[VeriaddKeyInfo]:
        """List key prefixes (full keys are never returned)."""
        data = self._request("GET", "/api/v1/keys")
        if not isinstance(data, list):
            return []
        return [VeriaddKeyInfo.from_dict(e) for e in data if isinstance(e, dict)]

    def create_key(self, env: str = "live", name: Optional[str] = None) -> Dict[str, Any]:
        """Issue a key. The full secret is shown once — store it immediately."""
        payload: Dict[str, Any] = {"env": env}
        if name is not None:
            payload["name"] = name
        return _as_map(
            self._request("POST", "/api/v1/keys", payload=payload)
        )

    def revoke_key(self, key_id: str) -> Dict[str, Any]:
        """Revoke a key by id. Immediate."""
        return _as_map(self._request("POST", f"/api/v1/keys/{key_id}/revoke"))


class AsyncVeriaddClient:
    """Async twin of :class:`VeriaddClient` (httpx.AsyncClient under the hood)."""

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        timeout: float = 15.0,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        if not api_key:
            raise ValueError("AsyncVeriaddClient requires an api_key")
        self.api_key = api_key
        self.base_url = (base_url or VERIADD_DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        self._http = http_client or httpx.AsyncClient(timeout=timeout)
        self._owns_http = http_client is None

    async def aclose(self) -> None:
        if self._owns_http:
            await self._http.aclose()

    async def __aenter__(self) -> "AsyncVeriaddClient":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, str]] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Any:
        try:
            res = await self._http.request(
                method,
                self.base_url + path,
                params=params,
                json=payload,
                headers={
                    "X-API-Key": self.api_key,
                    "X-Request-ID": uuid.uuid4().hex,
                },
            )
        except httpx.TimeoutException as exc:
            raise VeriaddError(
                code="timeout",
                status=0,
                message=f"Request timed out after {self.timeout:g}s",
            ) from exc
        except httpx.HTTPError as exc:
            raise VeriaddError(code="network_error", status=0, message=str(exc)) from exc
        try:
            body = res.json()
        except ValueError:
            body = {}
        if res.status_code < 200 or res.status_code >= 300:
            raise _error_from_response(res.status_code, body)
        return _unwrap(body)

    async def verify_address(self, **kwargs: Any) -> VeriaddVerifyResult:
        """Verify an address + optional identity cross-checks. The money endpoint."""
        return VeriaddVerifyResult.from_dict(
            _as_map(await self._request("POST", "/api/v1/verify/address", payload=kwargs))
        )

    async def lookup(self, code: str, level: int = 1) -> VeriaddNipostLookup:
        """Direct NIPOST postcode lookup. L1 is free."""
        return VeriaddNipostLookup.from_dict(
            _as_map(
                await self._request(
                    "GET", "/api/v1/lookup", params={"code": code, "level": str(level)}
                )
            )
        )

    async def status(self) -> VeriaddStatus:
        """Live dependency status (public — key is harmless if set)."""
        return VeriaddStatus.from_dict(
            _as_map(await self._request("GET", "/api/v1/status"))
        )

    async def wallet(self) -> VeriaddWallet:
        """Wallet balance + pricing for this key."""
        return VeriaddWallet.from_dict(
            _as_map(await self._request("GET", "/api/v1/wallet"))
        )


def with_veriadd_retry(
    fn: Callable[[], T],
    max_retries: int = 3,
    retryable: Optional[frozenset] = None,
    base_delay: float = 1.0,
) -> T:
    """Run ``fn`` with exponential backoff on retryable :class:`VeriaddError` codes."""
    codes = retryable if retryable is not None else VERIADD_RETRYABLE_CODES
    attempt = 0
    while True:
        try:
            return fn()
        except VeriaddError as err:
            if attempt >= max_retries or err.code not in codes:
                raise
            time.sleep(base_delay * (2**attempt))
            attempt += 1


async def awith_veriadd_retry(
    fn: Callable[[], Awaitable[T]],
    max_retries: int = 3,
    retryable: Optional[frozenset] = None,
    base_delay: float = 1.0,
) -> T:
    """Async twin of :func:`with_veriadd_retry`."""
    import asyncio

    codes = retryable if retryable is not None else VERIADD_RETRYABLE_CODES
    attempt = 0
    while True:
        try:
            return await fn()
        except VeriaddError as err:
            if attempt >= max_retries or err.code not in codes:
                raise
            await asyncio.sleep(base_delay * (2**attempt))
            attempt += 1
