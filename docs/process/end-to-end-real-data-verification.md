# Verifica end-to-end con dati reali

Questa procedura verifica manualmente che lo slice di implementazione iniziale
produca un archivio consultabile, isolato e verificabile a partire da dati reali.
Non sostituisce la suite automatica: serve a validare il comportamento operativo
su un dataset reale controllato.

## Obiettivo

Dimostrare che SaniKey può:

- leggere una configurazione locale fuori da Git;
- processare documenti reali di uno o piu' pazienti;
- generare database, export JSON, timeline, ricerca e frontend statico;
- costruire l'immagine USB canonica in `exports/usb-image/`;
- copiare l'immagine verso un target di verifica;
- validare manifest e checksum;
- mantenere i documenti originali invariati;
- evitare esportazione di cache, log e directory temporanee generate.

## Prerequisiti

Usare solo dati per cui si dispone di autorizzazione esplicita. La verifica può
contenere dati sanitari reali: non copiare configurazioni, documenti, export,
log o screenshot in Git.

Eseguire dal root del repository:

```bash
pwd
git status --short
uv run python scripts/validate_repo.py
```

La working tree deve essere pulita e la validazione deve passare prima di
iniziare.

## Directory locali

Creare un'area privata non committata dal repository, per esempio:

```bash
mkdir -p local-data/{usb-target,{marco,irene}/{documents,metadata/observations},generated/{marco,irene}}
mkdir -p local-data/{marco,irene}/documents/parametri
```

con `local-data/` in `.gitignore`.

Inserire in `local-data/marco/documents` e `local-data/irene/documents` un
piccolo campione reale ma controllato:

- almeno un referto testuale o PDF;
- almeno un documento con data nel nome, se disponibile;
- opzionalmente un supporto DICOM ISO o ZIP;
- opzionalmente sottodirectory cliniche, ad esempio `laboratory/` o `imaging/`.

## Configurazione locale

Creare `config/accounts.toml`. Il file è privato e deve restare ignorato da Git.

```bash
mkdir -p config
```

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

[[person]]
id = "irene"
display_name = "Irene Corazzesi"
source_documents = "local-data/irene/documents"
metadata_directory = "local-data/irene/metadata"
local_build = "local-data/generated/irene"
```

Prima di continuare, confrontare `config/accounts.toml` con la sintassi completa
descritta nella sezione “Sintassi completa di `accounts.toml`” della user guide.
In particolare verificare questi campi, perché influenzano direttamente la
prova end-to-end:

| Sezione | Campo | Sintassi attesa | Valore da verificare nella prova |
| --- | --- | --- | --- |
| `[global]` | `config_version` | intero | `1` |
| `[global.ui]` | `background_image` | stringa path a file esistente | assente oppure path privato non versionato |
| `[global.ui]` | `background_opacity` | numero `0.0`-`1.0` | valore basso, per esempio `0.10` |
| `[global.search]` | `dictionary` | stringa path a TOML esistente | file privato con sezioni `[terms]` e/o `[months]` |
| `[global.search]` | `advanced_index_warning_mb` | intero positivo | soglia coerente con il dataset reale |
| `[global.ingestion]` | `exclude_patterns` | una sola lista di stringhe glob, case-insensitive | esclusioni tecniche comuni, per esempio `["**/Help/**"]` |
| `[global.ingestion]` | `include_patterns` | una sola lista di stringhe glob, case-insensitive | recuperi comuni da esclusioni ampie, se necessari |
| `[person.ingestion]` | `exclude_patterns` | una sola lista di stringhe glob, case-insensitive | esclusioni aggiuntive del singolo paziente |
| `[person.ingestion]` | `include_patterns` | una sola lista di stringhe glob, case-insensitive | recuperi specifici del singolo paziente |
| `[global.usb]` | `usb_uuid` | stringa UUID o assente | UUID reale mostrato da `lsblk -f` per la chiavetta fisica |
| `[global.usb]` | `require_exfat` | booleano | `true` per la prova fisica exFAT |
| `[global.usb]` | `min_free_space_mb` | intero positivo | margine, per esempio `512` |
| `[global.usb]` | `copy_strategy` | stringa | `"rsync-preferred"` oppure `"python"` |
| `[[person]]` | `enabled` | booleano opzionale | assente o `true` per i pazienti inclusi |

Il file dizionario indicato da `[global.search].dictionary` deve avere questa
forma:

```toml
[terms]
rx = ["radiografia", "raggi x"]
tac = ["tc", "tomografia"]

