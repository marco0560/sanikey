# ADR: Visibilita' degli artefatti di consultazione

## Stato

Accettata.

## Contesto

La chiavetta e' consultata su computer non amministrati. Un file presente
nell'archivio non e' automaticamente consultabile dal browser: archivi,
documenti Office senza PDF e materiali tecnici DICOM generavano link inutili
e risultati di ricerca fuorvianti.

## Decisione

Il frontend e la ricerca contengono soltanto documenti con una rappresentazione
locale apribile. I documenti derivati da un archivio restano idonei alla
consultazione se SaniKey puo' copiarli o renderizzarli. I documenti Office
usano un PDF generato come azione primaria e conservano l'originale come
download secondario quando l'originale e' sorgente.

Gli elementi non apribili non sono cancellati: la build esporta la lista
tecnica `technical/documenti-non-apribili.html` e `.csv`, ordinata per
estensione. Gli studi DICOM sono le sole card cliniche nella sezione DICOM;
supporti, ISO e archivi rimangono dettagli tecnici dello studio.

## Conseguenze

Il medico non incontra link che richiedono software assente. L'operatore puo'
indagare ogni esclusione attraverso una lista deterministica senza esporre
materiale tecnico nella ricerca clinica. Una conversione Office non riuscita
e' un avviso di build e non un documento consultabile.
