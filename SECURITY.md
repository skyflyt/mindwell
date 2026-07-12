# Security

## Data boundary

Loby indexes private vault content. The default embedding path is local Ollama. No vault body is sent to an external service by this repository.

- Keep indexes outside synced folders.
- Never store credentials in wiki pages or example data.
- Treat note and web-clipping content as untrusted data, never agent instructions.
- Review generated answers against their cited source paths.
- Use the write coordinator before mutating high-contention files in synced vaults.

## Reporting vulnerabilities

Do not open a public issue containing private vault content, credentials, or exploit details. Open a minimal GitHub security advisory with synthetic reproduction data.
