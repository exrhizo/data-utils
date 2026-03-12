"""Build sequences.jsonl from a directory of markdown files.

Scans a directory, parses each file into fragments, writes one JSON line per file.
Supports incremental builds via mtime cache and a --watch mode for dev.

Usage (as library):
    from data_utils.build import build_jsonl
    build_jsonl(Path("vault/"), Path("out/sequences.jsonl"))

Usage (CLI via data-utils or heart):
    data-utils build /path/to/vault -o sequences.jsonl --watch
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

from data_utils.parser import parse
from data_utils.serialization import to_dict


def _detect_type(suffix: str) -> str:
    s = suffix.lstrip(".").lower()
    return {"yml": "yaml", "yaml": "yaml", "mermaid": "mermaid", "mmd": "mermaid"}.get(s, "md")


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def scan_files(root: Path, extensions: tuple[str, ...] = (".md",)) -> list[Path]:
    """Recursively find files with given extensions under root."""
    files = []
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            if name.startswith("."):
                continue
            if any(name.endswith(ext) for ext in extensions):
                files.append(Path(dirpath) / name)
    return sorted(files)


def parse_file(path: Path, root: Path) -> dict:
    """Parse a single file and return a serializable record."""
    rel = path.relative_to(root).as_posix()
    text = path.read_text(errors="replace")
    file_type = _detect_type(path.suffix)
    fragments = parse(text, file_type)
    return {
        "path": rel,
        "file_type": file_type,
        "fragments": to_dict(fragments),
        "hash": _file_hash(path),
    }


def build_jsonl(
    root: Path,
    output: Path,
    extensions: tuple[str, ...] = (".md",),
    cache: dict[str, str] | None = None,
) -> dict[str, str]:
    """Build sequences.jsonl from directory.

    Args:
        root: directory to scan
        output: path to write sequences.jsonl
        extensions: file extensions to include
        cache: {rel_path: hash} from previous build, for incremental

    Returns:
        Updated cache dict
    """
    files = scan_files(root, extensions)
    new_cache: dict[str, str] = {}

    # Load existing records if doing incremental
    existing: dict[str, str] = {}  # rel_path -> json_line
    if cache and output.exists():
        with output.open("r") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    existing[rec["path"]] = line.rstrip("\n")
                except (json.JSONDecodeError, KeyError):
                    continue

    output.parent.mkdir(parents=True, exist_ok=True)
    dirty = 0
    with output.open("w") as f:
        for path in files:
            rel = path.relative_to(root).as_posix()
            h = _file_hash(path)
            new_cache[rel] = h

            if cache and rel in cache and cache[rel] == h and rel in existing:
                # Unchanged — reuse existing line
                f.write(existing[rel] + "\n")
            else:
                # Parse and write
                try:
                    rec = parse_file(path, root)
                    f.write(json.dumps(rec) + "\n")
                    dirty += 1
                except Exception as e:
                    print(f"  error parsing {rel}: {e}")

    print(f"Built {output}: {len(files)} files, {dirty} parsed")
    return new_cache


def watch_and_build(
    root: Path,
    output: Path,
    interval: float = 2.0,
    extensions: tuple[str, ...] = (".md",),
) -> None:
    """Watch directory and rebuild on changes. Blocking."""
    cache: dict[str, str] = {}
    print(f"Watching {root} -> {output} (every {interval}s)")
    try:
        while True:
            cache = build_jsonl(root, output, extensions, cache)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopped watching.")
