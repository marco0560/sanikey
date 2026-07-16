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
- `usb_uuid`: UUID atteso del filesystem USB.

Esempio locale:

```toml
[global]
config_version = 1

[global.ingestion]
exclude_patterns = [
    "**/Help/**",
    "**/Viewer-Windows/**",
    "**/Viewer/**",
    "**/jre/**",
    "**/assets/**",
]

[global.usb]
usb_uuid = "MANUAL-TEST-USB"
require_exfat = true
min_free_space_mb = 512
copy_strategy = "rsync-preferred"

[[person]]
id = "marco"
display_name = "Marco Coppola"
source_documents = "local-data/marco/documents"
metadata_directory = "local-data/marco/metadata"
local_build = "local-data/generated/marco"
```

### Sintassi completa di `accounts.toml`

`accounts.toml` usa solo sezioni e campi chiusi: un campo non elencato qui viene
rifiutato da `validate-config`.

#### `[global]`

| Campo | Tipo TOML | Obbligatorio | Default | Valori ammessi |
| --- | --- | --- | --- | --- |
| `config_version` | intero | si | nessuno | `1` |

#### `[global.ui]` e `[person.ui]`

`[global.ui]` definisce i default per tutti i pazienti. `[person.ui]`, scritto
dopo una specifica voce `[[person]]`, sovrascrive solo i campi indicati per
quel paziente.

| Campo | Tipo TOML | Obbligatorio | Default | Valori ammessi |
| --- | --- | --- | --- | --- |
| `accent_color` | stringa | no | `"#2563eb"` | colore esadecimale `#rrggbb` |
| `density` | stringa | no | `"comfortable"` | `"compact"`, `"comfortable"` |
| `default_tab` | stringa | no | `"documents"` | `"documents"`, `"advanced"`, `"timeline"`, `"summary"` |
| `timeline_order` | stringa | no | `"desc"` | `"desc"`, `"asc"` |
| `document_link_mode` | stringa | no | `"usb-relative"` | `"usb-relative"` |
| `subtitle` | stringa | no | `"Archivio sanitario personale"` | testo fino a 120 caratteri |
| `background_image` | stringa path | no | assente | file esistente, relativo alla root repo o assoluto |
| `background_opacity` | numero | no | `0.1` | da `0.0` a `1.0` |

Esempio:

```toml
[global.ui]
accent_color = "#1d4ed8"
density = "compact"
default_tab = "documents"
timeline_order = "desc"
document_link_mode = "usb-relative"
subtitle = "Archivio sanitario personale"
background_image = "config/assets/background.png"
background_opacity = 0.10

[[person]]
id = "marco"
# ...

[person.ui]
default_tab = "timeline"
subtitle = "Archivio Marco"
```

#### `[global.search]` e `[person.search]`

`[person.search]` sovrascrive i campi indicati per il singolo paziente. Se
`dictionary` cambia, viene caricato il nuovo file TOML.

| Campo | Tipo TOML | Obbligatorio | Default | Valori ammessi |
| --- | --- | --- | --- | --- |
| `dictionary` | stringa path | no | assente | file TOML esistente |
| `advanced_index_warning_mb` | intero | no | `25` | intero positivo |

Il file indicato da `dictionary` ha solo due sezioni ammesse, entrambe
opzionali. Le chiavi sono stringhe TOML; i valori sono liste non vuote di
stringhe non vuote.

```toml
[terms]
rx = ["radiografia", "raggi x"]
rmn = ["risonanza magnetica", "rm"]
tac = ["tc", "tomografia"]

[months]
gennaio = ["01", "1"]
febbraio = ["02", "2"]
```

#### `[global.ingestion]` e `[person.ingestion]`

I pattern di `[person.ingestion]` si sommano a quelli globali; non li
sostituiscono. I pattern sorgente sono relativi a `source_documents`; dentro un
container sono relativi alla root estratta del container. Ogni pattern viene
confrontato sia con il path relativo sia con il solo nome file. Il confronto e'
case-insensitive, quindi `"**/Help/**"` esclude anche `help`, `HELP` o
combinazioni miste. `include_patterns` ha precedenza su `exclude_patterns` e
serve a recuperare un file specifico dentro una directory esclusa. Gli stessi
pattern filtrano anche la copia dei documenti
originali in `export-usb`: un file escluso dall'ingestione non viene copiato
nella directory `patients/<id>/documents` della chiavetta.

