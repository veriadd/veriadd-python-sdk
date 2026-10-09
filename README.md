# Veriadd Python SDK: `veriadd`

Official Python client for the Veriadd address KYC API. Sync and async clients,
typed models, zero surprises. Requires Python 3.9+.

## Install

```bash
pip install veriadd
```

## Quickstart

```python
import os
from veriadd import VeriaddClient

client = VeriaddClient(api_key=os.environ["VERIADD_KEY"])

# Primary KYC endpoint: postcode + identity cross-check
result = client.verify_address(
    postcode="LA-11-W06-TC-10",
    state="LAGOS",
    first_name="Adaeze",
    last_name="Okafor",
    bvn="22233344455",
    phone="08031234567",
    level=3,  # L1 free, L2 ₦30, L3 ₦50
)

if result.status == "verified" and result.confidence >= 80:
    pass  # proceed to onboarding — result.audit_id is your CBN trail
```

Async usage:

```python
from veriadd import AsyncVeriaddClient

async with AsyncVeriaddClient(api_key=os.environ["VERIADD_KEY"]) as client:
    result = await client.verify_address(postcode="LA-11-W06-TC-10", level=3)
```

> **Secret keys stay server-side.** A `vr_live_…` key inside a shipped app
> can be extracted. Mobile apps should call your backend, which holds the key.

## Error handling

Every failure raises `VeriaddError` with `code`, `status` and `request_id`:

```python
from veriadd import VeriaddClient, VeriaddError, with_veriadd_retry

try:
    result = client.verify_address(postcode="X", level=3)
except VeriaddError as err:
    if err.code == "insufficient_credits":
        pass  # pause onboarding, trigger a wallet top-up

# Retry transient states with backoff
result = with_veriadd_retry(
    lambda: client.verify_address(postcode="LA-11-W06-TC-10", level=3)
)
```

## Methods

| Method                                                                    | Endpoint                      |
| ------------------------------------------------------------------------- | ----------------------------- |
| `verify_address(**fields)`                                                | `POST /v1/verify/address`     |
| `lookup(code, level=1)`                                                   | `GET /v1/lookup`              |
| `autocomplete(q)`                                                         | `GET /v1/search/autocomplete` |
| `nearby(lat, lng, radius=None)`                                           | `GET /v1/search/nearby`       |
| `reverse(lat, lng, max_distance_m=None)`                                  | `GET /v1/search/reverse`      |
| `disassemble(code)` / `assemble(...)`                                     | assembly endpoints            |
| `wallet()` / `usage(limit=50)`                                            | wallet + history              |
| `topup_init(amount_kobo, email, callback_url=None)` / `topup_verify(ref)` | Bachs top-ups                 |
| `kyb_get()` / `kyb_submit(**fields)`                                      | business verification         |
| `list_keys()` / `create_key(env="live")` / `revoke_key(id)`               | API keys                      |
| `status()`                                                                | live dependency status        |

Full endpoint semantics: https://veriadd.tech/docs/api
