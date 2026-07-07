# Guida Utente

Questa guida descrive il flusso operativo attuale di SaniKey per costruire un
archivio medico locale ed esportarlo in una struttura USB.

## Confine dei Dati

Il repository pubblico non deve contenere dati personali, nomi reali di
pazienti, documenti clinici reali o percorsi locali privati. I dati reali
restano in directory locali referenziate da `config/accounts.toml`; le directory
`config` e `local-data` sono escluse da Git.

Gli esempi pubblicabili sotto `docs/config-example`, `docs/patients-example` e
`docs/generated-example` sono fixture di documentazione.

## Prerequisiti

L'ingestione dati e' stabilizzata e supportata su Linux. La consultazione degli
artefatti statici generati resta indipendente dalla piattaforma, ma la pipeline
di ingestione su Windows non e' ancora parte del contratto operativo.

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

Modifica `config/accounts.toml` in modo che ogni percorso punti a una directory
locale privata. I percorsi possono essere assoluti oppure relativi alla root del
repository quando il file si trova in `config/accounts.toml`:

- `source_documents`: documenti originali ricevuti da ospedali o operatori.
- `metadata_directory`: file di metadati curati per il paziente.
- `local_build`: artefatti generati per il paziente.
- `usb_uuid`: UUID atteso del filesystem USB o identificativo di deploy.

Esempio locale:

```toml
[global]
config_version = 1

[[person]]
id = "marco"
display_name = "Marco Coppola"
source_documents = "local-data/marco/documents"
metadata_directory = "local-data/marco/metadata"
local_build = "local-data/generated/marco"
usb_uuid = "MANUAL-TEST-USB"
```

I percorsi dentro `local-data/` sono accettati perché la directory è ignorata da
Git. Percorsi dentro directory versionate del repository, per esempio `docs/` o
`src/`, vengono rifiutati.

Valida la configurazione e gli invarianti di privacy:

```bash
uv run sanikey validate-config --config config/accounts.toml
```

`validate-config` carica anche i metadati curati dei pazienti abilitati e
segnala prima della build errori come TOML non valido, id duplicati o terapie
che fanno riferimento a farmaci non presenti in `medications.toml`.

Elenca i pazienti abilitati:

```bash
uv run sanikey list-patients --config config/accounts.toml
```

## Preparare i Documenti Sorgente

Inserisci i file sorgente nella directory `source_documents` configurata per
ciascun paziente. L'implementazione attuale esegue scansione deterministica,
estrae il testo supportato, cataloga i supporti DICOM e registra i metadati in
un archivio SQLite generato.

Per verificare il numero di file rilevati senza stampare l'intero inventario:

```bash
uv run sanikey scan-documents --config config/accounts.toml
```

Il comando segnala anche warning rilevabili senza build completa, come
duplicati e file con estensione non supportata. Per impostazione predefinita
estrae anche i container supportati in
`local_build/staging/containers/`, cosi' il contenuto degli archivi puo' essere
verificato manualmente prima della build completa. Il riepilogo include
`staged_containers=`, `staged_members=` e `derived_documents=` quando lo staging
e' attivo. Prima della scansione viene ripetuto il controllo dei metadati curati
dei pazienti selezionati, cosi' un errore in `therapies.toml` blocca subito il
comando invece di emergere dopo una build lunga.
Su terminali interattivi, i passi lunghi stampano punti di avanzamento su
`stderr`, senza modificare l'output riepilogativo su `stdout`.
`scan-documents` stampa un punto ogni 20 file sorgente, lo staging un punto per
ogni container processato e il catalogo DICOM un punto ogni 50 record. Per
disattivarli:

```bash
uv run sanikey scan-documents --config config/accounts.toml --no-progress
```

Per eseguire una scansione solo inventariale, senza creare o aggiornare lo
staging dei container:

```bash
uv run sanikey scan-documents --config config/accounts.toml --no-stage-containers
```

Per eseguire anche controlli preliminari leggeri su archivi e documenti Office:

```bash
uv run sanikey scan-documents --config config/accounts.toml --preflight
```

`--preflight` non esegue OCR PDF e non converte documenti legacy Office, ma può
individuare prima della build archivi corrotti o documenti Office non leggibili.

Per ispezionare a schermo la lista dei documenti ingeriti:

```bash
uv run sanikey scan-documents --config config/accounts.toml --verbose
```

Per salvare l'inventario in un file riprocessabile:

