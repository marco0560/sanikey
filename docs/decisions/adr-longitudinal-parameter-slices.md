# Slice longitudinali dei parametri

## Stato

Accettata.

## Decisione

SaniKey ricava candidati dal testo già estratto con una grammatica riga per
riga deterministica. Le proposte restano report di revisione: soltanto una
regola abilitata in `parameters.toml`, con termine presente nel dizionario,
può produrre un punto longitudinale.

Ogni punto derivato conserva documento, digest del testo, riga, offset,
etichetta, valore originale, unità, regola e reason code. Le conversioni sono
solo esplicite e versionate; date assenti, unità incompatibili e corrispondenze
ambigue non sono risolte automaticamente.

Quando una serie importata e un parametro derivato hanno lo stesso nome
normalizzato, confluiscono nella stessa serie se rappresentano valori scalari
compatibili (`numeric`, `scalar` o `qualified-scalar`) e l'unità coincide dopo
normalizzazione Unicode, spazi e maiuscole/minuscole. Le conversioni di scala
restano esplicite nella regola del parametro: non vengono inferite dal nome
dell'unità. Punti con la stessa data sono tutti mantenuti con la rispettiva
provenienza.

La build usa l'estrazione già eseguita; i comandi standalone richiedono una
cache valida e non avviano OCR o altri estrattori. SQLite, JSON e JavaScript
sono artefatti rigenerabili. Il frontend statico usa Chart.js locale e mantiene
la tabella come rappresentazione primaria.

## Conseguenze

La funzionalità è riproducibile e verificabile offline, ma non interpreta
tabelle generiche, etichette su righe diverse, range, valori paired o date
interne ai documenti. Non offre inferenze cliniche o diagnosi.
