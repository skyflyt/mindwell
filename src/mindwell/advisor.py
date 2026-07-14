from __future__ import annotations

import json
import sqlite3
import sys
import urllib.request
from pathlib import Path

from . import __version__


def _ollama_available() -> tuple[bool, str]:
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2) as response:
            models = [item.get("name", "") for item in
                      json.loads(response.read()).get("models", [])]
        return True, ", ".join(models) if models else "running; no models installed"
    except OSError as exc:
        return False, str(exc)


def recommend(vault: Path, prefer_semantic: bool = False,
              basic: bool = False) -> dict:
    vault = vault.expanduser().resolve()
    exists = vault.exists()
    has_content = exists and any(vault.iterdir())
    has_markdown = exists and any(vault.rglob("*.md"))
    if has_content:
        track = "existing-vault"
        profile = "personal-ops" if not basic else "basic"
    else:
        track = "basic-framework" if basic else "personal-ops"
        profile = "basic" if basic else "personal-ops"

    try:
        con = sqlite3.connect(":memory:")
        con.execute("CREATE VIRTUAL TABLE test_fts USING fts5(body)")
        con.close()
        fts5 = True
    except sqlite3.OperationalError:
        fts5 = False
    ollama_ok, ollama_value = _ollama_available() if prefer_semantic else (False, "not checked")
    provider = "ollama" if prefer_semantic and ollama_ok else "lexical"

    init = (f'mindwell init "{vault}" --profile {profile} '
            f'--automations {"core" if profile == "personal-ops" else "none"} '
            '--timezone local')
    commands = [init, f'mindwell index "{vault}"', f'mindwell doctor "{vault}"']
    if provider == "ollama":
        commands.insert(1, f'mindwell configure "{vault}" --provider ollama')
        commands[2] += " --rebuild"
    warnings = []
    if track == "existing-vault":
        warnings.append("Back up the vault, show the proposed additions, and ask before init.")
    if prefer_semantic and not ollama_ok:
        warnings.append("Semantic retrieval was requested but Ollama is unavailable; use lexical retrieval.")
    if not fts5:
        warnings.append("This Python build lacks SQLite FTS5; IT must provide a compatible Python build.")

    return {
        "mindwell_version": __version__,
        "recommendation": {
            "track": track,
            "profile": profile,
            "provider": provider,
            "requires_admin": False,
            "reason": ("Preserve and extend the existing Markdown vault non-destructively."
                       if track == "existing-vault" else
                       "Use the ready-to-work personal second-brain profile."
                       if track == "personal-ops" else
                       "Use the minimal framework for a custom or developer-managed system."),
        },
        "checks": {
            "python": {"ok": sys.version_info >= (3, 11), "value": sys.version.split()[0]},
            "sqlite_fts5": {"ok": fts5},
            "destination": {"exists": exists, "has_content": has_content,
                            "has_markdown": has_markdown, "value": str(vault)},
            "ollama": {"ok": ollama_ok, "value": ollama_value},
        },
        "commands": commands,
        "warnings": warnings,
    }
