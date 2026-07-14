# Architecture

Mindwell separates records from interpretations.

1. **Source layer** — dated notes, meetings, projects, people, and captured material.
2. **Synthesis layer** — linked pages that combine sources without replacing them.
3. **Current-state layer** — small dashboards for facts that must reflect today.
4. **Retrieval layer** — paragraph chunks, deterministic prefixes, FTS5, local embeddings, page-level RRF, and authority/intent adjustments.
5. **Trust layer** — fixed retrieval tests, contradiction objects, and coordinated writes.

Indexes live outside the vault. Each chunk retains its page, heading, ordinal, source class, status, updated date, and authority tier. Sparse and semantic rankings are fused before duplicate pages are removed. Query intent may promote current, historical, or procedural sources; the base score remains visible.

The answer model is deliberately outside the trust boundary. Retrieval recall and citation correctness are measured separately because a model can produce a plausible answer after weak retrieval—or cite the wrong path after perfect retrieval.

Optional private external workspaces sit outside every layer above. The main vault may
retain an alias and non-sensitive purpose, but never the workspace location or content.
Locations are supplied by the user per task and are not added to the Mindwell index.

Retrieved chunks are compacted into query-bearing evidence units before assembly. The router divides a hard character budget across selected sources so a large early chunk cannot crowd later evidence out. The shipped standard mode uses five sources and a 2,500-character budget; this was the lowest configuration that repeatedly stayed above the reference evaluation's 95% answer-accuracy floor.
