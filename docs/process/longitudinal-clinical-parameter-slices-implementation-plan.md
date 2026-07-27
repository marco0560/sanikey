# Piano di Implementazione delle Slice Longitudinali dei Parametri Clinici

Stato: approvato il 25 luglio 2026.

Issue di riferimento:
[#11 — Extract and visualize longitudinal clinical parameter slices][issue-11].

Questo documento definisce il piano approvato per individuare nei testi già
estratti misurazioni ripetute dello stesso parametro clinico, applicare regole
curate e produrre serie longitudinali consultabili offline. L'implementazione
deve precedere la migrazione architetturale della issue #12, mantenendo confini
che possano essere trasferiti successivamente negli application service.

[issue-11]: https://github.com/marco0560/sanikey/issues/11

## Decisioni Approvate

| ID | Decisione |
| --- | --------- |
| D1 | Implementare la issue #11 prima della issue #12 |
| D2 | Usare `metadata_directory/parameters.toml` e riusare i sinonimi di `[terms]` |
| D3 | Estendere in modo retrocompatibile `ObservationSeries` e `ObservationPoint` |
| D4 | Esporre `discover-parameters` e `build-parameter-slices` |
| D5 | Vendorizzare e versionare Chart.js localmente |
| D6 | Selezionare il punto, mostrarne il dettaglio e aprire il documento mediante azione esplicita |

## Invarianti

- L'analisi usa esclusivamente `ExtractedText` già prodotto da SaniKey.
- La pipeline non invoca OCR aggiuntiva, AI, fuzzy matching o servizi esterni.
- Nessun comando modifica automaticamente `parameters.toml` o altri metadati
  curati.
- Valore, unità, riga e provenienza originali sono sempre conservati.
- La data clinica deriva esclusivamente da `DocumentRecord.date`.
- Timestamp e metadati del filesystem non sono sostituti impliciti della data.
- Gli output hanno ordinamento canonico e sono byte-stabili.
- stdout contiene soltanto contatori aggregati, mai valori clinici o righe
  sorgente.
- Le osservazioni curate e importate restano compatibili e distinguibili dai
  punti estratti.
- Il frontend rimane statico, offline e compatibile con `file://`.
- Le modifiche non correlate già presenti nel worktree devono essere
  preservate.

## Architettura

### Nuovi Moduli

`src/sanikey/parameter_rules.py`:

- carica e valida `metadata_directory/parameters.toml`;
- risolve i riferimenti alla sezione `[terms]`;
- valida unità, intervalli, contesti e conversioni;
- calcola versione e digest canonico delle regole.

`src/sanikey/parameter_slices.py`:

- normalizza le righe senza alterare l'evidenza originale;
- riconosce candidati nome-valore;
- interpreta prudentemente i formati numerici;
- raggruppa soltanto etichette normalizzate esattamente uguali;
- applica le regole curate;
- genera decisioni, punti e slice deterministiche.

`src/sanikey/parameter_workflows.py`:

- orchestra discovery e build;
- produce report, scaffold e riepiloghi;
- fonde punti estratti e osservazioni curate;
- espone operazioni riutilizzabili dalla CLI e da `build-patient`.

### Moduli Esistenti Coinvolti

- `src/sanikey/models.py`;
- `src/sanikey/config.py`;
- `src/sanikey/build.py`;
- `src/sanikey/metadata.py`;
- `src/sanikey/observation_imports.py`;
- `src/sanikey/exports.py`;
- `src/sanikey/database.py`;
- `src/sanikey/frontend.py`;
- `src/sanikey/cli.py`.

## Contratti di Dominio

### Candidato

Il modello di candidato contiene:

- `stable_id`;
- `document_id`;
- `document_date`;
- `document_href`;
- `document_title`;
- `document_category`;
- `source_text_digest`;
- `line_number`;
- `character_start`;
- `character_end`;
- `page_number`;
- `original_line`;
- `normalized_label`;
- `raw_value`;
- `parsed_value`;
- `number_format`;
- `qualifier`;
- `raw_unit`;
- `normalized_unit`;
- `prefix_context`;
- `suffix_context`;
- `extractor_version`.

`line_number` parte da 1. Gli offset sono indici Unicode a partire da 0 e
definiscono un intervallo semiaperto nel testo esatto identificato dal digest.
`page_number` resta assente finché l'estrattore non fornisce una mappatura
affidabile; non sono ammesse inferenze euristiche.

### Estensione di `ObservationSeries`

I seguenti campi opzionali vengono aggiunti in modo retrocompatibile:

- `synonyms`;
- `parameter_rule_id`;
- `parameter_rule_version`;
- `parameter_rule_digest`;
- `unit_variant`.

I file di osservazioni esistenti restano validi e i nuovi campi hanno default
vuoti o null.

### Estensione di `ObservationPoint`

I seguenti campi opzionali vengono aggiunti:

- `source_kind`;
- `document_id`;
- `document_href`;
- `document_title`;
- `document_category`;
- `source_text_digest`;
- `original_line`;
- `line_number`;
- `page_number`;
- `character_start`;
- `character_end`;
- `matched_label`;
- `raw_value`;
- `parsed_value`;
- `raw_unit`;
- `normalized_unit`;
- `qualifier`;
- `rule_id`;
- `rule_version`;
- `rule_digest`;
- `reason_code`.

I valori iniziali di `source_kind` sono:

```text
curated-observation
document-extraction
```

Le osservazioni già importate ricevono implicitamente
`curated-observation`. `source_type` continua a descrivere il formato della
sorgente. Nessun punto curato viene sostituito o deduplicato automaticamente.

### Identificatori Stabili

- l'identità del candidato deriva da documento, digest del testo, offset e
  contenuto riconosciuto;
- l'identità del punto estratto combina `rule_id` e identità del candidato;
- l'identità della serie combina `series_id` ed eventuale variante di unità;
- timestamp, ordine del filesystem e path assoluti non partecipano mai agli
  identificatori.

## Contratto di `parameters.toml`

### Sezione `[discovery]`

Campi previsti:

- `min_label_length`;
- `max_label_length`;
- `max_label_words`;
- `min_occurrences`;
- `min_distinct_documents`;
- `min_distinct_dates`;
- `excluded_labels`;
- `excluded_line_patterns`.

Questi valori limitano il rumore nelle proposte, ma non conferiscono validità
clinica a un gruppo.

### Regola `[parameters.<id>]`

Campi obbligatori:

- `display_name`;
- `term`;
- `version`;
- `value_type`;
- `number_formats`;
- `unit_policy`;
- `enabled`.

Campi opzionali:

- `series_id`;
- `units`;
- `unit_aliases`;
- `canonical_unit`;
- `assumed_unit`;
- `minimum`;
- `maximum`;
- `document_categories`;
- `document_kinds`;
- `document_series`;
- `required_context`;
- `excluded_context`;
- `conversions`.

I tipi iniziali sono:

```text
scalar
qualified-scalar
```

Le politiche per unità assente sono:

```text
required
allowed-but-unknown
assume-configured-unit
```

La validazione applica i seguenti vincoli:

- `term` deve esistere in `SearchDictionary.terms`;
- ogni regola abilitata deve avere una versione positiva;
- il minimo non può superare il massimo;
- `assumed_unit` è obbligatoria solo con `assume-configured-unit`;
- unità e conversioni devono essere internamente coerenti;
- campi e sezioni sconosciuti causano `ConfigError`;
- errori e messaggi CLI restano in italiano.

### Conversioni

Il primo incremento supporta soltanto conversioni affini:

```text
normalized = raw * multiplier + offset
```

Ogni conversione dichiara:

- `from_unit`;
- `to_unit`;
- `multiplier`;
- `offset`;
- `version`.

Non esistono conversioni implicite. Valore e unità originali sono sempre
conservati, insieme alla versione e al digest della conversione.

## Grammatica di Riconoscimento

L'unità di analisi è la singola riga. Il primo incremento riconosce:

- una etichetta testuale prima del primo valore compatibile;
- separatore assente, spazio, due punti o uguale;
- qualificatore assente oppure `<`, `<=`, `>` o `>=`;
- unità facoltativa secondo la regola;
- una sola sequenza principale per riga.

La normalizzazione comprende:

- normalizzazione Unicode;
- trim;
- compressione degli spazi;
- normalizzazione dei simboli tipografici configurati;
- rimozione controllata del separatore terminale dall'etichetta;
- confronto case-insensitive delle etichette.

Sono vietati:

- correzione ortografica;
- stemming;
- lemmatizzazione;
- espansione medica implicita;
- fuzzy matching;
- traduzione.

I formati numerici iniziali sono:

- intero;
- decimale con virgola;
- decimale con punto;
- migliaia con virgola e decimali con punto;
- migliaia con punto e decimali con virgola.

Raggruppamenti invalidi vengono rifiutati. Le forme interpretabili in più modi
vengono rifiutate salvo che il formato sia autorizzato esplicitamente dalla
regola.

Il contesto viene confrontato deterministicamente sul testo normalizzato della
stessa riga. Tutti i contesti richiesti devono essere presenti; la presenza di
un contesto escluso rifiuta il candidato.

## Reason Code

### Accettazione

```text
ACCEPTED_EXACT_LABEL
ACCEPTED_CONFIGURED_SYNONYM
ACCEPTED_ASSUMED_UNIT
ACCEPTED_EXPLICIT_CONVERSION
```

### Rifiuto

```text
REJECTED_AMBIGUOUS_NUMBER_FORMAT
REJECTED_INVALID_NUMBER_FORMAT
REJECTED_UNKNOWN_UNIT
REJECTED_MISSING_UNIT
REJECTED_OUT_OF_RANGE
REJECTED_DOCUMENT_CATEGORY
REJECTED_DOCUMENT_KIND
REJECTED_DOCUMENT_SERIES
REJECTED_REQUIRED_CONTEXT_MISSING
REJECTED_EXCLUDED_CONTEXT
REJECTED_DOCUMENT_DATE_MISSING
REJECTED_MULTIPLE_RULE_MATCHES
```

### Conflitto

```text
DUPLICATE_EQUIVALENT_VALUE
CONFLICTING_SAME_DAY_VALUES
CONFLICTING_UNIT
CONFLICTING_CURATED_SERIES
```

La pipeline non sceglie automaticamente tra più regole, non elimina duplicati
provenienti da documenti differenti e conserva punti dello stesso giorno con
valori differenti. Report e frontend mostrano gli avvisi; i falsi positivi
vengono risolti modificando la regola.

## Fasi di Implementazione

### Fase 0 — Contratti e Fixture

Attività:

1. Definire dataclass, enum e schema JSON/TOML.
2. Aggiungere fixture esclusivamente sintetiche.
3. Fissare ordinamenti, identificatori e reason code.
4. Documentare la provenienza tramite linea e offset.
5. Limitare il primo incremento a `scalar` e `qualified-scalar`.
6. Registrare range, paired e tabelle tra le evoluzioni successive.

Test:

- serializzazione stabile;
- compatibilità dei modelli esistenti;
- assenza di dati clinici reali nelle fixture.

La fase termina quando i contratti sono coperti da test senza cambiamenti alla
CLI o al frontend.

### Fase 1 — Discovery Deterministica

Attività:

1. Implementare lo scanner riga per riga.
2. Calcolare il digest SHA-256 del testo esatto.
3. Conservare linea originale e offset.
4. Applicare i limiti configurati alle etichette.
5. Escludere deterministicamente date, righe principalmente numeriche e codici
   riconoscibili.
6. Raggruppare soltanto etichette normalizzate identiche.
7. Produrre statistiche, esempi e motivi di ambiguità.
8. Generare uno scaffold TOML disabilitato senza scrivere nei metadati.

I comandi standalone riusano esclusivamente una cache di estrazione valida e
non richiamano `extract_text`. Se la cache è assente o stale, falliscono con
un'istruzione esplicita. Durante `build-patient`, la derivazione consuma
direttamente gli `ExtractedText` già ottenuti dalla build.

Output:

```text
reports/parameter-candidates.json
reports/parameter-rules.proposed.toml
```

Test:

- formati numerici ammessi;
- formati ambigui e raggruppamenti invalidi;
- normalizzazione delle etichette;
- soglie di proposta;
- byte stability;
- cache assente o stale;
- assenza di modifiche a `parameters.toml`.

Validazione focalizzata:

```bash
uv run pytest tests/test_parameter_slices.py
```

### Fase 2 — Regole Curate e Modello Unificato

Attività:

1. Caricare e validare `parameters.toml`.
2. Risolvere termine canonico e sinonimi da `[terms]`.
3. Applicare i filtri nell'ordine definito dalla issue.
4. Generare una decisione spiegabile per ogni candidato.
5. Applicare politiche di unità e conversioni esplicite.
6. Estendere `ObservationSeries` e `ObservationPoint`.
7. Unire punti curati ed estratti nel modello in memoria.
8. Mantenere origini e simboli distinguibili.

I valori convertiti confluiscono nell'unità canonica. Le unità ammesse ma non
convertite generano varianti separate, presentate nello stesso pannello del
parametro.

`series_id` può riferirsi a una serie curata esistente. Tipo e unità
incompatibili producono un errore esplicito. I punti curati ed estratti vengono
entrambi conservati.

Test:

- sinonimo configurato;
- sigla ambigua limitata da categoria, unità e contesto;
- unità richiesta, sconosciuta e assunta;
- conversione versionata;
- valore fuori intervallo;
- documento senza data;
- corrispondenza a più regole;
- convivenza con osservazioni importate;
- retrocompatibilità dei TOML esistenti.

Validazione focalizzata:

```bash
uv run pytest tests/test_parameter_rules.py tests/test_metadata.py tests/test_observation_imports.py
```

### Fase 3 — Workflow, CLI e Build

Comandi:

```bash
uv run sanikey discover-parameters [PATIENT]
uv run sanikey build-parameter-slices [PATIENT]
```

`discover-parameters`:

- legge documenti e cache valida;
- genera report e scaffold;
- non richiede regole abilitate;
- non modifica metadati.

`build-parameter-slices`:

- richiede `parameters.toml` valido;
- applica le regole abilitate;
- genera slice, report ed export;
- stampa soltanto contatori aggregati.

`build-patient` esegue la derivazione dopo estrazione e caricamento dei
metadati. L'assenza di `parameters.toml` disabilita la derivazione senza
errore; una configurazione presente ma non valida interrompe la build.

Il riepilogo stdout contiene:

```text
documenti_analizzati
righe_analizzate
candidati
gruppi_proposti
regole_applicate
punti_accettati
punti_rifiutati
documenti_senza_data
```

Non contiene nomi di parametro, valori, righe sorgente o path assoluti.

Output:

```text
reports/parameter-extraction.json
exports/parameter-slices.json
web/parameter-slices.js
```

Gli export hanno `schema_version`, ordinamento per parametro, unità, data e
`stable_id`, link esclusivamente relativi e nessun timestamp di esecuzione.
Il JavaScript assegna i dati a una variabile globale e non usa `fetch()`.

Le tabelle SQLite `observation_series` e `observation_points` vengono estese e
ricevono anche i punti estratti, mantenendo il database un artefatto
rigenerabile.

Test:

- parsing CLI e delegazione;
- cache obbligatoria per i comandi standalone;
- integrazione automatica in `build-patient`;
- export JSON e JavaScript deterministici;
- link relativi;
- schema SQLite e convivenza delle origini;
- doppia esecuzione con output identico.

Validazione focalizzata:

```bash
uv run pytest tests/test_cli.py tests/test_build.py tests/test_exports.py tests/test_database.py
```

### Fase 4 — Frontend Statico

Una release precisa di Chart.js viene fissata e distribuita con il package
insieme alla relativa licenza. L'asset viene copiato nella directory web
durante la build. Non sono ammessi CDN, date adapter remoti o richieste di
rete.

Il pannello sinistro della sezione `Parametri` contiene:

- ricerca deterministica;
- elenco delle slice;
- conteggio delle misurazioni;
- intervallo temporale;
- unità;
- ultima misurazione;
- avvisi.

Il pannello destro contiene:

- intestazione e sinonimi;
- grafico;
- filtri;
- tabella;
- dettaglio del punto selezionato;
- pulsante `Apri documento`.

Ordine di ricerca:

1. nome canonico esatto;
2. sinonimo esatto;
3. prefisso del nome canonico;
4. prefisso del sinonimo;
5. sottostringa.

Filtri:

- intervallo di date;
- unità;
- categoria del documento;
- mostra o nascondi qualificati;
- ordinamento della tabella.

Il grafico:

- usa timestamp numerici sull'asse X;
- distingue dataset per unità e origine;
- usa marker distinti per `qualified-scalar`;
- esclude i punti qualificati dalla linea continua;
- si adatta a viewport stretti e larghi;
- mostra tooltip e pannello con valore originale e provenienza.

La tabella contiene:

| Data | Valore originale | Unità | Documento | Etichetta trovata | Provenienza |
| ---- | ---------------- | ----- | --------- | ----------------- | ----------- |

La selezione della riga mostra il dettaglio. `Apri documento` usa il link
relativo validato. La tabella resta utilizzabile senza il grafico.

Per l'accessibilità:

- la tabella è la rappresentazione primaria;
- il canvas ha nome e descrizione ARIA;
- lista, tabella e dettaglio sono navigabili da tastiera;
- nessuna informazione è affidata soltanto al colore.

Test:

- ricerca e ordinamento;
- filtri;
- selezione da grafico e tabella;
- punti qualificati;
- apertura del documento;
- assenza di URL remoti;
- caricamento tramite `file://`;
- comportamento responsive.

Validazione focalizzata:

```bash
uv run pytest tests/test_frontend.py tests/test_exports.py tests/test_usb.py
```

### Fase 5 — Documentazione ed Esempi

File da aggiornare:

- `docs/user-guide.md`;
- `docs/first-usb-key.md`;
- `docs/process/metadata-toml-reference.md`;
- `docs/architecture.md`;
- `docs/sanikey-detailed-spec.md`;
- `docs/limits-and-future-work.md`;
- `docs/decisions/adr-observation-imports.md`;
- nuovo `docs/decisions/adr-longitudinal-parameter-slices.md`;
- `docs/decisions/index.md`;
- `docs/patients-example/`;
- `mkdocs.yml`.

Esempi e riferimenti obbligatori:

1. `docs/config-example/` e `docs/patients-example/` devono contenere un
   esempio esclusivamente sintetico per ogni file che un utilizzatore possa
   compilare o copiare nella propria configurazione: configurazione account e
   dizionario, ogni metadato curato supportato, manifest di importazione delle
   osservazioni, serie/osservazioni manuali e `parameters.toml`.
2. Ogni file di esempio deve essere nominato nel README della directory di
   esempi, con scopo, relazioni con gli altri file e indicazione se sia letto
   direttamente o generato da un comando.
3. La guida utente e la guida della prima chiavetta devono collegare gli esempi
   pertinenti dalla procedura che richiede di compilarli; non basta un rimando
   generico alla directory.
4. La documentazione contributor deve aggiornare architettura, specifica,
   ADR, indice ADR e `limits-and-future-work`, descrivendo contratti,
   provenienza, confini deterministici e ambito esplicitamente rinviato.

La documentazione deve descrivere:

- workflow di discovery, revisione e build;
- schema completo di `parameters.toml`;
- politiche sulle unità;
- esempi esclusivamente sintetici;
- distinzione tra dati curati e derivati;
- reason code e risoluzione dei conflitti;
- limiti della grammatica iniziale;
- funzionamento offline di Chart.js;
- procedura di rigenerazione.

Validazione focalizzata:

```bash
uv run python -m mkdocs build --strict
```

### Fase 6 — Accettazione e Chiusura

Verifiche deterministiche:

1. Costruire due volte la stessa fixture.
2. Confrontare candidati, report ed export byte per byte.
3. Verificare l'assenza di path assoluti e timestamp.

Verifiche offline:

1. Aprire il frontend con Chrome headless tramite `file://`.
2. Rilevare ogni eventuale richiesta HTTP o HTTPS.
3. Verificare console, grafico, tabella e link agli originali.

Verifiche privacy:

1. Eseguire il privacy guard.
2. Controllare fixture, log e diff.

Validazione repository:

```bash
uv run codira index
uv run codira audit --json
uv run python scripts/validate_repo.py
```

Quando è disponibile una USB sintetica montata, eseguire anche il workflow
read-only `sanikey-usb-browser-audit`.

La chiusura comprende il confronto finale con la issue #11, la verifica che le
modifiche della issue #12 siano rimaste intatte e la preparazione di commit
atomici mediante `commit-block-generator`.

## File di Test Pianificati

Nuovi:

- `tests/test_parameter_rules.py`;
- `tests/test_parameter_slices.py`.

Da aggiornare:

- `tests/test_config.py`;
- `tests/test_metadata.py`;
- `tests/test_observation_imports.py`;
- `tests/test_cli.py`;
- `tests/test_build.py`;
- `tests/test_exports.py`;
- `tests/test_database.py`;
- `tests/test_frontend.py`;
- `tests/test_usb.py`;
- `tests/test_examples_acceptance.py`.

## Confini dei Commit

1. Contratti e discovery deterministica.
2. Regole curate e modello longitudinale unificato.
3. Workflow CLI, build, export e database.
4. Frontend Chart.js offline.
5. Documentazione, esempi e criteri di accettazione.
6. Eventuali sole correzioni emerse dalla validazione finale.

## Ambito Rinviato

- valori range;
- pressione sistolica e diastolica da forma paired;
- etichetta e valore su righe diverse;
- interpretazione generale di tabelle;
- date interne multiple;
- deep link affidabile alla pagina;
- valori esclusivamente grafici;
- conversioni non affini;
- inferenza clinica, diagnostica o soglie di normalità.

## Criteri di Accettazione

- [ ] Tutti i criteri della issue #11 sono coperti da test o verifica documentata.
- [ ] Gli output sono byte-stabili.
- [ ] La pipeline non usa AI, OCR aggiuntiva o fuzzy matching.
- [ ] Le proposte non vengono promosse automaticamente a regole.
- [ ] Le slice derivano soltanto da regole abilitate.
- [ ] Ogni punto conserva valore originale, etichetta e provenienza.
- [ ] I documenti senza data sono esclusi dal grafico con reason code.
- [ ] Unità incompatibili non vengono fuse automaticamente.
- [ ] Le conversioni sono esclusivamente esplicite e versionate.
- [ ] I valori qualificati non diventano silenziosamente valori ordinari.
- [ ] Le osservazioni curate ed estratte sono distinguibili e compatibili.
- [ ] La UI ricerca per nome canonico, sigla e sinonimo.
- [ ] Tabella e grafico funzionano offline tramite `file://`.
- [ ] Ogni punto consente di aprire il documento originale.
- [ ] Chart.js è interamente locale.
- [ ] Nessun dato clinico reale appare in fixture, log o repository.
- [ ] Ogni file compilabile dall'utilizzatore ha un esempio sintetico e un
  riferimento dalla documentazione utente pertinente.
- [ ] La documentazione contributor, ADR, limiti e specifiche descrivono la
  soluzione implementata e i confini rinviati.
- [ ] `uv run python scripts/validate_repo.py` e MkDocs strict sono verdi.
