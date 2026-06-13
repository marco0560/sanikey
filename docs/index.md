# SaniKey

SaniKey costruisce un archivio medico locale consultabile da browser ed
esportabile su chiavetta USB. Il repository contiene solo codice,
documentazione ed esempi sintetici; i dati reali dei pazienti e i percorsi
locali restano fuori dal repository pubblicato.

## Da Dove Iniziare

- [Guida utente](user-guide.md): usare SaniKey per un archivio paziente.
- [Esempi](examples.md): ispezionare la struttura degli esempi pubblicabili.
- [Avvio sviluppo](getting_started.md): configurare un checkout di sviluppo.
- [Architettura](architecture.md): comprendere la pipeline implementata.
- [Decisioni iniziali](decisions/decisioni-iniziali.md): consultare le ADR del
  progetto.

<!-- cheatsheet:start -->
## Comandi Principali

- `uv run python scripts/bootstrap_dev_environment.py`
- `uv run python scripts/validate_repo.py`
- `mkdocs build --strict`
<!-- cheatsheet:end -->

## Documentazione Pubblicata

La documentazione è organizzata per GitHub Pages con MkDocs:

- il materiale utente spiega configurazione, build, export USB e ripristino;
- il materiale sviluppatore documenta setup del repository, architettura,
  script, regole di contribuzione e processo di rilascio;
- specifiche e decisioni conservano le scelte usate per costruire la prima
  implementazione.
