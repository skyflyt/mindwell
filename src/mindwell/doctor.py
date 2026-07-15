from __future__ import annotations

import json
import sqlite3
import sys
import urllib.request
import os
from pathlib import Path

from . import __version__
from .config import index_path, load_config
from .guidance import non_local_ollama_caveat, ollama_unreachable_guidance

REQUIRED_CHECKS = ("python", "vault", "config", "vault_writable", "sqlite_fts5")


def inspect(vault: Path) -> dict:
    config = load_config(vault)
    installation_path = vault / "config" / "installation.json"
    try:
        installation = json.loads(installation_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        installation = {}
    checks = {
        "python": {"ok": sys.version_info >= (3, 10), "value": sys.version.split()[0]},
        "vault": {"ok": vault.is_dir(), "value": str(vault)},
        "config": {"ok": ((vault / "config" / "mindwell.json").exists()
                           or (vault / "config" / "loby.json").exists()),
                   "value": config["retrieval_provider"]},
        "vault_writable": {"ok": vault.is_dir() and os.access(vault, os.W_OK),
                           "value": str(vault)},
        "installation": {"ok": bool(installation),
                         "value": installation.get("mindwell_version", "unrecorded")},
        "version_match": {"ok": (not installation or
                                  installation.get("mindwell_version") == __version__),
                          "value": {"installed": __version__,
                                    "vault": installation.get("mindwell_version", "unrecorded")}},
        "core_contract": {"ok": all((vault / name).exists() for name in
                                     ("AGENTS.md", "AGENT.md", "USER.md", "MEMORY.md")),
                          "value": "AGENTS.md, AGENT.md, USER.md, MEMORY.md"},
        "index": {"ok": index_path(vault).exists(), "value": str(index_path(vault))},
    }
    try:
        con = sqlite3.connect(":memory:")
        try:
            con.execute("CREATE VIRTUAL TABLE test_fts USING fts5(body)")
            checks["sqlite_fts5"] = {"ok": True, "value": sqlite3.sqlite_version}
        finally:
            con.close()
    except sqlite3.OperationalError as exc:
        checks["sqlite_fts5"] = {"ok": False, "value": str(exc)}

    provider = config["retrieval_provider"]
    ollama_reachable = None
    if provider == "ollama":
        try:
            with urllib.request.urlopen(config["ollama_url"].rstrip("/") + "/api/tags",
                                        timeout=2) as response:
                models = [item.get("name", "") for item in json.loads(response.read()).get("models", [])]
            checks["ollama"] = {"ok": True, "value": models}
            ollama_reachable = True
        except OSError as exc:
            checks["ollama"] = {"ok": False, "value": str(exc)}
            ollama_reachable = False
    else:
        # Lexical installs never need Ollama. Probing it anyway produced a
        # perpetual "ok": false entry that made lexical-only doctor reports
        # look broken every time they were scanned for failures.
        checks["ollama"] = {"ok": True, "skipped": True,
                            "value": "skipped (provider: lexical)"}

    required_ok = all(checks[key]["ok"] for key in REQUIRED_CHECKS)
    provider_ready = provider == "lexical" or ollama_reachable is True
    ready = required_ok and provider_ready
    warnings = [key for key in ("installation", "version_match", "core_contract", "index")
                if not checks[key]["ok"]]

    result = {
        "ready": ready,
        "provider": provider,
        "checks": checks,
        "warnings": warnings,
    }

    if not required_ok:
        failing = [key for key in REQUIRED_CHECKS if not checks[key]["ok"]]
        result["mode"] = "blocked"
        result["recommendation"] = f"not ready: fix {', '.join(failing)} before retrieval will work"
    elif provider == "lexical":
        result["mode"] = "lexical"
        result["recommendation"] = "ready for zero-dependency lexical retrieval"
    elif ollama_reachable:
        result["mode"] = "semantic"
        result["recommendation"] = "ready for semantic retrieval via Ollama"
        caveat = non_local_ollama_caveat(config["ollama_url"])
        if caveat:
            result["security_notice"] = caveat
    else:
        result["mode"] = "semantic-unreachable"
        guidance = ollama_unreachable_guidance(vault, config["ollama_url"])
        result["recommendation"] = (
            guidance["summary"] +
            f' Run `mindwell configure "{vault}" --provider lexical` to use lexical '
            "retrieval here, or see 'guidance' for the native steps to restore semantic."
        )
        result["guidance"] = guidance["guidance"]

    return result
