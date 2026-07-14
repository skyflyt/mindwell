# Fresh agent prompt

```text
Set up the latest tagged Mindwell release from https://github.com/skyflyt/mindwell.

Read the repository's AGENTS.md and BOOTSTRAP.md before acting. If no tagged release exists, identify `main` as prerelease and ask before using it. Ask whether I want to name my agent. Run `mindwell recommend <VAULT_PATH>` and follow its plan. Use lexical retrieval unless I explicitly request semantic retrieval. Build the index, run the doctor, then verify a grounded query. Ask before installing Ollama, using a cloud service, or changing any existing vault files.
```

For an IT-assisted personal second brain, use this version:

```text
Set up the latest tagged Mindwell release from https://github.com/skyflyt/mindwell at <VAULT_PATH> without
administrator rights. Read AGENTS.md and BOOTSTRAP.md first. Use the personal-ops
profile, the core automation bundle, lexical retrieval, and my local timezone. Run the
setup advisor, build the initial index, run the doctor, and verify a grounded query. Open START-HERE.md and
confirm I can use a folder-capable AI workspace with the vault selected. Show me every proposed
schedule and ask before registering it. Never enable automatic external sending.
```
