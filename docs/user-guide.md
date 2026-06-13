# Guida Utente

Questa guida descrive il flusso operativo attuale di SaniKey per costruire un
archivio medico locale ed esportarlo in una struttura USB.

## Confine dei Dati

Il repository pubblico non deve contenere dati personali, nomi reali di
pazienti, documenti clinici reali o percorsi locali privati. I dati reali
restano in directory locali referenziate da `config/accounts.toml`; la directory
`config` è esclusa da Git.

Gli esempi pubblicabili sotto `docs/config-example`, `docs/patients-example` e
`docs/generated-example` sono fixture di documentazione.

## Prerequisiti

Installa le dipendenze del progetto e gli strumenti del repository da un
checkout locale:

```bash
uv run python scripts/bootstrap_dev_environment.py
```

Esegui la validazione del repository prima di affidarti al checkout:

```bash
uv run python scripts/validate_repo.py
```

## Configurare i Pazienti

Crea un file di configurazione locale privato:

```bash
mkdir -p config
cp docs/config-example/accounts.toml config/accounts.toml
```

Modifica `config/accounts.toml` in modo che ogni percorso sia assoluto e
locale:

- `source_documents`: documenti originali ricevuti da ospedali o operatori.
- `metadata_directory`: file di metadati curati per il paziente.
- `local_build`: artefatti generati per il paziente.
- `usb_uuid`: UUID atteso del filesystem USB o identificativo di deploy.

Valida la configurazione e gli invarianti di privacy:

```bash
uv run sanikey validate-config --config config/accounts.toml
```

Elenca i pazienti abilitati:

```bash
uv run sanikey list-patients --config config/accounts.toml
```

## Preparare i Documenti Sorgente

Inserisci i file sorgente nella directory `source_documents` configurata per
ciascun paziente. L'implementazione attuale esegue scansione deterministica,
estrae il testo supportato, cataloga i supporti DICOM e registra i metadati in
un archivio SQLite generato.

I file ISO e ZIP DICOM consegnati dagli ospedali sono conservati come documenti
sorgente. L'espansione in directory DICOM è attualmente manuale; la scelta tra
espansione automatica, opzionale durante l'ingestion o manuale è una decisione
rimandata.

## Costruire un Archivio

Costruisci un singolo paziente:

```bash
uv run sanikey build-patient patient-a --config config/accounts.toml --mode full
```

Costruisci tutti i pazienti abilitati:

```bash
uv run sanikey build-all --config config/accounts.toml --mode full
```

La build scrive gli artefatti generati nella directory `local_build` configurata
per il paziente, inclusi:

- `medical_archive.db`
- export JSON
- file statici del frontend
- manifest, checksum e report di build

## Revisionare le Proposte

La prima implementazione include proposte deterministiche da revisionare
manualmente. I provider AI reali sono rimandati.

Genera le proposte:

```bash
uv run sanikey generate-proposals --config config/accounts.toml --patient patient-a
```

Approva o rifiuta una proposta:

```bash
uv run sanikey review-proposal --config config/accounts.toml patient-a PROPOSAL-ID approved
uv run sanikey review-proposal --config config/accounts.toml patient-a PROPOSAL-ID rejected
```

## Esportare su USB

Costruisci ed esporta tutti i pazienti abilitati verso una radice USB o una
directory simulata:

```bash
uv run sanikey deploy-usb --config config/accounts.toml /path/to/usb-root
```

Valida la struttura esportata:

```bash
uv run sanikey validate-usb /path/to/usb-root
```

Apri la pagina iniziale generata dalla radice USB:

```text
START-HERE-Patient-A.html
```

## Struttura USB

Un export USB generato contiene:

```text
SANIKEY-MANIFEST.json
START-HERE-Patient-A.html
patients/
  patient-a/
    documents/
    medical_archive.db
    web/
      index.html
```

`SANIKEY-MANIFEST.json` registra i pazienti esportati e i checksum usati da
`validate-usb`.

## Backup e Ripristino

L'export USB è un artefatto portatile di consegna, non il backup autorevole.
Esegui il backup delle directory sorgente private, delle directory dei metadati
curati, delle radici di build locali e di `config/accounts.toml` secondo la
policy operativa locale.

## Risoluzione dei Problemi

Usa prima questi controlli:

- `uv run sanikey validate-config --config config/accounts.toml`
- `uv run sanikey build-patient PATIENT-ID --config config/accounts.toml --mode full`
- `uv run sanikey validate-usb /path/to/usb-root`
- `uv run python scripts/validate_repo.py`

Gli errori di configurazione indicano di solito un file privato mancante, un
percorso non assoluto, un identificativo paziente non valido o una violazione
degli invarianti di privacy.
