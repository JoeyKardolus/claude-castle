"""Nextcloud file-event to GitHub Contents API webhook bridge.

Nextcloud's webhook_listeners app (Nextcloud 30+) fires an HTTP POST on
file create/modify/delete/rename. This service receives each event, and
when the file lives in a user's "Sync" folder, reads it from the (read-only)
Nextcloud data volume and commits it to the GitHub repo via the Contents
API, with the Nextcloud user as the commit author. Result: anything a user
drops in their Sync folder also lands in the repo under `cloud-sync/<user>/`.

Module map (one concern per file):

    auth.py    verify_bearer() - constant-time Bearer check; AuthError
    events.py  parse_event() - the three webhook_listeners payload shapes
    paths.py   nextcloud_path_to_repo_path() - Nextcloud path to repo path,
               rejects anything outside the Sync folder (OutsideSyncFolder);
               repo_path_to_disk_path() - repo path back to the data volume
    writer.py  commit_event() - GitHub Contents API PUT/DELETE with
               idempotency + one 409 retry; raises on unresolved conflict
    app.py     the ONE transport-aware adapter (FastAPI); reached by uvicorn
               via its module path, deliberately NOT re-exported here so the
               seam imports without fastapi

What this package does NOT own: registering the listeners in Nextcloud
(register-webhooks.sh next to this file) and the compose wiring (the
`nextcloud-sync` service in the root docker-compose.yml).

FAILURE POLICY: the HTTP adapter fails closed on auth (401) and on
unparseable payloads (400); commit_event raises one exception class per
failure mode (SyncConflictUnresolved, FileTooLargeForGitHub) and logs an
error before raising - an event Nextcloud cannot deliver is retried by
Nextcloud, never dropped silently.
"""
from __future__ import annotations

from nextcloud_sync.auth import AuthError, verify_bearer
from nextcloud_sync.events import NextcloudEventError, parse_event
from nextcloud_sync.paths import (
    OutsideSyncFolder,
    nextcloud_path_to_repo_path,
    repo_path_to_disk_path,
)
from nextcloud_sync.writer import (
    FileTooLargeForGitHub,
    SyncConflictUnresolved,
    commit_event,
)

__all__ = [
    "AuthError",
    "FileTooLargeForGitHub",
    "NextcloudEventError",
    "OutsideSyncFolder",
    "SyncConflictUnresolved",
    "commit_event",
    "nextcloud_path_to_repo_path",
    "parse_event",
    "repo_path_to_disk_path",
    "verify_bearer",
]