```bash
uv run sanikey scan-documents --config config/accounts.toml --output local-data/scan.txt --format text
uv run sanikey scan-documents --config config/accounts.toml --output local-data/scan.csv --format csv
```

`--format` e' valido solo insieme a `--output`. Il formato `text` usa la riga
tab-separated estesa con paziente, tipo, categoria, data ISO, titolo, SHA256 e
path assoluto. Il formato `csv` usa gli stessi campi con intestazione.

Per verificare che i documenti sorgente non vengano modificati dalla pipeline,
creare uno snapshot prima della build, uno dopo la build e poi confrontarli:

```bash
uv run sanikey document-integrity before --config config/accounts.toml
uv run sanikey document-integrity after --config config/accounts.toml
uv run sanikey document-integrity check --config config/accounts.toml
```

Il comando usa i pazienti abilitati in `accounts.toml` e scrive per ciascun
`id` paziente i file `PATIENT-before.sha256`, `PATIENT-before-mtime.tsv`,
`PATIENT-after.sha256` e `PATIENT-after-mtime.tsv` nella directory `local-data`.
Usare `--patient` per limitare il controllo a un paziente e `--output-dir` per
salvare gli snapshot in un'altra directory.

Durante la build, SaniKey tenta di estrarre testo dai formati supportati:

- `.txt`: contenuto testuale diretto;
- `.md`: contenuto testuale diretto e rendering HTML Markdown nel frontend;
- `.pdf`: testo digitale con PyMuPDF e OCR con OCRmyPDF quando necessario;
- `.jpg`, `.jpeg`, `.png`: OCR immagine tramite `tesseract`;
- `.docx`, `.xlsx`, `.odt`, `.ods`: testo e celle tramite librerie Python;
- `.doc`, `.xls`: conversione tramite LibreOffice o `soffice`, se disponibile;
- `.zip`, `.7z`, `.rar`: inventario dei file contenuti nell'archivio.

Durante `scan-documents` e `build-patient`, gli archivi e le immagini disco
supportate vengono anche estratti in una staging area generata sotto
`local_build/staging/containers`. Il contenitore originale resta il documento
autorevole; i membri estratti sono documenti derivati con provenance verso il
contenitore, path interno e SHA256 proprio. Se un archivio è cifrato, corrotto o
non leggibile, il contenitore resta catalogato e il problema viene registrato
come warning.

I file ISO DICOM consegnati dagli ospedali sono conservati come documenti
sorgente. Gli archivi `.zip`, `.7z` e `.rar` sono trattati inizialmente come
archivi generici e promossi a supporti DICOM solo se contengono `DICOMDIR`, file
`.dcm`, path DICOM riconoscibili, immagini disco `.iso`/`.img`, ZIP annidati
con contenuto DICOM o file con magic bytes DICOM. Quando vengono estratti in
staging, eventuali immagini disco `.iso` o `.img` annidate vengono espanse a
loro volta. I file DICOM interni sono catalogati come DICOM e non passano
dall'OCR o dall'estrazione testo ordinaria.
Per le immagini disco SaniKey prova prima il comando `7z`; se il file è un ISO
valido ma `7z` non riesce ad aprirlo, ritenta con `bsdtar` quando disponibile.
Quando le istanze DICOM sono leggibili, SaniKey usa `pydicom` per raggrupparle
in studi clinici tramite `StudyInstanceUID`. Se è presente un `DICOMDIR`, i
record `STUDY` vengono usati per creare gli studi anche quando il supporto
contiene più arborescenze. Se lo stesso studio è rilevato sia dal `DICOMDIR` sia
dalle istanze DICOM, SaniKey conserva un solo record di studio prima della
scrittura nel database. I file DICOM privi di metadati leggibili restano
catalogati singolarmente come fallback diagnostico.
I file tecnici dei viewer inclusi nei supporti, per esempio runtime Java, DLL,
manuali, HTML di help o asset applicativi, restano tracciati nel manifest di
staging ma non entrano nella pipeline documentale ordinaria. Il manifest di
staging può essere molto grande perché registra ogni membro estratto dai
contenitori per audit e verifica manuale; non è un report compatto da leggere
integralmente in terminale.

Per i PDF, SaniKey sceglie automaticamente il provider:

- usa `PyMuPDF` (`fitz`) quando il PDF contiene testo digitale sufficiente;
- passa a `OCRmyPDF`, se disponibile come comando di sistema, quando PyMuPDF
  manca o produce testo vuoto/insufficiente.

