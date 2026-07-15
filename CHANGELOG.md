# Changelog

## 0.4.0

Fixes for sandboxed-agent setup friction identified in a field report
(`docs/SANDBOX_AGENT_FEEDBACK_REVIEW.md`).

### Changed

- Lowered the Python floor from 3.11 to 3.10 (`pyproject.toml`, `doctor.py`,
  `advisor.py`). The runtime package was already 3.10-clean; only the test
  suite needed `tomllib`, which is now a regex read of `pyproject.toml`
  instead (matching `release.yml`'s existing approach).
- The Ollama endpoint is now configurable via the `MINDWELL_OLLAMA_URL`
  environment variable (legacy alias `LOBY_OLLAMA_URL`), which overrides
  `ollama_url` in `config/mindwell.json`. `advisor.py` no longer hardcodes
  `localhost:11434` and now routes through the same resolved config as
  everything else.
- `mindwell index` and `mindwell retrieve` no longer crash with a raw
  traceback when Ollama is unreachable. `retrieve` degrades to the lexical
  ranking it already computed and returns a plain-language `warnings`/
  `guidance` explanation instead; `index` returns a clean one-line error with
  the same guidance.
- `mindwell doctor` and `mindwell recommend --prefer-semantic` now emit a
  `guidance` field with the concrete native commands to restore semantic
  retrieval when Ollama is configured but unreachable, and a `security_notice`
  when `ollama_url` points at a non-localhost (unauthenticated) address.
- `mindwell doctor`'s `ollama` check is skipped (not reported as `ok: false`)
  when the vault's provider is `lexical`, instead of probing an endpoint the
  provider doesn't need. **Field value change:** `checks.ollama` for a
  lexical-provider vault now reports `{"ok": true, "skipped": true, "value":
  "skipped (provider: lexical)"}` instead of probing `ollama_url` and
  reporting `ok: false` when nothing is listening there. All other `doctor`
  fields (`ready`, `provider`, `checks`, `warnings`, `recommendation`) are
  unchanged in shape; two fields were added additively: `mode`
  (`lexical`/`semantic`/`semantic-unreachable`/`blocked`) and, conditionally,
  `guidance`/`security_notice`.
- `doctor`'s `recommendation` no longer contradicts `ready` (previously a
  vault could report `ready: false` and `"recommendation": "ready for
  zero-dependency lexical retrieval"` in the same response).
- `mindwell init` accepts `--environment sandbox|native`; `config/
  installation.json` records it (auto-detected via container markers when not
  passed) alongside a new `runner_hint` field, so a health check running in a
  different environment than the one that ran `init` can tell an expected
  "CLI not reachable" state apart from a real failure.
- The weekly-health-check automation prompt now explains that a missing CLI,
  an unreachable Ollama, or a rebuilding index can be expected sandbox
  behavior rather than an actionable failure.
- The documented canonical agent install is now clone → checkout the latest
  tag → `pip install .` (needs only `github.com` and PyPI egress), not a
  release wheel or archive download (`docs/releasing.md`, `AGENTS.md`,
  `README.md`). The wheel/archive remain supported alternatives.
- Documented `MINDWELL_INDEX`/`LOBY_INDEX` and the index's automatic rebuild
  on first retrieval each session (README). No vault-local index option was
  added — see the review for why that's rejected by design.
- Added an AGENTS.md/README "Sandboxed and cloud agents" section describing
  the supported division of labor: the sandbox owns lexical retrieval;
  anything Ollama-bound (indexing and querying) runs natively where Ollama is
  reachable, because `retrieve` embeds the query itself on every call.

### Fixed

- `mindwell.engine.build()` no longer leaks its SQLite connection when
  Ollama embedding fails partway through.
- `mindwell.doctor.inspect()` no longer leaks its in-memory SQLite connection
  used for the FTS5 capability check.

### Open questions carried forward (not decided in this release)

- Whether to add a CI job that runs the test suite on push/PR (today only
  `release.yml` runs tests, and only on tag push) — flagged in the review as a
  question for the maintainer, not decided here.
