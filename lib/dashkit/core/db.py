"""Database connection for every dashkit dashboard — the ops compartment.

Every table dashkit touches — ``{domain}_activity``, ``{domain}_ai_calls``,
``{domain}_sync_status``, ``dashkit_*``, ``ops_*``, ``lit_*``,
``notulen_*`` — lives in the ``ops`` compartment (PRD #383 / #388,
ADR-0022). So dashkit reads its DSN from ``DB_URL_OPS`` and falls back
to the kitchen-sink ``DB_URL`` during the migration window: until
``DB_URL_OPS`` is set on the containers, the ops tables are still
co-resident on the shared instance, so the fallback keeps every
dashboard working without a flag day. dashkit is deliberately
self-contained — lean images copy only ``dashkit``; keep this module
free of imports from app code.

What this module does NOT own: SQL-identifier validation lives in
``core/identifiers.py``; per-table schemas live with their feature
modules (audit / sync / ai).

The regulated MDR dossier (``mdr_*``) is a DIFFERENT compartment and is
NOT touched by any dashkit caller. Routing dashkit to ops therefore
cannot affect the dossier.

FAILURE POLICY: import fails fast (SystemExit) when neither DSN env var
is set — deliberate, every downstream module assumes a working
connection string and a half-up dashboard is worse than a crashed one.
``get_db()`` fails OPEN (returns None) so HTTP routes can degrade to
503/empty payloads per route; routes that require the DB raise 503 on
None.
"""
from __future__ import annotations

import os
from typing import Optional

import psycopg2


def _ops_dsn() -> str:
    """DSN for the ops compartment: ``DB_URL_OPS`` or fallback ``DB_URL``."""
    return os.environ.get("DB_URL_OPS") or os.environ.get("DB_URL", "")


# Resolved once at import for back-compat consumers that read the
# constant directly (e.g. dashkit.ai opens a short-lived
# psycopg2.connect(DB_URL) for the *_ai_calls write). Connection-opening
# helpers below re-resolve per call so a mid-run env swap still works.
DB_URL: str = _ops_dsn()
if not DB_URL:
    raise SystemExit(
        "DB_URL_OPS (or DB_URL fallback) environment variable is required. "
        "Set it in your shell or .env file. "
        "See docs/infrastructure.md for the connection string."
    )


def get_db() -> Optional[psycopg2.extensions.connection]:
    """Return a fresh psycopg2 connection to the ops compartment, or None
    if the DB is unavailable.

    Routes that require a DB should raise HTTPException(503) on None;
    optional/observability code paths should treat None as a no-op.
    """
    try:
        return psycopg2.connect(_ops_dsn())
    except Exception:
        return None
