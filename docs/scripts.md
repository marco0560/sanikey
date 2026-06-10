# Scripts

## `scripts/bootstrap_dev_environment.py`

Synchronize the uv-managed environment, configure local Git state, and
optionally run validation.

This script verifies the repository root and runs `uv pip check` after
dependency synchronization.

## `scripts/install_repo_git_config.py`

Install the repo-local Git configuration expected by the generated project,
including hooks, commit template, and sanctioned aliases.

## `scripts/run_repo_tool.py`

Run sanctioned repository tools with cache and temporary state outside the
checkout.

## `scripts/validate_repo.py`

Run the standard local validation sequence through `scripts/run_repo_tool.py`.

Status:

- installed as `git check` by the bootstrap script
- runs the test suite under coverage and emits `.coverage-report.json`
- excludes Semgrep by default; regenerate with `--with-semgrep` to opt in

## `scripts/coverage_summary.py`

Render a compact coverage summary from `.coverage-report.json` and enforce the
repository coverage threshold.

## `scripts/clean_repo.py`

Remove ignored build and cache artifacts while preserving protected local
folders such as `.venv`.

## `scripts/generate_cheatsheet.py`

Regenerate `docs/cheatsheet.md` from marked documentation fragments.

## `scripts/new_decision.py`

Create a new decision note in `docs/decisions/` and update the index.

## `scripts/pyproject_lint.py`

Run deterministic structural validation for `pyproject.toml`.

## `scripts/release_audit.sh`

Run conservative release safety checks before pushing tags or publishing.

This script is the implementation behind `git release-audit`.

## `scripts/tag_guard.sh`

Validate that a release tag matches the expected `vX.Y.Z` pattern.

## `scripts/changelog_guard.sh`

Validate that `CHANGELOG.md` contains the expected `Unreleased` section.