In TOML le chiavi `exclude_patterns` e `include_patterns` possono comparire una
sola volta nella stessa tabella. Per indicare piu' pattern bisogna usare una
lista nello stesso campo.

| Campo | Tipo TOML | Obbligatorio | Default | Valori ammessi |
| --- | --- | --- | --- | --- |
| `exclude_patterns` | lista di stringhe | no | `[]` | glob non vuoti, per esempio `"**/Help/**"` o `"*.tmp"` |
| `include_patterns` | lista di stringhe | no | `[]` | glob non vuoti che recuperano file esclusi, per esempio `"**/Viewer/report.pdf"` |

Esempio:

```toml
[global.ingestion]
exclude_patterns = [
    "**/Help/**",
    "**/Viewer-Windows/**",
    "**/Viewer/**",
    "**/jre/**",
    "**/assets/**",
]
include_patterns = ["**/Viewer/report.pdf"]

[[person]]
id = "irene"
# ...

[person.ingestion]
exclude_patterns = ["**/documentazione-non-clinica/**"]
include_patterns = ["**/documentazione-non-clinica/referto.pdf"]
```

#### `[global.usb]`

Questa sezione regola l'export verso target fisici. I target locali simulati
restano supportati; i controlli UUID/fstype sono applicati ai mount fisici o
quando il campo globale lo richiede.

| Campo | Tipo TOML | Obbligatorio | Default | Valori ammessi |
| --- | --- | --- | --- | --- |
| `usb_uuid` | stringa o assente | no | assente | UUID filesystem reale, per esempio `"757F-7873"` |
| `require_exfat` | booleano | no | `false` | `true`, `false` |
| `min_free_space_mb` | intero | no | `256` | intero positivo |
| `copy_strategy` | stringa | no | `"rsync-preferred"` | `"rsync-preferred"`, `"python"` |

Esempio:

```toml
[global.usb]
usb_uuid = "757F-7873"
require_exfat = true
min_free_space_mb = 512
copy_strategy = "rsync-preferred"
```

`usb_uuid` è il default per i campi `usb_uuid` dei pazienti. Se
non è impostato, ogni paziente deve dichiarare `usb_uuid`; i pazienti abilitati
devono condividere lo stesso valore, che viene usato come UUID atteso quando il
target sembra una chiavetta fisica montata sotto `/run/media` o `/media`.

#### `[[person]]`

| Campo | Tipo TOML | Obbligatorio | Default | Valori ammessi |
| --- | --- | --- | --- | --- |
| `id` | stringa | si | nessuno | minuscole, numeri e trattini, per esempio `"patient-a"` |
| `display_name` | stringa | si | nessuno | stringa non vuota |
| `source_documents` | stringa path | si | nessuno | path assoluto o relativo alla root repo |
| `metadata_directory` | stringa path | si | nessuno | path assoluto o relativo alla root repo |
| `local_build` | stringa path | si | nessuno | path assoluto o relativo alla root repo |
| `usb_uuid` | stringa | no se `[global.usb].usb_uuid` è impostato | valore globale | Override UUID filesystem coerente con `[global.usb]` |
| `enabled` | booleano | no | `true` | `true`, `false` |

I percorsi dentro `local-data/` sono accettati perché la directory è ignorata da
Git. Percorsi dentro directory versionate del repository, per esempio `docs/` o
`src/`, vengono rifiutati.

Valida la configurazione e gli invarianti di privacy:

```bash
uv run sanikey validate-config
```

`validate-config` carica anche i metadati curati dei pazienti abilitati e
segnala prima della build errori come TOML non valido, id duplicati o terapie
che fanno riferimento a farmaci non presenti in `medications.toml`.

Elenca i pazienti abilitati:

```bash
uv run sanikey list-patients
```

## Preparare i Documenti Sorgente

Inserisci i file sorgente nella directory `source_documents` configurata per
ciascun paziente. L'implementazione attuale esegue scansione deterministica,
estrae il testo supportato, cataloga i supporti DICOM e registra i metadati in
un archivio SQLite generato.

