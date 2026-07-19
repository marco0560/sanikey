# Riferimento metadati TOML

Questa pagina descrive i file TOML supportati in `metadata_directory`.
Ogni `metadata_directory` appartiene a un solo paziente configurato in
`config/accounts.toml`; per questo i file di metadati non ripetono l'id
paziente.

I campi non indicati come obbligatori sono opzionali. Le date nei TOML sono
memorizzate in formato ISO `YYYY-MM-DD`; il frontend le presenta all'utente in
formato italiano `gg/mm/aaaa`.

## `clinical_summary.toml`

Contiene una sintesi clinica libera, orientata alla consultazione rapida.
Non e' una cartella clinica completa. Puo' includere una sezione di anamnesi,
ma la sintesi clinica e' il riepilogo operativo che un medico deve capire subito
aprendo l'archivio.

Campi:

| Campo | Tipo | Obbligatorio | Uso |
| --- | --- | --- | --- |
| `summary` | stringa Markdown | no | Testo libero mostrato nel riepilogo del frontend |

Esempio:

```toml
summary = """
# Sintesi clinica

## Problemi attivi rilevanti
- Ipertensione arteriosa.

## Terapie croniche principali
- Vedere therapies.toml per il dettaglio strutturato.
"""
```

### Markdown

Il campo `summary` supporta Markdown CommonMark e viene convertito in HTML
durante la build. L'HTML grezzo inserito nel Markdown viene escapato: usare
Markdown strutturale (`#`, `##`, liste, enfasi, link) invece di markup HTML
manuale.
- offline: eventuali librerie devono essere vendorizzate o eliminate durante la
  build, senza dipendenze cloud;
- test: servirebbero test per rendering, escaping, link, liste, titoli e
  contenuti malevoli;
- compatibilita': il testo gia' scritto come plain text deve continuare a
  essere leggibile.

Per lo slice attuale, la scelta corretta e' mantenerlo plain text.

## `document_tags.toml`

Associa tag liberi ai documenti originali.

I tag sono stringhe libere, non provengono da un vocabolario chiuso. Servono per:

- comparire in `documents.json`;
- contribuire al testo di `search.json`;
- apparire nel frontend accanto al documento;
- migliorare il filtro client-side del frontend.

La chiave preferita e' il percorso del documento relativo a `source_documents`,
con separatore `/`. Per casi semplici e' accettato anche il solo nome file, ma
il percorso relativo evita ambiguita' quando due directory contengono file con lo
stesso nome.

Esempio:

```toml
[tags]
"laboratory/20260102 Referto.txt" = ["laboratorio", "emocromo"]
"imaging/20260210 TAC.pdf" = ["radiologia", "tac"]
```

Non serve includere l'id paziente nella chiave: il file `document_tags.toml` si
trova gia' nella directory metadati del singolo paziente.

## `problems.toml`

Contiene problemi clinici curati.

Campi:

| Campo | Tipo | Obbligatorio | Uso |
| --- | --- | --- | --- |
| `id` | stringa | si | Identificativo stabile del problema |
| `title` | stringa | si | Nome leggibile del problema |
| `status` | stringa | no | Stato libero, default `unknown` |

Esempio:

```toml
[[problem]]
id = "ipertensione"
title = "Ipertensione arteriosa"
status = "active"
```

## `medications.toml`

Contiene l'anagrafica dei farmaci. Non rappresenta da sola una terapia: le
assunzioni stanno in `therapies.toml`.

Campi:

| Campo | Tipo | Obbligatorio | Uso |
| --- | --- | --- | --- |
| `id` | stringa | si | Identificativo stabile del farmaco |
| `name` | stringa | si | Nome commerciale o denominazione visibile |
| `active_ingredient` | stringa | no | Principio attivo |
| `form` | stringa | no | Forma, ad esempio `compresse`, `bustine`, `gocce` |
| `strength_per_unit` | stringa | no | Quantita' per unita', ad esempio `100 mg` |

Esempio:

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

## `medication_leaflets.toml`

Questo file e' generato da `resolve-medication-leaflets`; non compilare a mano
gli identificativi AIFA. Associa un farmaco già presente in `medications.toml`
alla sua fonte AIFA, dopo conferma automatica univoca o scelta dell'operatore
nei soli casi ambigui. `source_fingerprint` è gestito da SaniKey e consente di
riconoscere modifiche ai dati curati del farmaco.

