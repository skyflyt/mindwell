from __future__ import annotations

import re
from pathlib import Path

HEADER = re.compile(r"^> \[!(contradiction|gap)\](?:\s+(.+))?$", re.I)
FIELD = re.compile(r"^>\s*(claim|sources|status|owner|review):\s*(.*)$", re.I)


def scan(vault: Path) -> list[dict]:
    found = []
    for path in (vault / "wiki").rglob("*.md"):
        if path.name == "contradictions.md": continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for index, line in enumerate(lines):
            match = HEADER.match(line)
            if not match: continue
            fields = {"claim": "", "sources": "", "status": "open", "owner": "", "review": ""}
            cursor = index + 1
            while cursor < len(lines) and lines[cursor].startswith(">"):
                field = FIELD.match(lines[cursor])
                if field: fields[field.group(1).lower()] = field.group(2).strip()
                cursor += 1
            found.append({"kind": match.group(1).lower(), "title": match.group(2) or "Untitled",
                          "page": path.relative_to(vault).as_posix(), "line": index + 1, **fields})
    return found


def compile_registry(vault: Path) -> Path:
    items = scan(vault)
    lines = ["# Contradictions and evidence gaps", "", "Generated from source-linked callouts.", "", "## Open", ""]
    open_items = [item for item in items if item["status"] == "open"]
    if not open_items: lines.append("_no open items_")
    for item in open_items:
        lines += [f"### {item['title']}", "", f"- Type: `{item['kind']}`",
                  f"- Claim: {item['claim']}", f"- Sources: {item['sources']}",
                  f"- Origin: [[{item['page'][:-3]}]] line {item['line']}",
                  f"- Owner: {item['owner'] or '_unassigned_'}",
                  f"- Review: {item['review'] or '_unscheduled_'}", ""]
    output = vault / "wiki" / "contradictions.md"
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output