Usare directory con prefisso `_` per contenuti di servizio che devono restare in
testa all'ordine alfabetico senza diventare categorie cliniche ordinarie. Le
directory convenzionali sono `_Archivi` per supporti compressi, immagini disco e
altri container tecnici, `_Parametri` per fogli di misurazioni longitudinali e
`_Terapia` per documenti sulla terapia corrente. Il prefisso `_` non viene
mostrato nella categoria del documento.

Per verificare il numero di file rilevati senza stampare l'intero inventario:

```bash
uv run sanikey scan-documents
```

Il comando segnala anche avvisi rilevabili senza build completa, come
duplicati e file con estensione non supportata. Per impostazione predefinita
estrae anche i container supportati in
`local_build/staging/containers/`, cosi' il contenuto degli archivi puo' essere
verificato manualmente prima della build completa. Il riepilogo include
`archivi_preparati=`, `membri_in_archivi=` e `documenti_derivati=` quando lo
staging e' attivo e `esclusi=` quando pattern di ingestion hanno saltato file
deliberatamente. I file esclusi non sono avvisi. Prima della scansione viene
ripetuto il controllo dei metadati curati
dei pazienti selezionati, cosi' un errore in `therapies.toml` blocca subito il
comando invece di emergere dopo una build lunga.

I nomi mostrati per i documenti derivano dal nome file: se il nome inizia con
una data `aaaammgg`, quella parte diventa la data del documento e il resto del
nome, senza estensione, diventa il titolo. Gli underscore vengono mostrati come
spazi. Per esempio `20260102 Referto_Laboratorio.pdf` diventa data
`02/01/2026` e titolo `Referto Laboratorio`.

Su terminali interattivi, i passi lunghi stampano punti di avanzamento su
`stderr`, senza modificare l'output riepilogativo su `stdout`.
`scan-documents` stampa un punto ogni 20 file sorgente, lo staging un punto per
ogni container processato e il catalogo DICOM un punto ogni 50 record. Per
disattivarli:

```bash
uv run sanikey scan-documents --no-progress
```

Per eseguire una scansione solo inventariale, senza creare o aggiornare lo
staging dei container:

```bash
uv run sanikey scan-documents --no-stage-containers
```

Per eseguire anche controlli preliminari leggeri su archivi e documenti Office:

```bash
uv run sanikey scan-documents --preflight
```

`--preflight` non esegue OCR PDF e non converte documenti legacy Office, ma può
individuare prima della build archivi corrotti o documenti Office non leggibili.

Per ispezionare a schermo la lista dei documenti ingeriti:

```bash
uv run sanikey scan-documents --verbose
```

Per salvare l'inventario in un file riprocessabile:

```bash
uv run sanikey scan-documents --output local-data/scan.txt --format text
uv run sanikey scan-documents --output local-data/scan.csv --format csv
```

`--format` e' valido solo insieme a `--output`. Il formato `text` usa la riga
tab-separated estesa con paziente, tipo, categoria, data ISO, titolo, SHA256 e
path assoluto. Il formato `csv` usa gli stessi campi con intestazione.

Per verificare che i documenti sorgente non vengano modificati dalla pipeline,
creare uno snapshot prima della build, uno dopo la build e poi confrontarli:

