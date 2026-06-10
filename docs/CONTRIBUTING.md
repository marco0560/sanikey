# Contributing

## Validation

Run the standard validation surface before committing:

```bash
uv run python scripts/validate_repo.py
```

`scripts/validate_repo.py` is the authoritative validation entry point. It routes tools through `scripts/run_repo_tool.py` so cache and temporary state stay outside the checkout.

## Bootstrap

A fresh clone should be initialized with the repository bootstrap script:

```bash
uv run python scripts/bootstrap_dev_environment.py
```

## Git aliases

The repository installs local Git aliases for common project tasks. Use
`git config --local --get-regexp '^alias\.'` to inspect the current set.

## Release discipline

Before pushing a release tag, run:

```bash
git release-audit
```

The conservative release contract is documented in `docs/release/checklist.md`
and `docs/release/process.md`.

## Commit format

The repository uses a local commit-msg hook enforcing:

```text
type(scope): summary
```

Allowed types are `feat`, `fix`, `docs`, `perf`, `refactor`, `test`, `chore`,
and `style`. Scopes are restricted by `.githooks/commit-msg.py`.