`OCRmyPDF` è quindi una dipendenza di sistema supportata. Se nessun provider è
disponibile, il PDF resta catalogato ma l'estrazione testo viene saltata con un
warning esplicito sui provider mancanti o insufficienti.
Se OCRmyPDF fallisce durante l'ottimizzazione del PDF temporaneo, SaniKey ritenta
senza ottimizzazione perché usa solo il sidecar testuale. I warning registrati
nel report sono sintetici e non includono il log completo pagina-per-pagina del
tool esterno.

Il testo estratto con successo viene salvato nella tabella SQLite
`document_text` e indicizzato in `document_fts` insieme a titolo, categoria e
tag. I file DICOM restano esclusi dall'estrazione testo.
I documenti `.md` e i campi TOML documentati come Markdown, incluso
`clinical_summary.toml`, vengono convertiti in HTML durante la build. L'HTML
grezzo presente nel Markdown viene escapato; il frontend usa solo l'HTML
generato dalla pipeline.

Per le immagini, SaniKey usa il comando di sistema `tesseract`. Quando sono
disponibili i language pack `ita` ed `eng`, usa `ita+eng`; altrimenti ricade
sulla lingua predefinita di Tesseract. Se `tesseract` non e' installato,
l'immagine resta catalogata e il report contiene un warning di OCR saltato.

## Costruire un Archivio

Costruisci un singolo paziente:

```bash
uv run sanikey build-patient patient-a --config config/accounts.toml --mode full
```

Il comando stampa un riepilogo leggibile con conteggi, percorsi degli artefatti
principali e path del report. `documents=` conta i documenti sorgente
deduplicati; `derived_documents=`, `dicom_instances=` e `total_records=`
distinguono contenuti estratti dai contenitori e istanze DICOM.
`extracted_documents=` conta i documenti elaborati dall'estrazione testo nella
run corrente; `cached_documents=` conta i documenti invariati riusati dalla
cache incrementale. In modalità `incremental`, predefinita, SaniKey riusa il
testo estratto quando `document_id`, path, tipo, SHA256 e provenance del
documento coincidono con la cache in `local_build/cache/extracted_text.json`. In
modalità `full`, l'estrazione testo viene sempre rieseguita. Il database viene
comunque rigenerato dall'inventario corrente, usando testo nuovo o cache, per
evitare record obsoleti.
I warning lunghi o ripetitivi non vengono serializzati in stdout: sono
conservati nel report JSON indicato dalla riga
`report=...`. I warning sui documenti duplicati restano visibili anche in
stdout perché richiedono una decisione manuale.
Anche `build-patient` usa punti di avanzamento su `stderr` quando il terminale e'
interattivo; usare `--no-progress` per disattivarli.

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

Il frontend e' pensato per la consultazione diretta dalla chiavetta USB. I dati
necessari alla prima schermata sono esportati anche in `web/data.js`, caricato
come script locale, così Chrome e gli altri browser non devono usare `fetch()`
su URL `file://`.

### Personalizzare la Consultazione

L'aspetto e il comportamento iniziale del frontend possono essere configurati in
`config/accounts.toml`. I valori in `[global.ui]` valgono per tutti i pazienti;
un eventuale blocco `ui` dentro una voce `[[person]]` li sovrascrive solo per
quel paziente.

```toml
[global.ui]
accent_color = "#2563eb"
density = "comfortable"
default_tab = "documents"
timeline_order = "desc"
document_link_mode = "usb-relative"
subtitle = "Archivio sanitario personale"

[[person]]
id = "patient-a"
display_name = "Patient A"
source_documents = "local-data/patient-a/documents"
metadata_directory = "local-data/patient-a/metadata"
local_build = "local-data/generated/patient-a"
usb_uuid = "MANUAL-TEST-USB"

[person.ui]
default_tab = "timeline"
subtitle = "Archivio Patient A"
```

I valori ammessi sono:

- `density`: `compact`, `comfortable`;
- `default_tab`: `documents`, `timeline`, `summary`;
- `timeline_order`: `desc`, `asc`;
- `document_link_mode`: `usb-relative`;
- `accent_color`: colore esadecimale `#rrggbb`;
- `subtitle`: testo libero breve.

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
percorso risolto nella base sbagliata, un identificativo paziente non valido o
una violazione degli invarianti di privacy.
