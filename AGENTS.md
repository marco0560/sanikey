# AGENTS.md — Generated Python CLI Repo Contract

## 0. Mission

You are operating on a generated Python CLI repository.

Priority:

1. Correctness
2. Test integrity
3. Reproducibility
4. Traceability
5. Minimality of change

Fluency is irrelevant.

## 1. Operating Mode

Mode: HARD-FAIL DETERMINISTIC

Rules:

- Never guess
- Never infer missing code
- Never reconstruct unseen files
- Never approximate behavior

If required information is missing:

-> STOP
-> Ask for clarification

## 2. Sources of Truth

Priority order:

1. Repository files
2. Tests (`tests/`) as the authoritative behavior contract
3. Project documentation (`docs/`)
4. User instructions

Previous assistant output is not a source of truth.

## 3. Repository-Specific Constraints

- Generated repositories are deterministic, test-driven engineering projects.
- Scope control is strict: do only what is requested.
- Do not refactor unrelated code, rename symbols, introduce stylistic churn, or
  modify public CLI behavior unless explicitly required.
- Prefer repository-owned automation over workstation-specific shell state.
- Stop immediately if requirements are ambiguous, file context is missing, or a
  change risks breaking the documented CLI or bootstrap contract.

## 4. Required Shared Skills

Use the following shared skills for the corresponding task classes:

- `deterministic-change-workflow` for non-trivial code changes, bug fixes, and
  feature work
- `numpy-docstring-enforcer` whenever modifying modules, classes, public
  functions, or private functions
- `commit-block-generator` when proposing the final commit block

If a required skill is unavailable, state that explicitly and apply the same
rules manually.

For any task where an available skill is explicitly named by the user or clearly
matches the task class, read that skill before acting and follow it. Required
repo skills listed above are mandatory; other applicable skills are still part
of the operating contract when available.

## 4.1 Codira Orientation

When the repository provides `codira`, use it to orient code exploration before
broad text search or large file reads.

Required sequence for non-trivial code work:

1. Run `uv run codira caps --json` to confirm the current command surface.
2. Run `uv run codira index` before indexed lookup.
3. Prefer narrow indexed queries such as `sym`, `refs`, `calls`, or `ctx` to
   identify the relevant modules and symbols.
4. Read the files indicated by Codira before editing.
5. Use `rg` for textual follow-up, documentation search, or when Codira cannot
   answer the question directly.

Using Codira only as a final audit is insufficient for code changes unless the
task is trivial and already localized by an explicit file path and symbol.

## 5. Validation Contract

Assume the following commands are the required validation surface:

```bash
uv run python scripts/validate_repo.py
```

`scripts/validate_repo.py` is the authoritative validation entry point. It routes tools through `scripts/run_repo_tool.py` so cache and temporary state stay outside the checkout.

All required checks must pass before concluding.

## 6. Generated Repo Baseline

A repository generated from `dev-template` should normally provide:

- a Python package under `src/`
- a CLI entrypoint
- tests
- MkDocs documentation
- repo-owned hooks and commit template
- a uv-managed local bootstrap script
- repo-local Git aliases installed by repository code
- GitHub Actions for CI, docs, and release
- conservative release scripts and documentation
- deterministic versioning and packaging metadata in `pyproject.toml`

## 7. Commit Contract

Commit messages must satisfy `.githooks/commit-msg.py`.

Allowed types:

- `feat`
- `fix`
- `docs`
- `perf`
- `refactor`
- `test`
- `chore`
- `style`

Allowed scopes:

- `build`
- `ci`
- `cli`
- `config`
- `core`
- `decision`
- `dev`
- `docs`
- `git`
- `release`
- `scaffold`
- `template`
- `tests`
- `validation`

The first line must match `type(scope): summary`, with an optional scope and a
summary length of 1 to 72 characters.

## 8. Session Stability

Monitor for context drift, assumption creep, and loss of file grounding.

If detected:

-> recommend RESET


## 9. Debugging Discipline

- reproduce first
- identify root cause
- avoid speculative fixes
- do not repeatedly retry the same failing approach
- if the same error is encountered twice:
  - research 3-5 plausible fixes
  - compare tradeoffs
  - choose the most efficient correct solution
  - implement deterministically
