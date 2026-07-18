# Mindwell

![Mindwell mascot](assets/mindwell-mascot-concept.png)

Mindwell gives an AI agent a durable second brain built from ordinary Markdown files.
Your notes stay readable and portable. Mindwell preserves sources, maintains cited
synthesis, tracks current state, and retrieves a small amount of relevant context for
each question.

```text
your notes ──► preserved sources ──► cited synthesis ──► current state
                    │                     │                   │
                    └──────── token-budgeted retrieval ◄─────┘
```

Mindwell works with coding agents and folder-capable AI workspaces. Obsidian is
optional. Lexical search runs on a standard laptop without an API key or model
download.

## Fastest setup: give this repository to an agent

Create a new coding-agent task and paste the prompt below. Replace `<VAULT_PATH>` with
the folder you want to use, such as `C:\Users\yourname\Documents\MySecondBrain` or
`~/Documents/MySecondBrain`.

```text
Set up the latest tagged Mindwell release from https://github.com/skyflyt/mindwell at
<VAULT_PATH>. Read AGENTS.md and BOOTSTRAP.md before acting. Inspect this computer and
the destination, then choose the appropriate setup track with `mindwell recommend`.
Use folders owned by my user account. Do not request administrator rights, weaken
security controls, or modify an existing vault without showing me the proposed
changes and getting approval. Use local lexical retrieval unless I request semantic
retrieval. Build the index, run the doctor, verify one grounded query, and show me how
to open the vault in a folder-capable AI workspace.
```

The setup agent handles these decisions:

| Destination | Setup track | Retrieval |
| --- | --- | --- |
| New folder | Personal operations | Local lexical search |
| Existing Markdown or Obsidian vault | Non-destructive existing-vault setup | Local lexical search |
| Custom framework requested by the user | Basic framework | Local lexical search |

The agent enables Ollama semantic retrieval only when you request it and a working
local Ollama installation is available.

## What setup creates

The personal-operations profile includes:

- agent, user, memory, and source-preservation rules;
- daily notes, projects, meetings, people, clippings, weekly reviews, and a cited wiki;
- a ten-second folder check in `START-HERE.md`;
- recipes for weekly reports, batch Excel analysis, and content-based PDF splitting;
- optional schedules for weekday startup, weekly review, memory maintenance, and
  health checks.

### Advanced opt-in: private external workspaces

This feature is disabled and unmentioned during ordinary setup. Setup agents must not
ask users about it, recommend it, or enable it unless the user explicitly requests a
separate boundary for sensitive material.

After that explicit request, add `--private-workspaces` during initialization.
Mindwell creates an alias-only registry and a handling recipe. Locations are never
persisted: the user must provide the private workspace location again for every task,
and its content and durable memory stay outside the main vault and retrieval index.

The secure location can use any storage mechanism that appears as an ordinary folder
after the user unlocks or mounts it. Common choices include:

