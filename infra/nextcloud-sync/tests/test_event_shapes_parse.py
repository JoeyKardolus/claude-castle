"""Pydantic models parse the three Nextcloud webhook_listeners event types.

Fixtures match the shape in nextcloud/server PR #45475 (the PR that shipped
webhook_listeners in Nextcloud 30):

write/delete:
    {event: {class, node: {id, path}}, user: {uid, displayName}, time}
rename:
    {event: {class, source: {id, path}, target: {id, path}}, user, time}
"""
from __future__ import annotations

import pytest

from nextcloud_sync.events import (
    NextcloudEventError,
    NodeDeletedEvent,
    NodeRenamedEvent,
    NodeWrittenEvent,
    parse_event,
)


WRITE_PAYLOAD = {
    "event": {
        "class": "OCP\\Files\\Events\\Node\\NodeWrittenEvent",
        "node": {"id": 185, "path": "/alice/files/Sync/notes.md"},
    },
    "user": {"uid": "alice", "displayName": "Alice"},
    "time": 1717425671,
}


DELETE_PAYLOAD = {
    "event": {
        "class": "OCP\\Files\\Events\\Node\\NodeDeletedEvent",
        "node": {"id": 200, "path": "/alice/files/Sync/drafts/old.md"},
    },
    "user": {"uid": "alice", "displayName": "Alice"},
    "time": 1717425700,
}


RENAME_PAYLOAD = {
    "event": {
        "class": "OCP\\Files\\Events\\Node\\NodeRenamedEvent",
        "source": {"id": 210, "path": "/alice/files/Sync/drafts/draft.md"},
        "target": {"id": 210, "path": "/alice/files/Sync/final/draft.md"},
    },
    "user": {"uid": "alice", "displayName": "Alice"},
    "time": 1717425800,
}


def test_parse_write_event():
    event = parse_event(WRITE_PAYLOAD)
    assert isinstance(event, NodeWrittenEvent)
    assert event.node.path == "/alice/files/Sync/notes.md"
    assert event.user.uid == "alice"
    assert event.time == 1717425671


def test_parse_delete_event():
    event = parse_event(DELETE_PAYLOAD)
    assert isinstance(event, NodeDeletedEvent)
    assert event.node.id == 200


def test_parse_rename_event():
    event = parse_event(RENAME_PAYLOAD)
    assert isinstance(event, NodeRenamedEvent)
    assert event.source.path.endswith("draft.md")
    assert event.target.path.endswith("final/draft.md")


def test_unknown_event_class_raises():
    payload = dict(WRITE_PAYLOAD)
    payload["event"] = dict(payload["event"])
    payload["event"]["class"] = "OCP\\Some\\Other\\Event"
    with pytest.raises(NextcloudEventError):
        parse_event(payload)


def test_malformed_payload_raises():
    with pytest.raises(NextcloudEventError):
        parse_event({"not": "an event"})
