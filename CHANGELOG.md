# Changelog

## Unreleased

### Fixed

- **Every file Mindwell writes now lands atomically** (new
  `mindwell.fsio.atomic_write_text`, used by scaffold, upgrade, automations,
  configure, the contradictions registry, and the coordinator's baselines).
  `Path.write_text` truncates the target before writing, so a payload that
  fails to encode, a full disk, or a killed process left the file at zero
  bytes with the old content unrecoverable. The helper encodes first, writes
  to a sibling temporary file, and `os.replace`s it over the target, so a
  reader sees the old content or the new content and never an empty file. A
  regression test also fails the build if a bare `.write_text(` call returns
  to `src/mindwell`.

### Changed

- **Documented the failure mode for vaults in synced folders** (README
  "Vaults in synced folders", plus guidance for setup agents in AGENTS.md).
  Both documents already told users to keep the *checkout and venv* out of
  OneDrive/Dropbox/iCloud, and noted that a live search database must never be
  synced, but they said without qualification that the vault itself "may live
  in a synced folder". That is fine for one person on one machine and quietly
  dangerous for unattended runs: sync clients resolve a concurrent write by
  renaming one side rather than merging or erroring, so a scheduled task can
  write a note, have it land in a machine-renamed copy, leave the original
  filename holding older content, and report success throughout. A human
  editing by hand sees the duplicate appear; a scheduled task does not. The
  docs now describe that behaviour, and recommend a plain local folder plus
  backups or a git remote for anyone running unattended tasks against a vault.
- **Added a "Multi-machine and multi-agent vaults" section to README** giving
  the pattern that answers the question the warning above raises: keep the vault
  in a plain local folder as a git repository, give it a remote, and pull at the
  start of every session / push at the end - with that instruction written into
  the agent file the agent reads on wake, because an agent has no memory between
  sessions. Documents the three rules that matter more than the commands (a
  conflict stops rather than auto-merges, offline warns rather than fails,
  unattended runs push too), and is explicit that this converts a cross-machine
  collision from a silent overwrite into a visible conflict rather than
  eliminating it - and does nothing for two writers on the same machine.
- **Added an "If a timer runs the sync" section to README** with the four
  guards a scheduled sync task needs: a hold file sessions touch during long
  edits, a quiescence check that skips the cycle when files changed in the
  last two minutes, push-first-reconcile-on-rejection so the rebase runs only
  when the remote demands it, and a counter on consecutive offline warnings so
  a dead remote stops passing as a laptop off the network. Each guard maps to
  an observed failure from three weeks of running the pattern in production,
  including a day where a bare 15-minute timer collided with a working agent
  five times and an interrupted `pull --rebase --autostash` cost that agent
  its run. Also records the structural rule that code projects inside a vault
  keep their own git repository.
- **Added a "Two sessions, one machine, one repository" section to README**,
  from the second round of production incidents with the pattern above.
  `git add -A` at session end swept a concurrent session's half-written files
  into the closing session's commit (fix: commit named paths with
  `git commit -- <paths>`; in scripts, make an unscoped commit an error);
  `--autostash` before a routine push checked a working tree out from under
  the other writer (fix: push first, reconcile only on rejection, with
  `--no-autostash` - unpushed is recoverable, a clobbered working tree is
  not); and two sessions merely *pulling* concurrently hard-failed, because
  `FETCH_HEAD` is not written atomically (measured: 40/40 corrupted
  `FETCH_HEAD`s under six concurrent fetches; 24/24 failed concurrent pulls).
  The fix is layered so the structural part carries it alone: rebase onto the
  remote-tracking ref rather than `FETCH_HEAD`, serialise with a
  machine-local lock (never a lock inside the synced repository), and retry
  only a named list of transient errors, never a merge conflict. The session
  commands in "Multi-machine and multi-agent vaults" now demonstrate the safe
  shape.

