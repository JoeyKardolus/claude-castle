# Notulen dashboard image (CPU tier — the default working path).
# Build context is the REPO ROOT:
#   docker build -f infra/docker/notulen/Dockerfile -t castle-notulen .
FROM python:3.12-slim
WORKDIR /app

# git for the audit/version endpoints; ffmpeg for audio transcode.
RUN apt-get update -qq && apt-get install -y -qq git ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && git config --global --add safe.directory '*'

# dashkit deps + notulen extras. faster-whisper is the CPU transcription
# fallback (the default working path when no GPU cluster is configured);
# kubernetes is only exercised when KUBECONFIG_DATA is set (optional GPU tier).
# Versions are pinned by constraints.txt (regenerate with:
#   uv export --no-hashes --all-extras --no-emit-workspace --no-dev \
#     -o infra/docker/notulen/constraints.txt
# ) so image builds stay reproducible.
COPY infra/docker/notulen/constraints.txt /tmp/constraints.txt
RUN pip install --no-cache-dir -c /tmp/constraints.txt \
        fastapi \
        "uvicorn[standard]" \
        psycopg2-binary \
        anthropic \
        markdown \
        pydantic \
        requests \
        faster-whisper \
        boto3 \
        python-multipart \
        kubernetes

# Download and cache the whisper medium model at build time so the first
# CPU transcription doesn't stall on a model download.
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('medium', compute_type='int8', device='cpu')"

# Package layout mirrors the repo: uvicorn puts the CWD (/app) on
# sys.path, so `dashkit`, `gpu_jobs` and `apps.notulen...` all resolve
# with no sys.path tricks in source.
COPY lib/dashkit/ ./dashkit/
COPY infra/gpu-jobs/gpu_jobs/ ./gpu_jobs/
RUN mkdir -p apps && touch apps/__init__.py
COPY apps/notulen/ ./apps/notulen/

EXPOSE 8000
CMD ["uvicorn", "apps.notulen.app.entrypoints.main:app", "--host", "0.0.0.0", "--port", "8000"]
