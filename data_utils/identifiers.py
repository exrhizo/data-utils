"""Stable fragment ID generation."""

from __future__ import annotations

import hashlib


def fragment_id(line_start: int, content: str) -> str:
    """Generate a stable, file-scoped fragment ID.

    Format: "{line_start}:{sha256(content)[:8]}"
    """
    h = hashlib.sha256(content.encode()).hexdigest()[:8]
    return f"{line_start}:{h}"
