"""Parse text into typed Fragment blocks.

Three file types supported:
- markdown: frontmatter, headings, paragraphs, code blocks, mermaid, lists, hrs, footnotes
- yaml: whole file as single yaml_block
- mermaid: strip frontmatter + split diagrams (ported from heart/mermaid_lint.py)
"""

from __future__ import annotations

import re

import yaml

from data_utils.fragment import Fragment, FragmentType
from data_utils.identifiers import fragment_id

# --- Mermaid helpers (ported from heart/mermaid_lint.py) ---

_DIAGRAM_KEYWORDS = re.compile(
    r"^(graph|flowchart|sequenceDiagram|classDiagram|stateDiagram|erDiagram|"
    r"gantt|pie|gitgraph|mindmap|timeline|sankey|xychart|block|journey|quadrant)"
    r"(\s|$)",
    re.MULTILINE,
)


def _strip_frontmatter(text: str) -> tuple[str, str | None]:
    """Remove YAML frontmatter. Returns (body, frontmatter_raw|None)."""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            fm = text[3:end].strip()
            body = text[end + 4:]
            return body, fm
    return text, None


def _split_diagrams(text: str) -> list[str]:
    """Split mermaid text with multiple diagrams into individual strings."""
    starts = [m.start() for m in _DIAGRAM_KEYWORDS.finditer(text)]
    if not starts:
        return [text] if text.strip() else []
    diagrams = []
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(text)
        chunk = text[start:end].strip()
        if chunk:
            diagrams.append(chunk)
    return diagrams


# --- Footnote pattern ---
# [^ref_id]: comment text
# [^ref_id]: comment text -- by:author
_FOOTNOTE_RE = re.compile(
    r"^\[\^([^\]]+)\]:\s*(.+?)(?:\s*--\s*by:(\S+))?\s*$"
)


# --- Main parser ---

def parse(text: str, file_type: str = "md") -> list[Fragment]:
    """Parse text into a list of Fragment objects.

    file_type: "md", "yaml"/"yml", or "mermaid"/"mmd"
    """
    if file_type in ("yaml", "yml"):
        return _parse_yaml(text)
    if file_type in ("mermaid", "mmd"):
        return _parse_mermaid(text)
    return _parse_markdown(text)


def _parse_yaml(text: str) -> list[Fragment]:
    """Whole file as a single yaml_block fragment."""
    if not text.strip():
        return []
    return [Fragment(
        id=fragment_id(1, text),
        type=FragmentType.yaml_block,
        content=text,
        line_start=1,
        line_end=text.count("\n") + 1,
    )]


def _parse_mermaid(text: str) -> list[Fragment]:
    """Strip frontmatter, split diagrams into fragments."""
    fragments: list[Fragment] = []
    body, fm_raw = _strip_frontmatter(text)

    if fm_raw is not None:
        fm_lines = text.count("\n", 0, text.find("\n---", 3) + 4) + 1
        meta = {}
        try:
            parsed = yaml.safe_load(fm_raw)
            if isinstance(parsed, dict):
                meta = parsed
        except yaml.YAMLError:
            pass
        fragments.append(Fragment(
            id=fragment_id(1, fm_raw),
            type=FragmentType.frontmatter,
            content=fm_raw,
            line_start=1,
            line_end=fm_lines,
            meta=meta,
        ))

    diagrams = _split_diagrams(body)
    # Approximate line offsets
    offset = (fragments[-1].line_end + 1) if fragments else 1
    for diagram in diagrams:
        line_count = diagram.count("\n") + 1
        fragments.append(Fragment(
            id=fragment_id(offset, diagram),
            type=FragmentType.mermaid,
            content=diagram,
            line_start=offset,
            line_end=offset + line_count - 1,
        ))
        offset += line_count

    return fragments


