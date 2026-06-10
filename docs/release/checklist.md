# Release Checklist

1. Ensure the working tree is clean.
2. Run `uv run python scripts/validate_repo.py`.
4. Run `mkdocs build --strict`.
5. Review `CHANGELOG.md` and keep `## Unreleased` current.
6. Run `git release-audit`.
7. Create and push a `vX.Y.Z` tag when ready.
8. Confirm the GitHub release workflow publishes the built artifacts.
