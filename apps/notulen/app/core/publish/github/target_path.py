"""Repo-relative target path for a committed notulen markdown file.

Owns the path grammar ``<NOTULEN_TARGET_DIR>/<YYYY-MM>_<slug>.md``. Keep
the grammar stable once deployed so historic notulen don't get re-keyed.
The slug grammar lives in ``shared/slug.py`` (one home; this module used
to carry a private copy that had drifted from the AI-call ``doc_path``
label).
"""
from __future__ import annotations

import os

from apps.notulen.app.shared.slug import slugify


def target_path(meeting_date: str, title: str) -> str:
    """Repo-relative path for a notulen markdown file.

    The month comes from the first 7 chars of ``meeting_date`` (works for
    both ``YYYY-MM-DD`` and full ISO timestamps).
    """
    target_dir = os.environ.get("NOTULEN_TARGET_DIR", "minutes").strip("/")
    return f"{target_dir}/{meeting_date[:7]}_{slugify(title)}.md"
