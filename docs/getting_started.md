# Avvio Sviluppo

## Creare l'Ambiente Locale di Sviluppo

```bash
uv run python scripts/bootstrap_dev_environment.py
```

Lo script di bootstrap crea `.venv`, installa il pacchetto in modalità
modificabile con le dipendenze di sviluppo e MkDocs, installa la configurazione
Git locale del repository ed esegue la superficie standard di validazione salvo
richiesta contraria.

## Configurazione Git Gestita dal Repository

Il processo di bootstrap installa la configurazione Git locale per questo
repository, inclusi:

- hook versionati da `.githooks/`
- template di commit da `.gitmessage`
- alias locali autorizzati come `git clean-repo`, `git gen-cheatsheet`,
  `git release-audit` e `git release`

## Flusso del Primo Giorno

Dopo il bootstrap, il flusso locale normale è:

```bash
uv run python scripts/validate_repo.py
NO_MKDOCS_2_WARNING=1 uv run mkdocs build --strict
```

Il comando CLI installato è l'interfaccia utente autorevole. L'esecuzione diretta
`python -m sanikey ...` è supportata principalmente per sviluppo e debug.
