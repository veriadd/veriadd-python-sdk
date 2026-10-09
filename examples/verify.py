"""Minimal end-to-end example. Requires a test key.

Run with:  VERIADD_KEY=vr_test_... python examples/verify.py
"""

import os

from veriadd import VeriaddClient, VeriaddError


def main() -> None:
    api_key = os.environ.get("VERIADD_KEY", "")
    if not api_key:
        print("Set VERIADD_KEY=vr_test_... and retry.")
        return
    with VeriaddClient(api_key=api_key) as client:
        try:
            lookup = client.lookup("LA-11-W06-TC-10", 1)
            print(f"lookup: {lookup.postcode} valid={lookup.valid}")

            status = client.status()
            print(f"status: {status.service} {status.version}")
        except VeriaddError as err:
            print(f"failed: {err}")


if __name__ == "__main__":
    main()
