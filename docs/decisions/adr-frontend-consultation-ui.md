# ADR: Frontend di Consultazione Offline

## Stato

Accettata.

## Contesto

Il frontend SaniKey viene aperto direttamente dalla chiavetta USB, spesso con
browser e PC non noti in anticipo. Deve quindi funzionare senza server locale,
senza rete e senza richieste `fetch()` verso file locali. L'archivio puo'
contenere migliaia di eventi timeline e documenti: una pagina lineare rende la
ricerca poco usabile perche' gli esiti restano sotto una timeline lunga.

## Decisione

Il frontend di consultazione resta statico e offline. Usa HTML, CSS e
JavaScript generati localmente, con un piccolo helper JavaScript vendorizzato
solo se riduce la complessita' senza introdurre build frontend o rete.

La UI predefinita e' responsiva:

- su schermi larghi usa un layout a due aree, con ricerca e risultati in primo
  piano e timeline/riepilogo in un pannello secondario;
- su schermi stretti usa tab per `documenti`, `timeline` e `riepilogo`;
- durante una ricerca l'utente vede subito i risultati, senza dover scorrere
  oltre la timeline;
- la timeline e' mostrata per default in ordine cronologico inverso;
- i link ai documenti originali nella chiavetta sono relativi al frontend
  esportato e non puntano mai ai percorsi sorgente del computer di build.

La personalizzazione e' configurabile in `config/accounts.toml` con una tabella
`[global.ui]` e override opzionali in `[[person]].ui`. I valori sono chiusi e
validati, non CSS libero:

- `accent_color`;
- `density`;
- `default_tab`;
- `timeline_order`;
- `document_link_mode`;
- `subtitle`.

## Conseguenze

La UI rimane leggera e consultabile da `file://`, ma diventa piu' usabile sui
monitor larghi e sui portatili piccoli. La configurazione permette di adattare
l'export senza rendere fragile il rendering. La scelta esclude per ora temi CSS
arbitrari e framework frontend.

## Verifica

I test devono coprire:

- parsing e validazione della configurazione UI;
- precedenza `[[person]].ui` su `[global.ui]`;
- assenza di path assoluti nei link documentali esportati;
- ordine timeline configurato;
- presenza dei controlli di layout/tab nel frontend generato;
- consultazione manuale da directory locale e da chiavetta fisica.
