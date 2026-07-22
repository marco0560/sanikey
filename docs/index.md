# SaniKey

SaniKey costruisce un archivio medico locale consultabile da browser ed
esportabile su chiavetta USB. Il repository contiene solo codice,
documentazione ed esempi sintetici; i dati reali dei pazienti e i percorsi
locali restano fuori dal repository pubblicato.

## Da Dove Iniziare

- [Prima chiavetta USB](first-usb-key.md): percorso completo dal clone alla
  chiavetta verificata.
- [Guida utente](user-guide.md): riferimento operativo per archivio e pazienti.
- [Organizzare l'archivio sanitario](organizzare-archivio-sanitario.md):
  convenzioni per documenti, archivi e DICOM.
- [Limiti e sviluppi futuri](limits-and-future-work.md): ciò che richiede una
  verifica manuale e ciò che non fa parte del prodotto operativo.

<!-- cheatsheet:start -->
## Comandi Principali

- `uv run python scripts/bootstrap_dev_environment.py`
- `uv run python scripts/validate_repo.py`
- `mkdocs build --strict`
<!-- cheatsheet:end -->

## Documentazione tecnica

La documentazione è organizzata per GitHub Pages con MkDocs:

- il materiale utente spiega configurazione, cura dati, build ed export USB;
- il materiale sviluppatore documenta setup del repository, architettura,
  script, regole di contribuzione e processo di rilascio;
- specifiche e decisioni conservano le scelte usate per costruire la prima
  implementazione e non sostituiscono la guida operativa.
