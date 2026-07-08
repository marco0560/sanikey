# Ricerca Federata e Dashboard Clinica

## Stato

Accettata.

## Contesto

SaniKey acquisisce documenti e metadati curati: problemi clinici, farmaci,
terapie, procedure, osservazioni, timeline e studi DICOM. Un dato acquisito ma
non consultabile dal frontend non è utile durante la visita, perché il medico
non deve usare SQLite o file JSON grezzi.

La ricerca documentale e la ricerca avanzata nel testo estratto esistevano già,
ma la UI mostrava quasi solo documenti. I metadati curati erano indicizzati in
`search.json` senza una resa clinica dedicata.

## Decisione

La UI di consultazione deve essere federata:

- la ricerca rapida interroga documenti e metadati clinici curati;
- la ricerca avanzata interroga sia contenuti OCR/testo sia metadati clinici;
- i risultati sono raggruppati per sezione e preceduti da link con conteggi;
- il riepilogo diventa una dashboard clinica sempre consultabile;
- gli studi DICOM sono mostrati come schede sintetiche, non come elenco di ogni
  istanza.

Il payload `data.js` contiene un blocco `clinical` con problemi, farmaci,
terapie, procedure, osservazioni e studi DICOM sintetici. Le terapie vengono
arricchite con il farmaco collegato, in modo che nome commerciale, principio
attivo, schedula, dosaggio e istruzioni siano leggibili e ricercabili.

## Conseguenze

- Ogni dato clinico esportato ha una rappresentazione UI.
- Non vengono aggiunti campi di ricerca separati per ambito: le due ricerche
  esistenti restano le superfici operative.
- Le sezioni in testa ai risultati riducono il rischio che il medico perda
  risposte importanti sotto una lista lunga.
- Il frontend resta statico e compatibile con `file://`.