- **`docs/multi-writer.md` gained two sections from production incidents:**
  "Write so failure cannot destroy" (the truncate-then-write hazard above, and
  the shape vault automations should copy) and "Verify effects, not actors"
  (re-read what you changed; mtime is not freshness in a git-synced vault
  because checkouts and rebases rewrite timestamps wholesale; a liveness check
  must measure the monitored process's own artifact, not a proxy such as "the
  most recent commit by any author", which stayed green through a two-day
  backup outage; and an alert is an effect too - a monitor whose delivery leg
  failed authentication for nine days read green every cycle because the
  verdict was in the run receipt and the delivery was not, and the failure
  records lived in state the next success erased - so receipts record verdict
  and delivery, and failure records live in durable version-tracked state,
  resolved rather than deleted; see `docs/detectors.md`).

### Added

- **`docs/detectors.md` — "Detectors and receipts."** The failure class that
  dominated a month of production automation work, written up as doctrine: a
  detector that measures a proxy for the thing, rather than the thing itself,
  is indistinguishable from a working detector until the day it matters. The
  proxy catalogue (exit codes vs. side effects, repository activity vs. "the
  backup ran", mtimes vs. freshness, format-keyed staleness checks, name
  prefixes vs. rosters, a tool's own "verify", credential-gated coverage,
  structurally-incapable counting methods), the run-receipt pattern (verdict
  *and* delivery, tracked in version control, heartbeat at the end of the
  work), self-observation ("a check that measures itself is not a check" —
  receipts judged by a separate watchdog on a separate trigger and delivery
  path), durable alerting state (resolve, never delete; key findings
  individually; match alert cadence to decision cadence), alerts that assert
  only what they can observe, the four legs of a non-vacuous green, and
  proving alarms against a copy of the world.
