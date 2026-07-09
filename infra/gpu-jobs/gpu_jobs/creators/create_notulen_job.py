"""Submit one notulen GPU transcription Job.

Owns the Job manifest + the daily cost ceiling. What is NOT here:
dispatch policy (when to fire, CPU fallback, retry) — that lives with
the caller, apps/notulen/app/core/minutes/gpu_dispatch.py ("Notulen
Jobs belong to notulen").

FAILURE POLICY: Tier 1 — raises RuntimeError when the daily Job ceiling
is reached; ApiException propagates (through the single 401 retry).
The notulen dashboard catches and falls back to CPU — the fallback
decision is the caller's, never silently made here.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from kubernetes import client

from ..cluster.ensure_config import ensure_config
from ..naming.job_name import job_name
from ..cluster.k8s_call import k8s_call
from ..config.max_daily_jobs import max_daily_jobs
from ..cluster.namespace import namespace
from ..config.notulen_worker_image import notulen_worker_image
from ..security.worker_pod_security_context import worker_pod_security_context
from ..security.worker_security_context import worker_security_context

log = logging.getLogger(__name__)


def _count_recent_jobs() -> int:
    """Count K8s jobs created in the last 24h (cost-ceiling input)."""
    api = client.BatchV1Api()
    jobs = api.list_namespaced_job(
        namespace=namespace(), label_selector="app=notulen-worker",
    )
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    return sum(
        1
        for recent_job in jobs.items
        if recent_job.metadata.creation_timestamp
        and recent_job.metadata.creation_timestamp > cutoff
    )


def create_notulen_job(
    job_id: str,
    audio_key: str,
    title: str,
    meeting_date: str,
    attendees: str = "",
    agenda: str = "",
    *,
    count_recent_jobs: Callable[[], int] = _count_recent_jobs,
) -> str:
    """Create a K8s GPU Job that processes one notulen recording end-to-end.

    The worker: downloads audio from S3, runs pyannote diarization +
    whisper-large-v3 transcription on GPU, generates notulen markdown via
    Claude API, writes results back to PostgreSQL.

    ``count_recent_jobs`` is the injectable cost-ceiling collaborator
    (house DI: keyword-only callable with the production default);
    test_fail_loud_on_ceiling.py injects a stub so the ceiling invariant
    pins without a cluster.

    Returns the job name.
    """
    ensure_config()
    job_namespace = namespace()

    # Cost safeguard shared with video pipeline jobs
    max_daily = max_daily_jobs()
    if count_recent_jobs() >= max_daily:
        raise RuntimeError(
            f"Daily job limit reached (>={max_daily}). "
            f"Increase MAX_DAILY_JOBS env var if needed."
        )

    name = job_name("notulen", job_id, seed_chars=20)

    env_vars = [
        client.V1EnvVar(name="JOB_ID", value=job_id),
        client.V1EnvVar(name="AUDIO_KEY", value=audio_key),
        client.V1EnvVar(name="TITLE", value=title),
        client.V1EnvVar(name="MEETING_DATE", value=meeting_date),
        client.V1EnvVar(name="ATTENDEES", value=attendees or ""),
        client.V1EnvVar(name="AGENDA", value=agenda or ""),
        # The image bakes pyannote/whisper caches under /root/.cache (image
        # built as root) but the pod runs as uid 1000 per the worker
        # security context. uid 1000 can't read /root/.cache and can't
        # write to /.cache (its HOME defaults to /). Pointing HOME at /tmp
        # gives hf_hub_download a writable cache root; pyannote re-downloads
        # the tiny config + segmentation snapshot at startup (~10s).
        client.V1EnvVar(name="HOME", value="/tmp"),
    ]
    # Pass dashboard-side env directly into the Job.
    #
    # The worker writes notulen_jobs + notulen_ai_calls, which live in the
    # ops compartment (ADR-0022). Hand it the ops DSN as DB_URL — mirroring
    # dashkit's _ops_dsn() — so its write-back lands in the same database the
    # dashboard reads. Forwarding the bare DB_URL (the app compartment) made
    # every GPU-path notulen silently no-op its UPDATE and stick at
    # 'transcribing' after the dashkit→ops table migration.
    worker_db_url = os.environ.get("DB_URL_OPS") or os.environ.get("DB_URL")
    if worker_db_url:
        env_vars.append(client.V1EnvVar(name="DB_URL", value=worker_db_url))
    for key in ("ANTHROPIC_API_KEY", "HF_TOKEN"):
        val = os.environ.get(key)
        if val:
            env_vars.append(client.V1EnvVar(name=key, value=val))

    container = client.V1Container(
        name="notulen-worker",
        image=notulen_worker_image(),
        image_pull_policy="IfNotPresent",
        security_context=worker_security_context(),
        resources=client.V1ResourceRequirements(
            limits={"nvidia.com/gpu": "1"},
            requests={"nvidia.com/gpu": "1", "memory": "8Gi", "cpu": "2"},
        ),
        env=env_vars,
        env_from=[
            # Both optional: create a `castle-worker-secrets` Secret and/or a
            # `castle-worker-config` ConfigMap in the namespace to feed the
            # worker extra env (S3 creds, DB_URL, ...) without touching code.
            client.V1EnvFromSource(
                secret_ref=client.V1SecretEnvSource(
                    name="castle-worker-secrets", optional=True,
                ),
            ),
            client.V1EnvFromSource(
                config_map_ref=client.V1ConfigMapEnvSource(
                    name="castle-worker-config", optional=True,
                ),
            ),
        ],
    )

    # Optional pull secret for a private registry (name via env).
    pull_secret = os.environ.get("CASTLE_IMAGE_PULL_SECRET")
    pod_spec = client.V1PodSpec(
        containers=[container],
        restart_policy="Never",
        image_pull_secrets=(
            [client.V1LocalObjectReference(name=pull_secret)] if pull_secret else None
        ),
        security_context=worker_pod_security_context(),
        tolerations=[
            client.V1Toleration(
                key="nvidia.com/gpu",
                operator="Exists",
                effect="NoSchedule",
            ),
        ],
    )

    job = client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=client.V1ObjectMeta(
            name=name,
            namespace=job_namespace,
            labels={"app": "notulen-worker", "job-id": job_id},
        ),
        spec=client.V1JobSpec(
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(
                    labels={"app": "notulen-worker", "job-id": job_id},
                ),
                spec=pod_spec,
            ),
            backoff_limit=0,
            active_deadline_seconds=1800,   # 30 min hard timeout (most meetings under 2h)
            ttl_seconds_after_finished=300,  # clean up 5 min after done
        ),
    )

    api = client.BatchV1Api()
    k8s_call(api.create_namespaced_job, namespace=job_namespace, body=job)
    log.info("Created notulen K8s Job %s for job %s", name, job_id)
    return name
