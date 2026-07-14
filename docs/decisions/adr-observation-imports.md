# Import osservazioni longitudinali

## Stato

Accettata.

## Contesto

Peso, pressione, glicemia, INR e altre misurazioni possono arrivare da piu'
file tabellari, prodotti in periodi diversi e con intestazioni diverse. La build
non deve indovinare autoritativamente a quale categoria clinica appartiene un
file: una classificazione sbagliata produrrebbe dati sanitari fuorvianti.

## Decisione

SaniKey importa osservazioni longitudinali solo da un manifesto esplicito
`metadata/observation_imports.toml`.

Il manifesto:

- dichiara le serie con `[[series]]`;
- associa ogni file sorgente con `[[source]]`;
- mappa esplicitamente le colonne sorgente tramite `[source.columns]` oppure
  tramite uno o piu' `[[source.extract]]`;
- accetta file `.csv`, `.xlsx`, `.xlsm`, `.xlsb`, `.xls` e `.ods`;
- usa `python-calamine` per i fogli di calcolo e il parser CSV standard per
  CSV UTF-8.

Per accogliere fogli reali non normalizzati, il manifesto puo' dichiarare:

- `header_row`, `header_rows` e `data_start_row` per intestazioni non in prima
  riga o intestazioni su piu' righe;
- `fill_down` per celle vuote che ereditano il valore della riga precedente;
- `note_columns`, `static_note` e `note_join` per comporre note tracciabili;
- `date_policy` per date incomplete, normalizzate a una data ISO con nota;
- `skip_invalid_dates` per saltare righe descrittive dentro tabelle sporche,
  mantenendo il fallimento come comportamento predefinito;
- `compound_value` per celle come `113/65 54` lette con regex nominata;
- `layout = "repeating_matrix"` per tabelle in cui le date sono in intestazione
  e le misure nelle righe successive.

Le osservazioni ricavate da PDF clinici restano metadati curati manualmente:
`import-observations` e' una pipeline tabellare, non un estrattore clinico da
testo libero.

Gli artefatti normalizzati sono scritti in `metadata/observations/`:

- `series.toml` contiene le serie normalizzate;
- un file TOML per serie contiene i `[[point]]`;
- `import_state.toml` registra hash del manifesto e delle sorgenti.

`build-patient` e `build-all` falliscono se il manifesto o le sorgenti sono
stati modificati dopo l'ultimo `sanikey import-observations`.

## Conseguenze

La prima iterazione della UI mostra tabelle cronologiche per `Peso`,
`Pressione`, `Glicemia`, `INR` e `Parametri`.

Resta un gap documentato: la vista ricca con riepiloghi, trend, filtri e
anomalie di import sara' una fase successiva.