- **`docs/grounded-claims.md` — "Grounded claims."** Conventions that keep an
  agent from presenting its record as reality, each from a real anonymized
  incident: superlatives are artifacts of when the record began ("the record
  contains no instance of" is the honest sentence); how a scoped claim loses
  its qualifier across rewrite hops and gets promoted into standing memory;
  mixed-source answers; correction propagation (in place, struck-not-deleted,
  receipts exempt, retracted false alarms kept visible); the NOT-CURRENT
  banner convention for snapshots ("the live system is the record; nothing in
  the vault is"); writing rules for the misreader (ceiling-not-floor, inline
  misreading notes, one-question acceptance tests, saying what is *not* a
  finding); and verifying summaries against sources you still hold, with a
  deterministic dropped-negation guard.

## 0.4.3

One command to update everything, and one command to undo it. Built for the
first cohort of non-technical users: "update my Mindwell" should never require
knowing that a package layer and a vault layer exist.

### Added

- **`mindwell update <vault>`** — the all-in-one updater. In one invocation it:
  fetches the newest tagged release into a managed cache checkout (or uses
  `--source <checkout>` for offline/dev machines), upgrades the installed
  package with pip into the environment running the command (verified safe on
  Windows even when invoked through `mindwell.exe` — pip stashes the in-use
  launcher via rename), then runs the vault reconcile **in a fresh child
  interpreter so it executes under the just-installed version**, not the code
  loaded in the running process. Every `upgrade` guarantee carries through:
  never overwrites `AGENTS.md`/`AGENT.md` or any user-modified file, backs up
  every touched file first, idempotent, ends with `mindwell doctor`. It never
  downgrades (an installed version newer than the latest tag is left alone,
  with a note), `--dry-run` previews both layers without changing anything,
  a pip failure stops the run *before* the vault is touched ("nothing is
  half-applied"), and the result includes a `post_steps` reminder when the
  vault's automation schedules are registered with a scheduler whose prompt
  copies may now be stale.
- **`mindwell backups <vault>`** — lists the vault's pre-upgrade snapshots
  (stamp, date, file count), newest first, from the cache-side backup
  directory upgrades have always written.
- **`mindwell restore <vault> [--backup STAMP] [--yes]`** — one-command
  recovery from any of those snapshots. Preview by default: without `--yes` it
  only reports which files differ and writes nothing. With `--yes` it first
  snapshots the current state of every file it is about to change (so a
  restore is itself undoable the same way), then restores. Files already
  identical to the backup are reported `unchanged` and left alone.

### Changed

- `AGENTS.md`'s "Updating an existing installation" contract now leads with
  the single `mindwell update` command (dry-run preview → approval → run →
  report versions, preserved files, backup path, doctor, post-steps), keeps
  the manual two-step as the fallback for CLIs that predate `update`, and
  documents the `backups`/`restore` recovery path. `BOOTSTRAP.md`'s paste-able
  update prompt and the README's update section match.

## 0.4.2

Improvements grounded in a week of production use of a mature second-brain vault
plus a live group-training session where a room of standard Windows users installed
Mindwell. Three field-proven lessons drive this release: a run stamp alone cannot
tell "already done" from "started and died"; decisions that aren't written down
same-day are lost; and a cloned repo plus venv inside OneDrive is a sync storm.

### Changed

- **Run-stamp guards gained a `done:` marker protocol** (all four scheduled
  automation prompts). The old guard — "if the stamp exists, stop" — has a proven
  failure mode observed repeatedly in the field: a run that writes its stamp and
  then dies mid-work silently blocks every retry for the rest of the day. The new
  protocol: a stamp *with* a `done:` line means completed (stop); a stamp *without*
  one that is more than two hours old means the earlier run died — say so and take
  the run over; a fresh one may still be in progress (stop); on completion append
  `done: <timestamp> — <summary>`; on a deliberate early stop (a required system is
  unavailable), leave the stamp without `done:` so a later retry can take over. The
  weekly health check now counts done-less stamps as failed runs, not completed
  ones, and is told to corroborate before declaring an automation dead from one
  stale file — on a synced vault a single lagging replica can look stale while
  everything around it is current.
- **Decision capture is now prompted for, not assumed.** The weekday-startup prompt
  surfaces capture gaps (yesterday's meetings or decisions that left no note); the
  weekly review lists decisions with no written record in `wiki/decisions.md` and
  closes action items whose own text says DONE/RESOLVED but still sit open. Both
  prompts also say: if nothing changed since the last run, say so in one line
  instead of restating — recurring reports that repeat verbatim train people to
  stop reading them.
- **`mindwell upgrade` now reconciles the automation prompt files and
  `REGISTER-WITH-YOUR-AGENT.md`** with the same hash-based
  create/repair/preserve logic as scaffold files, so prompt improvements (like this
  release's) actually reach existing vaults. Unmodified prompts from any prior
  release (v0.3.0–v0.4.1, recognized via pinned historical template hashes) update
  in place; customized prompts are preserved and reported, exactly like scaffold
  files. `plan.json` is stateful and is still never reconciled — but a core-bundle
  vault that lost it gets it recreated. `init` now records these files in
  `scaffold_hashes`.
- **`MINDWELL_CACHE`** environment variable relocates the whole Mindwell cache
  directory (per-vault indexes and pre-upgrade backups) — a durable sandbox scratch
  volume is one line of configuration now. `MINDWELL_INDEX`/`MINDWELL_BACKUPS`
  still override the individual paths.
- The test suite no longer writes into the real user cache. Previously every run
  left one orphaned per-vault `.db` (and upgrade tests a backups directory) in
  `%LOCALAPPDATA%\mindwell` / `~/.cache/mindwell` per tempdir vault — observed in
  the field as ~110 abandoned databases on a dev machine. Tests now isolate via
  `MINDWELL_CACHE`.
- **Setup contract (AGENTS.md/README):** the checkout and venv must live in a plain
  local folder, never inside OneDrive/Dropbox/iCloud (on many Windows machines
  `Documents`/`Desktop` are synced — a fresh clone there becomes thousands of
  uploading files; observed live in a training room). Added the Windows PowerShell
  form of the canonical install, per-user (`winget --scope user`/Microsoft Store)
  Python+Git guidance for non-admin Windows users, and made "offer to register the
  automation schedules" an explicit numbered setup step instead of homework.
- **Existing-vault consent wording tightened:** announcing what you are about to do
  is not the same as asking. Before writing into an existing vault, show the exact
  proposed additions and wait for an explicit yes. (A field report praised an agent
  that "didn't even ask to merge" — impressive, but not the contract.)

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
