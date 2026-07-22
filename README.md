# SaniKey

[![PyPI](https://img.shields.io/pypi/v/sanikey.svg)](https://pypi.org/project/sanikey/)

<p align="center">
  <a href="https://github.com/marco0560/sanikey">
    <img src="https://raw.githubusercontent.com/marco0560/sanikey/main/immagini/SaniKey-logo-horizontal-transparent.svg" alt="SaniKey" width="360">
  </a>
  <a href="https://github.com/marco0560/sanikey">
    <img src="https://raw.githubusercontent.com/marco0560/sanikey/main/immagini/SaniKey-icon-transparent.svg" alt="Icona SaniKey" width="48">
  </a>
</p>

SaniKey prepara un archivio sanitario personale, consultabile localmente da
browser e copiabile su una chiavetta USB. I documenti clinici restano sul tuo
computer e sulla chiavetta: il programma non richiede un server né un account
online per la consultazione.

Il repository pubblico contiene codice ed esempi sintetici. Non inserire mai
nel repository documenti reali, nomi di pazienti o percorsi privati.

## Prima chiavetta in breve

Occorrono Linux, [uv](https://docs.astral.sh/uv/) e una chiavetta già montata.
Poi:

```bash
git clone https://github.com/marco0560/sanikey.git
cd sanikey
uv run python scripts/bootstrap_dev_environment.py
mkdir -p config
cp docs/config-example/accounts.toml config/accounts.toml
```

Completa `config/accounts.toml` con i percorsi privati, prepara i metadati e i
documenti del paziente, quindi esegui:

```bash
uv run sanikey validate-config
uv run sanikey scan-documents --preflight
uv run sanikey build-all --mode full
uv run sanikey export-usb /media/NOME_CHIAVETTA
uv run sanikey validate-usb /media/NOME_CHIAVETTA
```

La guida completa, inclusi metadati da curare, fogli illustrativi AIFA e
controlli prima della consegna, è in [Prima chiavetta USB](docs/first-usb-key.md).

## Cosa fa oggi

- organizza e indicizza documenti locali per più pazienti;
- rende consultabili offline documenti, terapia, fogli illustrativi AIFA,
  osservazioni e studi DICOM;
- genera una pagina USB statica adatta anche a un computer non preparato.

Le funzionalità sperimentali o non ancora complete sono raccolte separatamente
in [Limiti e sviluppi futuri](docs/limits-and-future-work.md): non fanno parte
del percorso operativo consigliato.

## Per sviluppatori e rilasci

```bash
uv run python scripts/validate_repo.py
uv run mkdocs build --strict
git release-audit
```

Il comando `sanikey` è l'interfaccia utente documentata. L'esecuzione
`python -m sanikey` è destinata a sviluppo e diagnostica.
