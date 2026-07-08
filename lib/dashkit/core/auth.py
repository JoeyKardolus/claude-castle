"""Username extraction from Caddy ``forward_auth`` headers.

Every dashkit dashboard sits behind Caddy, which terminates Nextcloud
SSO and forwards the authenticated identity in the ``Authorization``
header (``Basic <base64(user:pass)>``). We only need the username — the
password is already validated upstream.
"""
from __future__ import annotations

import base64
from typing import Optional


def get_user(authorization: Optional[str]) -> str:
    """Extract username from a Basic auth ``Authorization`` header.

    Returns ``"anonymous"`` if the header is missing or unparseable.
    Never raises — the caller can always proceed with an anonymous user
    and the audit log will record that fact.
    """
    if not authorization:
        return "anonymous"
    try:
        if authorization.startswith("Basic "):
            decoded = base64.b64decode(authorization.split(" ", 1)[1]).decode()
            return decoded.split(":", 1)[0]
    except Exception:
        # Defended swallow (Tier-2, fail-open by design): Caddy already
        # authenticated the request upstream; an unparseable header only
        # costs attribution, and the audit row records "anonymous".
        pass
    return "anonymous"
