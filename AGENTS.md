# AGENTS.md — SaniKey

## Repository and data boundaries

- `src/sanikey/`: Python package and CLI; `tests/`: behavior contract;
  `docs/`: documentation, ADRs, process, examples, and release material;
  `scripts/`: repository automation.
- `config/` may contain ignored/private local account and dictionary settings.
  `local-data/` contains ignored/private real patient data and generated output;
  `exports/` contains USB/export artifacts. Treat all as sensitive.
- `immagini/` contains UI assets; `.githooks/` and `.github/workflows/` own
  Git/CI policy; `.codira/` is ignored Codira state.

The project uses uv, targets Python 3.13, and exposes
`sanikey = sanikey.__main__:main`.

## Local requirements

- Keep end-user documentation, messages, and errors in Italian unless the
  relevant file deliberately uses another language.
- For public workflow or CLI changes, update code, tests, documentation, and
  examples together.
- `sanikey-usb-browser-audit` is required for mounted USB export audits; it is
  read-only unless the user separately requests a fix.
- Codira is available for non-trivial work. Refresh its index after tracked
  edits before making new indexed queries.

## Validation and commits

```bash
uv run python scripts/validate_repo.py
```

Allowed commit types are `feat`, `fix`, `docs`, `perf`, `refactor`, `test`,
`chore`, and `style`. The allowed scopes are `bootstrap`, `build`, `ci`, `cli`,
`config`, `core`, `coverage`, `curation`, `decision`, `dev`, `docs`,
`enrichment`, `generation`, `git`, `ingestion`, `process`, `release`,
`scaffold`, `schema`, `template`, `tests`, `validation`, and `version`.