```bash
uv run sanikey document-integrity before
uv run sanikey document-integrity after
uv run sanikey document-integrity check
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
- `.jpg`, `.jpeg`, `.png`: documento immagine consultabile, senza OCR diretto;
- `.docx`, `.odt`: testo tramite librerie Python;
- `.xlsx`, `.xlsm`, `.xlsb`, `.xls`, `.ods`: celle tramite `python-calamine`;
- `.doc`: conversione tramite LibreOffice o `soffice`, se disponibile;
- `.zip`, `.7z`, `.rar`, `.tar.xz`: inventario dei file contenuti nell'archivio.

Le misurazioni longitudinali come peso, pressione, glicemia e INR si importano
con un passaggio esplicito:

```bash
uv run sanikey import-observations PATIENT
uv run sanikey build-patient PATIENT
```

Il manifesto `metadata/observation_imports.toml` associa ogni file sorgente a
una serie clinica e mappa le colonne. Sono accettati CSV UTF-8 e fogli
`.xlsx`, `.xlsm`, `.xlsb`, `.xls`, `.ods`. Se manifesto o sorgenti cambiano,
la build chiede di rieseguire `import-observations`.

Durante `scan-documents`, `process-dicom` e `build-patient`, gli archivi e le
immagini disco supportate vengono anche estratti in una staging area generata
sotto `local_build/staging/containers`. Il contenitore originale resta il
documento autorevole; i membri estratti sono documenti derivati con provenance
verso il contenitore, path interno e SHA256 proprio. Se un archivio è cifrato,
corrotto o non leggibile, il contenitore resta catalogato e il problema viene
registrato come avviso. `process-dicom --no-stage-containers` esegue il solo
catalogo dei sorgenti e delle espansioni già presenti. L'output predefinito di
`process-dicom` è una riga per archivio/supporto trovato e segnala `ok`,
`nessuno studio DICOM`, `piu studi DICOM: N` oppure `problema: ...`; usare
`process-dicom --verbose` per contatori e tabella tecnica degli studi.

I file ISO DICOM consegnati dagli ospedali sono conservati come documenti
sorgente. Gli archivi `.zip`, `.7z`, `.rar` e `.tar.xz` sono trattati
inizialmente come archivi generici e promossi a supporti DICOM solo se
contengono `DICOMDIR`, file `.dcm`, path DICOM riconoscibili, immagini disco
`.iso`/`.img`, ZIP annidati con contenuto DICOM o file con magic bytes DICOM.
Quando vengono estratti in staging, eventuali immagini disco `.iso` o `.img`
annidate vengono espanse a loro volta. I file DICOM interni sono catalogati come
DICOM e non passano dall'OCR o dall'estrazione testo ordinaria.
Nel frontend non vengono mostrati i singoli file DICOM: la consultazione mostra
schede aggregate per studio, con numero istanze, UID quando disponibile e link
di apertura del viewer HTML quando rilevato. I supporti e i file tecnici non
vengono presentati come documenti clinici ordinari. Se uno studio DICOM viene
catalogato senza viewer HTML, resta nella sezione `Studi DICOM` come anomalia
da verificare.
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
manuali, HTML di help o asset applicativi, devono essere esclusi con pattern di
ingestione espliciti come `**/Viewer-Windows/**`, `**/jre/**` o `**/assets/**`.
I membri esclusi restano tracciati nel manifest di staging ma non entrano nella
pipeline documentale ordinaria. Se lo staging
contiene un viewer HTML consultabile, SaniKey preferisce entrypoint IHE PDI
come `IHE_PDI/PAGES/STUDIES/*.HTM`, poi altre pagine HTML note come
`index.html`, `index.htm`, `default.htm` o `start.htm`. In export USB questi
viewer vengono copiati sotto `patients/<id>/dicom-viewers/` e aperti dal
frontend con un link relativo in un nuovo tab del browser. Il manifest di
staging può essere molto grande perché registra ogni membro estratto dai
contenitori per audit e verifica manuale; non è un report compatto da leggere
integralmente in terminale.

Per i PDF, SaniKey sceglie automaticamente il provider:

- usa `PyMuPDF` (`fitz`) quando il PDF contiene testo digitale sufficiente;
- passa a `OCRmyPDF`, se disponibile come comando di sistema, quando PyMuPDF
  manca o produce testo vuoto/insufficiente.

`OCRmyPDF` è quindi una dipendenza di sistema supportata. Se nessun provider è
disponibile, il PDF resta catalogato ma l'estrazione testo viene saltata con un
avviso esplicito sui provider mancanti o insufficienti.
SaniKey configura OCRmyPDF per produrre un PDF temporaneo normale invece di un
PDF/A, perché conserva solo il sidecar testuale. Se OCRmyPDF fallisce durante
l'ottimizzazione del PDF temporaneo, SaniKey ritenta senza ottimizzazione. I
avvisi registrati nel report sono sintetici e non includono il log completo del
tool esterno. Se anche il retry fallisce e il numero di pagine è disponibile,
SaniKey ritenta su intervalli di pagine con una ricerca dicotomica per indicare
la prima pagina del PDF originale che riproduce il problema.

Il testo estratto con successo viene salvato nella tabella SQLite
`document_text` e indicizzato in `document_fts` insieme a titolo, categoria e
tag. I file DICOM restano esclusi dall'estrazione testo.
I documenti `.md` e i campi TOML documentati come Markdown, incluso
`clinical_summary.toml`, vengono convertiti in HTML durante la build. L'HTML
grezzo presente nel Markdown viene escapato; il frontend usa solo l'HTML
generato dalla pipeline.

Le immagini sorgente `.jpg`, `.jpeg` e `.png` restano documenti consultabili e
apribili dal frontend, ma SaniKey non esegue OCR diretto con Tesseract su questi
file. Questa scelta evita testo rumoroso e tempi di build non necessari. I PDF
scansionati restano invece gestiti dalla pipeline PDF con OCRmyPDF quando serve.

## Costruire un Archivio

Costruisci un singolo paziente:

```bash
uv run sanikey build-patient patient-a --mode full
```

Il comando stampa un riepilogo leggibile con conteggi, percorsi degli artefatti
principali e path del report. `documenti=` conta i documenti sorgente
deduplicati; `documenti_derivati=`, `istanze_dicom=` e `record_totali=`
distinguono contenuti estratti dai contenitori e istanze DICOM.
`documenti_estratti=` conta i documenti elaborati dall'estrazione testo nella
run corrente; `documenti_cached=` conta i documenti invariati riusati dalla
cache incrementale. In modalità `incremental`, predefinita, SaniKey riusa il
testo estratto quando `document_id`, path, tipo, SHA256 e provenance del
documento coincidono con la cache in `local_build/cache/extracted_text.json`. In
modalità `full`, l'estrazione testo viene sempre rieseguita. Il database viene
comunque rigenerato dall'inventario corrente, usando testo nuovo o cache, per
evitare record obsoleti.
Gli avvisi lunghi o ripetitivi non vengono serializzati in stdout: sono
conservati nel report JSON indicato dalla riga
`report=...`. Gli avvisi sui documenti duplicati restano visibili anche in
stdout perché richiedono una decisione manuale.
Anche `build-patient` usa punti di avanzamento su `stderr` quando il terminale e'
interattivo; usare `--no-progress` per disattivarli.

Costruisci tutti i pazienti abilitati:

```bash
uv run sanikey build-all --mode full
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
La ricerca rapida nel box in alto cerca in documenti, farmaci, terapie,
problemi, procedure, osservazioni e studi DICOM. I risultati vengono
raggruppati per sezione e mostrano link contestuali con conteggi dentro il
pannello dei risultati, in modo che il medico possa saltare subito alla parte
utile senza una seconda barra di navigazione sotto la ricerca.
Il bottone `Ricerca avanzata` cambia lo stesso box di ricerca e carica al primo
uso `web/content-search.js`, cercando
anche nel testo estratto da PDF, documenti Office e file testuali.
La ricerca avanzata combina quei risultati documentali con gli stessi metadati
clinici della ricerca rapida. Gli aiuti di ricerca base e avanzata sono
separati, restano accanto al rispettivo bottone e si aprono in finestre modali
locali richiudibili.

La sintassi della ricerca avanzata è case-insensitive e accent-insensitive.
Supporta parole, frasi tra virgolette, `AND`, `OR`, `NOT` e parentesi. Parole
adiacenti equivalgono a `AND`, quindi `creatinina 2024` è equivalente a
`creatinina AND 2024`.

La sezione `Sintesi Clinica` mostra una dashboard clinica sempre consultabile.
Include, quando presenti, problemi, terapie, farmaci, osservazioni e procedure.
Le terapie sono arricchite con nome commerciale, principio attivo, dosaggio,
schedula, istruzioni, periodo e ruolo. Quando sono presenti, hanno anche un
bottone di primo livello `Terapia` per l'accesso diretto senza passare dalla
sintesi generale. Gli studi DICOM hanno una sezione autonoma `Studi DICOM`,
visibile quando il payload contiene studi catalogati, con schede sintetiche per
data/UID quando disponibili e numero di istanze. Gli studi senza viewer HTML
sono segnalati come anomalie, mentre non viene mostrata la lista di ogni singola
slice. Il riepilogo tecnico con conteggi e' in fondo alla sintesi clinica.

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
background_image = "config/assets/background.png"
background_opacity = 0.10

[global.search]
dictionary = "config/search-dictionary.toml"
advanced_index_warning_mb = 25

[global.usb]
usb_uuid = "MANUAL-TEST-USB"

[[person]]
id = "patient-a"
display_name = "Patient A"
source_documents = "local-data/patient-a/documents"
metadata_directory = "local-data/patient-a/metadata"
local_build = "local-data/generated/patient-a"

[person.ui]
default_tab = "timeline"
subtitle = "Archivio Patient A"
```

I valori ammessi sono:

- `density`: `compact`, `comfortable`;
- `default_tab`: `documents`, `advanced`, `timeline`, `summary`;
- `timeline_order`: `desc`, `asc`;
- `document_link_mode`: `usb-relative`;
- `accent_color`: colore esadecimale `#rrggbb`;
- `subtitle`: testo libero breve;
- `background_image`: immagine opzionale copiata in `web/assets/` durante la
  build;
- `background_opacity`: numero tra `0` e `1`, da mantenere basso per non
  compromettere leggibilità;
- `dictionary`: TOML opzionale per sinonimi e normalizzazioni della ricerca
  avanzata;
- `advanced_index_warning_mb`: soglia oltre la quale la build segnala che
  `content-search.js` è grande, senza bloccare l'export.

Il dizionario di ricerca contiene sezioni chiuse:

```toml
[terms]
rx = ["radiografia", "raggi x"]
rmn = ["risonanza magnetica", "rm"]
tac = ["tc", "tomografia"]

[months]
gennaio = ["01", "1"]
febbraio = ["02", "2"]
```

Le espansioni sono simmetriche: cercare `rx` trova anche `radiografia`, e
cercare `radiografia` trova anche `rx`.

## Revisionare le Proposte

La prima implementazione include proposte deterministiche da revisionare
manualmente. I provider AI reali sono rimandati.

Genera le proposte:

```bash
uv run sanikey generate-proposals --patient patient-a
```

Approva o rifiuta una proposta:

```bash
uv run sanikey review-proposal patient-a PROPOSAL-ID approved
uv run sanikey review-proposal patient-a PROPOSAL-ID rejected
```

## Esportare su USB

Costruisci ed esporta tutti i pazienti abilitati verso una radice USB o una
directory simulata:

```bash
uv run sanikey deploy-usb /path/to/usb-root
```

Per esportare artefatti gia' generati:

```bash
uv run sanikey export-usb /path/to/usb-root
```

`export-usb` e `deploy-usb` usano punti di avanzamento su `stderr` quando il
terminale e' interattivo. Le fasi principali sono generazione immagine,
manifest/checksum e copia verso il target. Usare `--no-progress` per un output
strettamente testuale o facilmente copiabile.
Quando il target e' una chiavetta fisica montata sotto `/run/media` o `/media`,
`export-usb` verifica l'UUID atteso se configurato, controlla exFAT quando
`require_exfat = true`, controlla lo spazio libero e preferisce `rsync` quando
`copy_strategy = "rsync-preferred"`. Se `rsync` non e' installato, usa la copia
Python; se `rsync` parte e fallisce, il comando fallisce senza fallback
silenzioso.

Valida la struttura esportata:

```bash
uv run sanikey validate-usb /path/to/usb-root
```

Apri la pagina iniziale generata dalla radice USB:

```text
index.html
```

## Struttura USB

Un export USB generato contiene:

```text
SANIKEY-MANIFEST.json
index.html
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

- `uv run sanikey validate-config`
- `uv run sanikey build-patient PATIENT-ID --mode full`
- `uv run sanikey validate-usb /path/to/usb-root`
- `uv run python scripts/validate_repo.py`

Gli errori di configurazione indicano di solito un file privato mancante, un
percorso risolto nella base sbagliata, un identificativo paziente non valido o
una violazione degli invarianti di privacy.
