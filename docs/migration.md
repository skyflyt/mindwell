# Migrating an existing vault

Run `mindwell recommend <vault-path>` after installing the current package. An
existing non-empty destination is classified as the existing-vault track. Back up the
vault, review the proposed additions, and approve them before initialization.

This guide is for bringing a vault that has never used Mindwell under the framework
for the first time. If the vault already has `config/installation.json` (it was set up
with `mindwell init` at some earlier version), you are not migrating it — you are
updating it. Use `mindwell upgrade <vault-path>` instead; see the "Updating an
existing installation" section of `AGENTS.md`. `recommend` tells the two cases apart
automatically and suggests the right command. Do not run `mindwell init` or
`mindwell init --force` against a vault that already has an `AGENTS.md` you have
customized — `init --force` repairs missing/untouched scaffold files but, like
`upgrade`, never overwrites `AGENTS.md` or a file you have modified.

## From Loby Framework

Mindwell keeps compatibility with vaults created before the project rename. It reads `config/loby.json`, recognizes `LOBY.md` as a core agent file, honors `LOBY_INDEX`, and installs the `loby` command as a temporary alias. New setups use `config/mindwell.json`, `AGENT.md`, `MINDWELL_INDEX`, and the `mindwell` command.

You can keep an existing personal `LOBY.md`. Agent names belong to each vault and do not need to match the framework name.

## From another vault structure

Do not copy your vault into this repository.

1. Back up the existing vault.
2. Run `mindwell init` against a new empty folder and inspect the structure.
3. Copy only the generic contract/rules you want into the existing vault.
4. Configure source folders and core/current paths in `config/mindwell.json`.
5. Build the external index.
6. Create a benchmark with 20–40 durable questions and authoritative source paths.
7. Compare retrieval before changing agent boot instructions.
8. Introduce wiki synthesis non-destructively; never move source notes merely to match the example structure.

Start with retrieval and citations. Add automated writes only after your source-of-truth and rollback rules are explicit.
