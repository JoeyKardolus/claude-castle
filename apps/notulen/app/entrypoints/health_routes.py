"""Health endpoints — two endpoints, two purposes (PRD #255, ADR-0013).

- ``/healthz`` is the cheap liveness probe scraped by cluster blackbox-
  exporter. DB ping only, sub-50 ms ceiling, no upstream calls. Schema
  is fixed by ADR-0013: ``{ok: bool, checks: [{name, ok, ms}]}``.
  Returns HTTP 200 always when the app is alive; ``ok: false`` carries
  the bad news so blackbox can fail on a body match.
- ``/api/health/notulen/full`` is the rich payload for the dashboard
  UI banner: DB + K8s + 24h success rate. Was the only health endpoint
  pre-PRD #255; the K8s ``list_node`` call inside it stalled on cluster
  blips and timed out the probe path (2026-05-07 flap).

FAILURE POLICY: health endpoints never raise — every check converts its
failure into the response body (that IS the product of this module). Each
swallow below is that documented conversion.
"""
from __future__ import annotations

import os
import time

from fastapi import APIRouter

from dashkit.core.db import get_db

from apps.notulen.app.shared.jobs_table import ensure_jobs_table

router = APIRouter()


def _db_ping_ms() -> tuple[bool, int]:
    """Cheap DB liveness: ``SELECT 1`` round-trip, no schema lookups."""
    started = time.monotonic()
    try:
        conn = get_db()
        if not conn:
            return False, int((time.monotonic() - started) * 1000)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        finally:
            conn.close()
    except Exception:
        # Documented swallow: the probe's job is to REPORT failure, not raise.
        return False, int((time.monotonic() - started) * 1000)
    return True, int((time.monotonic() - started) * 1000)


@router.get("/healthz")
def _healthz():
    """Cheap liveness probe for blackbox-exporter (ADR-0013 carve-out)."""
    db_ok, db_ms = _db_ping_ms()
    return {"ok": db_ok, "checks": [{"name": "database", "ok": db_ok, "ms": db_ms}]}


def _check_kapsule() -> dict:
    """Probe the K8s capability we actually use — namespace-scoped job list —
    instead of cluster-wide list_node, which a least-privilege kubeconfig may
    reject (403) even when dispatch works."""
    if not os.environ.get("KUBECONFIG_DATA"):
        return {
            "name": "kapsule",
            "ok": False,
            "error": "KUBECONFIG_DATA not set (CPU fallback only)",
        }
    try:
        # Lazy: the dashboard boots without the kubernetes package. The
        # cluster() handle is the jobs package's one public door
        # (module-standard §8) — no reaching for its ``_``-privates.
        from gpu_jobs import cluster  # noqa: PLC0415
        from kubernetes import client as k8s_client  # noqa: PLC0415
        handle = cluster()
        handle.call(
            k8s_client.BatchV1Api().list_namespaced_job,
            namespace=handle.namespace, limit=1, timeout_seconds=5,
        )
        return {"name": "kapsule", "ok": True}
    except Exception as exc:
        # Documented swallow: degraded, CPU fallback still works.
        return {"name": "kapsule", "ok": False, "error": str(exc)[:200]}


@router.get("/api/health/notulen/full")
def _health_notulen_full():
    """Aggregate health for the dashboard UI banner.

    Returns 200 always so the UI sees the JSON. Consumers look at the
    ``status`` field (``ok``/``degraded``/``broken``) and the per-check
    list. Never on the cluster probe path (PRD #255) — chained 5s
    timeouts produced the 2026-05-07 flap.
    """
    checks: list[dict] = []
    overall = "ok"

    # DB check
    try:
        conn = get_db()
        if not conn:
            raise RuntimeError("get_db returned None")
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        finally:
            conn.close()
        checks.append({"name": "database", "ok": True})
    except Exception as exc:
        checks.append({"name": "database", "ok": False, "error": str(exc)[:200]})
        overall = "broken"

    # K8s check (only meaningful when configured).
    kapsule_check = _check_kapsule()
    checks.append(kapsule_check)
    if not kapsule_check["ok"] and overall == "ok":
        overall = "degraded"  # CPU fallback still works

    # Recent job success rate (last 24h, ignore still-running)
    try:
        conn = get_db()
        if conn:
            try:
                ensure_jobs_table(conn)
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT "
                        "  SUM(CASE WHEN status = 'complete' THEN 1 ELSE 0 END), "
                        "  SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) "
                        "FROM notulen_jobs "
                        "WHERE created_at > NOW() - INTERVAL '24 hours' "
                        "  AND status IN ('complete', 'failed')"
                    )
                    row = cur.fetchone() or (0, 0)
                    complete, failed = int(row[0] or 0), int(row[1] or 0)
                total = complete + failed
                rate = (complete / total) if total else 1.0
                checks.append({
                    "name": "recent_jobs_24h",
                    "ok": rate >= 0.5 or total == 0,
                    "complete": complete,
                    "failed": failed,
                    "success_rate": round(rate, 2),
                })
                if total >= 3 and rate < 0.5 and overall == "ok":
                    overall = "degraded"
            finally:
                conn.close()
    except Exception as exc:
        # Documented swallow: report the check as failed, keep the banner up.
        checks.append({"name": "recent_jobs_24h", "ok": False, "error": str(exc)[:200]})

    return {"status": overall, "checks": checks}
