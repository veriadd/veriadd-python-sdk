"""Typed models mirroring the Veriadd REST payloads.

See https://veriadd.tech/docs/api for field semantics.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def _as_int(v: Any, default: int = 0) -> int:
    if isinstance(v, bool):
        return default
    if isinstance(v, (int, float)):
        return int(v)
    return default


def _as_float(v: Any, default: float = 0.0) -> float:
    if isinstance(v, bool):
        return default
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _as_str_list(v: Any) -> List[str]:
    if not isinstance(v, list):
        return []
    return [str(e) for e in v]


@dataclass
class VeriaddNipostLookup:
    postcode: str = ""
    valid: bool = False
    administrative_address: Optional[Dict[str, Any]] = None
    recent_house_address: Optional[Dict[str, Any]] = None
    building_use_status: Optional[str] = None

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "VeriaddNipostLookup":
        admin = d.get("administrative_address")
        recent = d.get("recent_house_address")
        return cls(
            postcode=str(d.get("postcode", "")),
            valid=bool(d.get("valid", False)),
            administrative_address=dict(admin) if isinstance(admin, dict) else None,
            recent_house_address=dict(recent) if isinstance(recent, dict) else None,
            building_use_status=d.get("building_use_status"),
        )


@dataclass
class VeriaddIdentity:
    provider: str = ""
    bvn_valid: Optional[bool] = None
    bvn_name_match: Optional[bool] = None
    phone_linked: Optional[bool] = None
    phone_name_match: Optional[bool] = None
    nin_valid: Optional[bool] = None

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "VeriaddIdentity":
        def opt(key: str) -> Optional[bool]:
            v = d.get(key)
            return v if isinstance(v, bool) else None

        return cls(
            provider=str(d.get("provider", "")),
            bvn_valid=opt("bvn_valid"),
            bvn_name_match=opt("bvn_name_match"),
            phone_linked=opt("phone_linked"),
            phone_name_match=opt("phone_name_match"),
            nin_valid=opt("nin_valid"),
        )


@dataclass
class VeriaddVerifyResult:
    audit_id: str = ""
    status: str = ""
    confidence: int = 0
    reasons: List[str] = field(default_factory=list)
    postcode_canonical: str = ""
    nipost: Optional[VeriaddNipostLookup] = None
    identity: Optional[VeriaddIdentity] = None
    billed_kobo: int = 0
    billed_ngn: float = 0.0

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "VeriaddVerifyResult":
        nipost = d.get("nipost")
        identity = d.get("identity")
        return cls(
            audit_id=str(d.get("audit_id", "")),
            status=str(d.get("status", "")),
            confidence=_as_int(d.get("confidence")),
            reasons=_as_str_list(d.get("reasons")),
            postcode_canonical=str(d.get("postcode_canonical", "")),
            nipost=VeriaddNipostLookup.from_dict(nipost) if isinstance(nipost, dict) else None,
            identity=VeriaddIdentity.from_dict(identity) if isinstance(identity, dict) else None,
            billed_kobo=_as_int(d.get("billed_kobo")),
            billed_ngn=_as_float(d.get("billed_ngn")),
        )


@dataclass
class VeriaddWallet:
    client: str = ""
    email: str = ""
    balance_kobo: int = 0
    balance_ngn: float = 0.0
    price_l2_kobo: int = 0
    price_l3_kobo: int = 0
    topup_providers: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "VeriaddWallet":
        return cls(
            client=str(d.get("client", "")),
            email=str(d.get("email", "")),
            balance_kobo=_as_int(d.get("balance_kobo")),
            balance_ngn=_as_float(d.get("balance_ngn")),
            price_l2_kobo=_as_int(d.get("price_l2_kobo")),
            price_l3_kobo=_as_int(d.get("price_l3_kobo")),
            topup_providers=_as_str_list(d.get("topup_providers")),
        )


@dataclass
class VeriaddUsageRow:
    endpoint: str = ""
    status: str = ""
    billed_kobo: int = 0
    confidence: Optional[int] = None
    created_at: str = ""

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "VeriaddUsageRow":
        return cls(
            endpoint=str(d.get("endpoint", "")),
            status=str(d.get("status", "")),
            billed_kobo=_as_int(d.get("billed_kobo")),
            confidence=_as_opt_int(d.get("confidence")),
            created_at=str(d.get("created_at", "")),
        )


def _as_opt_int(v: Any) -> Optional[int]:
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return int(v)
    return None


@dataclass
class VeriaddTopupInit:
    provider: str = ""
    authorization_url: str = ""
    reference: str = ""
    checkout_id: Optional[str] = None

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "VeriaddTopupInit":
        return cls(
            provider=str(d.get("provider", "")),
            authorization_url=str(d.get("authorization_url", "")),
            reference=str(d.get("reference", "")),
            checkout_id=d.get("checkout_id"),
        )


@dataclass
class VeriaddTopupVerify:
    credited_kobo: int = 0
    already_credited: bool = False
    balance_kobo: int = 0
    balance_ngn: float = 0.0

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "VeriaddTopupVerify":
        return cls(
            credited_kobo=_as_int(d.get("credited_kobo")),
            already_credited=bool(d.get("already_credited", False)),
            balance_kobo=_as_int(d.get("balance_kobo")),
            balance_ngn=_as_float(d.get("balance_ngn")),
        )


@dataclass
class VeriaddKYB:
    id: str = ""
    business_name: str = ""
    rc_number: str = ""
    registered_address: str = ""
    website: str = ""
    use_case: str = ""
    company_type: str = ""
    cac_verified: bool = False
    cac_legal_name: Optional[str] = None
    status: str = ""
    review_note: Optional[str] = None

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "VeriaddKYB":
        return cls(
            id=str(d.get("id", "")),
            business_name=str(d.get("business_name", "")),
            rc_number=str(d.get("rc_number", "")),
            registered_address=str(d.get("registered_address", "")),
            website=str(d.get("website", "")),
            use_case=str(d.get("use_case", "")),
            company_type=str(d.get("company_type", "")),
            cac_verified=bool(d.get("cac_verified", False)),
            cac_legal_name=d.get("cac_legal_name"),
            status=str(d.get("status", "")),
            review_note=d.get("review_note"),
        )


@dataclass
class VeriaddKeyInfo:
    id: str = ""
    key_prefix: str = ""
    env: str = ""
    name: str = ""
    revoked: bool = False
    created_at: str = ""

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "VeriaddKeyInfo":
        return cls(
            id=str(d.get("id", "")),
            key_prefix=str(d.get("key_prefix", "")),
            env=str(d.get("env", "")),
            name=str(d.get("name", "")),
            revoked=bool(d.get("revoked", False)),
            created_at=str(d.get("created_at", "")),
        )


@dataclass
class VeriaddCreatedKey:
    #: Shown once — store it immediately, it is never returned again.
    api_key: str = ""
    key_prefix: str = ""
    warning: str = ""

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "VeriaddCreatedKey":
        return cls(
            api_key=str(d.get("api_key", "")),
            key_prefix=str(d.get("key_prefix", "")),
            warning=str(d.get("warning", "")),
        )


@dataclass
class VeriaddStatus:
    service: str = ""
    version: str = ""
    time: str = ""
    uptime_seconds: int = 0
    #: Raw dependency map (postgres, redis, nipost, dojah, bachs).
    deps: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "VeriaddStatus":
        deps = d.get("deps")
        return cls(
            service=str(d.get("service", "")),
            version=str(d.get("version", "")),
            time=str(d.get("time", "")),
            uptime_seconds=_as_int(d.get("uptime_seconds")),
            deps=dict(deps) if isinstance(deps, dict) else {},
        )
