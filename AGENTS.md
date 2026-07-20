# AGENTS.md — SaniKey Agent Contract

Operate from repository evidence, not memory. Source-of-truth order:

1. repository files;
2. tests;
3. docs;
4. user instructions.

Hard fail on missing information that cannot be derived locally. Do not broaden
scope, refactor unrelated code, rename public symbols, or change CLI behavior
unless the task requires it.

## Repository Structure

- `src/sanikey/` — Python package and CLI implementation.
- `tests/` — pytest behavior contract.
- `docs/` — MkDocs docs, ADRs, process docs, examples, release docs.
- `scripts/` — repo automation and validation entry points.
- `config/` — local account and dictionary configuration; may be ignored/private.
- `local-data/` — real local patient data and generated outputs; ignored/private.
- `exports/` — USB/export artifacts; ignored/private
- `immagini/` — UI image assets.
- `.githooks/` — repo git hooks.
- `.github/workflows/` — CI, docs, release.
- `.codira/` — Codira index/config artifacts; ignored

The project is uv-backed:

- use `uv run ...` for repository commands;
- Python target is 3.13;
- the CLI entry point is `sanikey = sanikey.__main__:main`.

## Documentation

For current third-party library, framework, SDK, or tool documentation, use the
Context7 MCP server before relying on model memory. Use it especially for
version-sensitive APIs, configuration syntax, setup steps, or package behavior.
For OpenAI products, Codex behavior, OpenAI APIs, Apps SDK, or OpenAI
documentation, use the OpenAI developer documentation MCP server instead.

## Skills And Tooling

At task start, check available Codex skills and use applicable ones. Required:

- `deterministic-change-workflow` for non-trivial code changes, bug fixes, and feature work;
- `planning-refinement-gate` for any plan before implementation;
- `numpy-docstring-enforcer` when modifying Python symbols;
- `commit-block-generator` for commits.
- `sanikey-usb-browser-audit` for mounted USB export audits with a headless
  browser; it is read-only unless the user separately requests a fix.

Codira is available. For non-trivial code work, orient before broad search or
edits:

```bash
uv run codira caps --json
uv run codira index
```

Use `sym`, `refs`, `calls`, or `ctx`; then read the referenced files. Use `rg`
only for follow-up or docs/text search. Refresh Codira (`uv run codira index`)
after tracked edits before new indexed queries.

## Change Discipline

- Preserve user work in dirty trees; do not revert unrelated changes.
- Use `apply_patch` for manual file edits.
- Keep documentation enduser-facing messages and errors in Italian unless a file
  explicitly uses another language by design.
- For Python edits, keep NumPy-style docstrings accurate for every modified
  symbol.
- For public workflow or CLI changes, update code, tests, docs, and examples in
  the same slice.

## Validation

The authoritative validation command is:

```bash
uv run python scripts/validate_repo.py
```

Run focused tests while iterating; run full validation before concluding tracked
changes.

## Commit Contract

Allowed types:

- `feat`, `fix`, `docs`, `perf`, `refactor`, `test`, `chore`, `style`

Allowed scopes:

- `bootstrap`, `build`, `ci`, `cli`, `config`, `core`, `coverage`,
  `curation`, `decision`, `dev`, `docs`, `enrichment`, `generation`, `git`,
  `ingestion`, `process`, `release`, `scaffold`, `schema`, `template`,
  `tests`, `validation`, `version`

First line format:

```text
type(scope): summary
```

The summary must be 1-72 characters. Include a descriptive commit body; do not
make subject-only commits for non-trivial work.
