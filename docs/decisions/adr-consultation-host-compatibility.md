# ADR: Compatibilita' del PC di consultazione

## Stato

Accettata.

## Contesto

SaniKey viene consultato da una chiavetta USB su computer non amministrati e
non prevedibili. Il computer puo' eseguire Windows di versione non nota, macOS
oppure Linux. Non e' disponibile alcuna procedura affidabile per installare
software, privilegi, runtime o servizi locali sul computer di consultazione.

Il frontend deve quindi restare utilizzabile aprendo direttamente
`index.html`, senza rete, server locale o dipendenze esterne al contenuto della
chiavetta.

## Decisione

L'export USB non richiede e non distribuisce software da installare sul
computer di consultazione. In particolare:

- non usa viewer DICOM nativi esterni, inclusi Weasis e applicazioni fornite
  nei supporti originali;
- non avvia protocolli applicativi, eseguibili, installer o servizi locali;
- non integra OHIF/Cornerstone3D finche' la loro consultazione richiede un
  server HTTP locale o un runtime da installare;
- conserva e apre soltanto viewer HTML statici gia' presenti nel supporto e
  compatibili con il frontend `file://`;
- esporta, per ogni supporto, una copia DICOM standard e un `DICOMDIR` quando
  validabile o rigenerabile, cosi' che un medico con un lettore professionale
  gia' installato possa importare il supporto selezionato;
- genera un fallback HTML statico basato su anteprime JPEG per gli studi privi
  di viewer HTML compatibile. Le anteprime non sono diagnostiche e non
  sostituiscono il contenuto DICOM originale;
- mostra come anomalie le limitazioni di copia, `DICOMDIR` e decodifica delle
  anteprime, mantenendo il supporto originale per l'eventuale consultazione su
  un sistema attrezzato separatamente.

Qualunque futuro viewer DICOM generale dovra' essere distribuito e avviato
direttamente dalla chiavetta, senza installazione e senza servizio locale, e
dovra' essere validato su Windows, macOS e Linux prima dell'adozione.

## Conseguenze

La consultazione resta portabile e non dipende dalla configurazione del PC
ospite. Il fallback consente una consultazione orientativa anche senza viewer
del CD, ma non e' un viewer diagnostico: il medico deve usare il contenuto
DICOM standard con il proprio lettore professionale per la valutazione clinica.

Weasis resta un possibile strumento di verifica fuori dal flusso SaniKey, ma
non una dipendenza dell'export. OHIF/Cornerstone3D resta una direzione da
riesaminare solo se sara' possibile usarlo senza violare questi vincoli.

## Verifica

- l'export non contiene installer, eseguibili di viewer o servizi locali;
- il frontend generato non contiene URL HTTP(S), `fetch()` o link a protocolli
  applicativi;
- i viewer HTML esportati e i link ai documenti restano relativi e risolvibili
  da `file://`;
- le anteprime JPEG non sono presentate come immagini diagnostiche e la loro
  mancata generazione non esclude le istanze DICOM dal supporto professionale;
- la procedura di verifica reale prova l'apertura della chiavetta su Windows,
  macOS e Linux quando disponibili.
