from __future__ import annotations

import json
import os
from pathlib import Path

DEFAULT_CONFIG = {
    "retrieval_provider": "lexical",
    "embedding_model": "qwen3-embedding:0.6b",
    "ollama_url": "http://localhost:11434",
    "chunk_target_chars": 2000,
    "chunk_max_chars": 2600,
    "chunk_overlap_chars": 300,
    "context_modes": {
        "quick": {"top_k": 3, "chunks": 2, "budget_chars": 1600},
        "standard": {"top_k": 5, "chunks": 5, "budget_chars": 2500},
        "deep": {"top_k": 10, "chunks": 6, "budget_chars": 5000}
    },
    "exclude_dirs": [".git", ".obsidian", ".trash", "_lint", "node_modules", "__pycache__"],
    "core_paths": ["MEMORY.md", "AGENT.md", "USER.md", "wiki/AGENT-WIKI-RULES.md"],
    "current_paths": ["wiki/now.md", "wiki/action-items.md", "wiki/decisions.md"]
}


def load_config(vault: Path) -> dict:
    config = json.loads(json.dumps(DEFAULT_CONFIG))
    path = vault / "config" / "mindwell.json"
    if not path.exists():
        path = vault / "config" / "loby.json"
    if path.exists():
        supplied = json.loads(path.read_text(encoding="utf-8"))
        for key, value in supplied.items():
            if isinstance(value, dict) and isinstance(config.get(key), dict):
                config[key].update(value)
            else:
                config[key] = value
    ollama_url = os.environ.get("MINDWELL_OLLAMA_URL") or os.environ.get("LOBY_OLLAMA_URL")
    if ollama_url:
        config["ollama_url"] = ollama_url
    return config


def index_path(vault: Path) -> Path:
    override = os.environ.get("MINDWELL_INDEX") or os.environ.get("LOBY_INDEX")
    if override:
        return Path(override)
    key = __import__("hashlib").sha256(str(vault.resolve()).encode()).hexdigest()[:16]
    if os.name == "nt":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "mindwell"
    else:
        root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "mindwell"
    root.mkdir(parents=True, exist_ok=True)
    return root / f"{key}.db"
