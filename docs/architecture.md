# Architettura

SaniKey è una CLI Python locale che costruisce un archivio medico per paziente
e lo esporta in una struttura USB statica.

## Confine del Repository

Il repository GitHub contiene:

- codice sorgente sotto `src/sanikey`
- test sotto `tests`
- script sotto `scripts`
- documentazione sotto `docs`
- esempi sintetici pubblicabili sotto `docs/*-example`

Il repository non deve contenere dati reali dei pazienti, nomi reali di
pazienti, documenti ospedalieri o nomi di directory locali private. Lo stato
operativo privato resta fuori dall'albero pubblicato o in directory ignorate
come:

- `config`
- `patients`
- `generated`
- `exports`
- `logs`

`config/accounts.toml` è privato e non contiene valori di percorso sicuri di
default.

## Flusso di Elaborazione

La pipeline implementata è:

1. Caricare e validare `config/accounts.toml`.
2. Applicare gli invarianti di privacy per percorsi privati e file paziente
   ignorati.
3. Eseguire la scansione dei documenti sorgente configurati.
4. Caricare i metadati curati.
5. Catalogare supporti DICOM e directory di espansione manuale.
6. Estrarre il testo supportato.
7. Costruire un archivio SQLite per paziente.
8. Generare export JSON.
9. Generare i file statici del frontend.
10. Esportare la build in una struttura USB e scrivere i checksum.

Il comando `deploy-usb` esegue la build dei pazienti abilitati e poi esporta la
struttura USB.

## Moduli Principali

- `config.py`: analizza e valida la configurazione privata degli account.
- `privacy.py`: controlla i confini di privacy del repository e i percorsi
  ignorati.
- `documents.py`: scansiona i documenti, calcola digest, estrae testo
  supportato e rileva duplicati.
- `metadata.py`: carica metadati curati da file TOML.
- `dicom.py`: cataloga supporti DICOM, legge DICOMDIR, raggruppa istanze per
  StudyInstanceUID e coalesce i record duplicati dello stesso studio prima
  della persistenza.
- `database.py`: scrive l'archivio SQLite.
- `exports.py`: scrive export JSON statici e il bundle dati JavaScript per
  ricerca, timeline e sommari.
- `frontend.py`: renderizza l'entrypoint web statico consultabile anche tramite
  `file://`.
- `build.py`: coordina la pipeline locale di build paziente e la cache
  incrementale dell'estrazione testo.
- `usb.py`: esporta e valida la struttura USB.
- `proposals.py`: salva proposte deterministiche da revisione manuale.
- `cli.py`: espone l'interfaccia a riga di comando.

## Modello di Paziente Configurato

Ogni voce `[[person]]` contiene:

- `id`: identificativo tecnico stabile in minuscolo.
- `display_name`: etichetta visualizzata negli artefatti generati.
- `source_documents`: percorso ai documenti sorgente, assoluto oppure relativo
  alla root del repository quando la configurazione e' `config/accounts.toml`.
- `metadata_directory`: percorso ai metadati curati, assoluto oppure relativo
  alla stessa base.
- `local_build`: percorso degli artefatti generati, assoluto oppure relativo
  alla stessa base.
- `usb_uuid`: UUID atteso del filesystem USB o identificativo di deploy.
- `enabled`: booleano opzionale, abilitato per default.

## Layout della Costruzione Locale

La radice di build locale è configurata per ciascun paziente. Una build genera
attualmente:

```text
medical_archive.db
checksums/
exports/
manifests/
reports/
web/
```

Il database generato e gli export statici sono artefatti derivati e possono
essere ricreati dai documenti sorgente e dai metadati curati.

## Struttura USB

La radice USB esportata contiene attualmente:

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

`web` è il frontend statico generato sulla chiavetta USB. Nel repository
corrisponde agli artefatti frontend generati da `frontend.py`.

## Funzionalità Rimandate

La prima implementazione lascia intenzionalmente fuori ambito diverse
funzionalità:

- provider AI reali
- espansione automatica o opzionale di ISO e archivi DICOM riconosciuti dal contenuto
- embedding semantici
- cifratura USB
- integrazione FHIR/HL7
- supporto mobile/PWA
- sincronizzazione cloud
- consultazione assistita da AI
- pacchettizzazione desktop
- import/export diretto dal Fascicolo Sanitario

Questi elementi sono tracciati come issue GitHub.
