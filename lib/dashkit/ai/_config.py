"""Shared AI config read: ``dashkit_ai_config`` (one row set per org).

The table is created by the storage migrations (it predates this
package split as ``mdr_ai_config``); this module only reads it.

FAILURE POLICY: fail-open to defaults (Tier 2) — a missing table or a
read hiccup must never block a Claude call; the defaults below are the
documented baseline.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("dashkit.ai")


def _get_ai_config(conn) -> dict[str, Any]:
    """Read AI config from ``dashkit_ai_config``. Returns defaults if missing.

    The values come back from JSONB as native Python types (str/int/
    dict/list); callers that expect a specific type should still
    coerce explicitly. The model/max_tokens/temperature defaults are
    strings to match the historical call_claude code path.
    """
    defaults: dict[str, Any] = {
        "model": "claude-sonnet-4-6",
        "max_tokens": "4000",
        "temperature": "0",
    }
    if conn is None:
        return defaults
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT config_key, config_value FROM dashkit_ai_config")
            for row in cur.fetchall():
                defaults[row[0]] = row[1]
    except Exception:
        # Tier-2 swallow: table may not exist yet; use defaults.
        try:
            conn.rollback()
        except Exception:
            logger.warning("rollback after failed dashkit_ai_config read failed")
    return defaults
