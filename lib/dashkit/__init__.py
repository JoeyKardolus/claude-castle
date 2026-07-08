"""dashkit — shared library for castle operator dashboards (e.g. notulen).

**Library, not application** — dashboards import it; it never imports a
dashboard. Worker images exclude it by design; ``import dashkit`` from
worker code is ModuleNotFoundError, and that import boundary is the
contract.

Layout (each subpackage carries its own module map):

- ``core``     bootstrap + observability primitives: app_factory, auth,
               db, constants, inspector, audit/, sync/.
- ``ai``       the single LLM metering seam (``call_claude``).
- ``secrets``  ops secrets registry + rotation audit trail (consumed by
               the rotation runners, secrets_sweep, secrets_exporter).
- ``frontend`` static JS/CSS assets served at ``/static/dashkit/*``.

The 5-layer application shape deliberately does not apply:
dashkit is a consumed library with no entrypoint and no gates
(sanctioned exception, declared here and in the package overlay).

FAILURE POLICY: observability writes (audit log, AI-call accounting)
are best-effort and fail open; secrets rotation state propagates. Each
subpackage seam declares its own split.
"""

from __future__ import annotations

from dashkit import ai, secrets  # noqa: F401
from dashkit.core import (  # noqa: F401
    app_factory,
    audit,
    auth,
    constants,
    db,
    inspector,
    sync,
)
from dashkit.core.app_factory import (
    DashkitConfig,
    make_dashboard_app,
)

__all__ = [
    "DashkitConfig",
    "ai",
    "app_factory",
    "audit",
    "auth",
    "constants",
    "db",
    "inspector",
    "make_dashboard_app",
    "secrets",
    "sync",
]
