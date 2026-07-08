"""Unit tests for the notulen GitHub writer.

Pins the contract:
- Target path is `<NOTULEN_TARGET_DIR>/<YYYY-MM>_<slug>.md` (default dir
  `minutes/`); keep the grammar stable so historic notulen don't re-key.
- Commit message ties the file back to the job that produced it.
- Idempotent on retry: same content + same path → no second commit.
- Adapts on update vs create (passes existing blob SHA when present).
- Publishing is optional: with NOTULEN_GITHUB_REPO unset the writer skips
  GitHub entirely and returns the UNPUBLISHED_URL sentinel.
"""
from __future__ import annotations

import base64
from unittest.mock import MagicMock

import pytest

from apps.notulen.app.core.publish.github.github_writer import (
    BRANCH,
    UNPUBLISHED_URL,
    _commit_message,
    commit_notulen_to_github,
)
from apps.notulen.app.core.publish.github.target_path import target_path

REPO = "example-org/example-repo"


@pytest.fixture(autouse=True)
def _configure_repo(monkeypatch):
    """Publishing is env-gated; point the writer at a dummy repo for tests."""
    monkeypatch.setenv("NOTULEN_GITHUB_REPO", REPO)


# ── pure helpers ────────────────────────────────────────────────────────────

def test_target_path_builds_yyyy_mm_slug():
    assert target_path("2026-05-23", "Team standup") == "minutes/2026-05_team_standup.md"


def test_target_path_handles_full_iso_timestamps():
    # meeting_date passes the YYYY-MM-DD prefix; longer strings still work
    assert target_path("2026-05-23T10:00:00Z", "Q2 review") == "minutes/2026-05_q2_review.md"


def test_target_path_slug_strips_punctuation():
    assert target_path("2026-05-23", "Alice & Bob: 1-on-1!").startswith("minutes/2026-05_")
    assert "&" not in target_path("2026-05-23", "A & B")
    assert "!" not in target_path("2026-05-23", "A!")


def test_commit_message_links_job_and_date():
    msg = _commit_message("Sprint planning", "2026-05-23", "job-abc-123")
    assert "Sprint planning" in msg
    assert "2026-05-23" in msg
    assert "job-abc-123" in msg
    assert msg.startswith("notulen:")


# ── PUT path: create (no existing file) ─────────────────────────────────────

def _make_session(*, get_status: int, get_payload=None, put_payload=None):
    """Build a mock requests.Session that returns scripted GET + PUT responses."""
    session = MagicMock()
    get_resp = MagicMock()
    get_resp.status_code = get_status
    get_resp.json.return_value = get_payload or {}
    session.get.return_value = get_resp

    put_resp = MagicMock()
    put_resp.status_code = 201
    put_resp.json.return_value = put_payload or {
        "commit": {"html_url": "https://github.com/example-org/example-repo/commit/deadbeef"},
        "content": {"sha": "newblob"},
    }
    put_resp.raise_for_status = MagicMock()
    session.put.return_value = put_resp
    return session


def test_create_sends_put_without_sha_when_file_absent():
    session = _make_session(get_status=404)
    url = commit_notulen_to_github(
        job_id="j1",
        title="Sprint planning",
        meeting_date="2026-05-23",
        output_markdown="# Sprint planning\n\nbody",
        token="ghp_fake",
        session=session,
    )

    assert url == "https://github.com/example-org/example-repo/commit/deadbeef"
    session.put.assert_called_once()
    _, kwargs = session.put.call_args
    payload = kwargs["json"]
    assert "sha" not in payload  # create path: no sha
    assert payload["branch"] == BRANCH
    assert payload["message"] == _commit_message("Sprint planning", "2026-05-23", "j1")
    decoded = base64.b64decode(payload["content"]).decode("utf-8")
    assert decoded == "# Sprint planning\n\nbody"


def test_create_targets_correct_api_url():
    session = _make_session(get_status=404)
    commit_notulen_to_github(
        job_id="j1", title="X", meeting_date="2026-05-23",
        output_markdown="body", token="ghp_fake", session=session,
    )
    expected_path = "minutes/2026-05_x.md"
    expected_url = f"https://api.github.com/repos/{REPO}/contents/{expected_path}"
    args, _ = session.put.call_args
    assert args[0] == expected_url


