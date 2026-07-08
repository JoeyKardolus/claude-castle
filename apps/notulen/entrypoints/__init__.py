"""Top-level entrypoints for notulen runtimes that ship as their own image.

``worker.py`` is the GPU K8s notulen-worker pod entrypoint (pyannote +
whisper-large-v3 + Claude). The FastAPI dashboard's entrypoint lives
under ``app/entrypoints/main.py`` because it has its own Docker build
context.
"""
