"""Official Python client for the Veriadd address KYC API."""

from .client import (
    VERIADD_DEFAULT_BASE_URL,
    VERIADD_RETRYABLE_CODES,
    AsyncVeriaddClient,
    VeriaddClient,
    awith_veriadd_retry,
    with_veriadd_retry,
)
from .errors import VeriaddError
from .models import (
    VeriaddCreatedKey,
    VeriaddIdentity,
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

__all__ = [
    "VERIADD_DEFAULT_BASE_URL",
    "VERIADD_RETRYABLE_CODES",
    "AsyncVeriaddClient",
    "VeriaddClient",
    "VeriaddCreatedKey",
    "VeriaddError",
    "VeriaddIdentity",
    "VeriaddKYB",
    "VeriaddKeyInfo",
    "VeriaddNipostLookup",
    "VeriaddStatus",
    "VeriaddTopupInit",
    "VeriaddTopupVerify",
    "VeriaddUsageRow",
    "VeriaddVerifyResult",
    "VeriaddWallet",
    "awith_veriadd_retry",
    "with_veriadd_retry",
]

__version__ = "0.1.0"
