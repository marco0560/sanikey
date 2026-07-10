# ADR: Hardening consultazione USB

## Stato

Accettata.

## Contesto

La validazione reale multi-paziente ha mostrato quattro problemi operativi:

- la ricerca avanzata poteva essere presente nel DOM ma non selezionabile su
  desktop;
- la timeline e i risultati occupavano la stessa esperienza di consultazione;
- i file DICOM interni apparivano come documenti ordinari pur non essendo
  consultabili direttamente;
- l'export USB doveva impedire regressioni verso link assoluti locali e doveva
  controllare meglio il target fisico.

## Decisione

Il frontend mantiene in alto la maschera di ricerca e i link alle sezioni. La
ricerca base e avanzata sono sempre selezionabili e i risultati sono raggruppati
per ambito clinico.

I singoli file DICOM sono record tecnici: restano disponibili per database,
catalogo e audit, ma la UI mostra studi aggregati con un link al supporto
esportato quando il supporto e' un documento sorgente.

La configurazione supporta pattern di esclusione globali e per paziente.
SaniKey li applica prima possibile nella scansione e nello staging dei
container.

L'export fisico controlla path relativi, link rotti, spazio disponibile e, sui
target fisici configurati, UUID filesystem e fstype exFAT. La copia preferisce
`rsync` quando disponibile e torna alla copia Python solo quando `rsync` manca.

## Conseguenze

La UI diventa piu' utile per un medico su schermi larghi e stretti, riducendo il
rumore dei supporti DICOM. Gli export USB sono piu' lenti da validare ma
falliscono prima e con messaggi piu' utili quando il target e' sbagliato.

La formattazione della chiavetta resta una procedura manuale documentata: non
viene automatizzata dalla CLI per evitare operazioni distruttive implicite.
