# Changelog

## 0.4.1

Fixes a real data-loss bug found in the field: `mindwell init --force` silently
overwrote a user's canonical `AGENTS.md` (and other Mindwell-managed scaffold files)
with the stock template, destroying customizations for exactly the users who bother to
customize `AGENTS.md`. Plain `init` already preserved existing files correctly; only
`--force` clobbered. This release adds a safe upgrade path and closes the `--force`
hole.

### Added

- **`mindwell upgrade <vault>`**, the canonical, non-destructive way to bring an
  existing Mindwell vault up to the installed version. It:
  - reconciles the vault's recorded `mindwell_version` to the installed CLI version so
    `doctor`'s `version_match` check goes green;
  - adds any new Mindwell-managed scaffold file a newer release introduced that the
    vault is missing;
  - never overwrites `AGENTS.md` or `AGENT.md` once they exist — both are created only
    if absent, and otherwise reported as `preserved_canonical`;
  - never overwrites any other scaffold file the user has modified since Mindwell last
    wrote it — such files are left alone and reported as `preserved_customized`, never
    silently dropped or replaced;
  - safely repairs a scaffold file that is still byte-identical to the last template
    Mindwell wrote, even across version bumps, via a per-file content hash
    (`scaffold_hashes`) recorded in `config/installation.json`;
  - backs up every file it is about to touch before writing anything, to a per-vault
    directory outside the vault (`config.backup_root`, next to the search index, for
    the same reason the index lives outside synced folders — see `--no-backup` to
    skip);
  - supports `--dry-run` to preview exactly what would be created/updated/left alone
    before writing, and `--agent-name` to name a missing `AGENT.md`;
  - rebuilds the index and runs `mindwell doctor` at the end and returns both results;
  - is idempotent — running it again on an already-current vault changes nothing.
- `mindwell recommend` now detects an existing vault whose recorded
  `config/installation.json` version is older than the installed CLI and suggests
  `mindwell upgrade "<vault>"` instead of `init`/`init --force`. A vault already on the
  current version is still offered `upgrade` as a safe no-op health/repair check. A
  brand-new or non-Mindwell existing destination is unaffected and still gets `init` as
  before.
- `AGENTS.md`/`BOOTSTRAP.md`/`README.md` document the canonical "just ask your agent to
  update" recipe: pull or clone the latest tag → reinstall the CLI (`pip install .`) →
  `mindwell upgrade "<vault>"`. Agents are told to preview with `--dry-run`, show the
  change summary, and get approval before writing, per the project's existing
  non-destructive-write discipline.

### Fixed

- `mindwell init --force` no longer overwrites a user-modified `AGENTS.md`/`AGENT.md`
  or any other scaffold file the user has changed. It still repairs missing files and
  files that are still byte-identical to what Mindwell last wrote (the same
  `scaffold_hashes`-based reconciliation `upgrade` uses); a genuinely customized file
  is left in place and reported under the new `preserved_customized` key in `init`'s
  JSON output rather than being silently replaced.

### Changed

- `mindwell init`'s JSON output shape changed from a flat `{"created": [...]}` list to
  `{"created": [...], "updated": [...], "preserved_canonical": [...],
  "preserved_customized": [...]}`, so callers can see what force-repaired versus what
  it declined to touch. `created` keeps its previous meaning (file did not exist and
  was written).
- `config/installation.json` gained two additive fields: `scaffold_hashes` (per-file
  content hashes of what Mindwell last wrote, used to detect user modification) and,
  after an `upgrade`, `last_upgraded_at`.

## 0.4.0

Fixes for sandboxed-agent setup friction identified in a field report
(`docs/SANDBOX_AGENT_FEEDBACK_REVIEW.md`).

**Retrieval tiers, plainly:** lexical search is the default and works on any
machine out of the box — no local AI needed. Semantic search is an optional
upgrade, available only where Ollama is installed and reachable; nobody is
forced onto the local-AI path to use Mindwell. This release also makes the
transition between the two tiers graceful in both directions: a vault that
can't reach Ollama now degrades to lexical instead of crashing, and `doctor`
stops misreporting a lexical-only install as broken.

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
