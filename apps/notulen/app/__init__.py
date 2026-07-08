"""Notulen dashboard — FastAPI app package.

Tier declaration (module-standard §1): 5-layer deep module —
``entrypoints/`` (FastAPI app + routes), ``gates/`` (upload validation),
``core/`` (minutes/publish/sessions role subdirs), ``shared/`` (config,
slug, S3, notulen_jobs DB helpers), ``inputs/`` (committed SPA assets:
dashboard.html + dashboard.js + this package's Dockerfile).

The GPU worker entrypoint is NOT here — it ships as its own image from
``apps/notulen/entrypoints/worker.py``.
"""
