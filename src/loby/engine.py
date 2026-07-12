from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .config import index_path, load_config


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
    if path in {"MEMORY.md", "LOBY.md", "USER.md", "wiki/AGENT-WIKI-RULES.md"}:
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


def embed(config: dict, texts: list[str]) -> list[np.ndarray]:
    request = urllib.request.Request(
        config["ollama_url"].rstrip("/") + "/api/embed",
        data=json.dumps({"model": config["embedding_model"], "input": texts}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=180) as response:
        return [np.asarray(item, dtype=np.float32)
                for item in json.loads(response.read())["embeddings"]]


def build(vault: Path, rebuild: bool = False) -> dict:
    config, con = load_config(vault), connect(vault)
    if rebuild:
        con.execute("DELETE FROM fts"); con.execute("DELETE FROM chunks"); con.execute("DELETE FROM meta")
    known = {p: sha for p, sha in con.execute("SELECT path,sha256 FROM meta")}
    seen, changed, chunk_count = set(), 0, 0
    for path in vault.rglob("*.md"):
        rel = path.relative_to(vault).as_posix()
        if any(part in config["exclude_dirs"] for part in path.parts):
            continue
        seen.add(rel)
        text = path.read_text(encoding="utf-8", errors="replace")
        digest = hashlib.sha256(text.encode()).hexdigest()
        if known.get(rel) == digest:
            continue
        note_chunks = chunks_for(vault, path, text, config)
        vectors = []
        for start in range(0, len(note_chunks), 16):
            vectors.extend(embed(config, [c.text for c in note_chunks[start:start + 16]]))
        meta, _ = frontmatter(text); source_class, authority = classify(rel, meta)
        con.execute("DELETE FROM fts WHERE path=?", (rel,)); con.execute("DELETE FROM chunks WHERE path=?", (rel,))
        for chunk, vector in zip(note_chunks, vectors):
            vector /= np.linalg.norm(vector) + 1e-9
            con.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                        (chunk.id, rel, chunk.ordinal, chunk.heading, chunk.body, chunk.prefix,
                         source_class, meta.get("status", ""), meta.get("updated", ""), authority,
                         vector.size, vector.tobytes()))
            con.execute("INSERT INTO fts VALUES (?,?,?,?)", (chunk.id, rel, chunk.heading, chunk.text))
        con.execute("INSERT OR REPLACE INTO meta VALUES (?,?,?)", (rel, digest, config["embedding_model"]))
        con.commit(); changed += 1; chunk_count += len(note_chunks)
    for rel in set(known) - seen:
        con.execute("DELETE FROM fts WHERE path=?", (rel,)); con.execute("DELETE FROM chunks WHERE path=?", (rel,)); con.execute("DELETE FROM meta WHERE path=?", (rel,))
    con.commit()
    return {"files": con.execute("SELECT count(*) FROM meta").fetchone()[0],
            "chunks": con.execute("SELECT count(*) FROM chunks").fetchone()[0],
            "changed_files": changed, "embedded_chunks": chunk_count,
            "index": str(index_path(vault))}


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


def retrieve(vault: Path, query: str, mode: str = "standard") -> dict:
    config, con = load_config(vault), connect(vault)
    cfg = config["context_modes"][mode]
    words = [w for w in re.findall(r"[A-Za-z0-9_.-]{3,}", query)][:12]
    expression = " OR ".join(f'"{w}"' for w in words)
    lexical = [r[0] for r in con.execute("SELECT id FROM fts WHERE fts MATCH ? ORDER BY bm25(fts) LIMIT 100", (expression,))]
    rows = con.execute("SELECT id,vec FROM chunks").fetchall()
    q = embed(config, ["Instruct: retrieve relevant notes\nQuery: " + query])[0]
    q /= np.linalg.norm(q) + 1e-9
    matrix = np.vstack([np.frombuffer(row[1], dtype=np.float32) for row in rows])
    semantic = [rows[i][0] for i in np.argsort(-(matrix @ q))[:100]]
    scores, query_intent = rrf([lexical, semantic]), intent(query)
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
    context, manifest, used = [], [], 0
    for score, cid, row in selected[:cfg["chunks"]]:
        block = f"=== SOURCE_PATH: {row[0]} ===\nSECTION: {row[1]}\n{row[3]}\n\n{row[2]}"
        block = block[:max(0, cfg["budget_chars"] - used)]
        if not block: break
        context.append(block); used += len(block) + 2
        manifest.append({"path": row[0], "chunk_id": cid, "score": round(score, 6),
                         "source_class": row[4], "authority": row[7], "chars": len(block)})
    body = "\n\n".join(context)
    return {"mode": mode, "query": query, "context": body,
            "context_chars": len(body), "estimated_tokens": math.ceil(len(body) / 4),
            "results": manifest}
