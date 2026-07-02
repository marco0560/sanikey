# Stato dei Test

Questo report confronta la specifica dettagliata, le decisioni architetturali
iniziali e la superficie di test corrente. L'obiettivo è identificare le
funzionalità e le decisioni non protette da test dedicati.

## Copertura Esistente

La suite protegge soprattutto il percorso minimo single-patient:

- configurazione base e privacy minima: `load_accounts`, path assoluti,
  identificativo paziente valido e rifiuto di path reali dentro il repository;
- scansione documenti: SHA256, categoria da directory, data/titolo da filename,
  duplicati, file `.txt` e supporti DICOM non estratti via OCR;
- DICOM: ISO/ZIP catalogati, directory di espansione manuale e viewer
  `index.html`;
- metadati curati: caricamento base di problemi, farmaci, terapie, procedure,
  osservazioni, timeline, tag e sommario;
- database: creazione SQLite, inserimento documenti/metadati/DICOM e presenza
  FTS;
- build: manifest, report, checksum e database;
- export JSON, frontend statico e USB single-patient;
- smoke test CLI per quasi tutti i sottocomandi.

Aggiornamento 2026-07-02: la suite protegge inoltre:

- build multi-paziente con esclusione dei pazienti disabilitati e artefatti
  database/frontend indipendenti;
- export USB multi-paziente con archivi separati, esclusione dei pazienti
  disabilitati e validazione negativa su checksum alterati;
- preservazione di contenuto e `mtime` dei documenti originali durante la build;
- eventi timeline manuali con intervallo `start_date`/`end_date` esportati nel
  JSON statico;
- errori TOML sintattici nei metadati, vincoli SQLite su terapie senza farmaco,
  esclusione delle proposte AI non approvate dagli export standard e blocco dei
  checksum USB alterati;
- esclusione di cache, log e directory temporanee generate dall'export USB;
- costruzione canonica della chiavetta da `exports/usb-image/`, mirror verso il
  target richiesto, rimozione dei file obsoleti nel target e test opzionale su
  filesystem reale tramite `SANIKEY_USB_INTEGRATION_TARGET`;
- default incrementale della build programmatica e stabilità di manifest e
  checksum su build incrementali ripetute senza modifiche agli input;
- assenza di storage browser, cookie, telemetry e URL HTTP(S) negli asset
  frontend generati.

## Scoperte Non Protette

### Multi-Paziente

Decisioni coinvolte: DA-001..DA-007, DA-108, DA-120.

I test usano quasi sempre un solo paziente. Non risultano test dedicati per:

- isolamento tra pazienti: coperto per build ed export USB;
- database indipendenti per più pazienti: coperto;
- frontend indipendenti per più pazienti: coperto;
- pazienti disabilitati: coperto per build ed export USB;
- chiavetta con più archivi: coperto per layout simulato.

### Identificazione USB

Decisioni coinvolte: DA-016, DA-105, DA-129.

`usb_uuid` è richiesto in configurazione, ma non risultano test per:

- identificazione della chiavetta;
- mismatch UUID;
- blocco del deploy su target errato;
- sostituzione chiavetta e registrazione del nuovo UUID.

### Distribuzione USB Reale

Decisioni coinvolte: DA-103..DA-112.

Sono testati export e checksum su directory simulata, ma non:

- uso preferenziale di `rsync`;
- fallback di copia;
- controllo spazio disponibile;
- rimozione file obsoleti: coperto per il mirror del target;
- atomicità logica;
- modalità `full`, `incremental` e `verify`;
- filesystem raccomandato exFAT.

### Incrementalità e Cache

Decisioni coinvolte: DA-035, DA-039, DA-060, DA-092, DA-094, DA-101, DA-122.

La suite usa principalmente build completa o singola. Non risultano protetti:

- default incrementale: coperto per `build_patient`;
- idempotenza delle fasi: coperta per manifest e checksum su build incrementali
  ripetute senza modifiche agli input;
- cache;
- riesecuzione fase-per-fase: coperta per build incrementale ripetuta;
- assenza di side effect.

### Precedenza dei Dati Curati

Decisioni coinvolte: DA-037, DA-046, DA-075.

I metadati vengono caricati, ma non è verificato che:

- i dati curati prevalgano sui derivati;
- gli override manuali prevalgano sugli elementi generati;
- le informazioni AI non approvate non abbiano autorità.

### Provenienza

Decisioni coinvolte: DA-030, DA-040, DA-059.

Esiste il modello `Provenance`, ma non risultano test su:

- persistenza della provenienza;
- propagazione della provenienza negli artefatti;
- provenienza delle informazioni derivate o AI.

### Modello Clinico Avanzato

Decisioni coinvolte: DA-023, DA-026..DA-034, DA-041..DA-042.

I modelli esistono in parte, ma non risultano test dedicati per:

- distinzione tra serie documentale e categoria;
- distinzione tra Document Series e Observation Series;
- campagne osservative;
- procedure come entità di primo livello;
- distinzione tra procedure e clinical events;
- supporto pluridecennale senza riorganizzazioni strutturali.

### Metadati Longitudinali

Decisioni coinvolte: DA-032, DA-049.

Sono testati file TOML base, ma non:

- partizionamento temporale;
- directory di dominio complesse;
- aggregazione di metadati longitudinali da più file.

### Errori nei Metadati

Decisioni coinvolte: DA-052, DA-095.

