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

## Keep operating instructions aligned

When an implementation changes, update the command examples and startup guidance
that agents actually read. Link to one canonical contract for shared-write rules.
During reviews, check that installed skill copies and scheduler prompts match their
sources. Preserve audit receipts as history and keep them distinguishable from current
guidance in retrieval. Repetition in a log is not additional authority for a claim.

See [architecture](architecture.md), [grounded claims](grounded-claims.md), and
[detectors and receipts](detectors.md).
