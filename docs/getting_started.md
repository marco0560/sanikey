# Avvio Sviluppo

## Creare l'Ambiente Locale di Sviluppo

```bash
python3 scripts/bootstrap_dev_environment.py
```

Lo script di bootstrap crea `.venv`, installa il pacchetto in modalità
modificabile con le dipendenze di sviluppo e MkDocs, installa la configurazione
Git locale del repository ed esegue la superficie standard di validazione salvo
richiesta contraria. Su Fedora installa, previa richiesta di `sudo`, gli
strumenti host mancanti dichiarati in `pyproject.toml` (`uv` e `pandoc`), quindi
installa o riusa Python 3.13 gestito da uv. Può essere rieseguito senza effetti
collaterali quando l'ambiente è già pronto.

## Configurazione Git Gestita dal Repository

Il processo di bootstrap installa la configurazione Git locale per questo
repository, inclusi:

- hook versionati da `.githooks/`
- template di commit da `.gitmessage`
- alias locali autorizzati come `git clean-repo`, `git gen-cheatsheet`,
  `git release-audit`, `git release-check` e `git rel`

## Flusso del Primo Giorno

Dopo il bootstrap, il flusso locale normale è:

```bash
uv run python scripts/validate_repo.py
NO_MKDOCS_2_WARNING=1 uv run mkdocs build --strict
```

Il comando CLI installato è l'interfaccia utente autorevole. L'esecuzione diretta
`python -m sanikey ...` è supportata principalmente per sviluppo e debug.
