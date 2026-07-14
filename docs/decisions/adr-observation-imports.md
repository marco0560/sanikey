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
- mappa esplicitamente le colonne sorgente tramite `[source.columns]`;
- accetta file `.csv`, `.xlsx`, `.xlsm`, `.xlsb`, `.xls` e `.ods`;
- usa `python-calamine` per i fogli di calcolo e il parser CSV standard per
  CSV UTF-8.

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
