# Lista di Controllo del Rilascio

## Prima del tag

1. Verificare che non esistano dati sanitari, percorsi privati o credenziali
   nel diff e che l'albero di lavoro sia pulito dopo il commit di release.
2. Revisionare questa release in `CHANGELOG.md`, lasciando una nuova sezione
   `## Unreleased` vuota per il lavoro successivo.
3. Eseguire:

   ```bash
   uv run python scripts/validate_repo.py
   NO_MKDOCS_2_WARNING=1 uv run mkdocs build --strict
   git release-audit
   ```

4. Creare e inviare il tag annotato `v0.8.0` solo quando i controlli sono
   positivi.

## TestPyPI

5. Configurare su TestPyPI il trusted publisher
   `marco0560/sanikey`, workflow `.github/workflows/release.yml`, environment
   `testpypi`. Avviare manualmente il workflow `Release` sul tag `v0.8.0` con
   destinazione `testpypi`.
6. In un ambiente pulito, installare e provare esattamente l'artefatto
   pubblicato:

   ```bash
   uv venv /tmp/sanikey-testpypi
   uv pip install --python /tmp/sanikey-testpypi/bin/python \
     --index-url https://test.pypi.org/simple/ \
     --extra-index-url https://pypi.org/simple/ sanikey==0.8.0
   /tmp/sanikey-testpypi/bin/sanikey --help
   ```

## PyPI e GitHub

7. Configurare su PyPI lo stesso trusted publisher con environment `pypi`,
   rieseguire il workflow sullo stesso tag con destinazione `pypi`, quindi
   verificare installazione da PyPI. Controllare infine la release GitHub,
   gli artefatti allegati e la documentazione pubblicata.
