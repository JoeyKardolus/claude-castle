"""Notulen GPU worker image accessor — read at CALL time.

Accessor, not a module constant (module-standard config doctrine): tests
monkeypatch ``NOTULEN_WORKER_IMAGE`` mid-run and the next call sees it.
Promoted out of ``_config.py`` when that grab-bag dissolved in the
de-slop campaign (ADR-0011: one public callable per file).

FAILURE POLICY: pure env read, no I/O, nothing to swallow.
"""

from __future__ import annotations

import os

def notulen_worker_image() -> str:
    """Notulen GPU worker image (build from infra/docker/notulen-worker/).

    Use a pinned tag (not :latest) so K8s' imagePullPolicy=IfNotPresent
    picks up new worker code when you bump the tag. Required: there is no
    sensible default registry for a standalone deployment.
    """
    image = os.environ.get("NOTULEN_WORKER_IMAGE")
    if not image:
        raise RuntimeError(
            "NOTULEN_WORKER_IMAGE is not set — point it at your pushed "
            "notulen-worker image (see infra/docker/notulen-worker/Dockerfile)."
        )
    return image
