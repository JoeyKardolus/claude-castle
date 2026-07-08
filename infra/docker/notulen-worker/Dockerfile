# GPU worker for the notulen pipeline: pyannote diarization + whisper-large-v3.
# OPTIONAL TIER — the stack works without it (the dashboard falls back to
# CPU transcription when no GPU cluster is configured).
#
# Build context is the REPO ROOT, and BuildKit is required for the secret:
#   DOCKER_BUILDKIT=1 docker build -f infra/docker/notulen-worker/Dockerfile \
#       --secret id=hf_token,src=/path/to/hf-token-file -t notulen-worker .
#
# Base: PyTorch's official image — torch + CUDA + cuDNN already compatible,
# avoids the version-hell cascade when building on bare nvidia/cuda + pip.

FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV PYTHONUNBUFFERED=1

# ffmpeg for audio transcode. Image already has Python, pip, torch.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# pyannote 3.3.2 — the last 3.x, uses soundfile (no torchcodec/FFmpeg7).
# Pin huggingface-hub<1.0 because pyannote 3.3.2 still calls
# hf_hub_download(use_auth_token=...), removed in hub 1.0.
# matplotlib is a pyannote runtime dep that pip doesn't always resolve.
# -c constraints.txt pins every transitive dep to what we know works.
COPY apps/notulen/shared/worker_constraints.txt /tmp/constraints.txt
RUN pip install --no-cache-dir -c /tmp/constraints.txt \
        pyannote.audio==3.3.2 \
        matplotlib \
        "huggingface-hub<1.0" \
        faster-whisper==1.2.1 \
        anthropic \
        boto3 \
        psycopg2-binary

# Build-time sanity check.
RUN python -c "from pyannote.audio import Pipeline; from faster_whisper import WhisperModel; print('imports OK')"

# Bake whisper large-v3 at build (int8 compute_type is ignored at runtime
# when we re-instantiate with float16 on GPU — the cache is reused).
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('large-v3', compute_type='int8')"

# Bake pyannote models at build. The Hugging Face token is fed via a
# BuildKit secret mount so it never lands in an image layer or in
# `docker history` output. (The naive `ARG HF_TOKEN` + `ENV HF_TOKEN=...`
# pattern bakes the token into a layer even with a trailing `ENV HF_TOKEN=`
# wipe; anyone who could pull the image could recover the token.)
# The token needs read access to the gated models
# pyannote/speaker-diarization-3.1 and pyannote/segmentation-3.0
# (accept their terms on huggingface.co first).
RUN --mount=type=secret,id=hf_token,required=true \
    HF_TOKEN="$(cat /run/secrets/hf_token)" \
    python -c "from pyannote.audio import Pipeline; import os; Pipeline.from_pretrained('pyannote/speaker-diarization-3.1', use_auth_token=os.environ['HF_TOKEN'])"

WORKDIR /app
COPY apps/notulen/entrypoints/worker.py /app/notulen_worker.py
COPY apps/notulen/inputs/notulen_template.md /app/notulen_template.md

ENTRYPOINT ["python", "/app/notulen_worker.py"]
