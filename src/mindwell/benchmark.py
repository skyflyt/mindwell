from __future__ import annotations

import json
import time
from pathlib import Path

from .engine import retrieve


def run(vault: Path, question_file: Path, mode: str = "standard") -> dict:
    questions = json.loads(question_file.read_text(encoding="utf-8"))["questions"]
    results, reciprocal = [], []
    for item in questions:
        started = time.perf_counter()
        answer = retrieve(vault, item["q"], mode)
        paths = [row["path"] for row in answer["results"]]
        expected = {path.lower() for path in item["expected_sources"]}
        rank = next((i for i, path in enumerate(paths, 1) if path.lower() in expected), None)
        if rank: reciprocal.append(1 / rank)
        results.append({"id": item["id"], "question": item["q"], "rank": rank,
                        "paths": paths, "context_chars": answer["context_chars"],
                        "milliseconds": round((time.perf_counter() - started) * 1000)})
    return {"questions": len(results),
            "source_recall_at_k": sum(r["rank"] is not None for r in results) / len(results),
            "mean_reciprocal_rank": sum(reciprocal) / len(results),
            "results": results}
