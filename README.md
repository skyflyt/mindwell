# Loby Framework

A source-preserving personal operating system for AI agents.

Loby turns an ordinary Markdown/Obsidian vault into a compounding knowledge system that maintains current state without erasing history. It is not another chat window over notes: it provides structured ingestion, local hybrid retrieval, authority-aware ranking, token-budgeted context, contradiction tracking, regression benchmarks, and safe multi-writer coordination.

## Why it is different

- **Sources stay sources.** Daily notes, projects, meetings, and clippings are never rewritten to fit the wiki.
- **Synthesis compounds.** Agents maintain a linked wiki with visible citations.
- **Current truth is explicit.** Current-state pages rank above stale evidence for current questions; historical questions keep historical evidence.
- **Retrieval is tested.** A known-answer benchmark measures source recall, MRR, context size, latency, answers, and citations separately.
- **Context has a budget.** Quick, standard, and deep modes prevent accidental whole-vault loading.
- **Uncertainty is first-class.** Contradictions and evidence gaps remain linked to their competing sources.
- **Writes are coordinated.** Local locks, shared leases, and committed hashes can reject stale synced replicas before mutation.

The architecture was validated in a real operational vault. In its reference evaluation, authority-aware chunk retrieval improved source recall@5 from 60% to 100% and MRR from 0.459 to 0.701 while using bounded context. The included example data is entirely fictional.

## Quick start

Requirements: Python 3.11+, [Ollama](https://ollama.com/), and an embedding model such as `qwen3-embedding:0.6b`.

```bash
git clone https://github.com/skyflyt/loby-framework
cd loby-framework
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e .
ollama pull qwen3-embedding:0.6b

loby init ~/MySecondBrain
loby index ~/MySecondBrain
loby retrieve ~/MySecondBrain "What is the current project risk?" --mode standard --explain
```

Open the generated folder as an Obsidian vault, then customize `LOBY.md`, `USER.md`, and `config/loby.json`. Point any Agent Skills-compatible coding agent at the vault and tell it to read `AGENTS.md`.

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
loby init PATH                     # scaffold a new vault
loby index PATH [--rebuild]        # incremental chunk/FTS/vector index
loby retrieve PATH QUERY           # ranked chunks + manifest
loby benchmark PATH tests.json     # source-level retrieval regression test
loby contradictions PATH           # compile structured uncertainty registry
```

Indexes live outside the vault by default; never sync a live SQLite database through OneDrive, Dropbox, or iCloud.

## Project status

This repository is the clean-room, generic framework. It contains no source notes or Git history from the private vault that inspired it. See [docs/architecture.md](docs/architecture.md), [docs/migration.md](docs/migration.md), and [SECURITY.md](SECURITY.md).

## License

MIT
