"""Shared test bootstrap for the notulen dashboard package.

dashkit.core.db enforces DB_URL at import time; give tests a dummy so the
package imports without a live Postgres. No test in this package ever
connects — they use fakes and injected collaborators only (module-standard
§4). Replaces the per-file env + ``_APP_ROOT`` sys.path bootstrap blocks
that were copy-pasted across five test files pre-2026-06-12.
"""
from __future__ import annotations

import os

os.environ.setdefault("DB_URL", "postgresql://test:test@127.0.0.1:5432/test")
