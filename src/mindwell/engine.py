from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .config import index_path, load_config
from .guidance import ollama_unreachable_guidance


class OllamaUnavailable(RuntimeError):
    """Raised when Ollama cannot be reached for embedding.

    Carries the resolved URL so callers can build vault-specific guidance
    (native install steps, MINDWELL_OLLAMA_URL) without embed() needing to
    know the vault path.
    """

    def __init__(self, url: str, detail: str):
        self.url = url
        super().__init__(f"Ollama at {url} is not reachable: {detail}")


EVIDENCE_STOPWORDS = {
    "about", "after", "again", "against", "also", "does", "from", "have",
    "into", "local", "must", "only", "should", "that", "their", "there",
    "these", "this", "vault", "what", "when", "where", "which", "while",
    "with", "work", "would", "your",
}


@dataclass
class Chunk:
    id: str
    path: str
    ordinal: int
    heading: str
    body: str
    prefix: str

    @property
    def text(self):
        return f"{self.prefix}\n\n{self.body}"


def connect(vault: Path) -> sqlite3.Connection:
    con = sqlite3.connect(index_path(vault))
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("CREATE TABLE IF NOT EXISTS meta(path TEXT PRIMARY KEY, sha256 TEXT, model TEXT)")
    con.execute("""CREATE TABLE IF NOT EXISTS chunks(
        id TEXT PRIMARY KEY,path TEXT,ordinal INTEGER,heading TEXT,body TEXT,prefix TEXT,
        source_class TEXT,status TEXT,updated TEXT,authority INTEGER,dim INTEGER,vec BLOB)""")
    con.execute("CREATE INDEX IF NOT EXISTS chunk_path ON chunks(path)")
    con.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(
        id UNINDEXED,path UNINDEXED,heading,text,tokenize='porter unicode61')""")
    return con


def frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        return {}, text
    end = text.find("\n---\n", 4)
    data = {}
    for line in text[4:end].splitlines():
        if ":" in line and not line[0].isspace():
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip().strip("'\"")
    return data, text[end + 5:]


def classify(path: str, meta: dict) -> tuple[str, int]:
    low = path.lower()
    if path in {"MEMORY.md", "AGENT.md", "LOBY.md", "USER.md", "wiki/AGENT-WIKI-RULES.md"}:
        return "core", 5
    if path in {"wiki/now.md", "wiki/action-items.md", "wiki/decisions.md"}:
        return "current", 5
    if low.startswith("projects/active/"):
        return "project", 5
    if low.startswith("wiki/projects/"):
        return "project", 5
    if low.startswith("people/"):
        return "people", 4
    if low.startswith("wiki/") and "/_archive/" not in low:
        return "synthesis", 4
    if low.startswith(("daily/", "meetings/")):
        return "operating", 3
    if "archive" in low or low.startswith("projects/completed/"):
        return "historical", 1
    return "source", 2


def chunks_for(vault: Path, path: Path, text: str, config: dict) -> list[Chunk]:
    meta, body = frontmatter(text)
    rel = path.relative_to(vault).as_posix()
    title_match = re.search(r"^#\s+(.+)$", body, re.M)
    title = title_match.group(1) if title_match else path.stem
    target, maximum, overlap = (config["chunk_target_chars"],
                                config["chunk_max_chars"],
                                config["chunk_overlap_chars"])
    parts = [part.strip() for part in re.split(r"\n\s*\n", body) if part.strip()]
    result, current, size, heading = [], [], 0, title
    def emit():
        nonlocal current, size, heading
        if not current:
            return
        combined = "\n\n".join(current)
        ordinal = len(result)
        prefix = f"Vault note: {rel}. Title: {title}. Section: {heading}."
        cid = hashlib.sha256(f"{rel}\0{ordinal}\0{combined}".encode()).hexdigest()[:24]
        result.append(Chunk(cid, rel, ordinal, heading, combined, prefix))
        tail = combined[-overlap:] if overlap else ""
        current, size = ([tail] if tail else []), len(tail)
    for part in parts:
        match = re.match(r"^#{1,6}\s+(.+)", part)
        if match:
            heading = match.group(1).strip()
        while len(part) > maximum:
            piece, part = part[:maximum], part[maximum - overlap:]
            if current:
                emit()
            current, size = [piece], len(piece)
            emit()
        if current and size + len(part) + 2 > maximum:
            emit()
        current.append(part)
        size += len(part) + 2
        if size >= target:
            emit()
    emit()
    return result


def embed(config: dict, texts: list[str]):
    try:
        import numpy as np
    except ImportError as exc:
        raise RuntimeError(
            'semantic retrieval needs NumPy; install with pip install "mindwell-framework[semantic]"'
        ) from exc
    url = config["ollama_url"]
    request = urllib.request.Request(
        url.rstrip("/") + "/api/embed",
        data=json.dumps({"model": config["embedding_model"], "input": texts}).encode(),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return [np.asarray(item, dtype=np.float32)
                    for item in json.loads(response.read())["embeddings"]]
    except OSError as exc:
        raise OllamaUnavailable(url, str(exc)) from exc


def build(vault: Path, rebuild: bool = False) -> dict:
    config, con = load_config(vault), connect(vault)
    try:
        index_model = ("lexical" if config["retrieval_provider"] == "lexical"
                       else f"ollama:{config['embedding_model']}")
        if rebuild:
            con.execute("DELETE FROM fts"); con.execute("DELETE FROM chunks"); con.execute("DELETE FROM meta")
        known = {p: (sha, model) for p, sha, model in con.execute("SELECT path,sha256,model FROM meta")}
        seen, changed, chunk_count = set(), 0, 0
        for path in vault.rglob("*.md"):
            rel = path.relative_to(vault).as_posix()
            if any(part in config["exclude_dirs"] for part in path.parts):
                continue
            seen.add(rel)
            text = path.read_text(encoding="utf-8", errors="replace")
            digest = hashlib.sha256(text.encode()).hexdigest()
            if known.get(rel) == (digest, index_model):
                continue
            note_chunks = chunks_for(vault, path, text, config)
            vectors = [None] * len(note_chunks)
            if config["retrieval_provider"] == "ollama":
                vectors = []
                for start in range(0, len(note_chunks), 16):
                    vectors.extend(embed(config, [c.text for c in note_chunks[start:start + 16]]))
            meta, _ = frontmatter(text); source_class, authority = classify(rel, meta)
            con.execute("DELETE FROM fts WHERE path=?", (rel,)); con.execute("DELETE FROM chunks WHERE path=?", (rel,))
            for chunk, vector in zip(note_chunks, vectors):
                if vector is not None:
                    import numpy as np
                    vector /= np.linalg.norm(vector) + 1e-9
                    dim, blob = vector.size, vector.tobytes()
                else:
                    dim, blob = 0, None
                con.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                            (chunk.id, rel, chunk.ordinal, chunk.heading, chunk.body, chunk.prefix,
                             source_class, meta.get("status", ""), meta.get("updated", ""), authority,
                             dim, blob))
                con.execute("INSERT INTO fts VALUES (?,?,?,?)", (chunk.id, rel, chunk.heading, chunk.text))
            con.execute("INSERT OR REPLACE INTO meta VALUES (?,?,?)", (rel, digest, index_model))
            con.commit(); changed += 1; chunk_count += len(note_chunks)
        for rel in set(known) - seen:
            con.execute("DELETE FROM fts WHERE path=?", (rel,)); con.execute("DELETE FROM chunks WHERE path=?", (rel,)); con.execute("DELETE FROM meta WHERE path=?", (rel,))
        con.commit()
        result = {"files": con.execute("SELECT count(*) FROM meta").fetchone()[0],
                  "chunks": con.execute("SELECT count(*) FROM chunks").fetchone()[0],
                  "changed_files": changed, "indexed_chunks": chunk_count,
                  "index": str(index_path(vault))}
        return result
    finally:
        con.close()


def intent(query: str) -> set[str]:
    low, out = query.lower(), set()
    if any(x in low for x in ("current", "now", "planned", "who is", "when is")): out.add("current")
    if any(x in low for x in ("completed", "historical", "previously", "past")): out.add("historical")
    if any(x in low for x in ("rule", "must", "should", "after", "where do")): out.add("procedure")
    return out


def rrf(rankings: list[list[str]], k: int = 60) -> dict[str, float]:
    scores = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, 1):
            scores[item] = scores.get(item, 0) + 1 / (k + rank)
    return scores


def evidence_units(text: str) -> list[str]:
    """Split a retrieved chunk into compact, readable evidence units."""
    units = []
    for paragraph in re.split(r"\n\s*\n", text):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if len(paragraph) <= 700:
            units.append(paragraph)
            continue
        for line in (line.strip() for line in paragraph.splitlines() if line.strip()):
            if len(line) <= 700:
                units.append(line)
            else:
                units.extend(part.strip() for part in
                             re.split(r"(?<=[.!?])\s+", line) if part.strip())
    return units


def compact_evidence(text: str, query: str, budget_chars: int) -> str:
    """Select query-bearing evidence from one chunk inside a hard budget."""
    if len(text) <= budget_chars:
        return text.strip()
    terms = {token.lower() for token in re.findall(r"[A-Za-z0-9_.-]{3,}", query)
             if token.lower() not in EVIDENCE_STOPWORDS}
    low_query = query.lower()
    if "layer" in low_query or "architecture" in low_query:
        terms.update({"sources", "schema", "synthesis"})
    if "retrieval-first" in low_query or "retrieve-first" in low_query:
        terms.update({"index", "search", "retrieve"})
    if "sqlite" in low_query or "sync" in low_query:
        terms.update({"conflict", "corruption", "database", "replica"})
    units = evidence_units(text)
    scored = []
    for index, unit in enumerate(units):
        low = unit.lower()
        matched = {term for term in terms if term in low}
        score = sum(3 if any(ch.isdigit() for ch in term) else 1 for term in matched)
        score += 2 * sum(1 for term in matched if low.count(term) > 1)
        scored.append((score, len(matched), -len(unit), index))
    order = [item[3] for item in sorted(scored, reverse=True)]
    selected, used = [], 0
    for index in order:
        unit = units[index]
        separator = 2 if selected else 0
        if used + separator + len(unit) <= budget_chars:
            selected.append(index)
            used += separator + len(unit)
        elif not selected:
            selected.append(index)
            used = budget_chars
        if used >= budget_chars * .88:
            break
    selected.sort()
    return "\n\n".join(units[index] for index in selected)[:budget_chars].rstrip()


def assemble_context(selected: list[tuple], query: str, budget_chars: int) -> tuple[str, list[dict]]:
    """Preserve top-source coverage while compacting each source around the query."""
    if not selected:
        return "", []
    headers = [f"=== SOURCE_PATH: {row[0]} ===\nSECTION: {row[1]}\n{row[3]}\n\n"
               for _score, _cid, row in selected]
    text_budget = max(220 * len(selected), budget_chars - sum(map(len, headers))
                      - 2 * (len(selected) - 1))
    per_source = max(220, text_budget // len(selected))
    blocks, manifest = [], []
    for (score, cid, row), header in zip(selected, headers):
        evidence = compact_evidence(row[2], query, per_source)
        remaining = budget_chars - sum(len(item) for item in blocks) - 2 * len(blocks)
        if remaining <= len(header):
            break
        block = (header + evidence)[:remaining]
        blocks.append(block)
        manifest.append({"path": row[0], "chunk_id": cid, "score": round(score, 6),
                         "source_class": row[4], "authority": row[7], "chars": len(block)})
    return "\n\n".join(blocks), manifest


def retrieve(vault: Path, query: str, mode: str = "standard",
             refresh: bool = True) -> dict:
    # Keep ordinary searches current. The incremental build hashes each note, so
    # unchanged vaults are inexpensive while new and edited notes are available
    # immediately without asking the user to remember a separate index command.
    ollama_error = None
    try:
        refresh_stats = build(vault) if refresh else None
    except OllamaUnavailable as exc:
        # Indexing couldn't embed changed notes, but the lexical ranking below
        # is computed independently - fall back to it instead of crashing.
        refresh_stats = None
        ollama_error = exc
    config, con = load_config(vault), connect(vault)
    cfg = config["context_modes"][mode]
    words = [w for w in re.findall(r"[A-Za-z0-9_.-]{3,}", query)][:12]
    expression = " OR ".join(f'"{w}"' for w in words)
    lexical = [r[0] for r in con.execute("SELECT id FROM fts WHERE fts MATCH ? ORDER BY bm25(fts) LIMIT 100", (expression,))]
    rankings = [lexical]
    if config["retrieval_provider"] == "ollama" and ollama_error is None:
        import numpy as np
        rows = con.execute("SELECT id,vec FROM chunks WHERE vec IS NOT NULL").fetchall()
        if rows:
            try:
                q = embed(config, ["Instruct: retrieve relevant notes\nQuery: " + query])[0]
            except OllamaUnavailable as exc:
                ollama_error = exc
            else:
                q /= np.linalg.norm(q) + 1e-9
                matrix = np.vstack([np.frombuffer(row[1], dtype=np.float32) for row in rows])
                rankings.append([rows[i][0] for i in np.argsort(-(matrix @ q))[:100]])
    scores, query_intent = rrf(rankings), intent(query)
    ranked = []
    for cid, base in scores.items():
        row = con.execute("SELECT path,heading,body,prefix,source_class,status,updated,authority FROM chunks WHERE id=?", (cid,)).fetchone()
        adjust = row[7] * .00035
        if "current" in query_intent and row[4] in {"current", "project", "people"}: adjust += .005
        if "current" in query_intent and row[4] == "core": adjust += .001
        if "current" in query_intent and row[4] == "historical": adjust -= .008
        if "historical" in query_intent and row[4] == "historical": adjust += .006
        if "procedure" in query_intent and row[4] == "core": adjust += .008
        ranked.append((base + adjust, cid, row))
    ranked.sort(reverse=True)
    pages, selected = set(), []
    for score, cid, row in ranked:
        if row[0] in pages: continue
        pages.add(row[0]); selected.append((score, cid, row))
        if len(selected) >= cfg["top_k"]: break
    body, manifest = assemble_context(selected[:cfg["chunks"]], query, cfg["budget_chars"])
    provider = config["retrieval_provider"]
    result = {"mode": mode, "provider": provider, "query": query,
              "index_refresh": refresh_stats, "context": body,
              "context_chars": len(body), "estimated_tokens": math.ceil(len(body) / 4),
              "results": manifest}
    if ollama_error is not None:
        guidance = ollama_unreachable_guidance(vault, ollama_error.url)
        result["provider"] = "lexical (ollama unreachable, degraded)"
        result["warnings"] = [guidance["summary"] +
                              " Results below are lexical-only. Semantic retrieval "
                              "requires running the whole `retrieve` call on the "
                              "machine where Ollama is reachable - see 'guidance'."]
        result["guidance"] = guidance["guidance"]
    con.close()
    return result
