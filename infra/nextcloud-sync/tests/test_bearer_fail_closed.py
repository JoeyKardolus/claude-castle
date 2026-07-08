"""Bearer-token verification (Nextcloud `authMethod=header` sends a fixed Bearer).

Core webhook_listeners has no HMAC; the listener registration includes
`authData` (e.g. `{"Authorization": "Bearer ..."}`) and Nextcloud relays
that header verbatim on every outbound POST. We compare the received token
to NEXTCLOUD_WEBHOOK_SECRET in constant time.
"""
from __future__ import annotations

import pytest

from nextcloud_sync.auth import AuthError, verify_bearer


def test_correct_bearer_passes():
    verify_bearer("Bearer s3cret", expected="s3cret")  # no exception


def test_correct_bearer_with_extra_whitespace_passes():
    verify_bearer("Bearer   s3cret   ", expected="s3cret")


def test_wrong_token_raises():
    with pytest.raises(AuthError):
        verify_bearer("Bearer wrong", expected="s3cret")


def test_missing_bearer_prefix_raises():
    with pytest.raises(AuthError):
        verify_bearer("s3cret", expected="s3cret")


def test_empty_header_raises():
    with pytest.raises(AuthError):
        verify_bearer("", expected="s3cret")


def test_none_header_raises():
    with pytest.raises(AuthError):
        verify_bearer(None, expected="s3cret")


def test_basic_auth_not_accepted():
    with pytest.raises(AuthError):
        verify_bearer("Basic dXNlcjpwYXNz", expected="s3cret")
