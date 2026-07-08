"""Translate Nextcloud file paths to repo paths and back to the data volume.

Nextcloud serialises paths as `/<uid>/files/<folder>/<rest>` where:
- `<uid>` is the Nextcloud login name
- `files` is a hardcoded segment
- `<folder>` is the sync folder in the user's home (default "Sync",
  override with NC_SYNC_FOLDER)
- `<rest>` is the path inside the folder

A Nextcloud path `/alice/files/Sync/notes.md` maps to the repo path
`cloud-sync/alice/notes.md` (prefix override with SYNC_TARGET_DIR). Each
user gets their own subtree, so two users with the same filename never
collide. Anything not under `/<uid>/files/<folder>/` is outside our scope
and raises OutsideSyncFolder - the caller treats that as a silent skip.

The reverse mapping (repo_path_to_disk_path) finds the file bytes on the
Nextcloud data volume, which the sync container mounts read-only:
`cloud-sync/alice/notes.md` lives at
`<NC_DATA_ROOT>/alice/files/Sync/notes.md`.
"""
from __future__ import annotations

import os
from pathlib import Path

DEFAULT_SYNC_FOLDER = "Sync"
DEFAULT_TARGET_DIR = "cloud-sync/"
DEFAULT_DATA_ROOT = "/nextcloud/data"


class OutsideSyncFolder(ValueError):
    """The path is not confined to <uid>/files/<sync folder>/."""


def _sync_folder() -> str:
    return os.environ.get("NC_SYNC_FOLDER") or DEFAULT_SYNC_FOLDER


def _target_dir() -> str:
    """Repo prefix for synced files, normalised to end with one slash."""
    raw = os.environ.get("SYNC_TARGET_DIR") or DEFAULT_TARGET_DIR
    return raw.strip("/") + "/"


def _reject_traversal(path: str) -> None:
    if ".." in path.split("/"):
        raise OutsideSyncFolder(f"path traversal rejected: {path!r}")


def nextcloud_path_to_repo_path(nc_path: str) -> str:
    """Strip the user + folder prefix, prepend the repo target dir + uid."""
    if not nc_path.startswith("/"):
        raise OutsideSyncFolder(f"path must be absolute: {nc_path!r}")
    _reject_traversal(nc_path)
    parts = nc_path.lstrip("/").split("/", 3)
    if len(parts) < 4:
        raise OutsideSyncFolder(f"path too short: {nc_path!r}")
    uid, files_segment, folder_name, rest = parts
    if files_segment != "files":
        raise OutsideSyncFolder(f"not under files/: {nc_path!r}")
    if folder_name != _sync_folder():
        raise OutsideSyncFolder(f"not under {_sync_folder()!r}: {nc_path!r}")
    if not uid or not rest:
        raise OutsideSyncFolder(f"empty uid or file path: {nc_path!r}")
    return f"{_target_dir()}{uid}/{rest}"


def repo_path_to_disk_path(repo_path: str) -> Path:
    """Locate a repo path's source bytes on the Nextcloud data volume.

    Inverse of nextcloud_path_to_repo_path: `<target>/<uid>/<rest>` becomes
    `<NC_DATA_ROOT>/<uid>/files/<sync folder>/<rest>`.
    """
    _reject_traversal(repo_path)
    target = _target_dir()
    if not repo_path.startswith(target):
        raise OutsideSyncFolder(f"not under {target!r}: {repo_path!r}")
    uid, _, rest = repo_path[len(target):].partition("/")
    if not uid or not rest:
        raise OutsideSyncFolder(f"empty uid or file path: {repo_path!r}")
    data_root = os.environ.get("NC_DATA_ROOT") or DEFAULT_DATA_ROOT
    return Path(data_root) / uid / "files" / _sync_folder() / rest
