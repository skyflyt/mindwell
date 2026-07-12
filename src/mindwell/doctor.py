from __future__ import annotations

import json
import sqlite3
import sys
import urllib.request
from pathlib import Path

from .config import load_config


def inspect(vault: Path) -> dict:
    config = load_config(vault)
    checks = {
        "python": {"ok": sys.version_info >= (3, 11), "value": sys.version.split()[0]},
        "vault": {"ok": vault.is_dir(), "value": str(vault)},
        "config": {"ok": ((vault / "config" / "mindwell.json").exists()
                           or (vault / "config" / "loby.json").exists()),
                   "value": config["retrieval_provider"]},
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
    return {"ready": all(checks[key]["ok"] for key in ("python", "vault", "config", "sqlite_fts5"))
                     and provider_ready,
            "provider": config["retrieval_provider"], "checks": checks,
            "recommendation": ("ready for zero-dependency lexical retrieval"
                               if config["retrieval_provider"] == "lexical"
                               else "Ollama is required for the selected provider")}
