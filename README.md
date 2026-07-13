# Mindwell

![Mindwell mascot](assets/mindwell-mascot-concept.png)

**A durable second brain for your personally named AI agent.**

Name your agent anything you like. Mindwell gives that agent a private, portable knowledge system built from ordinary Markdown. It preserves original notes, maintains current understanding with citations, and retrieves bounded context so the agent spends tokens on the work instead of rereading the vault.

```text
your notes ──► preserved sources ──► cited synthesis ──► current state
                    │                     │                   │
                    └──────── token-budgeted retrieval ◄─────┘
                                      │
                              your named AI agent
```

Mindwell works across agent harnesses because the durable knowledge lives in files rather than one chat product. Lexical retrieval runs on an ordinary laptop. Ollama adds semantic retrieval when the machine can support it.

## Contents

- [Why Mindwell is different](#why-it-is-different)
- [Choose an installation level](#choose-an-installation-level)
- [Check prerequisites](#check-prerequisites)
- [Restricted or standard-user accounts](#restricted-or-standard-user-accounts)
- [Level 1: Standard laptop](#level-1-standard-laptop)
- [Level 2: Enhanced local with Ollama](#level-2-enhanced-local-with-ollama)
- [Existing vault: Standard lexical setup](#existing-vault-standard-lexical-setup)
- [Existing vault: Enhanced Ollama setup](#existing-vault-enhanced-ollama-setup)
- [Context modes](#context-modes)
- [Vault layers](#vault-layers)
- [Commands](#commands)

## Why it is different

- **Sources stay sources.** Daily notes, projects, meetings, and clippings are never rewritten to fit the wiki.
- **Synthesis compounds.** Agents maintain a linked wiki with visible citations.
- **Current truth is explicit.** Current-state pages rank above stale evidence for current questions; historical questions keep historical evidence.
- **Retrieval is tested.** A known-answer benchmark measures source recall, MRR, context size, latency, answers, and citations separately.
- **Context has a budget.** Quick, standard, and deep modes prevent accidental whole-vault loading.
- **Uncertainty is first-class.** Contradictions and evidence gaps remain linked to their competing sources.
- **Writes are coordinated.** Local locks, shared leases, and committed hashes can reject stale synced replicas before mutation.

The architecture was validated in a real operational vault. In its reference evaluation, authority-aware chunk retrieval improved source recall@5 from 60% to 100% and MRR from 0.459 to 0.701 while using bounded context. The included example data is entirely fictional.

## Choose an installation level

These levels describe how Mindwell is installed. They are separate from the quick, standard, and deep context modes used when retrieving notes.

| Level | Best for | Retrieval | Requirements |
| --- | --- | --- | --- |
| 1: Standard laptop | Training, first-time setup, and ordinary laptops | Local lexical search with SQLite FTS5 | Git and Python 3.11+ |
| 2: Enhanced local | Machines that can run a local embedding model | Lexical and semantic search through Ollama | Level 1 plus Ollama, model storage, and enough memory to run it |
| 3A: Existing vault, standard | Adding Mindwell to an established vault on an ordinary laptop | Local lexical search | Level 1 plus a current vault backup |
| 3B: Existing vault, enhanced | Upgrading an established vault to local semantic retrieval | Lexical and semantic search through Ollama | Level 2 plus a current vault backup |

Obsidian is optional. Mindwell works with ordinary Markdown files.

### Check prerequisites

Run these before any level:

```bash
git --version
python --version
```

If `python` is not found, try `python3 --version` on macOS or Linux, or `py -3.11 --version` on Windows. Install Python 3.11 or newer before continuing.

Level 2 also requires:

```bash
ollama --version
ollama list
```

Do not ask an agent to install Ollama unless you want local semantic retrieval. Level 1 has no model download, NumPy dependency, API key, or cloud service.

### Restricted or standard-user accounts

Level 1 does not require administrator rights when Python 3.11+ and the repository are available. Mindwell writes to the repository, the selected vault, and a cache inside the current user's profile.

On a managed computer, do not change execution policy, disable security controls, or install blocked software. Stop and report the missing prerequisite if company policy blocks Python, GitHub, downloaded programs, or virtual environments.

You do not need to activate a virtual environment. Direct commands work in PowerShell, Command Prompt, macOS Terminal, and agent shells.

**Windows PowerShell:**

```powershell
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -e .
.venv\Scripts\mindwell.exe init "$HOME\Documents\MySecondBrain" --agent-name "Nova"
.venv\Scripts\mindwell.exe doctor "$HOME\Documents\MySecondBrain"
.venv\Scripts\mindwell.exe index "$HOME\Documents\MySecondBrain"
```

**Windows Command Prompt:**

```batch
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -e .
.venv\Scripts\mindwell.exe init "%USERPROFILE%\Documents\MySecondBrain" --agent-name "Nova"
.venv\Scripts\mindwell.exe doctor "%USERPROFILE%\Documents\MySecondBrain"
.venv\Scripts\mindwell.exe index "%USERPROFILE%\Documents\MySecondBrain"
```

**macOS:**

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/mindwell init ~/Documents/MySecondBrain --agent-name "Nova"
.venv/bin/mindwell doctor ~/Documents/MySecondBrain
.venv/bin/mindwell index ~/Documents/MySecondBrain
```

If Git is unavailable but GitHub downloads are allowed, download the repository ZIP from the **Code** menu, extract it to a writable folder, open a terminal in that folder, and continue with the commands above. Keep the extracted folder because the editable installation points to it.

## Level 1: Standard laptop

This is the default and recommended setup.

```bash
git clone https://github.com/skyflyt/mindwell
cd mindwell
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
mindwell init ~/MySecondBrain --agent-name "Nova"
mindwell doctor ~/MySecondBrain
mindwell index ~/MySecondBrain
mindwell retrieve ~/MySecondBrain "What is the current project risk?" --mode standard --explain
```

On Windows PowerShell, create and activate the environment with:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .
```

The agent name is optional. Omit `--agent-name` and edit `AGENT.md` later if you prefer. Open the generated folder as an Obsidian vault if desired, then customize `AGENT.md`, `USER.md`, and `config/mindwell.json`.

### Fresh-agent prompt for Level 1

Paste this into a new coding-agent session:

```text
Set up Mindwell from https://github.com/skyflyt/mindwell at Level 1 for a standard laptop. Read the repository's AGENTS.md, README.md, BOOTSTRAP.md, and SECURITY.md before making changes. Ask what I want to name my agent; skip naming if I have no preference. Detect the operating system and check Python 3.11+, Git, filesystem access, and security restrictions. Work entirely in user-writable folders. Do not request administrator rights, change PowerShell execution policy, disable security controls, or install blocked prerequisites. Clone the repository, or use GitHub's source ZIP if Git is unavailable and downloads are permitted. Create a project-local virtual environment and call its Python and Mindwell executables directly without requiring activation. Create a new vault at <VAULT_PATH> with lexical retrieval. Do not install Ollama, add a cloud service, or send vault content outside this machine. Run mindwell doctor, build the index, and verify a grounded standard-mode query. Report the chosen agent name, operating system, retrieval provider, files created, index location, test result, and any policy or permission blocker. If <VAULT_PATH> already contains files, stop and ask before modifying it.
```

Replace `<VAULT_PATH>` with the destination you want, such as `C:\Users\yourname\Documents\MySecondBrain` or `~/Documents/MySecondBrain`.

## Level 2: Enhanced local with Ollama

Start with Level 1, then add the optional semantic dependency and local embedding model:

```bash
python -m pip install -e ".[semantic]"
ollama pull qwen3-embedding:0.6b
mindwell configure ~/MySecondBrain --provider ollama
mindwell doctor ~/MySecondBrain
mindwell index ~/MySecondBrain --rebuild
```

Switch back at any time with `mindwell configure ~/MySecondBrain --provider lexical` followed by a rebuild.

### Fresh-agent prompt for Level 2

```text
Set up Mindwell from https://github.com/skyflyt/mindwell at Level 2 with local Ollama semantic retrieval. Read the repository's AGENTS.md, README.md, BOOTSTRAP.md, and SECURITY.md first. Ask what I want to name my agent; skip naming if I have no preference. Check Git, Python 3.11+, Ollama, available models, and the target path. Clone the repository, create a project-local virtual environment, and install the semantic extra. Create a new vault at <VAULT_PATH>. Use qwen3-embedding:0.6b unless a compatible embedding model is already configured. Ask before installing Ollama or downloading a model. Never configure a remote embedding service or send vault content outside this machine. Run mindwell doctor, configure the ollama provider, rebuild the index, and verify a grounded standard-mode query. If Ollama cannot pass the checks, restore the lexical provider and explain why. Report the chosen agent name, provider, model, files created, index location, test result, and manual next steps.
```

## Existing vault: Standard lexical setup

Choose this path for an existing Markdown vault, an existing Obsidian vault, or a vault created from an earlier second-brain prompt. It runs on an ordinary laptop without Ollama.

Preserve the current agent name, identity files, notes, rules, and folder structure. Mindwell supports existing `LOBY.md` and `config/loby.json` files, so renaming them is optional.

### Standard prerequisites

1. Create a current backup of the vault.
2. Confirm that Git and Python 3.11+ are available.
3. Confirm write access to a development folder, the vault, and the current user's cache.
4. Review [docs/migration.md](docs/migration.md).
5. Inspect the vault and approve a file-by-file plan before the agent writes.

```bash
git --version
python --version
git clone https://github.com/skyflyt/mindwell
cd mindwell
python -m venv .venv
```

Install from the virtual environment without requiring activation:

```powershell
# Windows
.venv\Scripts\python.exe -m pip install -e .
.venv\Scripts\mindwell.exe doctor "<VAULT_PATH>"
.venv\Scripts\mindwell.exe index "<VAULT_PATH>"
```

```bash
# macOS
.venv/bin/python -m pip install -e .
.venv/bin/mindwell doctor "<VAULT_PATH>"
.venv/bin/mindwell index "<VAULT_PATH>"
```

### Fresh-agent prompt for an existing standard vault

```text
Upgrade my existing second-brain vault at <VAULT_PATH> to the standard lexical Mindwell setup using https://github.com/skyflyt/mindwell.

Read Mindwell's AGENTS.md, README.md, SECURITY.md, and docs/migration.md before acting. Confirm that I have a current backup. Detect Windows or macOS and check the Level 1 prerequisites: Git, Python 3.11+, GitHub access, virtual-environment support, and write access to user folders. Do not request administrator rights, change execution policy, disable security controls, install Ollama, or configure a cloud service. Use GitHub's source ZIP if Git is unavailable and downloads are permitted.

Inspect my vault without changing it. Identify the current agent name, identity file, instructions, memory files, source folders, wiki structure, and configuration. Preserve the existing agent identity and useful rules. Keep LOBY.md and config/loby.json if they exist. Do not move, rename, delete, summarize, or rewrite source notes. Show me every proposed file addition or modification and wait for my approval.

After approval, install Mindwell in a separate user-writable folder with a project-local virtual environment. Call the environment's executables directly without activation. Add only missing framework components and use lexical retrieval. Run mindwell doctor, build the external index, and test at least three grounded questions whose answers exist in the vault. Report the operating system, prerequisites, files changed, compatibility files retained, index location, retrieval results, rollback steps, and any policy blocker.
```

## Existing vault: Enhanced Ollama setup

Choose this path to add local semantic retrieval to any existing vault, including an earlier second brain that has never used Ollama. Complete the standard prerequisites above, then check the Level 2 requirements.

### Enhanced prerequisites

1. Confirm that the computer has enough memory and storage for Ollama and an embedding model.
2. Check whether Ollama is already installed and whether a compatible embedding model is available.
3. Ask before installing Ollama or downloading a model.
4. Stop if company policy blocks Ollama, background model services, or downloads.

```bash
ollama --version
ollama list
```

After Mindwell's base installation succeeds:

```powershell
# Windows
.venv\Scripts\python.exe -m pip install -e ".[semantic]"
ollama pull qwen3-embedding:0.6b
.venv\Scripts\mindwell.exe configure "<VAULT_PATH>" --provider ollama
.venv\Scripts\mindwell.exe doctor "<VAULT_PATH>"
.venv\Scripts\mindwell.exe index "<VAULT_PATH>" --rebuild
```

```bash
# macOS
.venv/bin/python -m pip install -e ".[semantic]"
ollama pull qwen3-embedding:0.6b
.venv/bin/mindwell configure "<VAULT_PATH>" --provider ollama
.venv/bin/mindwell doctor "<VAULT_PATH>"
.venv/bin/mindwell index "<VAULT_PATH>" --rebuild
```

If Ollama fails, restore lexical retrieval with the matching virtual-environment path:

```bash
mindwell configure "<VAULT_PATH>" --provider lexical
mindwell index "<VAULT_PATH>" --rebuild
```

### Fresh-agent prompt for an existing vault with Ollama

```text
Upgrade my existing second-brain vault at <VAULT_PATH> to Mindwell with local Ollama semantic retrieval using https://github.com/skyflyt/mindwell. This vault may have no previous Ollama setup.

Read Mindwell's AGENTS.md, README.md, SECURITY.md, and docs/migration.md before acting. Confirm that I have a current backup. Detect Windows or macOS. Check all Level 1 prerequisites first: Git, Python 3.11+, GitHub access, virtual-environment support, and write access to user folders. Then check the Level 2 prerequisites: available memory and storage, Ollama installation, Ollama service access, and installed embedding models. Explain any missing prerequisite. Ask before installing Ollama or downloading qwen3-embedding:0.6b. Do not request administrator rights, bypass company policy, change execution policy, disable security controls, configure a remote embedding service, or send vault content outside this machine.

Inspect my vault without changing it. Identify the current agent name, identity file, instructions, memory files, source folders, wiki structure, and configuration. Preserve the existing agent identity and useful rules. Keep LOBY.md and config/loby.json if they exist. Do not move, rename, delete, summarize, or rewrite source notes. Show me every proposed file addition or modification, Ollama installation action, and model download, then wait for my approval.

After approval, install Mindwell in a separate user-writable folder with a project-local virtual environment. Call the environment's executables directly without activation. Add only missing framework components. Install the semantic dependency, prepare Ollama and the approved embedding model, configure the ollama provider, run mindwell doctor, and rebuild the external index. Test at least three grounded questions and report the operating system, prerequisites, model, files changed, compatibility files retained, index location, retrieval results, rollback steps, and any policy blocker.

If Ollama cannot pass the checks, restore lexical retrieval, rebuild the index, verify that lexical retrieval works, and explain the failed prerequisite.
```

If you received an earlier prompt but never created a vault, use Level 1 or Level 2 instead.

See [BOOTSTRAP.md](BOOTSTRAP.md) for shorter prompt variants.

## Context modes

| Mode | Pages | Context budget | Intended use |
| --- | ---: | ---: | --- |
| quick | 3 candidates / 2 chunks | 4,200 chars | names, IDs, simple current facts |
| standard | 5 / 3 | 7,500 chars | ordinary grounded questions |
| deep | 10 / 6 | 16,000 chars | synthesis and contradiction research |

## Vault layers

```text
Sources: daily/ projects/ meetings/ people/ clippings/
                    ↓ ingest and reconcile
Synthesis: wiki/topics/ wiki/entities/ wiki/projects/ wiki/questions/
                    ↓ route by intent and authority
Current state: wiki/now.md wiki/action-items.md wiki/decisions.md
```

## Commands

```bash
mindwell init PATH [--agent-name NAME]
mindwell index PATH [--rebuild]    # incremental chunk/FTS/vector index
mindwell retrieve PATH QUERY       # ranked chunks + manifest
mindwell benchmark PATH tests.json # source-level retrieval regression test
mindwell contradictions PATH       # compile structured uncertainty registry
mindwell doctor PATH               # check Python, FTS5, provider, and Ollama
mindwell configure PATH --provider lexical|ollama
```

Indexes live outside the vault by default; never sync a live SQLite database through OneDrive, Dropbox, or iCloud.

## Project status

This repository is the clean-room, generic framework. It contains no source notes or Git history from the private vault that inspired it. See [docs/architecture.md](docs/architecture.md), [docs/migration.md](docs/migration.md), and [SECURITY.md](SECURITY.md).

## License

MIT