```toml
[[leaflet]]
medication_id = "atenololo"
codice_sis = "123456"
aic6 = "012345"
source_fingerprint = "..."
```

`downloaded_at`, se presente, descrive una precedente copia locale. La data
mostrata nell'export proviene invece dal manifesto generato durante la build e
corrisponde all'ultimo download FI riuscito.

Per integratori o altri prodotti senza foglio illustrativo AIFA applicabile, il
comando può registrare una scelta esplicita e persistente. Non deve coesistere
con un blocco `[[leaflet]]` dello stesso `medication_id`:

```toml
[[unavailable]]
medication_id = "integratore"
reason = "non_aifa"
```

Creare questi blocchi tramite `resolve-medication-leaflets --mark-non-aifa` o
con il tasto `n` nella schermata di revisione; non inserire codici AIFA a mano.

## `therapies.toml`

Contiene episodi o terapie in corso che fanno riferimento a `medications.toml`.

Campi:

| Campo | Tipo | Obbligatorio | Uso |
| --- | --- | --- | --- |
| `id` | stringa | no | Identificativo stabile della terapia; se omesso viene generato |
| `medication_id` | stringa | si | Farmaco collegato in `medications.toml` |
| `start_date` | stringa ISO | no | Data inizio nota |
| `end_date` | stringa ISO | no | Data fine nota |
| `dosage` | stringa | no | Dose assunta, ad esempio `1 compressa` |
| `role` | stringa | no | Ruolo clinico o indicazione, ad esempio `antipertensivo` |
| `schedule` | lista di stringhe | no | Orari o fasce di assunzione |
| `instructions` | stringa | no | Indicazioni libere |

`medication_id` deve riferirsi a un `id` presente in `medications.toml`.
Gli `id` espliciti, quando presenti, devono essere univoci. Omettere `id` e'
accettabile: SaniKey genera un identificativo stabile basato su `medication_id`
e posizione della terapia nel file. Il campo `role` serve a descrivere il
target clinico della terapia e non deve essere usato come identificativo unico:
piu' terapie possono avere lo stesso ruolo, per esempio piu' antipertensivi.

Se la data di inizio e' sconosciuta, omettere `start_date`. Se la terapia e'
in corso o permanente, omettere `end_date`. Non usare date fittizie.

Esempio:

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

Valori tipici per `schedule`: `risveglio`, `mattino`, `pranzo`, `cena`,
`sera`, `notte`, oppure orari come `08:00`.

## `procedures.toml`

Contiene procedure o interventi clinici curati.

Campi:

| Campo | Tipo | Obbligatorio | Uso |
| --- | --- | --- | --- |
| `id` | stringa | si | Identificativo stabile |
| `title` | stringa | si | Titolo leggibile |
| `date` | stringa ISO | no | Data della procedura |
| `status` | stringa | no | Stato libero, default `unknown` |

Esempio:

```toml
[[procedure]]
id = "angioplastica-2021"
title = "Angioplastica coronarica"
date = "2021-04-12"
status = "completed"
```

## `observations.toml`

Contiene osservazioni cliniche puntuali curate.

Campi:

| Campo | Tipo | Obbligatorio | Uso |
| --- | --- | --- | --- |
| `id` | stringa | si | Identificativo stabile |
| `kind` | stringa | si | Tipo di osservazione |
| `value` | stringa | si | Valore leggibile |
| `date` | stringa ISO | no | Data dell'osservazione |

Esempio:

```toml
[[observation]]
id = "peso-2026-01"
kind = "peso"
value = "70 kg"
date = "2026-01-03"
```

## `observation_imports.toml`

Contiene il protocollo di import per osservazioni longitudinali da CSV UTF-8 e
fogli di calcolo `.xlsx`, `.xlsm`, `.xlsb`, `.xls`, `.ods`.

Esempio:

```toml
[[series]]
id = "peso"
name = "Peso"
value_type = "numeric"
unit = "kg"
warn_duplicate_same_day = false

[[source]]
path = "_Parametri/peso-2025.xlsx"
series_id = "peso"
sheet = "Peso"
source_reference = "peso-2025.xlsx"

[source.columns]
date = "Data"
numeric_value = "Peso"
note = "Note"
```

