"""Pins: the orphan-recovery UPDATE casts its bound id array to uuid[].

notulen_jobs.id is UUID. The orphan list is built from str()'d ids, so the
bound parameter is a text[]. Without an explicit `::uuid[]` cast Postgres
raises "operator does not exist: uuid = text" inside the FastAPI startup
hook, which crash-loops the whole dashboard whenever an orphan row exists
(2026-06-18 incident). This is a real-Postgres-only failure, so we pin it
at the SQL level with a fake connection.
"""

from __future__ import annotations

import apps.notulen.app.core.sessions.recovery as recovery


class _FakeCursor:
    def __init__(self, select_rows):
        self._select_rows = select_rows
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchall(self):
        return self._select_rows


class _FakeConn:
    def __init__(self, select_rows):
        self.cursors = [_FakeCursor(select_rows), _FakeCursor(select_rows)]
        self._i = 0
        self.committed = False

    def cursor(self):
        cur = self.cursors[self._i]
        self._i += 1
        return cur

    def commit(self):
        self.committed = True

    def close(self):
        pass


def test_update_casts_orphan_ids_to_uuid_array(monkeypatch):
    orphan_id = "1ad0d603-1de1-4b7f-a5bf-6ad8bda94293"
    fake = _FakeConn(select_rows=[(orphan_id,)])

    monkeypatch.setattr(recovery, "get_db", lambda: fake)
    monkeypatch.setattr(recovery, "ensure_jobs_table", lambda conn: None)
    # All candidates are orphaned (no live K8s job).
    monkeypatch.setattr(recovery, "_live_k8s_job_ids", lambda candidates: set())

    recovery.recover_interrupted_jobs()

    update_sql, params = fake.cursors[1].executed[0]
    assert "UPDATE notulen_jobs" in update_sql
    assert "%s::uuid[]" in update_sql, "orphan id array must be cast to uuid[]"
    assert params == ([orphan_id],)
    assert fake.committed