def _parse_markdown(text: str) -> list[Fragment]:
    """Parse markdown into fragments."""
    fragments: list[Fragment] = []
    lines = text.split("\n")
    i = 0
    n = len(lines)

    # --- Frontmatter ---
    if lines and lines[0].strip() == "---":
        end_idx = None
        for j in range(1, n):
            if lines[j].strip() == "---":
                end_idx = j
                break
        if end_idx is not None:
            fm_content = "\n".join(lines[1:end_idx])
            meta = {}
            try:
                parsed = yaml.safe_load(fm_content)
                if isinstance(parsed, dict):
                    meta = parsed
            except yaml.YAMLError:
                pass
            fragments.append(Fragment(
                id=fragment_id(1, fm_content),
                type=FragmentType.frontmatter,
                content=fm_content,
                line_start=1,
                line_end=end_idx + 1,
                meta=meta,
            ))
            i = end_idx + 1

    while i < n:
        line = lines[i]
        line_num = i + 1  # 1-based

        # Blank line — skip
        if line.strip() == "":
            i += 1
            continue

        # Footnote: [^ref]: text -- by:author
        fn_match = _FOOTNOTE_RE.match(line)
        if fn_match:
            ref, body, by = fn_match.groups()
            meta: dict = {"ref": ref}
            if by:
                meta["by"] = by
            fragments.append(Fragment(
                id=fragment_id(line_num, line),
                type=FragmentType.footnote,
                content=body,
                line_start=line_num,
                line_end=line_num,
                meta=meta,
            ))
            i += 1
            continue

        # Horizontal rule
        if re.match(r"^---+\s*$", line) or re.match(r"^\*\*\*+\s*$", line):
            fragments.append(Fragment(
                id=fragment_id(line_num, line),
                type=FragmentType.hr,
                content=line,
                line_start=line_num,
                line_end=line_num,
            ))
            i += 1
            continue

        # Heading
        heading_match = re.match(r"^(#{1,6})\s+(.+)", line)
        if heading_match:
            level = len(heading_match.group(1))
            fragments.append(Fragment(
                id=fragment_id(line_num, line),
                type=FragmentType.heading,
                content=heading_match.group(2),
                line_start=line_num,
                line_end=line_num,
                level=level,
            ))
            i += 1
            continue

        # Code block
        if line.startswith("```"):
            lang = line[3:].strip()
            code_lines: list[str] = []
            i += 1
            while i < n and not lines[i].startswith("```"):
                code_lines.append(lines[i])
                i += 1
            end_line = i + 1  # include closing ```
            i += 1  # skip closing ```

            content = "\n".join(code_lines)
            ftype = FragmentType.mermaid if lang == "mermaid" else FragmentType.code_block

            fragments.append(Fragment(
                id=fragment_id(line_num, content),
                type=ftype,
                content=content,
                line_start=line_num,
                line_end=end_line,
                lang=lang,
            ))
            continue

        # List block — collect consecutive list items
        if re.match(r"^\s*[-*+]\s", line) or re.match(r"^\s*\d+\.\s", line):
            list_lines = [line]
            i += 1
            while i < n and (
                re.match(r"^\s*[-*+]\s", lines[i])
                or re.match(r"^\s*\d+\.\s", lines[i])
                or (lines[i].startswith("  ") and list_lines)  # continuation
            ):
                list_lines.append(lines[i])
                i += 1
            content = "\n".join(list_lines)
            fragments.append(Fragment(
                id=fragment_id(line_num, content),
                type=FragmentType.list_block,
                content=content,
                line_start=line_num,
                line_end=line_num + len(list_lines) - 1,
            ))
            continue

        # Paragraph — collect consecutive non-special lines
        para_lines = [line]
        i += 1
        while (
            i < n
            and lines[i].strip() != ""
            and not lines[i].startswith("#")
            and not lines[i].startswith("```")
            and not re.match(r"^---+\s*$", lines[i])
            and not re.match(r"^\s*[-*+]\s", lines[i])
            and not re.match(r"^\s*\d+\.\s", lines[i])
            and not _FOOTNOTE_RE.match(lines[i])
        ):
            para_lines.append(lines[i])
            i += 1
        content = "\n".join(para_lines)
        fragments.append(Fragment(
            id=fragment_id(line_num, content),
            type=FragmentType.paragraph,
            content=content,
            line_start=line_num,
            line_end=line_num + len(para_lines) - 1,
        ))

    return fragments
