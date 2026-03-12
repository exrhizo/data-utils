"""Serialize Fragment lists to/from JSON-compatible dicts."""

from __future__ import annotations

import json

from data_utils.fragment import Fragment, FragmentType


def to_dict(fragments: list[Fragment]) -> list[dict]:
    """Convert fragments to JSON-serializable dicts."""
    return [
        {
            "id": f.id,
            "type": f.type.value,
            "content": f.content,
            "line_start": f.line_start,
            "line_end": f.line_end,
            "level": f.level,
            "lang": f.lang,
            "meta": f.meta,
        }
        for f in fragments
    ]


def from_dict(data: list[dict]) -> list[Fragment]:
    """Reconstruct fragments from dicts."""
    return [
        Fragment(
            id=d["id"],
            type=FragmentType(d["type"]),
            content=d["content"],
            line_start=d["line_start"],
            line_end=d["line_end"],
            level=d.get("level", 0),
            lang=d.get("lang", ""),
            meta=d.get("meta", {}),
        )
        for d in data
    ]


def to_json(fragments: list[Fragment], **kwargs) -> str:
    """Serialize fragments to JSON string."""
    return json.dumps(to_dict(fragments), **kwargs)


def from_json(text: str) -> list[Fragment]:
    """Deserialize fragments from JSON string."""
    return from_dict(json.loads(text))
