# ADR: Pattern di ingestione espliciti

## Stato

Accettata.

## Contesto

SaniKey filtra i documenti sorgente e i membri estratti dai container prima di
costruire inventari, database, OCR e export USB. Alcuni path tecnici dei viewer
DICOM erano esclusi da una lista hardcoded nel codice, mentre i pattern utente
erano configurabili solo come esclusioni.

Questa separazione rendeva difficile spiegare perche' un membro fosse stato
filtrato e impediva di recuperare in modo dichiarativo un file specifico dentro
una directory esclusa.

## Decisione

La configurazione di ingestione e' l'unica policy per i filtri tecnici non
derivati dal tipo file:

- `exclude_patterns` esclude path sorgente e membri interni dei container;
- `include_patterns` recupera path che corrispondono anche a un'esclusione;
- i pattern globali e quelli del paziente si sommano;
- `include_patterns` ha precedenza su `exclude_patterns`;
- i path tecnici dei viewer devono essere dichiarati nel TOML, non nel codice.

La validazione della configurazione rifiuta anche i campi sconosciuti sotto
`[[person]]`, cosi' un pattern scritto nella sezione sbagliata non viene
ignorato silenziosamente.

## Conseguenze

Le esclusioni tecniche sono visibili, versionabili e verificabili dal comando
`validate-config`. I membri esclusi restano nel manifest di staging, ma non
entrano nella pipeline documentale ordinaria. Quando serve mantenere un file
dentro una directory esclusa, l'operatore aggiunge un `include_patterns`
specifico invece di modificare il codice.
