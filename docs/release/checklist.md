# Lista di Controllo del Rilascio

## Prima della push controllata

1. Verificare che non esistano dati sanitari, percorsi privati o credenziali
   nel diff e che l'albero di lavoro sia pulito dopo il commit di release.
2. Revisionare questa release in `CHANGELOG.md`, lasciando una nuova sezione
   `## Unreleased` vuota per il lavoro successivo.
3. Eseguire:

   ```bash
   uv run python scripts/validate_repo.py
   NO_MKDOCS_2_WARNING=1 uv run mkdocs build --strict
   git release-audit
   git release-check
   ```

4. Inviare `main` soltanto tramite `git rel` quando i controlli sono positivi.
   Non creare manualmente il tag: la CI calcola versione, changelog e tag da
   commit `feat`/`fix` e dalle modifiche incompatibili.

## Dopo il workflow GitHub

5. Verificare che la release GitHub abbia il tag `vX.Y.Z`, il changelog
   aggiornato e le note generate da Semantic Release.
6. Aggiornare il checkout locale e confermare la versione:

   ```bash
   git pull --ff-only
   uv sync
   uv run sanikey -V
   ```
