"""Retention purge: delete login/audit log rows older than 90 days.

Why: logs of who logged in when are personal data. Keeping them forever is
both a privacy liability and pointless — 90 days is enough to investigate
anything odd. This script deletes older rows, once a day, via the systemd
timer in infra/systemd/purge-auth-logs.timer.

How: it runs `psql` inside the castle-postgres container (so it needs no
Python database driver on the VM — plain python3 is enough). The container
already knows the database credentials from its own environment.

Configuration (all optional, via environment variables):
  RETENTION_DAYS    how long to keep rows (default 90, minimum 7)
  PURGE_TABLES      comma-separated table names
                    (default: auth_login_log,account_audit_log)
  PURGE_TIME_COLUMN timestamp column the age is measured on
                    (default: occurred_at)

A table that does not exist is skipped with a notice — that is normal until
the app creates it. A database that cannot be reached is a hard error (the
systemd unit goes red).
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

_DEFAULT_DAYS = 90
_DEFAULT_TABLES = "auth_login_log,account_audit_log"
_DEFAULT_COLUMN = "occurred_at"

# Table/column names are interpolated into SQL, so only allow plain
# identifiers — no quotes, spaces, or punctuation.
_IDENT = re.compile(r"^[a-z_][a-z0-9_]*$")


def _psql(sql: str) -> subprocess.CompletedProcess:
    """Run one SQL statement inside the postgres container via psql."""
    return subprocess.run(
        [
            "docker", "exec", "-i", "castle-postgres",
            "sh", "-c",
            'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tA',
        ],
        input=sql,
        capture_output=True,
        text=True,
    )


def main() -> int:
    days = int(os.environ.get("RETENTION_DAYS", str(_DEFAULT_DAYS)))
    if days < 7:
        print(f"RETENTION_DAYS={days} is too aggressive; refusing", file=sys.stderr)
        return 2

    column = os.environ.get("PURGE_TIME_COLUMN", _DEFAULT_COLUMN)
    tables = [
        name.strip()
        for name in os.environ.get("PURGE_TABLES", _DEFAULT_TABLES).split(",")
        if name.strip()
    ]
    for ident in [column, *tables]:
        if not _IDENT.match(ident):
            print(f"invalid identifier {ident!r}; refusing", file=sys.stderr)
            return 2

    failures = 0
    for table in tables:
        # to_regclass returns NULL when the table does not exist yet.
        exists = _psql(f"SELECT to_regclass('{table}') IS NOT NULL;")
        if exists.returncode != 0:
            print(f"cannot reach the database:\n{exists.stderr}", file=sys.stderr)
            return 1
        if exists.stdout.strip() != "t":
            print(f"table {table} does not exist (yet) — skipped")
            continue

        result = _psql(
            f"WITH gone AS ("
            f"  DELETE FROM {table}"
            f"  WHERE {column} < NOW() - make_interval(days => {days})"
            f"  RETURNING 1"
            f") SELECT count(*) FROM gone;"
        )
        if result.returncode != 0:
            print(f"purge of {table} failed:\n{result.stderr}", file=sys.stderr)
            failures += 1
            continue
        print(f"purged {result.stdout.strip()} rows from {table} (older than {days} days)")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
