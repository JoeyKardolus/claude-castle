"""Pydantic models for Nextcloud webhook_listeners payloads (Nextcloud 30+).

Shape from nextcloud/server PR #45475 (the PR that shipped webhook_listeners):

write/delete:
    {event: {class, node: {id, path}}, user: {uid, displayName}, time}
rename:
    {event: {class, source: {id, path}, target: {id, path}}, user, time}
"""
from __future__ import annotations

from typing import Union

from pydantic import BaseModel, ValidationError


class NextcloudEventError(ValueError):
    """Payload was malformed or named an event class we don't handle."""


class _Node(BaseModel):
    # `id` is absent on NodeDeletedEvent - the node's already gone by the time
    # the event fires, so Nextcloud doesn't carry an id forward.
    id: int | None = None
    path: str


class _User(BaseModel):
    uid: str
    displayName: str


class NodeWrittenEvent(BaseModel):
    class_: str  # populated from "class" via the mapping below
    node: _Node
    user: _User
    time: int

    @classmethod
    def model_validate(cls, payload: dict) -> "NodeWrittenEvent":
        event_block = payload.get("event") or {}
        return super().model_validate({
            "class_": event_block.get("class"),
            "node": event_block.get("node"),
            "user": payload.get("user"),
            "time": payload.get("time"),
        })


class NodeDeletedEvent(BaseModel):
    class_: str
    node: _Node
    user: _User
    time: int

    @classmethod
    def model_validate(cls, payload: dict) -> "NodeDeletedEvent":
        event_block = payload.get("event") or {}
        return super().model_validate({
            "class_": event_block.get("class"),
            "node": event_block.get("node"),
            "user": payload.get("user"),
            "time": payload.get("time"),
        })


class NodeRenamedEvent(BaseModel):
    class_: str
    source: _Node
    target: _Node
    user: _User
    time: int

    @classmethod
    def model_validate(cls, payload: dict) -> "NodeRenamedEvent":
        event_block = payload.get("event") or {}
        return super().model_validate({
            "class_": event_block.get("class"),
            "source": event_block.get("source"),
            "target": event_block.get("target"),
            "user": payload.get("user"),
            "time": payload.get("time"),
        })


NextcloudEvent = Union[NodeWrittenEvent, NodeDeletedEvent, NodeRenamedEvent]


_EVENT_CLASS_MAP = {
    "OCP\\Files\\Events\\Node\\NodeWrittenEvent": NodeWrittenEvent,
    "OCP\\Files\\Events\\Node\\NodeDeletedEvent": NodeDeletedEvent,
    "OCP\\Files\\Events\\Node\\NodeRenamedEvent": NodeRenamedEvent,
}


def parse_event(payload: dict) -> NextcloudEvent:
    """Dispatch on event.class, return the matching parsed model.

    Raises NextcloudEventError on unknown class or malformed payload.
    """
    event_block = payload.get("event") if isinstance(payload, dict) else None
    if not isinstance(event_block, dict):
        raise NextcloudEventError("missing 'event' object")
    cls_name = event_block.get("class")
    model = _EVENT_CLASS_MAP.get(cls_name)
    if model is None:
        raise NextcloudEventError(f"unsupported event class: {cls_name!r}")
    try:
        return model.model_validate(payload)
    except ValidationError as exc:
        raise NextcloudEventError(f"malformed {cls_name}: {exc}") from exc