Per la pressione:

```toml
[[series]]
id = "pressione"
name = "Pressione"
value_type = "blood_pressure"
unit = "mmHg"
warn_duplicate_same_day = false

[[source]]
path = "_Parametri/diario-pressorio.csv"
series_id = "pressione"

[source.columns]
date = "Data"
systolic = "Sistolica"
diastolic = "Diastolica"
pulse = "Frequenza"
```

I path relativi sono risolti rispetto alla directory documenti sorgente del
paziente. Dopo ogni modifica al manifesto o ai file sorgente eseguire:

```bash
uv run sanikey import-observations PATIENT
```

La build fallisce se gli artefatti in `metadata/observations/` sono assenti o
stale rispetto al manifesto.

Opzioni supportate per sorgenti reali non normalizzate:

| Campo | Uso |
| --- | --- |
| `header_row` | riga 1-based che contiene l'intestazione |
| `header_rows` | righe 1-based da combinare per intestazioni su piu' righe |
| `data_start_row` | prima riga dati 1-based, se non e' subito dopo l'header |
| `fill_down` | campi logici che ereditano il valore non vuoto precedente |
| `[[source.extract]]` | estrazioni multiple dalla stessa riga o sorgente |
| `note_columns` | colonne da concatenare in `note` |
| `static_note` | nota fissa da aggiungere a ogni punto |
| `date_policy` | `exact`, `year_start` o `period_start` |
| `skip_invalid_dates` | salta righe non-dato con data non valida |
| `compound_value` | colonna e regex con gruppi nominati per valori composti |
| `layout = "repeating_matrix"` | layout con date in intestazione e misure in righe ripetute |

Esempio con due serie dalla stessa riga e anno approssimato:

```toml
[[source]]
path = "_Parametri/peso-storico.xlsx"
sheet = "Peso"
header_row = 3

[[source.extract]]
series_id = "peso"
date_policy = "year_start"
note_columns = ["Evento", "Farmaci"]

[source.extract.columns]
date = "Anno"
numeric_value = "Peso"

[[source.extract]]
series_id = "bmi"
date_policy = "year_start"
static_note = "BMI da foglio peso"

[source.extract.columns]
date = "Anno"
numeric_value = "BMI"
```

Esempio con pressione in una cella composta:

```toml
[[source]]
path = "_Parametri/pressione.csv"
series_id = "pressione"

[source.columns]
date = "Data"

[source.compound_value]
column = "Misura"
pattern = '^(?P<systolic>\d+)/(?P<diastolic>\d+)\s+(?P<pulse>\d+)$'
```

Esempio per layout a matrice ripetuta:

```toml
[[source]]
path = "Cardiologo/20080900 Pressione.xls"
layout = "repeating_matrix"

[source.matrix]
year = 2008
start_month = 9
block_height = 3
date_column_start = 2
value_rows = ["mattino", "pomeriggio"]
date_column = "Data"
value_column = "Misura"
label_column = "Fascia"

[[source.extract]]
series_id = "pressione"
note_columns = ["Fascia"]

[source.extract.columns]
date = "Data"

[source.extract.compound_value]
column = "Misura"
pattern = '^(?P<systolic>\d+)/(?P<diastolic>\d+)\s+(?P<pulse>\d+)$'
```

## `timeline_events.toml`

Contiene eventi manuali da mostrare nella timeline.

Campi:

| Campo | Tipo | Obbligatorio | Uso |
| --- | --- | --- | --- |
| `id` | stringa | si | Identificativo stabile |
| `title` | stringa | si | Titolo leggibile |
| `start_date` | stringa ISO | no | Data inizio |
| `end_date` | stringa ISO | no | Data fine intervallo |
| `source` | stringa | no | Fonte, default `manual` |
| `links` | lista di stringhe | no | Id documenti o entita' correlate |

Esempio:

```toml
[[event]]
id = "ricovero-2021"
title = "Ricovero cardiologico"
start_date = "2021-04-10"
end_date = "2021-04-15"
source = "manual"
links = ["angioplastica-2021"]
```
