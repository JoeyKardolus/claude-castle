"""Commit notulen markdown to a GitHub repo via the Contents API.

The target repo comes from ``NOTULEN_GITHUB_REPO`` (``owner/name``). When
it is unset, publishing is skipped: the job still completes, with a
sentinel instead of a commit URL — the stack works out of the box without
any GitHub wiring.

Idempotent: same content at the same path is a no-op. Real changes create
a commit authored as the configured PAT identity. Does NOT own when/whether
to commit — that policy lives in ``core/publish/finalize_commit.py`` and
``core/publish/git_writer_loop.py``.

FAILURE POLICY: Tier-1 — raises (KeyError on a missing PAT,
requests.HTTPError on a non-2xx); callers keep the job ``committing`` and
retry.
"""
from __future__ import annotations

import base64
import logging
import os
from typing import Optional

import requests

from apps.notulen.app.core.publish.github.target_path import target_path

BRANCH = os.environ.get("NOTULEN_GITHUB_BRANCH", "main")
API_ROOT = "https://api.github.com"

# Returned instead of a commit URL when NOTULEN_GITHUB_REPO is unset —
# publishing is an optional tier; the job still completes.
UNPUBLISHED_URL = "unpublished://notulen-github-repo-not-configured"

logger = logging.getLogger("notulen")


def _github_repo() -> str:
    """Target repo as ``owner/name`` — empty string means publishing is off.

    Read at call time so tests (and a live env change) take effect without
    a re-import.
    """
    return os.environ.get("NOTULEN_GITHUB_REPO", "")


def commit_notulen_to_github(
    job_id: str,
    title: str,
    meeting_date: str,
    output_markdown: str,
    *,
    token: Optional[str] = None,
    session: Optional[requests.Session] = None,
) -> str:
    """Commit (or no-op) the notulen markdown; return a URL pointing at it.

    Returns the commit URL on a real write, or the file URL when the call
    was idempotent (content already matches). Callers store this against
    the job row for the audit trail.

    Raises:
        KeyError: if publishing is configured but no token is passed and
            NOTULEN_GITHUB_PAT is not set.
        requests.HTTPError: if the GitHub API returns a non-2xx on PUT.
    """
    repo = _github_repo()
    if not repo:
        logger.info(
            "NOTULEN_GITHUB_REPO is not set — skipping GitHub publish for job %s. "
            "Set NOTULEN_GITHUB_REPO=<owner>/<repo> (and NOTULEN_GITHUB_PAT) to "
            "commit finished minutes to a git repo.",
            job_id,
        )
        return UNPUBLISHED_URL

    if token is None:
        token = os.environ.get("NOTULEN_GITHUB_PAT")
        if not token:
            raise KeyError("NOTULEN_GITHUB_PAT")

    path = target_path(meeting_date, title)
    api_url = f"{API_ROOT}/repos/{repo}/contents/{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    http = session or requests.Session()

    existing_sha, idempotent_url = _read_existing_for_idempotency(
        http, api_url, headers, output_markdown
    )
    if idempotent_url is not None:
        return idempotent_url

    payload = {
        "message": _commit_message(title, meeting_date, job_id),
        "content": base64.b64encode(output_markdown.encode("utf-8")).decode("ascii"),
        "branch": BRANCH,
    }
    if existing_sha:
        payload["sha"] = existing_sha

    resp = http.put(api_url, headers=headers, json=payload)
    resp.raise_for_status()
    return resp.json()["commit"]["html_url"]


def _commit_message(title: str, meeting_date: str, job_id: str) -> str:
    """Human-readable, audit-friendly commit message tying file → job.

    QMS audit traces a notulen markdown back to its job row in
    `notulen_jobs` via the `[job:<id>]` tag.
    """
    return f"notulen: {title} ({meeting_date}) [job:{job_id}]"


def _read_existing_for_idempotency(
    http: requests.Session,
    api_url: str,
    headers: dict,
    new_markdown: str,
) -> tuple[Optional[str], Optional[str]]:
    """Return (existing_sha, idempotent_url) for the target path.

    `existing_sha` is None when the file does not yet exist (create path),
    otherwise the blob SHA needed to update.

    `idempotent_url` is non-None only when the existing content already
    matches the new content — in that case callers skip the PUT entirely
    and return this URL as the result.
    """
    resp = http.get(api_url, headers={**headers, "Accept": "application/vnd.github+json"})
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

    if existing_bytes == new_markdown.encode("utf-8"):
        return existing_sha, body.get("html_url") or api_url

    return existing_sha, None
