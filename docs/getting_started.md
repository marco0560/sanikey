# Getting Started

## Create the local development environment

```bash
uv run python scripts/bootstrap_dev_environment.py
```

The bootstrap script creates `.venv`, installs editable development and
MkDocs dependencies, installs repo-local Git configuration, and runs the
standard validation surface unless skipped.

## Repository-owned Git setup

The bootstrap process installs local Git configuration for this repository,
including:

- versioned hooks from `.githooks/`
- the commit template from `.gitmessage`
- sanctioned local aliases such as `git clean-repo`,
  `git gen-cheatsheet`, `git release-audit`, and `git release`

## First-day workflow

After bootstrap, the normal local workflow is:

```bash
uv run python scripts/validate_repo.py
mkdocs build --strict
```

The installed CLI command is the authoritative user-facing interface. Direct
`python -m sanikey ...` execution is supported primarily for
development and debugging.
