# Lista di Controllo del Rilascio

1. Verificare che l'albero di lavoro sia pulito.
2. Eseguire `uv run python scripts/validate_repo.py`.
3. Eseguire `mkdocs build --strict`.
4. Revisionare `CHANGELOG.md` e mantenere aggiornata la sezione `## Unreleased`.
5. Eseguire `git release-audit`.
6. Creare e inviare un tag `vX.Y.Z` quando il rilascio è pronto.
7. Confermare che la procedura GitHub di rilascio pubblichi gli artefatti
   costruiti.
