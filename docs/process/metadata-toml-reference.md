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
| `summary` | stringa | no | Testo libero mostrato nel riepilogo del frontend |

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

Il campo `summary` e' oggi trattato come testo semplice. E' possibile usare una
struttura markdown-like per leggibilita' nel file sorgente, ma SaniKey non
converte Markdown in HTML.

Blast radius di un vero rendering Markdown:

- frontend: servirebbe un renderer Markdown o una conversione build-time;
- sicurezza: l'HTML generato dovrebbe essere sanificato per evitare injection;
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
