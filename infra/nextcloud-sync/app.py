"""FastAPI app - Bearer auth + event dispatch.

``app`` is the one public symbol; the route handlers are ``_``-prefixed
internals reached only via their routes. Runs as the `nextcloud-sync`
container in the compose stack, internal-only (Nextcloud reaches it by
service name, nothing else does):

    uvicorn nextcloud_sync.app:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import logging
import os

from fastapi import FastAPI, HTTPException, Request

from nextcloud_sync.auth import AuthError, verify_bearer
from nextcloud_sync.events import NextcloudEventError, parse_event
from nextcloud_sync.paths import repo_path_to_disk_path
from nextcloud_sync.writer import SyncConflictUnresolved, commit_event

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(message)s")

app = FastAPI(title="Nextcloud sync")


def _expected_secret() -> str:
    secret = os.environ.get("NEXTCLOUD_WEBHOOK_SECRET")
    if not secret:
        raise HTTPException(status_code=500, detail="NEXTCLOUD_WEBHOOK_SECRET unset")
    return secret


def _github_token() -> str:
    token = os.environ.get("SYNC_GITHUB_PAT")
    if not token:
        raise HTTPException(status_code=500, detail="SYNC_GITHUB_PAT unset")
    return token


def _read_from_disk(repo_path: str) -> bytes:
    """Read a repo-relative path's bytes off the Nextcloud data volume."""
    return repo_path_to_disk_path(repo_path).read_bytes()


@app.get("/healthz")
def _healthz() -> dict:
    return {"ok": True}


@app.post("/nextcloud/file-event")
async def _file_event(request: Request) -> dict:
    try:
        verify_bearer(request.headers.get("Authorization"), expected=_expected_secret())
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc))

    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"invalid JSON: {exc}")

    try:
        event = parse_event(payload)
    except NextcloudEventError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        url = commit_event(event, _read_from_disk, token=_github_token())
    except SyncConflictUnresolved as exc:
        # Already logged inside the writer; surface as 503 so Nextcloud's
        # background job marks the delivery as failed and we can spot it
        # in the listener's run log.
        raise HTTPException(status_code=503, detail=str(exc))

    if not url:
        log.info('{"event": "skipped", "reason": "outside the sync folder"}')
        return {"skipped": True}

    log.info('{"event": "committed", "url": "%s"}', url)
    return {"committed": True, "url": url}