[months]
gennaio = ["01", "1"]
febbraio = ["02", "2"]
```

`validate-config` deve fallire se trova campi non documentati, valori fuori set
chiuso, path richiesti inesistenti o tipi TOML errati.

Verificare che Git non veda dati privati:

```bash
git status --short
```

Se compaiono configurazioni reali, documenti, export o dati sanitari, fermarsi e
correggere `.gitignore` o i percorsi locali prima di procedere.

## Metadati curati minimi

Creare metadati minimi in `local-data/marco/metadata` e
`local-data/irene/metadata`. Gli esempi sotto usano un solo paziente: replicare
la stessa struttura nella directory metadata di ogni paziente configurato,
adattando id, nomi e contenuti.

Prima di scrivere i contenuti, verificare quali TOML servono nel caso reale. La
procedura deve coprire almeno l'inventario seguente:

| File | Origine | Quando crearlo |
| --- | --- | --- |
| `config/accounts.toml` | manuale | sempre |
| `config/search-dictionary.toml` | manuale | se `[global.search].dictionary` e' configurato |
| `clinical_summary.toml` | manuale | sempre nella verifica reale |
| `document_tags.toml` | manuale | se si vogliono tag per ricerca/UI |
| `problems.toml` | manuale | se ci sono problemi clinici strutturati |
| `medications.toml` | manuale | se ci sono farmaci strutturati |
| `therapies.toml` | manuale | se ci sono terapie strutturate |
| `procedures.toml` | manuale | se ci sono procedure/interventi strutturati |
| `observations.toml` | manuale legacy | solo per osservazioni puntuali curate a mano |
| `observation_imports.toml` | manuale | se si importano peso, pressione, glicemia, INR o altri parametri |
| `timeline_events.toml` | manuale | se servono eventi timeline manuali |
| `observations/series.toml` | generato | prodotto da `sanikey import-observations` |
| `observations/*.toml` | generato | punti osservazione normalizzati, uno o piu' file per serie |
| `observations/import_state.toml` | generato | hash di manifesto e sorgenti importati |

Non modificare a mano i file generati sotto `metadata/observations/` durante la
verifica: modificarli solo rigenerandoli da `observation_imports.toml` e dai
file sorgente.

`clinical_summary.toml` contiene una sintesi clinica libera. Per l'uso corrente
può essere trattata come anamnesi/sommario narrativo: problemi rilevanti,
interventi, terapie importanti, allergie note, avvertenze e contesto utile alla
consultazione. Se il testo ha più righe, usare una stringa TOML multilinea.
Il testo supporta Markdown CommonMark e viene convertito in HTML durante la
build; eventuale HTML grezzo nel Markdown viene escapato.

Esempio `clinical_summary.toml`:

```toml
summary = """
# Sintesi clinica

## Identificazione clinica
Paziente seguito per: ...
Contesto generale: ...

## Problemi attivi rilevanti
- ...
- ...

## Anamnesi patologica remota significativa
- ...
- ...

## Interventi, ricoveri e accessi rilevanti
- ...

## Terapie croniche principali
- ...
Nota: il dettaglio strutturato delle terapie è in therapies.toml.

## Allergie, intolleranze e reazioni avverse
- Nessuna nota / ...
- ...

## Fattori di rischio e abitudini rilevanti
- ...

## Dispositivi, protesi, impianti
- ...

## Monitoraggi e follow-up
- ...

## Avvertenze pratiche per la consultazione
- Documenti chiave da guardare prima: ...
- Criticità note: ...

## Data e criterio di aggiornamento
Aggiornata il: YYYY-MM-DD.
Fonte: revisione manuale dei documenti presenti in archivio.
"""
```

Usare questa distinzione:

- **Anamnesi**: storia clinica, cioè “che cosa è successo nel tempo”.
- **Sintesi clinica**: riassunto operativo, cioè “che cosa deve capire subito un medico che apre la chiavetta”.

Quindi l’anamnesi è una sezione della sintesi, non l’intera sintesi.

Per SaniKey non duplicare nella sintesi dati già strutturati altrove, se non
come riepilogo leggibile. Esempio: le terapie dettagliate stanno in
`therapies.toml`; nella sintesi mettere solo le terapie clinicamente importanti
o avvertenze.

Esempio `document_tags.toml`:

```toml
[tags]
"laboratory/20260102 Referto.txt" = ["laboratorio", "emocromo"]
```

La chiave e' preferibilmente il percorso relativo a `source_documents`. I tag
sono stringhe libere e sono usati negli export JSON, nella ricerca e nel
frontend. Per il riferimento completo dei file TOML vedere
`docs/process/metadata-toml-reference.md`.

Esempio opzionale `problems.toml`:

```toml
[[problem]]
id = "ipertensione"
title = "Ipertensione arteriosa"
status = "active"
```

Esempio opzionale `medications.toml`:

```toml
[[medication]]
id = "atenololo"
name = "Atenololo 100mg"
active_ingredient = "Atenololo"
form = "compresse"
strength_per_unit = "100 mg"

[[medication]]
id = "cardioaspirina"
name = "Cardioaspirina"
active_ingredient = "Acido acetilsalicilico"
form = "compresse rivestite"
strength_per_unit = "100 mg"
```

`name` è il nome commerciale o la denominazione visibile sulla confezione.
`active_ingredient` è il principio attivo. `form` descrive il formato fisico
usato nella terapia, per esempio `compresse`, `compresse rivestite`, `capsule`,
`bustine`, `gocce`, `fiale`. `strength_per_unit` conserva quantità e unità in un
unico campo leggibile, per esempio `100 mg`.

Esempio opzionale `therapies.toml`:

```toml
[[therapy]]
medication_id = "atenololo"
dosage = "1 compressa"
role = "antipertensivo"
schedule = ["mattino"]
instructions = "dopo colazione"

[[therapy]]
medication_id = "cardioaspirina"
start_date = "2021-04-01"
dosage = "1 compressa"
role = "antiaggregante"
schedule = ["cena"]
instructions = "dopo il pasto"
```

`schedule` è una lista di indicazioni leggibili. Può contenere orari puntuali
come `08:00` o fasce/etichette come `risveglio`, `mattino`, `pranzo`, `cena`,
`sera`, `notte`. `instructions` contiene indicazioni libere come `lontano dai
pasti`, `dopo il pasto` o `prima di coricarsi`.

Se la data di inizio è sconosciuta, omettere `start_date`. Se la terapia è
ancora in corso o permanente, omettere `end_date`. Non usare date fittizie per
forzare l'ordinamento: è meglio lasciare esplicitamente sconosciuto il dato.
`id` è opzionale: se omesso viene generato da SaniKey. Se lo si indica
manualmente deve essere univoco. `role` descrive il ruolo clinico della terapia,
per esempio `antipertensivo`; più terapie possono avere lo stesso ruolo.

Esempio opzionale `procedures.toml`:

```toml
[[procedure]]
id = "colecistectomia-2021"
title = "Colecistectomia laparoscopica"
date = "2021-04-12"
status = "completed"
```

Esempio opzionale `observations.toml` per osservazioni puntuali curate a mano:

```toml
[[observation]]
id = "peso-riferito-2026-01"
kind = "peso"
value = "70 kg riferiti"
date = "2026-01-03"
```

Preferire `observation_imports.toml` quando la stessa grandezza e' presente in
file tabellari o in piu' periodi.

Esempio opzionale `timeline_events.toml`:

```toml
[[event]]
id = "ricovero-2024-09"
title = "Ricovero per accertamenti"
start_date = "2024-09-10"
end_date = "2024-09-14"
source = "manual"
links = ["colecistectomia-2021"]
```

### Import osservazioni longitudinali

Se sono disponibili file tabellari per peso, pressione, glicemia, INR o altri
parametri, conservarli sotto `source_documents`, per esempio:

```bash
test -f local-data/marco/documents/parametri/peso-2025.xlsx
test -f local-data/marco/documents/parametri/diario-pressorio.csv
```

Creare `local-data/marco/metadata/observation_imports.toml` con mapping esplicito
tra file, serie e colonne. Esempio:

```toml
[[series]]
id = "peso"
name = "Peso"
value_type = "numeric"
unit = "kg"
warn_duplicate_same_day = true

[[source]]
path = "parametri/peso-2025.xlsx"
series_id = "peso"
sheet = "Peso"
source_reference = "peso-2025.xlsx"

[source.columns]
date = "Data"
numeric_value = "Peso"
note = "Note"

[[series]]
id = "pressione"
name = "Pressione"
value_type = "blood_pressure"
unit = "mmHg"
warn_duplicate_same_day = false

[[source]]
path = "parametri/diario-pressorio.csv"
series_id = "pressione"
source_reference = "diario-pressorio.csv"

[source.columns]
date = "Data"
systolic = "Sistolica"
diastolic = "Diastolica"
pulse = "Frequenza"
note = "Note"
```

Regole operative:

- `path` relativo e' risolto rispetto a `source_documents`;
- i formati accettati sono `.csv`, `.xlsx`, `.xlsm`, `.xlsb`, `.xls`, `.ods`;
- il manifesto esplicito vince sempre;
- eventuali convenzioni di path/sheet servono solo per preparare proposte future,
  non per generare dati autorevoli;
- una stessa serie può avere piu' `[[source]]`, anche con mapping diversi e
  periodi diversi;
- `warn_duplicate_same_day = false` e' normale per diari pressori o curve
  glicemiche con piu' misurazioni nella stessa data.

## Esecuzione pipeline

Validare la configurazione:

```bash
uv run sanikey validate-config
```

Questo passo deve anche validare i metadati curati: correggere subito TOML
malformati, id duplicati o terapie che citano un `medication_id` non presente in
`medications.toml`.

Creare lo snapshot iniziale dei documenti sorgente configurati:

```bash
uv run sanikey document-integrity before --output-dir local-data
```

Il comando usa i pazienti abilitati in `accounts.toml` e produce per ciascun
paziente i file `PATIENT-before.sha256` e `PATIENT-before-mtime.tsv`, per
esempio `local-data/marco-before.sha256` e
`local-data/irene-before-mtime.tsv`.

Eseguire una scansione preliminare dei documenti:

```bash
uv run sanikey scan-documents
```

Il comando stampa solo il riepilogo per paziente e gli eventuali avvisi
rilevabili senza build completa. Su terminale interattivo puo' stampare punti di
avanzamento su `stderr`; aggiungere `--no-progress` se si vuole un log
strettamente privo di progress. Per impostazione predefinita crea anche lo
staging dei container in `local_build/staging/containers/`; usare
`--no-stage-containers` solo quando serve una scansione esclusivamente
inventariale e non si vuole materializzare il contenuto degli archivi.

Se sono presenti archivi, prima della build lunga aprire il manifest e le
directory di staging generate dallo scan:

```bash
python -m json.tool local-data/generated/marco/manifests/container_staging.json | less
find local-data/generated/marco/staging/containers -maxdepth 2 -type f | sort | less
python -m json.tool local-data/generated/irene/manifests/container_staging.json | less
find local-data/generated/irene/staging/containers -maxdepth 2 -type f | sort | less
```

Questo controllo serve a verificare manualmente se gli archivi contengono
supporti DICOM, immagini disco annidate, referti PDF o solo materiale tecnico
del viewer. Se un paziente non contiene archivi, il manifest deve comunque
esistere con `members` vuoto. Eseguire anche il preflight leggero prima di una
build lunga:

```bash
uv run sanikey scan-documents --preflight
```

Il preflight controlla archivi e documenti Office moderni/OpenDocument senza
eseguire OCR PDF, senza convertire documenti legacy Office e senza richiedere
OCR diretto per immagini sorgente `.jpg`, `.jpeg` o `.png`. Se
compaiono avvisi inattesi, fermarsi e risolverli o annotarli prima di
proseguire.

Per leggere a schermo l'inventario dei documenti ingeriti:

```bash
uv run sanikey scan-documents --verbose
```

Per conservare l'inventario completo in un file riprocessabile:

```bash
uv run sanikey scan-documents --output local-data/scan-documents.tsv --format text
uv run sanikey scan-documents --output local-data/scan-documents.csv --format csv
```

Se esiste almeno un `observation_imports.toml`, importare le osservazioni prima
della build:

```bash
uv run sanikey import-observations
```

Per isolare un paziente:

```bash
uv run sanikey import-observations marco
uv run sanikey import-observations irene
```

Verificare che il comando abbia generato gli artefatti normalizzati attesi:

```bash
test ! -f local-data/marco/metadata/observation_imports.toml || test -f local-data/marco/metadata/observations/series.toml
test ! -f local-data/marco/metadata/observation_imports.toml || test -f local-data/marco/metadata/observations/import_state.toml
test ! -f local-data/marco/metadata/observation_imports.toml || find local-data/marco/metadata/observations -maxdepth 1 -type f -name '*.toml' | sort
test ! -f local-data/irene/metadata/observation_imports.toml || test -f local-data/irene/metadata/observations/series.toml
test ! -f local-data/irene/metadata/observation_imports.toml || test -f local-data/irene/metadata/observations/import_state.toml
test ! -f local-data/irene/metadata/observation_imports.toml || find local-data/irene/metadata/observations -maxdepth 1 -type f -name '*.toml' | sort
```

Aprire `import_state.toml` e verificare che contenga `manifest_hash` e una
tabella `[source_hashes]`. Se si modifica un file sorgente o
`observation_imports.toml`, ripetere `import-observations`: la build deve
fallire con un errore esplicito se gli artefatti sono stale.

Se l'output contiene `duplicati=`, leggere eventuali righe `AVVISO:`. File con
lo stesso SHA256 sono identici: SaniKey conserva solo la prima occorrenza
nell'archivio generato e segnala il file saltato insieme al file trattenuto. In
presenza di duplicati inattesi, fermarsi e decidere manualmente se rimuovere,
rinominare o archiviare separatamente una delle copie prima di proseguire.

Eseguire la build completa per tutti i pazienti abilitati:

```bash
uv run sanikey build-all --mode full
```

In alternativa, per isolare un problema, eseguire un paziente alla volta:

```bash
uv run sanikey build-patient marco --mode full
uv run sanikey build-patient irene --mode full
```

L'output deve essere un riepilogo multi-riga leggibile per ogni paziente, non
una riga JSON minificata. Annotare ogni percorso `report=...`: contiene il
dettaglio completo degli avvisi e deve essere consultato se `avvisi` e'
maggiore di zero.
`documenti=` conta solo i documenti sorgente deduplicati; usare
`documenti_derivati=`, `istanze_dicom=` e `record_totali=` per valutare quanto
deriva da contenitori e supporti diagnostici.
I punti di avanzamento, quando presenti, devono essere su `stderr`, non dentro
il riepilogo su `stdout`.

Se sono presenti archivi o immagini ISO, riverificare anche dopo la build il
manifest di staging rigenerato:

```bash
python -m json.tool local-data/generated/marco/manifests/container_staging.json | less
python -m json.tool local-data/generated/irene/manifests/container_staging.json | less
```

Controllare che ogni membro estratto abbia `container_id`, `internal_path`,
`sha256` e `path`. Questo manifest e' intenzionalmente completo e può essere
molto grande: serve per audit, controllo manuale e provenienza dei membri
estratti, inclusi i file tecnici non ingeriti come documenti. Gli archivi
`.zip`, `.7z` e `.rar` devono risultare supporti DICOM solo quando il contenuto
lo giustifica, per esempio per presenza di `DICOMDIR`, file `.dcm`, immagini
disco `.iso`/`.img`, ZIP annidati con slice DICOM, path DICOM o magic bytes
DICOM. I file DICOM interni devono risultare catalogati come DICOM derivati, non
trattati come documenti OCR o testo ordinario. Se un archivio contiene
un'immagine disco `.iso` o `.img`, la directory di staging deve contenere sia
l'immagine disco estratta sia la sua espansione ricorsiva sotto una seconda
directory di container. I path tecnici dei viewer, ad esempio `Help`, `Manual`,
`Viewer-Windows`, `jre` e `assets`, devono essere elencati nei pattern di
ingestione; i membri esclusi devono restare nel manifest ma non comparire come
documenti derivati nel database.
Se il supporto contiene più ISO o più arborescenze DICOM, verificare che tutti i
file DICOM attesi compaiano come membri derivati e che gli studi nel database
siano raggruppati per `StudyInstanceUID` o, quando presente, dai record `STUDY`
del `DICOMDIR`. Se uno stesso `StudyInstanceUID` compare sia in `DICOMDIR` sia
nelle istanze DICOM, il database deve contenere un solo record per quello
studio.

Eseguire una build incrementale ripetuta:

```bash
uv run sanikey build-patient marco
uv run sanikey build-patient marco
uv run sanikey build-patient irene
uv run sanikey build-patient irene
```

Dopo una build full completata, la cache di estrazione testo esiste già. La
prima e la seconda build incrementale senza modifiche ai sorgenti devono quindi
mostrare `documenti_estratti=0` e `documenti_cached=` maggiore di zero per i
documenti non DICOM già estratti con la stessa identità (`document_id`, path,
kind, SHA256 e provenance). Se la cache viene rimossa manualmente, la prima
build incrementale successiva può riestrarre i documenti e ricrearla. Il file di
cache si trova in:

```bash
test -f local-data/generated/marco/cache/extracted_text.json
test -f local-data/generated/irene/cache/extracted_text.json
```

Eseguire una build full per verificare che la cache non venga usata come
scorciatoia:

```bash
uv run sanikey build-patient marco --mode full
uv run sanikey build-patient irene --mode full
```

In questo caso `documenti_cached=` deve essere `0` e `documenti_estratti=` deve
riflettere i documenti non DICOM sottoposti a estrazione testo.

Generare l'export USB verso un target locale di verifica e rigenerare anche
l'immagine canonica prima di validarla, in modo da non controllare un residuo di
run precedenti:

Prima di usare un target locale diverso da `exports/usb-image`, verificare
l'UUID del filesystem che contiene quel target. Se
`[global.usb].usb_uuid` è impostato, SaniKey confronta quel
valore anche per `local-data/usb-target`; un valore pensato per una chiavetta
fisica farà fallire l'export locale se il filesystem del checkout ha UUID
diverso.

```bash
mkdir -p local-data/usb-target
findmnt --json --output TARGET,FSTYPE,UUID --target local-data/usb-target
```

Per eseguire il solo smoke test locale, usare una copia temporanea della
configurazione con l'UUID del filesystem locale. Non registrare questo UUID come
UUID definitivo della chiavetta.

```bash
export LOCAL_USB_UUID="$(findmnt -no UUID --target local-data/usb-target)"
test -n "$LOCAL_USB_UUID"
cp config/accounts.toml local-data/accounts.local-usb.toml
python - <<'PY'
from pathlib import Path
import os
import re

path = Path("local-data/accounts.local-usb.toml")
uuid = os.environ["LOCAL_USB_UUID"]
text = path.read_text(encoding="utf-8")
text = re.sub(
    r'usb_uuid = "[^"]*"',
    f'usb_uuid = "{uuid}"',
    text,
)
path.write_text(text, encoding="utf-8")
PY
uv run sanikey validate-config local-data/accounts.local-usb.toml
```

```bash
rm -rf exports/usb-image local-data/usb-target
uv run sanikey export-usb exports/usb-image
uv run sanikey export-usb --config local-data/accounts.local-usb.toml local-data/usb-target
uv run sanikey validate-usb exports/usb-image
uv run sanikey validate-usb local-data/usb-target
```

`export-usb` stampa progress interattivo su `stderr` durante generazione
immagine, checksum/manifest e copia verso il target. Se serve un log senza
punti di avanzamento, aggiungere `--no-progress`.

I comandi `validate-usb` devono stampare:

```text
stato=ok
```

Interrogare anche il target USB locale simulato, non solo `local-data/generated`:

```bash
test -f local-data/usb-target/SANIKEY-MANIFEST.json
test -f local-data/usb-target/patients/marco/medical_archive.db
test -f local-data/usb-target/patients/marco/web/data.js
test -f local-data/usb-target/patients/marco/web/content-search.js
test -f local-data/usb-target/patients/irene/medical_archive.db
test -f local-data/usb-target/patients/irene/web/data.js
test -f local-data/usb-target/patients/irene/web/content-search.js
sqlite3 local-data/usb-target/patients/marco/medical_archive.db 'SELECT count(*) FROM documents;'
sqlite3 local-data/usb-target/patients/irene/medical_archive.db 'SELECT count(*) FROM documents;'
```

### Verifica su Chiavetta Fisica

Inserire la chiavetta USB, montarla con gli strumenti del sistema operativo e
identificare il mountpoint. Su Linux:

```bash
lsblk -f
findmnt
```

Verificare subito UUID e filesystem del mountpoint della chiavetta:

```bash
USB_MOUNT=/run/media/$USER/SANIKEY
findmnt --json --output SOURCE,TARGET,FSTYPE,UUID --target "$USB_MOUNT"
USB_DEVICE="$(findmnt -no SOURCE --target "$USB_MOUNT")"
USB_UUID="$(findmnt -no UUID --target "$USB_MOUNT")"
test -n "$USB_DEVICE"
test -n "$USB_UUID"
printf 'device=%s uuid=%s\n' "$USB_DEVICE" "$USB_UUID"
```

Se la chiavetta è quella corretta, aggiornare la configurazione con l'UUID reale
del filesystem USB. Aggiornare `[global.usb].usb_uuid`; i campi
`usb_uuid` dei pazienti sono opzionali e devono essere aggiornati solo se sono
presenti come override espliciti.

```bash
cp config/accounts.toml config/accounts.toml.bak
export USB_UUID="$(findmnt -no UUID --target "$USB_MOUNT")"
test -n "$USB_UUID"
python - <<'PY'
from pathlib import Path
import os
import re

path = Path("config/accounts.toml")
uuid = os.environ["USB_UUID"]
text = path.read_text(encoding="utf-8")
text = re.sub(
    r'usb_uuid = "[^"]*"',
    f'usb_uuid = "{uuid}"',
    text,
)
path.write_text(text, encoding="utf-8")
PY
uv run sanikey validate-config
```

In alternativa, se la configurazione contiene già l'UUID desiderato e si vuole
assegnarlo alla chiavetta, smontare il filesystem e cambiare l'UUID del volume
exFAT. Questo modifica la chiavetta: eseguirlo solo dopo aver verificato con
certezza `USB_DEVICE`.

```bash
EXPECTED_USB_UUID="$(python - <<'PY'
import tomllib
from pathlib import Path

config = tomllib.loads(Path("config/accounts.toml").read_text(encoding="utf-8"))
print(config["global"]["usb"]["usb_uuid"])
PY
)"
test -n "$EXPECTED_USB_UUID"
sudo umount "$USB_MOUNT"
sudo tune.exfat -U "$EXPECTED_USB_UUID" "$USB_DEVICE"
sync
```

Rimontare la chiavetta e ricontrollare che `findmnt -no UUID --target
"$USB_MOUNT"` stampi lo stesso UUID registrato in `config/accounts.toml`.

Se la chiavetta non e' ancora preparata, formattarla e assegnare label con
comandi di sistema, dopo aver identificato con certezza la partizione corretta.
Questi comandi sono distruttivi: sostituire `/dev/sdX1` solo dopo verifica con
`lsblk -f`.

```bash
lsblk -f
sudo mkfs.exfat -n SANIKEY /dev/sdX1
sudo exfatlabel /dev/sdX1 SANIKEY
sync
```

Smontare e rimontare la chiavetta, poi aggiornare
`[global.usb].usb_uuid` con l'UUID reale mostrato da `lsblk -f`
o `findmnt`.

Impostare una variabile con il mountpoint reale. Esempio:

```bash
USB_MOUNT=/run/media/$USER/SANIKEY
test -d "$USB_MOUNT"
test -w "$USB_MOUNT"
findmnt "$USB_MOUNT"
```

L'export verso una chiavetta fisica sostituisce il contenuto SaniKey nel target:
usare solo un mountpoint verificato e dedicato.

```bash
uv run sanikey export-usb "$USB_MOUNT"
sync
uv run sanikey validate-usb "$USB_MOUNT"
```

Il comando `validate-usb` deve stampare:

```text
stato=ok
```

Verificare gli artefatti direttamente sulla chiavetta, non solo nella directory
locale:

```bash
test -f "$USB_MOUNT/SANIKEY-MANIFEST.json"
test -f "$USB_MOUNT/index.html"
test -f "$USB_MOUNT/patients/marco/medical_archive.db"
test -f "$USB_MOUNT/patients/marco/web/data.js"
test -f "$USB_MOUNT/patients/marco/web/content-search.js"
test -f "$USB_MOUNT/patients/irene/medical_archive.db"
test -f "$USB_MOUNT/patients/irene/web/data.js"
test -f "$USB_MOUNT/patients/irene/web/content-search.js"
sqlite3 "$USB_MOUNT/patients/marco/medical_archive.db" 'SELECT count(*) FROM documents;'
sqlite3 "$USB_MOUNT/patients/irene/medical_archive.db" 'SELECT count(*) FROM documents;'
xdg-open "$USB_MOUNT/index.html"
```

Nel browser, controllare che la ricerca funzioni e che non compaia `Failed to
fetch` aprendo le pagine direttamente dalla chiavetta. Smontare la chiavetta
solo dopo `sync` e dopo la chiusura delle verifiche:

Verificare anche il comportamento della UI di consultazione:

- la pagina mostra il paziente corretto e l'eventuale sottotitolo configurato;
- la ricerca porta immediatamente a risultati federati raggruppati per sezioni,
  con link contestuali a `Documenti`, `Terapie`, `Farmaci`, `Problemi`,
  `Procedure`, `Osservazioni` o `Studi DICOM` dentro il pannello dei risultati
  quando presenti;
- una query con nome commerciale di un farmaco reale mostra il farmaco e le
  terapie collegate;
- una query con principio attivo reale mostra farmaci o terapie collegate;
- una query con schedula reale, per esempio `cena` o `risveglio`, mostra le
  terapie che la contengono;
- il bottone `Ricerca avanzata` cambia il box di ricerca e permette una query
  su testo estratto/OCR, per esempio un valore di laboratorio realmente
  presente come `Creatinina`;
- i punti interrogativi di aiuto della ricerca base e avanzata sono accanto al
  rispettivo bottone, si aprono in modal locali e il bottone `Chiudi` libera la
  navigazione;
- una query booleana reale, per esempio `creatinina AND (2024 OR 2025) NOT urine`,
  mostra risultati comprensibili anche nei metadati clinici, oppure un messaggio
  di sintassi leggibile;
- `Sintesi Clinica` mostra una dashboard clinica con problemi, terapie,
  farmaci, osservazioni e procedure quando presenti;
- `Studi DICOM` compare come sezione autonoma quando il payload contiene studi;
- la timeline e' consultabile in ordine cronologico inverso salvo diversa
  configurazione;
- su schermo largo e sufficiente la UI passa al layout a due sezioni, con
  azioni esplicite per aprire una sezione nel pane sinistro o destro e timeline
  inizialmente a destra;
- su schermo stretto o riducendo la finestra header, ricerca e controlli
  restano utilizzabili;
- i link `Apri originale` puntano a file sotto la chiavetta e non a percorsi
  assoluti del computer di build.
- gli studi DICOM appaiono come schede aggregate e non come migliaia di file
  interni non cliccabili.
- se uno studio DICOM contiene un viewer HTML, la scheda mostra `Apri studio
  DICOM` e il link si apre in un nuovo tab da un path relativo sotto
  `patients/<id>/dicom-viewers/`.

Controllare automaticamente che il payload frontend della chiavetta non contenga
path sorgente assoluti:

```bash
! rg '/home/|file://' "$USB_MOUNT"/patients/*/web/data.js
! rg '/home/|file://' "$USB_MOUNT"/patients/*/web/content-search.js
```

Verificare anche che almeno un link `Apri originale` risolva realmente a un
file copiato sulla chiavetta. Il comando seguente legge il primo `href`
documentale dal `data.js` del paziente `marco`, lo risolve rispetto alla
directory `web/` e controlla che il file esista:

```bash
python - "$USB_MOUNT/patients/marco/web" <<'PY'
import json
import re
import sys
from pathlib import Path

web = Path(sys.argv[1])
payload = web.joinpath("data.js").read_text(encoding="utf-8")
match = re.fullmatch(r"window[.]SANIKEY_DATA = (.*);\n", payload, re.S)
if match is None:
    raise SystemExit("data.js non contiene il payload SANIKEY_DATA atteso")
data = json.loads(match.group(1))
href = next(item["href"] for item in data["documents"] if item.get("href"))
target = (web / href).resolve()
if not target.is_file():
    raise SystemExit(f"Apri originale non risolve a un file: {target}")
print(target)
PY
```

Verificare allo stesso modo gli eventuali link ai viewer HTML DICOM. Se un
paziente non ha viewer HTML, il comando stampa `no viewer href` ed e' comunque
accettabile.

```bash
python - "$USB_MOUNT/patients/marco/web" <<'PY'
import json
import re
import sys
from pathlib import Path

web = Path(sys.argv[1])
payload = web.joinpath("data.js").read_text(encoding="utf-8")
match = re.fullmatch(r"window[.]SANIKEY_DATA = (.*);\n", payload, re.S)
if match is None:
    raise SystemExit("data.js non contiene il payload SANIKEY_DATA atteso")
data = json.loads(match.group(1))
hrefs = [
    item.get("viewer_href")
    for item in data.get("clinical", {}).get("dicom_studies", [])
    if item.get("viewer_href")
]
if not hrefs:
    print("no viewer href")
    raise SystemExit(0)
target = (web / hrefs[0]).resolve()
if not target.is_file():
    raise SystemExit(f"Apri studio DICOM non risolve a un file: {target}")
print(target)
PY
```

```bash
sync
```

## Controlli sugli artefatti

Verificare la presenza degli artefatti principali:

```bash
test -f local-data/generated/marco/database/medical_archive.db
test -f local-data/generated/marco/web/index.html
test -f local-data/generated/marco/web/data/documents.json
test -f local-data/generated/marco/web/data/search.json
test -f local-data/generated/marco/web/data/timeline.json
test -f local-data/generated/marco/web/data.js
test -f local-data/generated/marco/web/content-search.js
test -f local-data/generated/marco/checksums.sha256
test -f local-data/generated/irene/database/medical_archive.db
test -f local-data/generated/irene/web/index.html
test -f local-data/generated/irene/web/data/documents.json
test -f local-data/generated/irene/web/data/search.json
test -f local-data/generated/irene/web/data/timeline.json
test -f local-data/generated/irene/web/data.js
test -f local-data/generated/irene/web/content-search.js
test -f local-data/generated/irene/checksums.sha256
test -f exports/usb-image/SANIKEY-MANIFEST.json
test -f local-data/usb-target/SANIKEY-MANIFEST.json
```

Verificare che l'immagine canonica e il target siano validabili:

```bash
uv run sanikey validate-usb exports/usb-image
uv run sanikey validate-usb local-data/usb-target
```

Verificare che i documenti originali non siano stati modificati:

```bash
uv run sanikey document-integrity after --output-dir local-data
uv run sanikey document-integrity check --output-dir local-data
```

Il controllo deve stampare `stato=ok` per ogni paziente. Se stampa
`stato=changed` o restituisce stato non zero, fermarsi: almeno un file sotto
`source_documents` e' stato modificato, aggiunto o rimosso rispetto allo
snapshot iniziale.

Verificare che cache, log e directory temporanee generate non siano nel target:

```bash
find local-data/usb-target \( -name cache -o -name logs -o -name tmp -o -name temporary \) -print
```

Il comando non deve elencare directory operative non consultabili.

Verificare anche i manifest prodotti dalla build e dall'export:

```bash
test -f local-data/generated/marco/manifests/container_staging.json
test -f local-data/generated/marco/manifests/dicom_html_viewers.json
test -f local-data/generated/marco/reports/build_report.json
test -f local-data/generated/marco/checksums.sha256
test -f local-data/generated/irene/manifests/container_staging.json
test -f local-data/generated/irene/manifests/dicom_html_viewers.json
test -f local-data/generated/irene/reports/build_report.json
test -f local-data/generated/irene/checksums.sha256
test -f exports/usb-image/SANIKEY-MANIFEST.json
test -f local-data/usb-target/SANIKEY-MANIFEST.json
```

Se il paziente non ha viewer HTML DICOM, `dicom_html_viewers.json` deve comunque
essere JSON valido con lista `viewers` vuota.

## Controlli sul contenuto

Ispezionare i JSON statici:

```bash
python -m json.tool local-data/generated/marco/web/data/documents.json >/tmp/sanikey-documents.json
python -m json.tool local-data/generated/marco/web/data/search.json >/tmp/sanikey-search.json
python -m json.tool local-data/generated/marco/web/data/timeline.json >/tmp/sanikey-timeline.json
python -m json.tool local-data/generated/irene/web/data/documents.json >/tmp/sanikey-irene-documents.json
python -m json.tool local-data/generated/irene/web/data/search.json >/tmp/sanikey-irene-search.json
python -m json.tool local-data/generated/irene/web/data/timeline.json >/tmp/sanikey-irene-timeline.json
```

Controllare manualmente che:

- `documents.json` contenga i documenti attesi, le categorie derivate dalle
  directory e i tag curati;
- `search.json` contenga sia documenti sia metadati curati, con sezioni e campi
  renderizzabili dalla UI;
- `content-search.js` contenga il payload `SANIKEY_CONTENT_SEARCH` con documenti
  dotati di testo estratto quando l'estrazione/OCR e' riuscita;
- `timeline.json` contenga eventi datati e terapie come intervalli, se i dati
  curati li includono;
- `summary.json` contenga `clinical_summary_html` quando
  `clinical_summary.toml` usa `summary`;
- i documenti `.md` in `documents.json` contengano `markdown_html`;
- proposte AI non approvate non compaiano negli export standard.

Verificare che `data.js` contenga il payload clinico usato dalla dashboard:

```bash
python - <<'PY'
import json
import re
from pathlib import Path

for patient in ("marco", "irene"):
    script = Path("local-data/generated") / patient / "web" / "data.js"
    payload = script.read_text(encoding="utf-8")
    match = re.fullmatch(r"window[.]SANIKEY_DATA = (.*);\n", payload, re.S)
    if match is None:
        raise SystemExit(f"{script} non contiene SANIKEY_DATA")
    data = json.loads(match.group(1))
    clinical = data["clinical"]
    print(
        patient,
        "therapies", len(clinical["therapies"]),
        "medications", len(clinical["medications"]),
        "observation_series", len(clinical.get("observation_series", [])),
        "observation_points", len(clinical.get("observation_points", [])),
        "dicom_studies", len(clinical["dicom_studies"]),
    )
PY
```

Verificare che il payload avanzato sia JSON valido all'interno dello script
locale:

```bash
python - <<'PY'
import json
import re
from pathlib import Path

for patient in ("marco", "irene"):
    script = Path("local-data/generated") / patient / "web" / "content-search.js"
    payload = script.read_text(encoding="utf-8")
    match = re.fullmatch(r"window[.]SANIKEY_CONTENT_SEARCH = (.*);\n", payload, re.S)
    if match is None:
        raise SystemExit(f"{script} non contiene SANIKEY_CONTENT_SEARCH")
    data = json.loads(match.group(1))
    print(patient, "advanced_documents", len(data["documents"]))
PY
```

Verificare il rendering Markdown senza esporre HTML grezzo:

```bash
python - <<'PY'
import json
from pathlib import Path

for patient in ("marco", "irene"):
    root = Path("local-data/generated") / patient / "web" / "data"
    summary = json.loads((root / "summary.json").read_text(encoding="utf-8"))
    documents = json.loads((root / "documents.json").read_text(encoding="utf-8"))
    html_fields = [summary.get("clinical_summary_html") or ""]
    html_fields.extend(item.get("markdown_html") or "" for item in documents)
    assert not any("<script" in value.lower() for value in html_fields)
    print(patient, "markdown_html_fields", sum(1 for value in html_fields if value))
PY
```

Verificare il database:

```bash
sqlite3 local-data/generated/marco/database/medical_archive.db '.tables'
sqlite3 local-data/generated/marco/database/medical_archive.db 'SELECT count(*) FROM documents;'
sqlite3 local-data/generated/marco/database/medical_archive.db 'SELECT count(*) FROM document_text;'
sqlite3 local-data/generated/marco/database/medical_archive.db 'SELECT count(*) FROM observation_series;'
sqlite3 local-data/generated/marco/database/medical_archive.db 'SELECT count(*) FROM observation_points;'
sqlite3 local-data/generated/marco/database/medical_archive.db "SELECT count(*) FROM document_fts WHERE document_fts MATCH 'test';"
sqlite3 local-data/generated/marco/database/medical_archive.db "SELECT support_kind, count(*) AS studies, sum(instance_count) AS instances FROM dicom_studies GROUP BY support_kind ORDER BY support_kind;"
sqlite3 local-data/generated/marco/database/medical_archive.db "SELECT support_kind, study_instance_uid, instance_count FROM dicom_studies ORDER BY CASE WHEN support_kind IN ('dicom_study','dicomdir_study') THEN 0 ELSE 1 END, instance_count DESC, support_path LIMIT 20;"
sqlite3 local-data/generated/marco/database/medical_archive.db "SELECT id, count(*) FROM dicom_studies GROUP BY id HAVING count(*) > 1;"
sqlite3 local-data/generated/irene/database/medical_archive.db '.tables'
sqlite3 local-data/generated/irene/database/medical_archive.db 'SELECT count(*) FROM documents;'
sqlite3 local-data/generated/irene/database/medical_archive.db 'SELECT count(*) FROM document_text;'
sqlite3 local-data/generated/irene/database/medical_archive.db 'SELECT count(*) FROM observation_series;'
sqlite3 local-data/generated/irene/database/medical_archive.db 'SELECT count(*) FROM observation_points;'
sqlite3 local-data/generated/irene/database/medical_archive.db "SELECT count(*) FROM document_fts WHERE document_fts MATCH 'test';"
sqlite3 local-data/generated/irene/database/medical_archive.db "SELECT support_kind, count(*) AS studies, sum(instance_count) AS instances FROM dicom_studies GROUP BY support_kind ORDER BY support_kind;"
sqlite3 local-data/generated/irene/database/medical_archive.db "SELECT support_kind, study_instance_uid, instance_count FROM dicom_studies ORDER BY CASE WHEN support_kind IN ('dicom_study','dicomdir_study') THEN 0 ELSE 1 END, instance_count DESC, support_path LIMIT 20;"
sqlite3 local-data/generated/irene/database/medical_archive.db "SELECT id, count(*) FROM dicom_studies GROUP BY id HAVING count(*) > 1;"
```

La query su `document_text` deve essere maggiore di zero se nel set sono presenti
documenti testuali, PDF con testo digitale, PDF OCR riusciti o documenti Office
leggibili. Le immagini sorgente isolate non producono testo OCR diretto. La
query su `observation_series` e `observation_points` deve essere maggiore di
zero solo per i pazienti con `observation_imports.toml` importato; altrimenti
può restituire `0`.
La
query FTS può restituire `0` se il
termine scelto non esiste in titolo, categoria, tag o testo estratto. Ripetere
con un termine realmente presente.
Per i DICOM, `support_kind='dicom_study'` o `support_kind='dicomdir_study'`
indica uno studio raggruppato; `instance_count` deve essere maggiore di 1 quando
più slice appartengono allo stesso `StudyInstanceUID`. Record `dicom_file`
singoli indicano file DICOM senza metadati studio leggibili. Le query con
`GROUP BY id HAVING count(*) > 1` non devono stampare righe.
Se il supporto contiene un viewer HTML riconosciuto, `data.js` contiene un
`viewer_href` relativo; `validate-usb` lo controlla come gli altri href.

## Consultazione offline

Aprire il frontend generato dal target:

```bash
xdg-open local-data/usb-target/index.html
```

Se `xdg-open` non è disponibile, aprire manualmente i file nel browser.

Controllare:

- la pagina `index.html` apre direttamente l'unico paziente o mostra la lista dei pazienti;
- la sintesi clinica mostra il contenuto atteso;
- la timeline è visibile;
- la ricerca client-side filtra i documenti;
- non compare il messaggio `Failed to fetch` aprendo la pagina direttamente dal
  file manager o con URL `file://`;
- i link ai documenti originali puntano a file presenti nel target;
- la pagina resta consultabile scollegando la rete.

Non usare screenshot con dati reali come evidenza persistente nel repository.

## Test negativo checksum

Su una copia del target, alterare un file e verificare il fallimento:

```bash
cp -a local-data/usb-target local-data/usb-target-tampered
printf '\nTAMPER\n' >> local-data/usb-target-tampered/patients/marco/web/index.html
uv run sanikey validate-usb local-data/usb-target-tampered
```

Il comando deve restituire stato non zero e stampare:

```text
stato=invalido
```

## Criteri di accettazione

La verifica è superata solo se:

- `validate-config`, `build-patient`, `export-usb` e `validate-usb` completano
  con successo;
- eventuali duplicati SHA256 sono stati segnalati e valutati manualmente;
- `exports/usb-image/` e il target di verifica contengono manifest valido;
- hash e `mtime` dei documenti originali non cambiano;
- database, JSON e frontend contengono i dati attesi;
- il frontend è consultabile da file locale;
- il test negativo checksum fallisce come previsto;
- `git status --short` non mostra dati reali, configurazioni private o export.

## Esito e registrazione

Registrare l'esito fuori dal repository, includendo:

- data della verifica;
- commit verificato, ottenuto con `git rev-parse HEAD`;
- numero e tipi di documenti usati;
- comandi eseguiti;
- esito dei controlli;
- eventuali anomalie.

Non registrare nomi reali, contenuti clinici, UUID reali o percorsi privati in
documentazione versionata.

## Limiti noti

Questa procedura non dimostra ancora:

- identificazione automatica della chiavetta tramite UUID filesystem reale;
- preferenza `rsync` e fallback operativo;
- controllo spazio disponibile;
- verifica exFAT;
- backup e disaster recovery;
- accessibilità e responsività complete del frontend;
- provider AI reali o integrazioni FHIR/HL7.

Questi punti restano fuori dallo slice di implementazione iniziale.
