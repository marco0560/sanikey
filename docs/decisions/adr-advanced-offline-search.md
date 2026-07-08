# Ricerca Avanzata Offline

## Stato

Accettata.

## Contesto

La chiavetta SaniKey deve essere consultabile da un medico senza server locale,
senza installazioni e senza accesso di rete. La ricerca rapida su `data.js`
funziona direttamente da `file://`, ma cerca solo metadati leggeri: titolo,
data, categoria, percorso, tag e tipo file.

Il testo estratto da PDF, OCR, Office e file testuali esiste già nella build e
nel database SQLite, ma non è usabile da un medico se l'unica alternativa è una
query SQL. Inoltre `fetch()` su file locali non è affidabile nei browser.

## Decisione

SaniKey espone due modalità:

- `Documenti`: ricerca rapida, leggera, sempre disponibile;
- `Ricerca avanzata`: ricerca nel contenuto estratto/OCR, caricata su richiesta.

La ricerca avanzata usa un asset separato `web/content-search.js` che assegna il
payload a `window.SANIKEY_CONTENT_SEARCH`. Il frontend lo carica con un tag
`script`, non con `fetch()`, per restare compatibile con `file://`.

La sintassi avanzata supporta parole, frasi tra virgolette, `AND`, `OR`, `NOT`,
parentesi e AND implicito fra termini adiacenti. La ricerca è case-insensitive e
accent-insensitive. Sinonimi e normalizzazioni possono essere definiti in un TOML
configurato in `[global.search]` o in override per paziente.

L'indice avanzato può duplicare testo sensibile già presente nei documenti
originali esportati sulla stessa chiavetta. Questa duplicazione è accettata
perché rende possibile una consultazione clinica reale senza strumenti tecnici.
La build segnala solo se l'asset supera una soglia configurabile.

## Conseguenze

- L'apertura iniziale resta leggera perché `data.js` non contiene tutto il testo
  OCR.
- La ricerca nel contenuto è disponibile al medico dal browser, senza SQL.
- I link `Apri originale` restano relativi alla struttura USB.
- Il dizionario di ricerca è dato curato e validato, non logica cablata nel
  frontend.
- `content-search.js` diventa un artefatto generato da controllare nella
  procedura end-to-end.
