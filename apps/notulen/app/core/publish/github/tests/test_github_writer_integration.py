"""Integration test for the notulen GitHub writer.

Skipped by default (integration tests are env-gated). Runs a real commit
on a throwaway branch in the configured repo and cleans up after itself.
Requires:

    NOTULEN_GITHUB_REPO         # <owner>/<repo> target
    NOTULEN_GITHUB_PAT          # fine-grained PAT with contents:write
    NOTULEN_INTEGRATION_TESTS=1

Without the env vars, this whole module is skipped — unit tests in
test_github_writer.py give full mocked coverage.
"""
from __future__ import annotations

import os
import time
import uuid

import pytest
import requests

pytestmark = pytest.mark.skipif(
    os.environ.get("NOTULEN_INTEGRATION_TESTS") != "1"
    or "NOTULEN_GITHUB_PAT" not in os.environ
    or "NOTULEN_GITHUB_REPO" not in os.environ,
    reason=(
        "integration test (set NOTULEN_INTEGRATION_TESTS=1 + "
        "NOTULEN_GITHUB_REPO + NOTULEN_GITHUB_PAT)"
    ),
)

from apps.notulen.app.core.publish.github.github_writer import (  # noqa: E402
    API_ROOT,
    commit_notulen_to_github,
)

REPO = os.environ.get("NOTULEN_GITHUB_REPO", "")


def _github_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {os.environ['NOTULEN_GITHUB_PAT']}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    return session


def _create_branch(session: requests.Session, name: str) -> str:
    """Branch off main; return the new branch's commit SHA."""
    main = session.get(f"{API_ROOT}/repos/{REPO}/git/ref/heads/main")
    main.raise_for_status()
    sha = main.json()["object"]["sha"]
    resp = session.post(
        f"{API_ROOT}/repos/{REPO}/git/refs",
        json={"ref": f"refs/heads/{name}", "sha": sha},
    )
    resp.raise_for_status()
    return sha


def _delete_branch(session: requests.Session, name: str) -> None:
    session.delete(f"{API_ROOT}/repos/{REPO}/git/refs/heads/{name}")


def test_real_commit_on_throwaway_branch(monkeypatch):
    """End-to-end: PUT contents, verify the commit lands, clean up.

    The branch never merges to main; this is purely an auth + path +
    payload-shape smoke against the real GitHub API.
    """
    branch = f"test/notulen-writer-{uuid.uuid4().hex[:8]}"
    monkeypatch.setattr(
        "apps.notulen.app.core.publish.github.github_writer.BRANCH", branch
    )

    session = _github_session()
    _create_branch(session, branch)

    try:
        job_id = f"itest-{uuid.uuid4().hex[:8]}"
        title = "Integration smoke"
        meeting_date = "2026-05-23"
        body = f"# Integration smoke\n\nrun id: {job_id}\n"

        commit_url = commit_notulen_to_github(job_id, title, meeting_date, body)
        assert commit_url.startswith(f"https://github.com/{REPO}/commit/")

        # Idempotent: same content + same branch + same path = no new PUT,
        # returns a URL pointing at the same file.
        again = commit_notulen_to_github(job_id, title, meeting_date, body)
        assert again  # non-empty
        # The idempotent path returns the file's html_url, not a /commit/<sha>;
        # accept either shape but require it references the file.
        assert "minutes/" in again or commit_url in again

        time.sleep(1)  # let GitHub's index catch up
        verify = session.get(
            f"{API_ROOT}/repos/{REPO}/contents/minutes/2026-05_integration_smoke.md",
            params={"ref": branch},
        )
        assert verify.status_code == 200, verify.text
    finally:
        _delete_branch(session, branch)
