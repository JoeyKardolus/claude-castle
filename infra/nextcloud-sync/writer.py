"""GitHub Contents API writer for Nextcloud-driven per-file commits.

One entry point - ``commit_event`` - that takes a parsed Nextcloud event +
a disk-reader callable, and issues PUT / DELETE calls against the repo's
main branch (repo comes from the GITHUB_REPO env var, `owner/name`). The
reader is injected so unit tests can supply bytes without touching the
filesystem.

Behaviours pinned by the tests in tests/:
- Create / update: PUT with existing-sha when present; idempotent on
  identical content (returns the file URL, no PUT).
- Delete: DELETE with existing-sha; 404 is a no-op (file already gone).
- Rename: PUT target + DELETE source.
- 409 (sha drifted between read and write): refetch + retry once; second
  409 logs an error and raises SyncConflictUnresolved.
- Author is derived from the Nextcloud actor: `displayName` as name,
  `<uid>@nextcloud.invalid` as fallback email.
- Path outside the sync folder returns the empty-string skip marker.
"""
from __future__ import annotations

import base64
import logging
import os
from typing import Callable, Optional, Union

import requests

from nextcloud_sync.events import (
    NodeDeletedEvent,
    NodeRenamedEvent,
    NodeWrittenEvent,
)
from nextcloud_sync.paths import OutsideSyncFolder, nextcloud_path_to_repo_path

log = logging.getLogger(__name__)

BRANCH = "main"
API_ROOT = "https://api.github.com"
# `.invalid` is the RFC 2606 reserved TLD: the address can never be real,
# but GitHub accepts it as a commit author email.
FALLBACK_EMAIL_DOMAIN = "nextcloud.invalid"

# GitHub Contents API rejects >100 MB; we pre-check at 95 to leave headroom
# for base64 encoding overhead (~33% inflation). Files larger than this stay
# in Nextcloud only; the error log says so, loudly.
MAX_FILE_BYTES = 95 * 1024 * 1024


class SyncConflictUnresolved(RuntimeError):
    """Second 409 from the Contents API; needs a human look at the file."""


class FileTooLargeForGitHub(RuntimeError):
    """File exceeds the GitHub Contents API 100 MB limit."""


class RepoNotConfigured(RuntimeError):
    """GITHUB_REPO env var is missing or not `owner/name`."""


NextcloudEvent = Union[NodeWrittenEvent, NodeDeletedEvent, NodeRenamedEvent]
Reader = Callable[[str], bytes]


def _repo_slug() -> str:
    """Validated `owner/name` from the GITHUB_REPO env var."""
    slug = os.environ.get("GITHUB_REPO", "").strip().strip("/")
    if slug.count("/") != 1 or not all(slug.split("/")):
        raise RepoNotConfigured(f"GITHUB_REPO must be owner/name, got {slug!r}")
    return slug


def commit_event(
    event: NextcloudEvent,
    read_disk: Reader,
    *,
    token: str,
    session: Optional[requests.Session] = None,
) -> str:
    """Dispatch on event type; return a URL (commit or file) or "" if skipped."""
    if isinstance(event, NodeRenamedEvent):
        try:
            src_repo = nextcloud_path_to_repo_path(event.source.path)
            dst_repo = nextcloud_path_to_repo_path(event.target.path)
        except OutsideSyncFolder:
            return ""
        http = session or requests.Session()
        try:
            body = read_disk(dst_repo)
        except FileNotFoundError:
            # Same race as Written. Defer to the Deleted event for cleanup.
            return ""
        author = _author_from(event)
        msg = _message_for(event, dst_repo)
        put_url = _put_file(http, token, dst_repo, body, msg, author)
        _delete_file(http, token, src_repo, _message_for(event, src_repo, is_rename_source=True), author)
        return put_url

    try:
        repo_path = nextcloud_path_to_repo_path(event.node.path)
    except OutsideSyncFolder:
        return ""

    http = session or requests.Session()
    author = _author_from(event)
    msg = _message_for(event, repo_path)

    if isinstance(event, NodeWrittenEvent):
        try:
            body = read_disk(repo_path)
        except FileNotFoundError:
            # Race: file deleted between Written-event fire and our cron-
            # processed read. Treat as a skip; the queued Deleted event
            # (already in line behind us) will reconcile.
            return ""
        if len(body) > MAX_FILE_BYTES:
            _log_too_large(repo_path, len(body), author)
            raise FileTooLargeForGitHub(
                f"{repo_path}: {len(body)} bytes > {MAX_FILE_BYTES} limit"
            )
        return _put_file(http, token, repo_path, body, msg, author)

    if isinstance(event, NodeDeletedEvent):
        return _delete_file(http, token, repo_path, msg, author)

    raise TypeError(f"unsupported event type: {type(event).__name__}")