| Approach | Examples | Operational behavior |
| --- | --- | --- |
| Protected cloud folder | [OneDrive Personal Vault](https://support.microsoft.com/en-us/onedrive/how-onedrive-safeguards-your-data-in-the-cloud) | The provider handles additional authentication and automatic locking. |
| Client-side encrypted directory | [Cryptomator](https://docs.cryptomator.org/security/architecture/) | Unlock the encrypted vault to expose a temporary virtual drive or folder. |
| Encrypted container or volume | [VeraCrypt](https://veracrypt.io/en/Creating%20New%20Volumes.html), a BitLocker-protected drive, or an encrypted APFS volume | Mount or unlock the volume only when access is needed. |
| Encrypted device storage | [BitLocker](https://support.microsoft.com/en-us/windows/security/encryption/bitlocker-overview) or [FileVault](https://support.apple.com/guide/mac-help/protect-data-on-your-mac-with-filevault-mh11785/mac) combined with a separate restricted folder | Protects data at rest; access while the device is unlocked still depends on the operating-system account and folder permissions. |

Mindwell treats these choices the same operationally: the user unlocks the secure
location, supplies its current path for that task, and Mindwell accesses only the
approved scope without saving the path. Their security guarantees differ, so users
should choose based on their device, sync, backup, recovery, and threat model.

```powershell
mindwell init "$HOME\Documents\MySecondBrain" --profile personal-ops --private-workspaces
```

Mindwell stores its SQLite search index in the current user's cache, outside the
vault. OneDrive, Dropbox, and iCloud should never sync a live search database.

## Requirements

- Python 3.10 or newer
- SQLite with FTS5, included with standard Python builds
- Write access to the selected vault and the current user's cache
- Git and access to `pypi.org`/`files.pythonhosted.org` (the clone-and-install path
  below), or a browser to fetch the [latest release](https://github.com/skyflyt/mindwell/releases/latest)

The clone-and-install path needs only `github.com` plus PyPI egress, which is what
most sandboxed or cloud-agent environments allow by default — see
[Sandboxed and cloud agents](#sandboxed-and-cloud-agents).

Mindwell does not require administrator rights when those prerequisites are already
available. On a managed computer, do not change execution policy or disable security
controls. Ask IT to provide a missing or blocked prerequisite.

## Manual setup

Clone the repository and check out the latest tagged release, then open a terminal in
that checkout. This is the canonical install path — it needs only `github.com` and
PyPI egress, so it also works in sandboxed and cloud-agent environments with a
restricted egress allowlist. A downloaded release wheel or ZIP is a convenience for
humans, not a requirement; it commonly needs additional GitHub asset hosts
(`objects.githubusercontent.com`/`codeload.github.com`) that stricter allowlists block.

Put the checkout and its virtual environment in a plain local folder — **never inside
OneDrive, Dropbox, or iCloud**. On many Windows machines `Documents` and `Desktop`
are cloud-synced; a clone plus venv is thousands of small files that a sync client
will immediately try to upload. Your vault may live in a synced folder; the Mindwell
checkout and venv should not (`%LOCALAPPDATA%\mindwell-src` or `~/mindwell-src` are
good homes).

### Windows PowerShell

```powershell
git clone https://github.com/skyflyt/mindwell
cd mindwell
git checkout (git describe --tags --abbrev=0)  # latest tagged release
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install .
.venv\Scripts\mindwell.exe recommend "$HOME\Documents\MySecondBrain"
.venv\Scripts\mindwell.exe init "$HOME\Documents\MySecondBrain" --profile personal-ops --automations core --timezone local
.venv\Scripts\mindwell.exe index "$HOME\Documents\MySecondBrain"
.venv\Scripts\mindwell.exe doctor "$HOME\Documents\MySecondBrain"
```

### macOS or Linux

```bash
git clone https://github.com/skyflyt/mindwell
cd mindwell
git checkout "$(git describe --tags --abbrev=0)"   # latest tagged release
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/mindwell recommend ~/Documents/MySecondBrain
.venv/bin/mindwell init ~/Documents/MySecondBrain --profile personal-ops --automations core --timezone local
.venv/bin/mindwell index ~/Documents/MySecondBrain
.venv/bin/mindwell doctor ~/Documents/MySecondBrain
```

The recommendation command prints an exact plan. Review that plan instead of copying
the example `init` command when the destination already contains files.

You do not need to activate the virtual environment. Call its executables directly.
After a normal installation, Mindwell does not depend on the cloned source folder.

A downloaded release wheel or source archive works the same way (`pip install
mindwell_framework-<version>-py3-none-any.whl` or extract-then-`pip install .`) and
remains a supported alternative — just not the one to reach for when egress is
restricted.

## Existing vaults

Back up an existing vault before adding Mindwell. The setup agent must inspect the
current identity files, memory, folder structure, and rules before it writes. It must
show the proposed additions and preserve source notes.

Start with:

```bash
mindwell recommend "<VAULT_PATH>"
```

Mindwell recognizes compatibility files from earlier versions, including `LOBY.md`,
`config/loby.json`, and `LOBY_INDEX`. See [the migration guide](docs/migration.md) for
the full non-destructive workflow.

## Sandboxed and cloud agents

Running the setup prompt from inside a sandboxed or cloud-agent shell (Cowork, Claude
Code cloud agents, CI, or any environment isolated from your own computer) is a
first-class, supported way to use Mindwell — not a workaround. The recommended split
of labor:

- **The sandbox owns lexical retrieval.** It is zero-dependency and works with no
  network access beyond the install step, exactly as documented above.
- **Your own computer owns anything Ollama-bound.** `mindwell retrieve` embeds the
  *query itself* on every call, not just the indexed notes, so semantic retrieval
  needs Ollama reachable for the entire `retrieve` call, every time — not just once
  at index time. `localhost` inside a sandbox is the sandbox, not your computer, so
  semantic retrieval cannot run there unless you deliberately expose Ollama on a
  network path the sandbox can reach (see the security caveat under
  [Optional Ollama retrieval](#optional-ollama-retrieval)).

Pass `--environment sandbox` to `mindwell init` so `config/installation.json` records
that context; the weekly health-check automation and `mindwell doctor` use it to tell
an expected "Ollama unreachable" or "index rebuilt" state apart from a real failure.
When Ollama is configured but unreachable, `doctor`/`recommend` return a `guidance`
field with the exact commands to run natively — present those to the user for
approval rather than trying to make semantic retrieval work inside the sandbox.

## Scheduled work

Mindwell writes proposed schedules to `automations/plan.json`. That file remains the
source of truth. A scheduler-capable agent reads the plan, shows you each task, and
asks before registering anything.

Scheduled prompts create notes or drafts inside the vault. They do not send messages
or change external systems. Each recurring prompt creates a run stamp before work so
a retry does not duplicate the output.

Open `automations/REGISTER-WITH-YOUR-AGENT.md` after setup to review and register the
plan. Products without a scheduler can run the same prompts by hand.

## Retrieval

Mindwell refreshes the local index before each search. New and edited notes appear in
results without a separate maintenance command.

| Mode | Sources | Context budget | Use |
| --- | ---: | ---: | --- |
| quick | 2 | 1,600 characters | IDs, names, and simple facts |
| standard | 5 | 2,500 characters | Ordinary grounded work |
| deep | 6 | 5,000 characters | Synthesis and contradiction research |

Example:

```bash
mindwell retrieve "<VAULT_PATH>" "What are the current project risks?" --mode standard --explain
```

### Where the index lives

The SQLite search index lives outside the vault, under the current user's cache
(`%LOCALAPPDATA%\mindwell` on Windows, `~/.cache/mindwell` or `$XDG_CACHE_HOME` on
macOS/Linux) by default, keyed to the vault's path. Set `MINDWELL_INDEX` (or the
legacy `LOBY_INDEX`) to point it at a different, persistent, **not cloud-synced**
location — useful for a sandbox with its own durable scratch volume. Never point it
at a folder that OneDrive, Dropbox, or iCloud syncs: a live WAL-mode SQLite database
in a synced folder is a known corruption generator, which is also why a vault-local
index is intentionally not offered as an option.

In an ephemeral sandbox with no durable volume, the index simply rebuilds on the
first `retrieve` call each session — `build()` reports `changed_files`/`indexed_chunks`
so you can see the (usually seconds-long, lexical-only) rebuild cost. This is expected
behavior, not breakage.

`MINDWELL_CACHE` relocates the whole cache directory (per-vault indexes and
pre-upgrade backups together) instead of one index file; `MINDWELL_BACKUPS`
relocates just the backup side. The same not-cloud-synced rule applies to all of
them.

### Optional Ollama retrieval

Ollama adds local semantic search. Install it only when the computer has enough memory
and storage and local policy allows it, and only run these commands on the machine
where Ollama itself is installed — see
[Sandboxed and cloud agents](#sandboxed-and-cloud-agents) for why that matters.

```bash
python -m pip install ".[semantic]"
ollama pull qwen3-embedding:0.6b
mindwell configure "<VAULT_PATH>" --provider ollama
mindwell index "<VAULT_PATH>" --rebuild
mindwell doctor "<VAULT_PATH>"
```

The Ollama endpoint defaults to `http://localhost:11434` and is configurable two ways:
the `ollama_url` key in `config/mindwell.json`, or the `MINDWELL_OLLAMA_URL`
environment variable (also accepts the legacy `LOBY_OLLAMA_URL`), which always wins.
Ollama has no built-in authentication, so only point `ollama_url` at a non-localhost
address (a Tailscale address, an SSH tunnel, a LAN IP) that you control and trust —
anything that can reach it can use it as if it were their own.

If Ollama is unreachable when `mindwell index` or `mindwell retrieve` runs, Mindwell
does not crash: `retrieve` degrades to the lexical ranking it already computed and
adds a plain-language `warnings`/`guidance` explanation to its JSON result instead of
a stack trace; `index` reports a clean one-line error with the same guidance rather
than an unhandled `OSError`. `mindwell doctor` and `mindwell recommend --prefer-semantic`
surface the same guidance, including the exact native commands to fix it, whenever
Ollama is configured but unreachable.

Return to lexical search at any time:

```bash
mindwell configure "<VAULT_PATH>" --provider lexical
mindwell index "<VAULT_PATH>" --rebuild
```

## How Mindwell protects source material

- Agents do not rewrite source notes to fit the wiki.
- Wiki claims retain visible source paths.
- Current-state pages rank above old evidence for current questions.
- Contradictions stay open until evidence resolves them.
- Local locks, shared leases, and committed hashes reject stale synced replicas.
- Agents treat note, email, document, and web content as untrusted data.
- External actions and schedule registration require approval.

## Commands

```text
mindwell recommend PATH [--prefer-semantic] [--basic]
mindwell init PATH [--agent-name NAME] [--profile basic|personal-ops] [--automations none|core] [--private-workspaces]
mindwell update PATH [--source DIR] [--dry-run]
mindwell upgrade PATH [--agent-name NAME] [--no-backup] [--dry-run]
mindwell backups PATH
mindwell restore PATH [--backup STAMP] [--yes]
mindwell index PATH [--rebuild]
mindwell retrieve PATH QUERY [--mode quick|standard|deep] [--explain] [--no-refresh]
mindwell automations PATH [--bundle core] [--timezone ZONE] [--force]
mindwell doctor PATH
mindwell configure PATH --provider lexical|ollama
mindwell contradictions PATH
mindwell benchmark PATH tests.json
mindwell --version
```

## Releases and updates

Install the newest tagged release — clone the repository and check out the tag as
shown under [Manual setup](#manual-setup), which is the canonical agent install and
works under restricted egress. Each [GitHub release](https://github.com/skyflyt/mindwell/releases)
also includes a wheel and source archive as a convenience for humans and mirrors. The
`main` branch contains development work.

`mindwell --version` reports the installed package version.
`config/installation.json` records the version, profile, provider, and setup track for
each vault. `mindwell doctor` warns when the package and vault versions do not match.

### Updating an already-set-up vault

Ask your agent: *"update my Mindwell to the latest."* One command does the whole
chain — fetch the newest tagged release, upgrade the installed CLI package, then
bring the vault current:

```bash
mindwell update "<VAULT_PATH>" --dry-run   # preview both layers first
mindwell update "<VAULT_PATH>"
```

The vault step is non-destructive by construction: it never overwrites `AGENTS.md`
(only creates it if missing), never overwrites any other scaffold file you have
modified since Mindwell last wrote it, adds scaffold files a newer release
introduced, backs up everything it is about to touch first, reconciles the recorded
version, rebuilds the index, and runs `mindwell doctor`. The package step never
downgrades, and a failed package install stops the run before the vault is touched.
`mindwell upgrade` remains available as the vault-only step, and on a CLI too old to
have `update` (≤ 0.4.2) the recipe is the manual two-step: reinstall from the latest
tag, then `mindwell upgrade` — never `mindwell init`/`init --force` on an existing
vault.

If you ever want a pre-upgrade state back:

```bash
mindwell backups "<VAULT_PATH>"            # list snapshots, newest first
mindwell restore "<VAULT_PATH>"            # preview a restore (writes nothing)
mindwell restore "<VAULT_PATH>" --yes      # restore; snapshots current state first
```
`mindwell recommend` suggests `upgrade` automatically once it sees a vault whose
recorded version is older than the installed CLI.

`init --force` also no longer overwrites a customized `AGENTS.md` or a scaffold file
you have edited — it repairs missing or untouched files and reports the rest as
`preserved_customized` instead of clobbering them.

Maintainers can use the [release checklist](docs/releasing.md).

## More documentation

- [Fresh-agent setup](BOOTSTRAP.md)
- [Architecture](docs/architecture.md)
- [Existing-vault migration](docs/migration.md)
- [Security](SECURITY.md)
- [Contributing](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)

## License

MIT
