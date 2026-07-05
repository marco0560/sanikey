# Verifica end-to-end con dati reali

Questa procedura verifica manualmente che lo slice di implementazione iniziale
produca un archivio consultabile, isolato e verificabile a partire da dati reali.
Non sostituisce la suite automatica: serve a validare il comportamento operativo
su un dataset reale controllato.

## Obiettivo

Dimostrare che SaniKey può:

- leggere una configurazione locale fuori da Git;
- processare documenti reali di un paziente;
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
mkdir -p local-data/{usb-target,generated/marco,marco/{documents,metadata}}
```

con `local-data/` in `.gitignore`.

Inserire in `local-data/marco/documents` un piccolo campione reale
ma controllato:

- almeno un referto testuale o PDF;
- almeno un documento con data nel nome, se disponibile;
- opzionalmente un supporto DICOM ISO o ZIP;
- opzionalmente sottodirectory cliniche, ad esempio `laboratory/` o `imaging/`.

Annotare hash e timestamp prima della build:

```bash
find local-data/marco/documents -type f -print0 | sort -z | xargs -0 sha256sum > local-data/before.sha256
find local-data/marco/documents -type f -printf '%p\t%T@\n' | sort > local-data/before-mtime.tsv
```

## Configurazione locale

Creare `config/accounts.toml`. Il file è privato e deve restare ignorato da Git.

```bash
mkdir -p config
```

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

Verificare che Git non veda dati privati:

```bash
git status --short
```

Se compaiono configurazioni reali, documenti, export o dati sanitari, fermarsi e
correggere `.gitignore` o i percorsi locali prima di procedere.

## Metadati curati minimi

Creare metadati minimi in `local-data/marco/metadata`.

`clinical_summary.toml` contiene una sintesi clinica libera. Per l'uso corrente
può essere trattata come anamnesi/sommario narrativo: problemi rilevanti,
interventi, terapie importanti, allergie note, avvertenze e contesto utile alla
consultazione. Se il testo ha più righe, usare una stringa TOML multilinea.
Il testo e' trattato come plain text: eventuali marker Markdown aiutano la
scrittura ma non vengono convertiti in HTML nel frontend.

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

## Esecuzione pipeline

Validare la configurazione:

```bash
uv run sanikey validate-config --config config/accounts.toml
```

Questo passo deve anche validare i metadati curati: correggere subito TOML
malformati, id duplicati o terapie che citano un `medication_id` non presente in
`medications.toml`.

Eseguire una scansione preliminare dei documenti:

```bash
uv run sanikey scan-documents --config config/accounts.toml
```

Il comando stampa solo il riepilogo per paziente e gli eventuali warning
rilevabili senza build completa. Eseguire anche il preflight leggero prima di
una build lunga:

```bash
uv run sanikey scan-documents --config config/accounts.toml --preflight
```

Il preflight controlla archivi, immagini e documenti Office moderni/OpenDocument
senza eseguire OCR PDF e senza convertire documenti legacy Office. Per le
immagini verifica anche la disponibilita' del provider OCR `tesseract`. Se
compaiono warning inattesi, fermarsi e risolverli o annotarli prima di
proseguire.

Per leggere a schermo l'inventario dei documenti ingeriti:

```bash
uv run sanikey scan-documents --config config/accounts.toml --verbose
```

Per conservare l'inventario completo in un file riprocessabile:

```bash
uv run sanikey scan-documents --config config/accounts.toml --output local-data/scan-documents.tsv --format text
uv run sanikey scan-documents --config config/accounts.toml --output local-data/scan-documents.csv --format csv
```

Se l'output contiene `duplicates=`, leggere eventuali righe `WARNING:`. File con
lo stesso SHA256 sono identici: SaniKey conserva solo la prima occorrenza
nell'archivio generato e segnala il file saltato insieme al file trattenuto. In
presenza di duplicati inattesi, fermarsi e decidere manualmente se rimuovere,
rinominare o archiviare separatamente una delle copie prima di proseguire.

Eseguire la build completa:

```bash
uv run sanikey build-patient marco --config config/accounts.toml --mode full
```

L'output deve essere un riepilogo multi-riga leggibile, non una riga JSON
minificata. Annotare il percorso `report=...`: contiene il dettaglio completo
dei warning e deve essere consultato se `warnings` e' maggiore di zero.
`documents=` conta solo i documenti sorgente deduplicati; usare
`derived_documents=`, `dicom_instances=` e `total_records=` per valutare quanto
deriva da contenitori e supporti diagnostici.

Se sono presenti archivi o immagini ISO, verificare anche il manifest di
staging:

```bash
python -m json.tool local-data/generated/marco/manifests/container_staging.json | less
```

Controllare che ogni membro estratto abbia `container_id`, `internal_path`,
`sha256` e `path`. I file DICOM interni devono risultare catalogati come DICOM
derivati, non trattati come documenti OCR o testo ordinario. I path tecnici dei
viewer, ad esempio `Help`, `Manual`, `Viewer-Windows`, `jre` e `assets`, devono
restare nel manifest ma non comparire come documenti derivati nel database.

Eseguire una build incrementale ripetuta:

```bash
uv run sanikey build-patient marco --config config/accounts.toml
uv run sanikey build-patient marco --config config/accounts.toml
```

Generare l'export USB verso un target locale di verifica:

```bash
uv run sanikey export-usb --config config/accounts.toml local-data/usb-target
uv run sanikey validate-usb local-data/usb-target
```

Il secondo comando deve stampare:

```text
status=ok
```

## Controlli sugli artefatti

Verificare la presenza degli artefatti principali:

```bash
test -f local-data/generated/marco/database/medical_archive.db
test -f local-data/generated/marco/web/index.html
test -f local-data/generated/marco/web/data/documents.json
test -f local-data/generated/marco/web/data/search.json
test -f local-data/generated/marco/web/data/timeline.json
test -f local-data/generated/marco/checksums.sha256
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
find local-data/marco/documents -type f -print0 | sort -z | xargs -0 sha256sum > local-data/after.sha256
find local-data/marco/documents -type f -printf '%p\t%T@\n' | sort > local-data/after-mtime.tsv
diff -u local-data/before.sha256 local-data/after.sha256
diff -u local-data/before-mtime.tsv local-data/after-mtime.tsv
```

Entrambi i `diff` devono essere vuoti.

Verificare che cache, log e directory temporanee generate non siano nel target:

```bash
find local-data/usb-target \( -name cache -o -name logs -o -name tmp -o -name temporary \) -print
```

Il comando non deve elencare directory operative non consultabili.

## Controlli sul contenuto

Ispezionare i JSON statici:

```bash
python -m json.tool local-data/generated/marco/web/data/documents.json >/tmp/sanikey-documents.json
python -m json.tool local-data/generated/marco/web/data/search.json >/tmp/sanikey-search.json
python -m json.tool local-data/generated/marco/web/data/timeline.json >/tmp/sanikey-timeline.json
```

Controllare manualmente che:

- `documents.json` contenga i documenti attesi, le categorie derivate dalle
  directory e i tag curati;
- `search.json` contenga sia documenti sia metadati curati;
- `timeline.json` contenga eventi datati e terapie come intervalli, se i dati
  curati li includono;
- proposte AI non approvate non compaiano negli export standard.

Verificare il database:

```bash
sqlite3 local-data/generated/marco/database/medical_archive.db '.tables'
sqlite3 local-data/generated/marco/database/medical_archive.db 'SELECT count(*) FROM documents;'
sqlite3 local-data/generated/marco/database/medical_archive.db "SELECT count(*) FROM document_fts WHERE document_fts MATCH 'test';"
```

La query FTS può restituire `0` se il termine scelto non esiste nei titoli,
categorie o tag. Ripetere con un termine realmente presente.

## Consultazione offline

Aprire il frontend generato dal target:

```bash
xdg-open local-data/usb-target/START-HERE-Marco-Coppola.html
```

Se `xdg-open` non è disponibile, aprire manualmente il file nel browser.

Controllare:

- la pagina `START-HERE` apre il frontend del paziente corretto;
- il riepilogo mostra il numero documenti atteso;
- la timeline è visibile;
- la ricerca client-side filtra i documenti;
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
status=invalid
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
