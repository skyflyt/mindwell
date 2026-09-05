# Reviewing retrieval health

Check runtime readiness, cache health, source coverage, and answer quality separately.
Each answers a different question.

`mindwell doctor` checks the runtime and opens the index in read-only mode. Its
`checks.index` result reports missing, unreadable, invalid, empty, inconsistent, or
readable state. It checks SQLite structure, exercises full-text search, and compares
chunk identities with full-text entries. An empty cache produces a warning, including
for a vault with no indexable notes. The runtime can still be ready to build it.

Doctor reports `freshness: "not assessed"`. It does not scan notes or generate
embeddings. A readable cache is not proof that it contains today's notes, that its
vectors match the configured model, or that a citation supports an answer.

## Verify a complete lookup

1. Run `mindwell index <vault-path>` and inspect its file and chunk counts.
2. Run `mindwell doctor <vault-path>` and resolve index warnings.
3. Retrieve a known fact with `mindwell retrieve <vault-path> "your question" --explain`.
4. Open the cited note and check the specific supporting passage.
5. Change a fictional test note and repeat the query. Check that retrieval returns
   the new fact. Include a removed note and an excluded directory in the test set.

Mindwell refreshes before ordinary retrieval. The result's `index_refresh_status`
reports `complete`, `skipped` (with `--no-refresh`), or `incomplete`. If Ollama fails during indexing, it
can return lexical results from an older or partially refreshed cache. Read the
degradation and incomplete-refresh warnings and check source files before answering a current-state question.
Separate this from systems that serve a completed snapshot while a worker refreshes:
those systems must disclose each cache's completion time and refresh outcome. A queued
worker does not establish freshness.

## Measure before changing ranking

Use fictional examples to cover exact identifiers, paraphrases, current versus
historical facts, procedural rules, contradictory claims, and genuine no-answer
questions. Add a journal or receipt that repeats the query more often than its
canonical source. Measure whether the canonical source still appears in the first
few results, then check citation support separately from retrieval recall.

Keep the same questions and expected sources for the baseline and candidate. Record
corpus size, provider/model, cache state, source coverage, latency, and context size.
Report lexical and semantic results separately. A small fixture can catch a regression;
it cannot establish accuracy on another person's vault.

### Audit the evidence supplied to the answer model

A source can rank first while the answer-bearing sentence never reaches the model.
Save the exact initial answer context, selected chunks, source manifest, question-set
hash, and cache provenance with each evaluation. Treat those artifacts as private
vault content and exclude them from indexing; otherwise later searches can retrieve
the benchmark's own answers. A list of source paths is insufficient to reproduce a
passage-selection failure.

For a context-selection experiment, replay the captured chunks with the same fixed
questions. This isolates compaction from live note edits, refresh timing, and query
embedding changes. Record replay latency as replay overhead, not retrieval speed.
Keep the baseline intact, and reject replays with missing evidence or changed questions.

Do not score factual keywords in appended citation labels. A project number in a
filename does not establish that the answer named the project. Score the narrative
separately; keyword presence still cannot establish factual correctness. Citation-path
membership checks also cannot establish that a passage supports a claim.

### Spend the context budget on evidence

Mindwell keeps the generated embedding prefix in the result manifest. The answer
context includes source path and section once, along with available status and update
date qualifiers. Repeating the generated path/title/section prefix uses space that
could hold a supporting sentence or another source.

The fictional fixture in `tests/test_evidence_budget.py` supplies five selected
bulletins with long headings. At a 2,500-character budget, the previous header retained
four sources and four recipient facts (2,382 characters); the revised header retains
all five (2,368 characters). This is a deterministic passage-coverage check, not a
measurement of answer-model accuracy or a claim about other vaults.

A larger context is another candidate to measure, not an automatic improvement.
Report question-level regressions alongside aggregate scores. Keep incomplete names,
contradictory sources, and date-sensitive expectations visible rather than changing
the expected answers to make a run pass.

## Keep operating instructions aligned

When an implementation changes, update the command examples and startup guidance
that agents actually read. Link to one canonical contract for shared-write rules.
During reviews, check that installed skill copies and scheduler prompts match their
sources. Preserve audit receipts as history and keep them distinguishable from current
guidance in retrieval. Repetition in a log is not additional authority for a claim.

See [architecture](architecture.md), [grounded claims](grounded-claims.md), and
[detectors and receipts](detectors.md).
