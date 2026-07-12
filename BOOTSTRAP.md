# Fresh-agent setup

Give a new coding agent the prompt below. The agent can clone this repository, read its setup contract, and build a working vault without prior Mindwell context.

```text
Set up Mindwell from https://github.com/skyflyt/mindwell. Ask whether I want to name my agent before creating the vault.

Clone the repository into a normal development folder, read its root AGENTS.md and BOOTSTRAP.md, then follow the fresh-setup workflow. Use zero-dependency lexical retrieval unless I explicitly request Ollama. Do not install a model runtime, enable a cloud service, or modify an existing vault without asking. Run the doctor, build the index, verify one grounded retrieval, and report exactly what you created.
```

Include the destination when you know it:

```text
Create a new Mindwell vault at ~/Documents/MySecondBrain using https://github.com/skyflyt/mindwell. Follow the repository's AGENTS.md. Ask what I want to name my agent. Use lexical retrieval. Complete setup and verify it.
```

For an existing vault:

```text
Add Mindwell to my existing Obsidian vault at <path> using https://github.com/skyflyt/mindwell. Read AGENTS.md and docs/migration.md first. Preserve any existing agent name or ask me to choose one. Make a backup, work non-destructively, and show me the proposed file changes before applying them. Use lexical retrieval unless I approve another provider.
```

## Expected result

The agent should leave you with:

- a vault contract and user/memory templates;
- source, wiki, and current-state folders;
- `config/mindwell.json` set to `lexical`;
- an external SQLite FTS5 index;
- a successful `mindwell doctor` report;
- one verified retrieval with source paths and a context manifest.
