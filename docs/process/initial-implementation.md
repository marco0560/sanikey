# Initial Implementation Ledger

This ledger tracks the phase-by-phase implementation of SaniKey v1.

Branch: `initial-implementation`

Note: the approved plan named `feat/initial-implementation`, but this checkout
has a Git ref namespace conflict for `feat/...`. The dedicated branch is
therefore `initial-implementation`.

Each phase can be checked only after code, tests, documentation, repository
validation, and the phase commit are complete.

## Deferred Items

The following items are out of scope for this initial implementation branch and
remain deferred by design:

* real local or remote AI providers;
* automatic or optional DICOM ISO/ZIP expansion;
* semantic embeddings beyond stable disabled interfaces;
* USB encryption;
* FHIR or HL7 integration;
* mobile or PWA packaging;
* cloud synchronization;
* AI-assisted consultation during archive use;
* desktop application packaging.

## Phase Ledger

| Phase | Scope | ADR Range | Done | Validation Evidence | Commit |
| ----- | ----- | --------- | ---- | ------------------- | ------ |
| 01 | Preflight and ledger | DA-001..DA-144 | [x] | `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/validate_repo.py` passed | `4b10c5b` |
| 02 | Core configuration and privacy guard | DA-008..DA-018, DA-113..DA-120 | [x] | `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/validate_repo.py` passed | `e10c88c` |
| 03 | Domain models and metadata contracts | DA-019..DA-053 | [x] | `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/validate_repo.py` passed | Pending |
| 04 | Document inventory and text extraction | DA-019..DA-040, DA-121..DA-124 | [ ] | Pending | Pending |
| 05 | DICOM catalog | DA-024, DA-086, DA-123 | [ ] | Pending | Pending |
| 06 | SQLite archive | DA-001..DA-003, DA-041..DA-045, DA-098 | [ ] | Pending | Pending |
| 07 | Build pipeline | DA-035..DA-040, DA-091..DA-103 | [ ] | Pending | Pending |
| 08 | AI proposal interface | DA-054..DA-060, DA-100, DA-117 | [ ] | Pending | Pending |
| 09 | Search, timeline, and summary exports | DA-061..DA-078, DA-099 | [ ] | Pending | Pending |
| 10 | Static frontend | DA-079..DA-090, DA-113..DA-115 | [ ] | Pending | Pending |
| 11 | USB export and deploy | DA-004..DA-005, DA-104..DA-112, DA-125..DA-129 | [ ] | Pending | Pending |
| 12 | Examples, docs, and final acceptance | DA-013, DA-130..DA-144 | [ ] | Pending | Pending |
