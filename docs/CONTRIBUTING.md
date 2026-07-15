# Contribuire

## Validazione

Esegui la superficie standard di validazione prima di committare:

```bash
uv run python scripts/validate_repo.py
```

`scripts/validate_repo.py` è l'entrypoint autorevole di validazione. Instrada
gli strumenti tramite `scripts/run_repo_tool.py`, in modo che cache e stato
temporaneo restino fuori dal checkout.

La validazione include un guard privacy sul contenuto che Git vede come
tracciato o nuovo non ignorato. Il guard blocca dati locali e path host-locali
che finirebbero nel commit; non sostituisce la revisione manuale di testi
clinici, log e screenshot.

## Inizializzazione

Un clone nuovo deve essere inizializzato con lo script di bootstrap del
repository:

```bash
uv run python scripts/bootstrap_dev_environment.py
```

## Alias Git

Il repository installa alias Git locali per le attività comuni del progetto.
Usa `git config --local --get-regexp '^alias\.'` per ispezionare l'insieme
corrente.

## Disciplina di Rilascio

Prima di inviare un tag di rilascio, esegui:

```bash
git release-audit
```

Il contratto conservativo di rilascio è documentato in
`docs/release/checklist.md` e `docs/release/process.md`.

## Formato dei Commit

Il repository usa un hook locale `commit-msg` che impone:

```text
type(scope): summary
```

I tipi consentiti sono `feat`, `fix`, `docs`, `perf`, `refactor`, `test`,
`chore` e `style`. Gli scope sono limitati da `.githooks/commit-msg.py`.
