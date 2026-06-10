# sanikey

Medical documents on a USB key

## Quick start

```bash
git init
uv run python scripts/bootstrap_dev_environment.py
```

The bootstrap script creates `.venv`, upgrades packaging tools, installs the
repository in editable mode with development dependencies, applies repo-local
Git configuration, and runs the standard validation surface unless skipped.

## Validation

```bash
uv run python scripts/validate_repo.py
```

`scripts/validate_repo.py` is the authoritative validation entry point. It routes tools through `scripts/run_repo_tool.py` so cache and temporary state stay outside the checkout.

## Documentation

```bash
mkdocs serve
```

## Release Safety

```bash
git release-audit
```

The release workflow and checklist are documented in `docs/release/`.

## Notes on direct module execution

Commands can also be executed directly via Python, for example:

```bash
python -m sanikey --help
```

This mode is supported primarily for development and debugging.

The installed CLI command (`sanikey`) is the authoritative and documented
user-facing interface.
