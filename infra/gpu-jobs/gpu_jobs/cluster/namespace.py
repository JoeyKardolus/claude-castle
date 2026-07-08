"""K8s namespace accessor — read at CALL time.

Accessor, not a module constant (module-standard config doctrine): tests
monkeypatch ``CASTLE_K8S_NAMESPACE`` mid-run and the next call sees it; no
re-import tricks. Promoted from ``_config.py`` in the de-slop campaign:
five sibling files imported the private, so the seam is public now.

FAILURE POLICY: pure env read, no I/O, nothing to swallow.
"""

from __future__ import annotations

import os


def namespace() -> str:
    """K8s namespace every Job in this package is submitted to."""
    return os.environ.get("CASTLE_K8S_NAMESPACE", "default")
