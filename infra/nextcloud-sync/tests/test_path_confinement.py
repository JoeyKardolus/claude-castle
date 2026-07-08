"""Path translation: Nextcloud path to repo path, repo path to data volume.

Nextcloud sends paths like `/alice/files/Sync/reports/q1.md`; the sync
folder ("Sync" by default, NC_SYNC_FOLDER to override) maps to the repo
prefix ("cloud-sync/" by default, SYNC_TARGET_DIR to override) plus the
user id, so users never collide. Everything else raises OutsideSyncFolder.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from nextcloud_sync.paths import (
    OutsideSyncFolder,
    nextcloud_path_to_repo_path,
    repo_path_to_disk_path,
)


# -- Nextcloud path to repo path --------------------------------------------

def test_basic_path():
    assert nextcloud_path_to_repo_path("/alice/files/Sync/reports/q1.md") == "cloud-sync/alice/reports/q1.md"


def test_top_level_file():
    assert nextcloud_path_to_repo_path("/alice/files/Sync/notes.md") == "cloud-sync/alice/notes.md"


def test_deep_nested_path():
    p = nextcloud_path_to_repo_path("/alice/files/Sync/a/b/c/paper.pdf")
    assert p == "cloud-sync/alice/a/b/c/paper.pdf"


def test_different_uid_gets_own_subtree():
    p = nextcloud_path_to_repo_path("/bob/files/Sync/contract.pdf")
    assert p == "cloud-sync/bob/contract.pdf"


def test_path_with_spaces():
    p = nextcloud_path_to_repo_path("/alice/files/Sync/pitch deck v2.pdf")
    assert p == "cloud-sync/alice/pitch deck v2.pdf"


def test_outside_sync_folder_raises():
    with pytest.raises(OutsideSyncFolder):
        nextcloud_path_to_repo_path("/alice/files/Personal/notes.md")


def test_outside_files_raises():
    with pytest.raises(OutsideSyncFolder):
        nextcloud_path_to_repo_path("/alice/notes.md")


def test_missing_uid_prefix_raises():
    with pytest.raises(OutsideSyncFolder):
        nextcloud_path_to_repo_path("Sync/foo.md")


def test_traversal_segment_raises():
    with pytest.raises(OutsideSyncFolder):
        nextcloud_path_to_repo_path("/alice/files/Sync/../../admin/files/secret.md")


# -- env overrides -----------------------------------------------------------

def test_sync_folder_env_override(monkeypatch):
    monkeypatch.setenv("NC_SYNC_FOLDER", "Dropbox")
    assert nextcloud_path_to_repo_path("/alice/files/Dropbox/x.md") == "cloud-sync/alice/x.md"
    with pytest.raises(OutsideSyncFolder):
        nextcloud_path_to_repo_path("/alice/files/Sync/x.md")


def test_target_dir_env_override_normalises_slash(monkeypatch):
    monkeypatch.setenv("SYNC_TARGET_DIR", "from-cloud")  # no trailing slash
    assert nextcloud_path_to_repo_path("/alice/files/Sync/x.md") == "from-cloud/alice/x.md"


# -- repo path back to the data volume ---------------------------------------

def test_repo_path_to_disk_path(monkeypatch):
    monkeypatch.setenv("NC_DATA_ROOT", "/nc/data")
    p = repo_path_to_disk_path("cloud-sync/alice/reports/q1.md")
    assert p == Path("/nc/data/alice/files/Sync/reports/q1.md")


def test_disk_path_roundtrip(monkeypatch):
    monkeypatch.setenv("NC_DATA_ROOT", "/nc/data")
    repo_path = nextcloud_path_to_repo_path("/bob/files/Sync/a/b.txt")
    assert repo_path_to_disk_path(repo_path) == Path("/nc/data/bob/files/Sync/a/b.txt")


def test_disk_path_outside_target_raises():
    with pytest.raises(OutsideSyncFolder):
        repo_path_to_disk_path("somewhere-else/alice/x.md")


def test_disk_path_traversal_raises():
    with pytest.raises(OutsideSyncFolder):
        repo_path_to_disk_path("cloud-sync/alice/../../etc/passwd")


def test_disk_path_missing_file_part_raises():
    with pytest.raises(OutsideSyncFolder):
        repo_path_to_disk_path("cloud-sync/alice")
