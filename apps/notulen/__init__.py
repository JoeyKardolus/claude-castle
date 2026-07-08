"""Notulen — automated Dutch meeting minutes (dashboard + GPU worker).

Tier declaration (module-standard §1): two runtimes, one package.

    app/          — the FastAPI dashboard (5-layer deep module; see its
                    docstring for the layer map). Builds from app/Dockerfile.
    entrypoints/  — worker.py, the self-contained GPU K8s Job entrypoint
                    (its own image: infra/docker/notulen-worker).
    shared/       — worker_constraints.txt (GPU image dep pins)
    inputs/       — notulen_template.md (shared by both runtimes)

The two runtimes deliberately do NOT import each other: the worker image
carries no package code, so its transcription/prompt logic is a declared
twin of ``app/core/minutes`` (module-standard §2.2).
"""
