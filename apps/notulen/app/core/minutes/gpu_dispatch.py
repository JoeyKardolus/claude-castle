"""Try-dispatch a K8s GPU notulen-worker job.

The gate between the GPU path and the local-CPU fallback in
``core/minutes/process_job.py``. The kubernetes client imports lazily —
the dashboard boots without it.

FAILURE POLICY: fail-OPEN by design — any dispatch error returns False so
the recording still transcribes on CPU; the failure pages ops (throttled)
because CPU-only speed is the regression that hid for weeks until a
meeting longer than 3 min exposed it. The notifier itself is a documented
Tier-2 swallow: a broken alert path must never block a recording.
"""
from __future__ import annotations

import logging
import os
import time

logger = logging.getLogger("notulen")

# Throttle "GPU dispatch failed" pages to one per hour. Without this the dashboard
# would page on every meeting upload while K8s is broken, drowning the signal.
# Module-global; resets on container restart, which is fine — restart is itself
# a recovery signal worth re-paging on.
_CPU_FALLBACK_ALERT_THROTTLE_SEC = 3600
_last_cpu_fallback_alert_ts: float = 0.0


def _alert_cpu_fallback(job_id: str, reason: str) -> None:
    """Page ops when KUBECONFIG_DATA is set but dispatch failed."""
    global _last_cpu_fallback_alert_ts
    now = time.time()
    if now - _last_cpu_fallback_alert_ts < _CPU_FALLBACK_ALERT_THROTTLE_SEC:
        return
    _last_cpu_fallback_alert_ts = now
    try:
        # Standalone default: log-only. Swap in a call to your own alerting
        # stack here if you have one.
        logger.error(
            "⚠️ notulen: GPU dispatch failed — running on CPU\n%s",
            f"Job: {job_id}\n"
            f"Reason: {reason}\n\n"
            "The dashboard fell back to local CPU transcription. Real meetings "
            "(>5 min) will take hours instead of minutes. Check kubeconfig auth "
            "and K8s permissions; throttled to one page per hour.",
        )
    except Exception:
        # Documented Tier-2 swallow (see module FAILURE POLICY).
        logger.exception("Failed to page on CPU fallback for %s", job_id)


def try_dispatch_gpu(
    job_id: str,
    s3_key: str,
    title: str,
    meeting_date: str,
    attendees: list[str],
    agenda: str,
) -> bool:
    """Try to dispatch a K8s GPU job. Returns True if dispatched, False otherwise."""
    if not os.environ.get("KUBECONFIG_DATA"):
        return False
    try:
        # Lazy: the dashboard boots without the kubernetes package.
        from gpu_jobs import create_notulen_job  # noqa: PLC0415
        create_notulen_job(
            job_id=job_id,
            audio_key=s3_key,
            title=title,
            meeting_date=meeting_date,
            attendees=", ".join(attendees),
            agenda=agenda,
        )
        logger.info("Dispatched GPU job for %s", job_id)
        return True
    except Exception as exc:
        # Documented fail-open: CPU fallback still produces the notulen.
        logger.warning("GPU dispatch failed, falling back to CPU: %s", exc)
        _alert_cpu_fallback(job_id, repr(exc)[:200])
        return False