def _author_from(event: NextcloudEvent) -> dict:
    user = event.user
    name = user.displayName or user.uid
    return {
        "name": name.title() if name == user.uid else name,
        "email": f"{user.uid}@{FALLBACK_EMAIL_DOMAIN}",
    }


def _message_for(event: NextcloudEvent, repo_path: str, *, is_rename_source: bool = False) -> str:
    kind = type(event).__name__.replace("Event", "").replace("Node", "").lower()
    if isinstance(event, NodeRenamedEvent) and is_rename_source:
        return f"cloud: rename remove {repo_path}"
    return f"cloud: {kind} {repo_path}"


def _put_file(
    http: requests.Session,
    token: str,
    repo_path: str,
    body: bytes,
    message: str,
    author: dict,
) -> str:
    api_url = f"{API_ROOT}/repos/{_repo_slug()}/contents/{repo_path}"
    headers = _headers(token)

    existing_sha, idempotent_url = _existing_for_idempotency(http, api_url, headers, body)
    if idempotent_url is not None:
        return idempotent_url

    payload = {
        "message": message,
        "content": base64.b64encode(body).decode("ascii"),
        "branch": BRANCH,
        "author": author,
    }
    if existing_sha:
        payload["sha"] = existing_sha

    resp = http.put(api_url, headers=headers, json=payload)
    if resp.status_code == 409:
        # The blob SHA drifted between our GET and PUT. Refetch + retry once.
        existing_sha, _ = _existing_for_idempotency(http, api_url, headers, body)
        if existing_sha:
            payload["sha"] = existing_sha
        resp = http.put(api_url, headers=headers, json=payload)
        if resp.status_code == 409:
            _log_conflict(repo_path, author, attempts=2)
            raise SyncConflictUnresolved(
                f"two consecutive 409s on {repo_path}; see the error log"
            )

    resp.raise_for_status()
    return resp.json()["commit"]["html_url"]


def _delete_file(
    http: requests.Session,
    token: str,
    repo_path: str,
    message: str,
    author: dict,
) -> str:
    api_url = f"{API_ROOT}/repos/{_repo_slug()}/contents/{repo_path}"
    headers = _headers(token)
    get = http.get(api_url, headers=headers)
    if get.status_code == 404:
        # Already absent on GitHub. Nothing to do.
        return api_url
    if get.status_code != 200:
        get.raise_for_status()
    existing_sha = get.json().get("sha")
    payload = {"message": message, "sha": existing_sha, "branch": BRANCH, "author": author}
    resp = http.delete(api_url, headers=headers, json=payload)
    resp.raise_for_status()
    return resp.json()["commit"]["html_url"]


def _existing_for_idempotency(
    http: requests.Session,
    api_url: str,
    headers: dict,
    new_body: bytes,
) -> tuple[Optional[str], Optional[str]]:
    resp = http.get(api_url, headers=headers)
    if resp.status_code == 404:
        return None, None
    if resp.status_code != 200:
        resp.raise_for_status()
    body = resp.json()
    existing_sha = body.get("sha")
    encoded = body.get("content", "")
    if body.get("encoding") == "base64":
        existing_bytes = base64.b64decode(encoded)
    else:
        existing_bytes = encoded.encode("utf-8")
    if existing_bytes == new_body:
        return existing_sha, body.get("html_url") or api_url
    return existing_sha, None


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _log_conflict(repo_path: str, author: dict, *, attempts: int) -> None:
    log.error(
        "nextcloud-sync: unresolved conflict on %s - GitHub Contents API "
        "returned 409 %dx in a row (triggering user: %s <%s>). Likely cause: "
        "another writer modified the blob between our GET and PUT. Inspect "
        "the file on main; reconcile by hand if needed.",
        repo_path,
        attempts,
        author.get("name"),
        author.get("email"),
    )


def _log_too_large(repo_path: str, size: int, author: dict) -> None:
    log.error(
        "nextcloud-sync: file too large for git (%d MB) - GitHub Contents "
        "API caps at 100 MB; %s is %d bytes (user: %s <%s>). The file is in "
        "Nextcloud but NOT in git. To preserve it in git, split it into "
        "smaller files or move it to object storage and commit a pointer.",
        size // 1024 // 1024,
        repo_path,
        size,
        author.get("name"),
        author.get("email"),
    )
