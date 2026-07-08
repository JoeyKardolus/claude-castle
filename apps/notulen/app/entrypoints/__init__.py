"""Notulen dashboard FastAPI surface (``entrypoints/`` layer).

The only layer that imports FastAPI routing. uvicorn target:
``apps.notulen.app.entrypoints.main:app``.

Module map:
    main.py           — app assembly: DashkitConfig + factory + routers +
                        startup hooks (thin bootstrap, the overlay convention)
    spa_routes.py     — GET / + /dashboard.js (the SPA shell, no-store)
    upload_routes.py  — POST /api/upload/* chunked-upload lifecycle
    jobs_routes.py    — GET/DELETE /api/jobs* projections + download
    health_routes.py  — /healthz (ADR-0013 carve-out) + /api/health/notulen/full

No re-exports: route modules register everything on their ``router``; the
seam is HTTP, not Python (stated rationale per module-standard §2.1).
"""
