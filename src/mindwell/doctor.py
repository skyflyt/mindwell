from __future__ import annotations

import json
import sqlite3
import sys
import urllib.request
import os
from pathlib import Path

from . import __version__
from .config import index_path, load_config


def inspect(vault: Path) -> dict:
    config = load_config(vault)
    installation_path = vault / "config" / "installation.json"
    try:
        installation = json.loads(installation_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        installation = {}
    checks = {
        "python": {"ok": sys.version_info >= (3, 11), "value": sys.version.split()[0]},
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
        con.execute("CREATE VIRTUAL TABLE test_fts USING fts5(body)")
        checks["sqlite_fts5"] = {"ok": True, "value": sqlite3.sqlite_version}
    except sqlite3.OperationalError as exc:
        checks["sqlite_fts5"] = {"ok": False, "value": str(exc)}
    try:
        with urllib.request.urlopen(config["ollama_url"].rstrip("/") + "/api/tags",
                                    timeout=2) as response:
            models = [item.get("name", "") for item in json.loads(response.read()).get("models", [])]
        checks["ollama"] = {"ok": True, "value": models}
    except OSError as exc:
        checks["ollama"] = {"ok": False, "value": str(exc)}
    provider_ready = (config["retrieval_provider"] == "lexical" or checks["ollama"]["ok"])
    warnings = [key for key in ("installation", "version_match", "core_contract", "index")
                if not checks[key]["ok"]]
    return {"ready": all(checks[key]["ok"] for key in ("python", "vault", "config", "vault_writable", "sqlite_fts5"))
                     and provider_ready,
            "provider": config["retrieval_provider"], "checks": checks,
            "warnings": warnings,
            "recommendation": ("ready for zero-dependency lexical retrieval"
                               if config["retrieval_provider"] == "lexical"
                               else "Ollama is required for the selected provider")}
