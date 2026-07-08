"""Configured-cluster accessor for external K8s Job builders.

External callers (the notulen dashboard's live-Job matcher, any
future Job builders) need the same kubeconfig bootstrap,
one-retry-on-401 call wrapper, namespace, and hardened SecurityContexts
that the creators in this package use. Reaching them as ``_``-privates
made the declared seam paper-only; ``cluster()`` is the one public door.

What is NOT here: Job manifests and dispatch policy — external builders
own their manifests, the creators in this package own theirs; nobody
shares a manifest through this handle.

FAILURE POLICY: Tier 1 — the config bootstrap raises when no source
loads; ``handle.call`` retries exactly once on 401 (stale token after
rotation, 2026-05-21 incident) and otherwise propagates ApiException.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .ensure_config import ensure_config
from .k8s_call import k8s_call
from .namespace import namespace
from ..security.worker_pod_security_context import worker_pod_security_context
from ..security.worker_security_context import worker_security_context


@dataclass(frozen=True)
class ClusterHandle:
    """What an external Job builder may take from this package — the
    signature type riding with ``cluster()`` (ADR-0011 rider).

    Fields are injected collaborators (house DI), not copies: ``call``
    IS the creators' retry wrapper, the two context factories ARE the
    creators' hardening posture, so external Jobs cannot drift from it.
    """

    namespace: str
    call: Callable[..., Any]
    worker_security_context: Callable[[], Any]
    worker_pod_security_context: Callable[[], Any]


def cluster() -> ClusterHandle:
    """Bootstrap K8s config (idempotent) and return the configured handle.

    ``namespace`` is the env value at THIS call (call-time config
    doctrine, module-standard §6.1) — re-call ``cluster()`` instead of
    caching a handle across env changes. Construct kubernetes API
    objects (``client.BatchV1Api()`` etc.) only AFTER this returns;
    they snapshot the default Configuration at construction.
    """
    ensure_config()
    return ClusterHandle(
        namespace=namespace(),
        call=k8s_call,
        worker_security_context=worker_security_context,
        worker_pod_security_context=worker_pod_security_context,
    )
