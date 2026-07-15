from __future__ import annotations

from pathlib import Path


def _is_local(url: str) -> bool:
    return any(marker in url for marker in ("localhost", "127.0.0.1", "::1"))


def ollama_unreachable_guidance(vault: Path, url: str) -> dict:
    """Plain-language guidance for setup agents when Ollama cannot be reached.

    Ollama is needed at both index time and query time (`retrieve` embeds the
    query itself, see engine.py), so semantic retrieval genuinely requires the
    *entire* `mindwell retrieve` call - not just a one-time index build - to run
    on the machine where Ollama is reachable. A sandboxed or cloud agent can
    never satisfy that from inside the sandbox unless Ollama is exposed on a
    network address it can reach.
    """
    native_commands = [
        'pip install ".[semantic]"',
        "ollama pull qwen3-embedding:0.6b",
        f'mindwell configure "{vault}" --provider ollama',
        f'mindwell doctor "{vault}"',
        f'mindwell index "{vault}" --rebuild',
    ]
    lines = [
        f"Ollama is not reachable at {url}.",
        "Semantic retrieval needs Ollama for indexing AND for every single "
        "query (the query text itself is embedded), so it cannot run from an "
        "environment that cannot reach Ollama - a one-time index build is not "
        "enough.",
        "Division of labor: this environment (a sandbox, container, or cloud "
        "agent) owns lexical retrieval - it already works here with no setup. "
        "Anything Ollama-bound - semantic indexing and semantic queries - "
        "belongs on the machine where Ollama actually runs, usually your own "
        "computer.",
        "To get semantic retrieval working, run these commands natively on "
        "that machine (not in this sandbox), then approve them before I run "
        "anything:",
        *[f"  {command}" for command in native_commands],
        "Alternative: if you expose Ollama on a network address this "
        "environment can reach (for example a Tailscale address, an SSH "
        "tunnel, or a LAN IP) and set MINDWELL_OLLAMA_URL to that address, "
        "semantic retrieval can run from here too. Ollama has no built-in "
        "authentication, so only do this on a network you trust - anyone who "
        "can reach that address can use your model runtime as if it were "
        "their own.",
    ]
    return {
        "summary": f"Ollama at {url} is not reachable from this environment; "
                   "using lexical retrieval instead.",
        "guidance": lines,
        "native_commands": native_commands,
    }


def non_local_ollama_caveat(url: str) -> str | None:
    if _is_local(url):
        return None
    return (f"ollama_url is set to {url}, which is not localhost. Ollama has no "
            "built-in authentication, so anything that can reach that address "
            "can use it. Only point Ollama at a network address you control and "
            "trust.")
