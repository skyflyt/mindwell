# Releasing Mindwell

Users install the newest tagged GitHub release. The `main` branch is a development
channel and should not be presented as stable.

## Release checklist

1. Confirm `pyproject.toml` and `mindwell.__version__` match.
2. Run the complete test suite and a clean, non-editable package installation.
3. Review migration notes and update the setup contract when behavior changes.
4. Merge the release-ready changes to `main`.
5. Create and push an annotated tag such as `v0.3.0`.

The release workflow verifies that the tag matches the package version, runs tests,
builds a wheel and source archive, and attaches both to a GitHub release. Do not reuse
or move a published version tag.

Fresh setup agents should inspect the repository contract, resolve the newest release
tag, and install its wheel in a user-owned virtual environment. If no release exists,
they must identify `main` as prerelease and ask before proceeding.