def test_create_sends_bearer_token():
    session = _make_session(get_status=404)
    commit_notulen_to_github(
        job_id="j1", title="X", meeting_date="2026-05-23",
        output_markdown="body", token="ghp_fake", session=session,
    )
    _, kwargs = session.put.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer ghp_fake"
    assert kwargs["headers"]["Accept"] == "application/vnd.github+json"


# ── PUT path: update (existing file, new content) ───────────────────────────

def test_update_sends_put_with_existing_sha():
    existing_content_b64 = base64.b64encode(b"old body").decode("ascii")
    session = _make_session(
        get_status=200,
        get_payload={"sha": "oldblob", "content": existing_content_b64, "encoding": "base64"},
    )
    commit_notulen_to_github(
        job_id="j1", title="X", meeting_date="2026-05-23",
        output_markdown="new body", token="ghp_fake", session=session,
    )
    _, kwargs = session.put.call_args
    assert kwargs["json"]["sha"] == "oldblob"


# ── Idempotency: same content = no PUT, no new commit ──────────────────────

def test_idempotent_skips_put_when_content_identical():
    identical_content_b64 = base64.b64encode(b"# Notulen\n\nbody").decode("ascii")
    session = _make_session(
        get_status=200,
        get_payload={
            "sha": "blobsha",
            "content": identical_content_b64,
            "encoding": "base64",
            "html_url": "https://github.com/example-org/example-repo/blob/main/minutes/2026-05_x.md",
        },
    )
    url = commit_notulen_to_github(
        job_id="j1", title="X", meeting_date="2026-05-23",
        output_markdown="# Notulen\n\nbody", token="ghp_fake", session=session,
    )
    # No PUT issued
    session.put.assert_not_called()
    # Returns a URL pointing at the existing file (not a commit URL, since no new commit)
    assert "minutes/2026-05_x.md" in url


# ── Error surfacing ────────────────────────────────────────────────────────

def test_put_failure_propagates():
    session = _make_session(get_status=404)
    failure = MagicMock()
    failure.status_code = 422
    failure.json.return_value = {"message": "Invalid request"}
    failure.raise_for_status.side_effect = Exception("422 Unprocessable Entity")
    session.put.return_value = failure

    with pytest.raises(Exception, match="422"):
        commit_notulen_to_github(
            job_id="j1", title="X", meeting_date="2026-05-23",
            output_markdown="body", token="ghp_fake", session=session,
        )


def test_missing_token_raises_keyerror(monkeypatch):
    monkeypatch.delenv("NOTULEN_GITHUB_PAT", raising=False)
    session = _make_session(get_status=404)
    with pytest.raises(KeyError):
        commit_notulen_to_github(
            job_id="j1", title="X", meeting_date="2026-05-23",
            output_markdown="body", session=session,  # no token kwarg, no env
        )


def test_reads_pat_from_env(monkeypatch):
    monkeypatch.setenv("NOTULEN_GITHUB_PAT", "ghp_env_token")
    session = _make_session(get_status=404)
    commit_notulen_to_github(
        job_id="j1", title="X", meeting_date="2026-05-23",
        output_markdown="body", session=session,  # no token kwarg
    )
    sent_auth = session.put.call_args.kwargs["headers"]["Authorization"]
    assert sent_auth == "Bearer ghp_env_token"


# ── Optional tier: unset repo = skip publishing ─────────────────────────────

def test_unset_repo_skips_github_and_returns_sentinel(monkeypatch):
    monkeypatch.delenv("NOTULEN_GITHUB_REPO", raising=False)
    session = _make_session(get_status=404)
    url = commit_notulen_to_github(
        job_id="j1", title="X", meeting_date="2026-05-23",
        output_markdown="body", session=session,
    )
    assert url == UNPUBLISHED_URL
    session.get.assert_not_called()
    session.put.assert_not_called()
