"""Constant-time Bearer-token verification for inbound Nextcloud webhooks.

Nextcloud webhook_listeners has no HMAC-of-body. The registration takes an
`authMethod=header` + `authData={"Authorization": "Bearer ..."}` and relays
that header verbatim on every outbound POST. We compare the received token
to NEXTCLOUD_WEBHOOK_SECRET in constant time.
"""
from __future__ import annotations

import hmac
from typing import Optional

_BEARER_PREFIX = "Bearer"


class AuthError(PermissionError):
    """Authorization header missing, malformed, or token mismatched."""


def verify_bearer(header_value: Optional[str], *, expected: str) -> None:
    """Raise AuthError unless header_value is `Bearer <expected>`."""
    if not header_value:
        raise AuthError("Authorization header missing")
    stripped = header_value.strip()
    if not stripped.startswith(_BEARER_PREFIX):
        raise AuthError("not a Bearer token")
    token = stripped[len(_BEARER_PREFIX):].strip()
    if not hmac.compare_digest(token, expected):
        raise AuthError("token mismatch")
