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

```powershell
mindwell init "$HOME\Documents\MySecondBrain" --profile personal-ops --private-workspaces
```

Mindwell stores its SQLite search index in the current user's cache, outside the
vault. OneDrive, Dropbox, and iCloud should never sync a live search database.

## Requirements

- Python 3.11 or newer
- SQLite with FTS5, included with standard Python builds
- Write access to the selected vault and the current user's cache
- Git or access to the [latest release](https://github.com/skyflyt/mindwell/releases/latest)

Mindwell does not require administrator rights when those prerequisites are already
available. On a managed computer, do not change execution policy or disable security
controls. Ask IT to provide a missing or blocked prerequisite.

## Manual setup

Download and extract the latest tagged release, then open a terminal in the extracted
folder.

### Windows PowerShell

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install .
.venv\Scripts\mindwell.exe recommend "$HOME\Documents\MySecondBrain"
.venv\Scripts\mindwell.exe init "$HOME\Documents\MySecondBrain" --profile personal-ops --automations core --timezone local
.venv\Scripts\mindwell.exe index "$HOME\Documents\MySecondBrain"
.venv\Scripts\mindwell.exe doctor "$HOME\Documents\MySecondBrain"
```

### macOS or Linux

```bash
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
After a normal installation, Mindwell does not depend on the extracted source folder.

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

### Optional Ollama retrieval

Ollama adds local semantic search. Install it only when the computer has enough memory
and storage and local policy allows it.

```bash
python -m pip install ".[semantic]"
ollama pull qwen3-embedding:0.6b
mindwell configure "<VAULT_PATH>" --provider ollama
mindwell index "<VAULT_PATH>" --rebuild
mindwell doctor "<VAULT_PATH>"
```

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

Install the newest tagged [GitHub release](https://github.com/skyflyt/mindwell/releases).
Each release includes a wheel and source archive. The `main` branch contains
development work.

`mindwell --version` reports the installed package version.
`config/installation.json` records the version, profile, provider, and setup track for
each vault. `mindwell doctor` warns when the package and vault versions do not match.

Maintainers can use the [release checklist](docs/releasing.md).

## More documentation

- [Fresh-agent setup](BOOTSTRAP.md)
- [Architecture](docs/architecture.md)
- [Existing-vault migration](docs/migration.md)
- [Security](SECURITY.md)
- [Contributing](CONTRIBUTING.md)

## License

MIT
