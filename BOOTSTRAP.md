# Fresh-agent setup

## Recommended single prompt

Give a fresh agent only the destination and this request:

```text
Set up the latest tagged Mindwell release from https://github.com/skyflyt/mindwell at
<VAULT_PATH>. Read the repository's AGENTS.md and follow it. Inspect the machine and
destination, choose the appropriate setup track, explain the choice briefly, and
complete setup. Do not ask me to choose a numbered level. Do not request administrator
rights, weaken security controls, enable cloud data egress, or modify an existing
vault without approval. Use lexical retrieval unless I explicitly request semantic
retrieval. If no tagged release exists, tell me `main` is prerelease and ask before
using it. Build the index, run the doctor, verify a grounded query, and show me how to
start in a folder-capable AI workspace with the vault selected.
```

This is the canonical public setup path. The variants below are useful when a machine
or migration requirement is already known, but ordinary users should not need them.
Ordinary setup must not ask about or enable private external workspaces. That advanced
feature is configured only after the user explicitly requests it.

Give a new coding agent the prompt below. The agent can clone this repository, read its setup contract, and build a working vault without prior Mindwell context.

```text
Set up Mindwell from https://github.com/skyflyt/mindwell. Ask whether I want to name my agent before creating the vault.

Clone the repository into a normal development folder, read its root AGENTS.md and BOOTSTRAP.md, then follow the fresh-setup workflow. Use zero-dependency lexical retrieval unless I explicitly request Ollama. Do not install a model runtime, enable a cloud service, or modify an existing vault without asking. Run the doctor, build the index, verify one grounded retrieval, and report exactly what you created.
```

For a standard or managed user account:

```text
Set up Mindwell from https://github.com/skyflyt/mindwell without administrator rights. Detect Windows or macOS, read AGENTS.md, and use only user-writable folders. Do not change execution policy or security controls. Use a project virtual environment without activating it. If Git is unavailable, use GitHub's source ZIP only when downloads are allowed. Stop and report any policy blocker. Use lexical retrieval, run the doctor and index, and verify one grounded query.
```

For an IT-assisted training setup, add:

```text
Create the vault with the personal-ops profile and core automation bundle in the user's local timezone. Build the initial index, run the doctor, and open START-HERE.md. Confirm the user can open a folder-capable AI workspace with the vault selected. Read automations/plan.json, show the user the four proposed schedules, and ask before registering them in any supported scheduler. Do not enable automatic external sending. Leave weekly reports, batch Excel analysis, and PDF splitting as ready-to-use recipes; configure source folders with the user during or after training.
```

Include the destination when you know it:

```text
Create a new Mindwell vault at ~/Documents/MySecondBrain using https://github.com/skyflyt/mindwell. Follow the repository's AGENTS.md. Ask what I want to name my agent. Use lexical retrieval. Complete setup and verify it.
```

For an existing vault:

```text
Add Mindwell to my existing Obsidian vault at <path> using https://github.com/skyflyt/mindwell. Read AGENTS.md and docs/migration.md first. Preserve any existing agent name or ask me to choose one. Make a backup, work non-destructively, and show me the proposed file changes before applying them. Use lexical retrieval unless I approve another provider.
```

## Updating an existing installation

Give a coding agent this single prompt to bring an already-set-up vault current:

```text
Update my Mindwell installation at <VAULT_PATH>. Read AGENTS.md's "Updating an
existing installation" section and follow it exactly: run
`mindwell update "<VAULT_PATH>" --dry-run`, show me the preview of both layers (CLI
package and vault), wait for my approval, then run `mindwell update "<VAULT_PATH>"`.
Never run `mindwell init` or `mindwell init --force` on my existing vault. Afterward
tell me the version before and after, where the backup was saved, any file left
alone because I customized it, and whether my registered schedules need
re-registering. If my installed Mindwell is too old to have the `update` command,
follow AGENTS.md's manual fallback instead.
```

This is safe by construction: `mindwell update` runs the whole chain — fetch the
latest tag, upgrade the CLI package, reconcile the vault — and the vault step never
overwrites `AGENTS.md` or any file you have customized, only adds files a newer
release introduces and repairs files still byte-identical to what Mindwell last
wrote, backs up everything it touches first, and ends with a `mindwell doctor`
report. If you ever want something back, `mindwell backups` lists the snapshots and
`mindwell restore` brings them back (preview first, undoable itself). See AGENTS.md
for the exact contract.

## Expected result

The agent should leave you with:

- a vault contract and user/memory templates;
- source, wiki, and current-state folders;
- `config/mindwell.json` set to `lexical`;
- an external SQLite FTS5 index;
- a successful `mindwell doctor` report;
- one verified retrieval with source paths and a context manifest.
- `config/installation.json` recording the installed version, profile, provider, setup
  track, and command runner;
- for `personal-ops`, a ten-second folder check, three work recipes, and a
  scheduler-neutral automation plan with duplicate-run guards and a weekly health
  check.
