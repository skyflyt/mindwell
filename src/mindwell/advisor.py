from __future__ import annotations

import json
import re
import sqlite3
import sys
import urllib.request
from pathlib import Path

from . import __version__
from .config import load_config
from .guidance import non_local_ollama_caveat, ollama_unreachable_guidance


def _ollama_available(url: str) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(url.rstrip("/") + "/api/tags", timeout=2) as response:
            models = [item.get("name", "") for item in
                      json.loads(response.read()).get("models", [])]
        return True, ", ".join(models) if models else "running; no models installed"
    except OSError as exc:
        return False, str(exc)


def _version_tuple(value: str) -> tuple[int, ...]:
    return tuple(int(match.group()) for match in re.finditer(r"\d+", str(value)))


def recommend(vault: Path, prefer_semantic: bool = False,
              basic: bool = False) -> dict:
    vault = vault.expanduser().resolve()
    config = load_config(vault)
    exists = vault.exists()
    has_content = exists and any(vault.iterdir())
    has_markdown = exists and any(vault.rglob("*.md"))
    if has_content:
        track = "existing-vault"
        profile = "personal-ops" if not basic else "basic"
    else:
        track = "basic-framework" if basic else "personal-ops"
        profile = "basic" if basic else "personal-ops"

    installation = None
    install_path = vault / "config" / "installation.json"
    if install_path.exists():
        try:
            installation = json.loads(install_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            installation = None
    vault_version = installation.get("mindwell_version") if installation else None
    is_mindwell_vault = track == "existing-vault" and installation is not None
    needs_upgrade = bool(vault_version and _version_tuple(vault_version) < _version_tuple(__version__))

    try:
        con = sqlite3.connect(":memory:")
        con.execute("CREATE VIRTUAL TABLE test_fts USING fts5(body)")
        con.close()
        fts5 = True
    except sqlite3.OperationalError:
        fts5 = False
    ollama_url = config["ollama_url"]
    ollama_ok, ollama_value = _ollama_available(ollama_url) if prefer_semantic else (False, "not checked")
    provider = "ollama" if prefer_semantic and ollama_ok else "lexical"

    if is_mindwell_vault:
        commands = [f'mindwell upgrade "{vault}"', f'mindwell doctor "{vault}"']
    else:
        init = (f'mindwell init "{vault}" --profile {profile} '
                f'--automations {"core" if profile == "personal-ops" else "none"} '
                '--timezone local')
        commands = [init, f'mindwell index "{vault}"', f'mindwell doctor "{vault}"']
        if provider == "ollama":
            commands.insert(1, f'mindwell configure "{vault}" --provider ollama')
            commands[2] += " --rebuild"
    python_ok = sys.version_info >= (3, 10)
    warnings = []
    guidance = None
    if is_mindwell_vault:
        if needs_upgrade:
            warnings.append(
                f"This vault is on Mindwell {vault_version}; the installed CLI is "
                f"{__version__}. Use `mindwell upgrade \"{vault}\"` to reconcile it "
                "safely - it never overwrites AGENTS.md or a customized scaffold file, "
                "unlike `init --force`. Show the change summary and get approval "
                "before running it."
            )
        else:
            warnings.append(
                f"Vault is already on {vault_version}. `mindwell upgrade \"{vault}\"` "
                "remains safe to run as a no-op health/repair check."
            )
    elif track == "existing-vault":
        warnings.append("Back up the vault, show the proposed additions, and ask before init.")
    if not python_ok:
        warnings.append(
            f"Python {sys.version.split()[0]} is older than the required 3.10; "
            "upgrade or provide a compatible interpreter before installing."
        )
    if prefer_semantic and not ollama_ok:
        guidance = ollama_unreachable_guidance(vault, ollama_url)
        warnings.append(
            "Semantic retrieval was requested but Ollama is unavailable; using lexical "
            "retrieval instead. If you are running in a sandbox or container isolated "
            "from the user's machine, semantic retrieval must run natively on the "
            "machine where Ollama is installed - see 'ollama_guidance' for exact steps "
            "to present to the user."
        )
    if not fts5:
        warnings.append("This Python build lacks SQLite FTS5; IT must provide a compatible Python build.")
    if provider == "ollama":
        caveat = non_local_ollama_caveat(ollama_url)
        if caveat:
            warnings.append(caveat)

    result = {
        "mindwell_version": __version__,
        "recommendation": {
            "track": track,
            "profile": profile,
            "provider": provider,
            "requires_admin": False,
            "reason": ("Reconcile the existing Mindwell vault to the installed version "
                       "without overwriting your customizations."
                       if is_mindwell_vault else
                       "Preserve and extend the existing Markdown vault non-destructively."
                       if track == "existing-vault" else
                       "Use the ready-to-work personal second-brain profile."
                       if track == "personal-ops" else
                       "Use the minimal framework for a custom or developer-managed system."),
        },
        "checks": {
            "python": {"ok": python_ok, "value": sys.version.split()[0]},
            "sqlite_fts5": {"ok": fts5},
            "destination": {"exists": exists, "has_content": has_content,
                            "has_markdown": has_markdown, "value": str(vault)},
            "ollama": {"ok": ollama_ok, "value": ollama_value},
            "installation": {"managed": is_mindwell_vault, "vault_version": vault_version,
                             "needs_upgrade": needs_upgrade},
        },
        "commands": commands,
        "warnings": warnings,
    }
    if guidance is not None:
        result["ollama_guidance"] = guidance["guidance"]
    return result
