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

Il frontend di consultazione resta statico e offline. Usa HTML, CSS,
JavaScript generati localmente e asset Material Web vendorizzati nel
repository. L'export non dipende da CDN, backend o build frontend eseguita sulla
chiavetta.

La UI predefinita e' responsiva:

- su schermi larghi usa un header a due aree, con identita' paziente e controlli
  a sinistra e ricerca a destra;
- su schermi stretti adatta header, ricerca e controlli alla larghezza
  disponibile;
- la ricerca base e quella avanzata usano lo stesso box e si alternano dal
  frame superiore, con accento visivo diverso e aiuto accanto al rispettivo
  bottone;
- gli aiuti della ricerca base e avanzata sono separati e si aprono in modal
  locali richiudibili;
- durante una ricerca l'utente vede subito i risultati, senza dover scorrere
  oltre la timeline;
- la sezione clinica si chiama `Sintesi Clinica` e sposta i conteggi tecnici in
  fondo;
- le terapie hanno anche un bottone diretto di primo livello quando presenti;
- gli studi DICOM aggregati hanno una sezione autonoma quando sono apribili con
  viewer HTML, separata dai documenti ordinari e dai supporti tecnici non
  visualizzabili;
- su schermi larghi la UI puo' mostrare due sezioni affiancate, con azioni
  esplicite per aprire una sezione a sinistra o a destra;
- la timeline e' mostrata per default in ordine cronologico inverso;
- i link ai documenti originali nella chiavetta sono relativi al frontend
  esportato e non puntano mai ai percorsi sorgente del computer di build.

La radice USB contiene `index.html`: con un solo paziente apre direttamente il
frontend del paziente; con piu' pazienti mostra una lista di scelta.

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

La UI rimane consultabile da `file://`, ma adotta componenti locali piu'
strutturati. La configurazione permette di adattare l'export senza rendere
fragile il rendering. La scelta richiede test espliciti sugli asset locali e sui
link relativi.

## Verifica

I test devono coprire:

- parsing e validazione della configurazione UI;
- precedenza `[[person]].ui` su `[global.ui]`;
- assenza di path assoluti nei link documentali esportati;
- ordine timeline configurato;
- presenza dei controlli header, ricerca, modal e sintesi nel frontend generato;
- presenza dell'entrypoint root USB;
- consultazione manuale da directory locale e da chiavetta fisica.
