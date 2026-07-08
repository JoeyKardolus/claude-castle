"""Hardened container SecurityContext shared by every GPU worker Job.

One home so every Job creator (and external Job builders, who take
this via the public ``cluster()`` handle) cannot drift on the hardening
posture. The pod-level twin lives in ``worker_pod_security_context.py``.
Promoted from ``_security.py`` in the de-slop campaign: four sibling
files imported the private, so the seam is public now.

FAILURE POLICY: pure object construction — nothing to swallow.
"""

from __future__ import annotations

from kubernetes import client


def worker_security_context() -> "client.V1SecurityContext":
    """Hardened SecurityContext for every GPU worker container.

    - allowPrivilegeEscalation=False: setuid binaries / no_new_privs.
    - capabilities.drop=[ALL]: the worker does not need CAP_NET_*, CAP_SYS_*,
      anything. If ffmpeg pops a shell on a crafted upload, dropping caps
      stops the shell from doing kernel-level damage.
    - privileged=False: explicit for defense in depth.
    - runAsNonRoot=True + runAsUser=1000: the worker image now bakes a
      `worker` user (uid 1000) via Dockerfile.worker. kube-scheduler
      refuses to start the pod if the image would try to run as uid 0.

    NOT set here:
    - readOnlyRootFilesystem: GEM-X is installed editable at /app/lib/GEM-X/
      and the venv writes .pyc files at import time; read-only root would
      break inference. Can flip once those paths are moved under emptyDirs.
    """
    return client.V1SecurityContext(
        allow_privilege_escalation=False,
        privileged=False,
        run_as_non_root=True,
        run_as_user=1000,
        capabilities=client.V1Capabilities(drop=["ALL"]),
    )
