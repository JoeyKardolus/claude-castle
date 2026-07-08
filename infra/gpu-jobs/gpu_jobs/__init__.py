"""Kubernetes Job submission for the optional GPU notulen worker.

OPTIONAL TIER: the castle stack works without this package. When no GPU
cluster is configured (``KUBECONFIG_DATA`` unset, or dispatch fails for
any reason), the notulen dashboard transcribes on CPU via its fail-open
fallback (``apps/notulen/app/core/minutes/gpu_dispatch.py``). Install and
configure this only when you have a K8s cluster with GPU nodes.

Configuration (all env vars):

- ``KUBECONFIG_DATA``        base64 kubeconfig blob; presence enables the GPU path
- ``CASTLE_K8S_NAMESPACE``   namespace Jobs are submitted to (default: ``default``)
- ``NOTULEN_WORKER_IMAGE``   the notulen GPU worker image (required for dispatch;
                             build from ``infra/docker/notulen-worker/Dockerfile``)
- ``MAX_DAILY_JOBS``         daily Job cost ceiling (default: 50)

Module map (one public callable per file):

- ``creators/create_notulen_job.py`` — submit one notulen transcription Job;
  owns the MAX_DAILY_JOBS cost ceiling.
- ``naming/job_name.py``      — the Job-name mangling grammar callers may
  rely on to find Jobs later.
- ``cluster/cluster.py``      — ``cluster()``, the configured-cluster
  accessor: hands external callers the same bootstrap/retry/namespace/
  SecurityContext collaborators the creator uses.
- ``cluster/ensure_config.py``— kubeconfig bootstrap, idempotent.
- ``cluster/k8s_call.py``     — one-retry-on-401 call wrapper.
- ``cluster/namespace.py``    — CASTLE_K8S_NAMESPACE env knob, read at CALL time.
- ``config/notulen_worker_image.py`` — notulen GPU worker image knob.
- ``config/max_daily_jobs.py``— MAX_DAILY_JOBS cost-ceiling knob.
- ``security/worker_security_context.py``     — hardened container SecurityContext.
- ``security/worker_pod_security_context.py`` — hardened pod SecurityContext.

FAILURE POLICY: the creator and ``cluster()`` are Tier 1 — they raise
(RuntimeError on the cost ceiling, ApiException through the single 401
retry). The CPU-fallback decision belongs to the caller, never here.
"""

from __future__ import annotations

from .cluster.cluster import ClusterHandle, cluster
from .cluster.ensure_config import ensure_config
from .cluster.k8s_call import k8s_call
from .cluster.namespace import namespace
from .config.max_daily_jobs import max_daily_jobs
from .config.notulen_worker_image import notulen_worker_image
from .creators.create_notulen_job import create_notulen_job
from .naming.job_name import job_name
from .security.worker_pod_security_context import worker_pod_security_context
from .security.worker_security_context import worker_security_context

__all__ = [
    "ClusterHandle",
    "cluster",
    "create_notulen_job",
    "ensure_config",
    "job_name",
    "k8s_call",
    "max_daily_jobs",
    "namespace",
    "notulen_worker_image",
    "worker_pod_security_context",
    "worker_security_context",
]