C'è copertura su un item malformato, ma non su:

- tutti i tipi di file TOML supportati;
- TOML sintatticamente invalido: coperto;
- riferimenti incrociati mancanti;
- fallimento su foreign key logiche, per esempio terapia senza farmaco: coperto
  a livello SQLite.

### Contratto AI

Decisioni coinvolte: DA-054..DA-060, DA-067, DA-100, DA-117.

Sono testati la proposta placeholder e il cambio status. Non risultano test per:

- esclusione delle proposte non approvate da export/search standard: coperto per
  gli export JSON standard;
- assenza di autorità clinica dell'AI;
- provenienza AI;
- cache incrementale AI;
- indipendenza delle funzionalità fondamentali dall'AI.

### Ricerca

Decisioni coinvolte: DA-061..DA-069, DA-090.

Sono testati payload JSON e presenza FTS, ma non:

- query FTS reali;
- ricerca su entità cliniche;
- metadati curati ricercabili;
- assenza o disabilitazione della ricerca semantica;
- fallback utilizzabile senza embedding.

### Timeline

Decisioni coinvolte: DA-070..DA-078.

È testata una timeline semplice da documento datato. Non risultano test per:

- intervalli temporali: coperto per eventi manuali;
- terapie come intervalli;
- campagne osservative;
- eventi manuali come cittadini di prima classe: coperto nell'export statico;
- override manuali;
- rigenerabilità e consultazione offline della timeline.

### Frontend Offline e Privacy

Decisioni coinvolte: DA-079..DA-089, DA-113..DA-115.

Sono presenti smoke test su file statici e un controllo parziale sulla parola
`telemetry`. La suite ora controlla anche gli asset generati contro storage
browser, cookie e URL HTTP(S). Non risultano test robusti per:

- assenza di cookie: coperto tramite assenza di `document.cookie`;
- assenza di `localStorage` o storage locale: coperto per `localStorage`,
  `sessionStorage` e `indexedDB`;
- assenza di chiamate cloud: coperto per URL HTTP(S) statici;
- funzionamento da `file://`;
- modalità sola lettura;
- accessibilità;
- stampa;
- responsività.

### Viewer DICOM

Decisione coinvolta: DA-086.

È testato il viewer `index.html`, ma non:

- viewer `.exe`;
- `autorun.inf`;
- assenza del viewer con referto ancora consultabile;
- link frontend allo studio diagnostico.

### Documenti Originali

Decisioni coinvolte: DA-021, DA-121, DA-123.

I documenti vengono letti, ma non è verificato esplicitamente che:

- hash e `mtime` restino invariati dopo build;
- ISO e ZIP DICOM siano conservati integralmente;
- la manutenzione ordinaria non modifichi documenti originali: coperto per build.

### Artefatti Non Esportabili

Decisioni coinvolte: DA-102, DA-103.

Non risultano test che impediscano l'esportazione di:

- cache: coperto per artefatti sotto `local_build`;
- log: coperto per artefatti sotto `local_build`;
- directory temporanee: coperto per artefatti sotto `local_build`;
- artefatti non esportabili.

### Backup e Disaster Recovery

Decisioni coinvolte: DA-118..DA-131.

Sono decisioni operative documentate ma non protette da test:

- backup locale ed esterno;
- verifica periodica di recuperabilità;
- procedura di restore;
- perdita degli artefatti generati senza perdita di dati autorevoli;
- chiavetta USB non considerata backup.

### Requisiti Tecnici ed Evolutivi

Decisioni coinvolte: DA-132..DA-144.

Python, SQLite, TOML e frontend statico sono parzialmente coperti. Non risultano
protetti:

- FHIR/HL7 come direzioni future;
- sincronizzazione cloud esclusa dalla versione iniziale;
- consultazione assistita da AI esclusa dalla versione iniziale;
- longevità degli archivi;
- criteri di valutazione delle evoluzioni future.

## Contratti Deboli o Ambigui

- DA-010 dichiara che la chiavetta viene sempre costruita da
  `exports/usb-image/`: coperto. L'implementazione costruisce prima
  l'immagine canonica e poi la copia verso il target passato al comando.
- DA-044 dichiara FTS5 obbligatorio. La suite conta righe nella tabella FTS, ma
  non esegue query full-text.
- DA-045 dichiara chiavi esterne SQLite obbligatorie. Il codice abilita
  `PRAGMA foreign_keys = ON`, ma non c'è un test negativo su referenze invalide.
- DA-083 e DA-114 vietano cloud, telemetria e cookie. La suite contiene solo un
  controllo parziale sul JavaScript generato.

## Priorità Consigliate

1. Multi-paziente e isolamento USB/database/frontend.
2. Privacy ed export: nessun log/cache/temp su USB e nessuna modifica agli
   originali.
3. Build incrementale, idempotenza e checksum manifest.
4. Ricerca FTS e JSON search su documenti e metadati.
5. Timeline con eventi manuali, intervalli e override.
6. Contratto AI proposal: proposte non approvate escluse dagli export standard.
7. UUID USB, checksum tamper negativo, file obsoleti e target errato.

## Sintesi

La suite protegge bene la pipeline minima single-patient, ma non protegge ancora
le decisioni architetturali più forti: multi-paziente, incrementalità, privacy
completa, offline/read-only, ricerca e timeline avanzate, distribuzione USB
reale e disaster recovery.
