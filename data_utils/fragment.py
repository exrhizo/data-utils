"""Fragment dataclass and FragmentType enum."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class FragmentType(str, Enum):
    frontmatter = "frontmatter"
    heading = "heading"
    paragraph = "paragraph"
    code_block = "code_block"
    mermaid = "mermaid"
    yaml_block = "yaml_block"
    list_block = "list"
    hr = "hr"
    footnote = "footnote"


@dataclass
class Fragment:
    id: str  # "{line_start}:{content_sha256[:8]}"
    type: FragmentType
    content: str  # raw text
    line_start: int  # 1-based
    line_end: int
    level: int = 0  # heading level (1-6), 0 otherwise
    lang: str = ""  # code block language
    meta: dict = field(default_factory=dict)
