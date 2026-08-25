"""Resolve the Windows release signing mode without exposing credentials."""

from __future__ import annotations

import os
import sys


def resolve_signing_mode(
    certificate_base64: str | None,
    certificate_password: str | None,
) -> str:
    """Return SIGNED/UNSIGNED, rejecting a partially configured signing setup."""

    has_certificate = bool(certificate_base64 and certificate_base64.strip())
    has_password = bool(certificate_password and certificate_password.strip())
    if has_certificate != has_password:
        raise ValueError(
            "Windows signing is partially configured. Both "
            "WINDOWS_CERTIFICATE_BASE64 and WINDOWS_CERTIFICATE_PASSWORD must be present, "
            "or both must be absent."
        )
    return "SIGNED" if has_certificate else "UNSIGNED"


def main() -> int:
    try:
        mode = resolve_signing_mode(
            os.environ.get("WINDOWS_CERTIFICATE_BASE64"),
            os.environ.get("WINDOWS_CERTIFICATE_PASSWORD"),
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(mode)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
