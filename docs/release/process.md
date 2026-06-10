# Release Process

This template uses a conservative tag-driven release flow.

## Local checks

Before creating a release tag, verify the repository is in a publishable state:

```bash
git release-audit
```

That guard checks:

- clean working tree
- staged state is empty
- branch is not behind its upstream
- latest version tag is an ancestor of `HEAD`
- `CHANGELOG.md` still contains an `Unreleased` section

## Tagging

Release tags must match `vX.Y.Z`.

Example:

```bash
git tag v0.2.0
git push --follow-tags
```

The template also provides `scripts/tag_guard.sh` for standalone validation of a
proposed tag.

## GitHub Actions

The generated repository ships with a release workflow that triggers on pushed
version tags and publishes the built distribution artifacts as a GitHub release.
