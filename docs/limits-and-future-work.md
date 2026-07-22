# Limiti e Sviluppi Futuri

Questa pagina separa ciò che è operativo nella versione corrente da idee,
prototipi e limiti da conoscere prima di una consegna. Il percorso consigliato
è quello di [Prima chiavetta USB](first-usb-key.md).

## Operativo nella versione corrente

- archivio multi-paziente locale, scansione, ricerca e consultazione offline;
- export USB statico con controllo di integrità e di link relativi;
- documenti supportati, conversioni consultabili e fogli illustrativi AIFA
  confermati e copiati localmente;
- catalogazione di studi DICOM, viewer HTML incluso quando disponibile e
  fallback JPEG non diagnostico quando le istanze sono leggibili;
- import esplicito di osservazioni da fogli e CSV configurati.

## Richiede cura o verifica manuale

- la pipeline di ingestione è supportata su Linux; la consultazione USB è
  statica, ma va provata sul computer destinato al medico;
- un viewer DICOM nativo fornito sul CD non può essere avviato dal browser.
  Per studi senza viewer HTML, usare il DICOMDIR/media esportato con un viewer
  professionale già installato; le anteprime JPEG non sono diagnostiche;
- AIFA e Internet servono per confermare o aggiornare FI/RCP prima della
  build. La chiavetta contiene poi le copie locali verificate;
- i documenti non supportati o corrotti restano originali da conservare, ma
  possono non essere ricercabili o consultabili direttamente nel browser;
- dati clinici, scelta delle fonti e metadati restano responsabilità del
  curatore: SaniKey non formula diagnosi né sostituisce la cartella clinica.

## Non usare nel flusso di consegna

`generate-proposals` e `review-proposal` sono uno scaffold sperimentale:
producono e cambiano lo stato di segnaposto, non analizzano documenti e non
aggiornano metadati clinici. Non sono una funzione di assistenza clinica e non
vanno usati per preparare una chiavetta destinata alla consultazione.

FHIR e HL7, integrazioni online e un viewer DICOM generale sono direzioni
future documentate nelle specifiche e nelle ADR; non sono promesse di questa
release.

## Prima di affidarsi a una nuova configurazione

Eseguire sempre `validate-config`, `scan-documents --preflight`, la build,
`validate-usb` e una prova nel browser sul supporto prodotto. Gli errori o gli
avvisi devono essere compresi e risolti, oppure valutati dal curatore, prima
della consegna.
