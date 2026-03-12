"""CLI for data-utils — parse files and build JSONL."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from data_utils.build import build_jsonl, watch_and_build
from data_utils.parser import parse
from data_utils.serialization import to_dict


def _detect_type(suffix: str) -> str:
    s = suffix.lstrip(".").lower()
    return {"yml": "yaml", "yaml": "yaml", "mermaid": "mermaid", "mmd": "mermaid"}.get(s, "md")


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print("Usage:")
        print("  data-utils parse <file>                 Parse file to fragment JSON")
        print("  data-utils build <dir> [-o out.jsonl]    Build sequences.jsonl")
        print("  data-utils watch <dir> [-o out.jsonl]    Watch + rebuild on changes")
        return

    cmd = args[0]

    if cmd == "parse" and len(args) >= 2:
        p = Path(args[1])
        file_type = _detect_type(p.suffix)
        frags = parse(p.read_text(), file_type)
        print(json.dumps(to_dict(frags), indent=2))

    elif cmd in ("build", "watch") and len(args) >= 2:
        root = Path(args[1])
        out = Path("sequences.jsonl")
        if "-o" in args:
            idx = args.index("-o")
            if idx + 1 < len(args):
                out = Path(args[idx + 1])

        if cmd == "build":
            build_jsonl(root, out)
        else:
            watch_and_build(root, out)
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
