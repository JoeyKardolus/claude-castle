# Nextcloud-to-GitHub sync service (the `nextcloud-sync` compose service).
# Build context is the REPO ROOT:
#   docker build -f infra/nextcloud-sync/Dockerfile -t castle-nextcloud-sync .
FROM python:3.12-slim
WORKDIR /app

RUN pip install --no-cache-dir \
        "fastapi>=0.115,<1" \
        "uvicorn[standard]>=0.30,<1" \
        "pydantic>=2.7,<3" \
        "requests>=2.31,<3"

# The service directory becomes the `nextcloud_sync` package: uvicorn puts
# the CWD (/app) on sys.path, so `nextcloud_sync.*` resolves with no
# sys.path tricks in source.
COPY infra/nextcloud-sync/ ./nextcloud_sync/

EXPOSE 8000
CMD ["uvicorn", "nextcloud_sync.app:app", "--host", "0.0.0.0", "--port", "8000"]
