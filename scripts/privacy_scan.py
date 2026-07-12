#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PATTERNS = {
    "credential": re.compile(r"(?i)(api[_ -]?key|password|secret|token)\s*[:=]\s*['\"]?[A-Za-z0-9_/+.-]{12,}"),
    "email": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    "windows-user-path": re.compile(r"(?i)C:\\Users\\(?!example|yourname)[^\\\s]+"),
    "private-ip": re.compile(r"\b(?:10\.|192\.168\.|172\.(?:1[6-9]|2\d|3[01])\.)\d{1,3}\.\d{1,3}\b"),
}
ALLOW = {"security@example.com"}
SKIP = {".git", ".venv", "__pycache__", "dist", "build"}


def scan(root: Path) -> list[str]:
    findings = []
    for path in root.rglob("*"):
        if not path.is_file() or any(part in SKIP for part in path.parts): continue
        try: text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError): continue
        for name, pattern in PATTERNS.items():
            for match in pattern.finditer(text):
                if match.group(0) in ALLOW: continue
                if name == "credential" and (re.search(r"\b(?:lease|self)\.token\b", match.group(0))
                                             or any(code_word in match.group(0)
                                                    for code_word in (".unlink", ".get", "os.environ"))):
                    continue
                line = text.count("\n", 0, match.start()) + 1
                findings.append(f"{path.relative_to(root)}:{line}: {name}")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("root", type=Path, nargs="?", default=Path(".")); args = parser.parse_args()
    findings = scan(args.root)
    print("\n".join(findings) if findings else "privacy scan: clean")
    return 1 if findings else 0


if __name__ == "__main__": raise SystemExit(main())
