"""Typed API error parsed from the Veriadd ``{error: {code, message}}`` envelope."""

from typing import Optional


class VeriaddError(Exception):
    """Every SDK failure raises this (never raw httpx errors)."""

    def __init__(
        self,
        code: str,
        status: int,
        message: str = "",
        request_id: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status = status
        self.message = message
        self.request_id = request_id

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"VeriaddError({self.code}, {self.status}): {self.message}"
