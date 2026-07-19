# Trattamento DICOM

## Sintesi

Il comportamento corrente è vicino al CD originale solo quando il supporto
contiene un viewer HTML apribile dal browser. Non equivale all'avvio
dell'autorun o del viewer nativo del CD.

## Archivi e immagini disco

- Gli archivi sorgente come `.zip`, `.7z`, `.rar`, `.tar.xz`, `.iso` e `.img`
  sono rilevati come documenti contenitore o supporto.
- `scan-documents`, `process-dicom` e `build-patient` espandono per default i
  contenitori supportati in `local_build/staging/containers/`.
- `process-dicom --no-stage-containers` evita l'estrazione e cataloga soltanto
  i supporti sorgente e le espansioni gia' esistenti.
- Se un archivio contiene un'immagine disco annidata, ad esempio ZIP -> ISO ->
  albero DICOM, SaniKey espande ricorsivamente anche l'immagine annidata.
- L'espansione registra tutti i membri estratti nel manifesto per l'audit.
- Soltanto i documenti derivati clinicamente utili entrano nella pipeline dei
  documenti; i percorsi tecnici o di supporto possono essere filtrati con
  `exclude_patterns`.
- Le istanze DICOM sono catalogate come record e studi DICOM, non mostrate come
  migliaia di file ordinari.

## Studi DICOM

- SaniKey cerca file DICOM e `DICOMDIR` nel supporto espanso.
- Quando possibile raggruppa le istanze per `StudyInstanceUID`.
- Se `DICOMDIR` contiene record di studio utilizzabili, usa anche quelli.
- Il frontend mostra schede aggregate degli studi DICOM con metadati quali
  data, UID e numero di istanze.
- Se esiste un viewer HTML riconosciuto, in particolare nei percorsi IHE PDI
  come `IHE_PDI/PAGES/STUDIES/*.HTM`, SaniKey copia il sottoalbero necessario
  sulla chiavetta in:
  `patients/<id>/dicom-viewers/<study_id>/...`
- Il frontend lo espone con l'azione `Apri studio DICOM`.

## Export USB

- Il supporto sorgente originale, ad esempio `Referto TAC.zip`, puo' essere
  ancora copiato in `patients/<id>/documents/` salvo esclusione dai pattern di
  ingestione, ma il pannello clinico `Studi DICOM` non presenta il download
  dell'archivio come flusso primario.
- I file esclusi da `exclude_patterns` non sono copiati in
  `patients/<id>/documents/`.
- I viewer HTML DICOM sono rilevati soltanto nei path non esclusi dai pattern
  configurati di ingestione e sono copiati separatamente mediante il manifesto
  dei viewer.
- L'interfaccia mostra solo studi clinici; il supporto originale e i dettagli
  tecnici restano richiudibili nella scheda dello studio e non compaiono come
  documenti o risultati di ricerca ordinari.
- Quando esiste `viewer_href`, l'azione primaria apre il viewer nativo oppure
  il visualizzatore integrato non diagnostico. Il link `DICOMDIR per viewer
  professionale` resta disponibile ogni volta che il media e' stato creato.
- Uno studio e' anomalo solo senza viewer, anteprima e `DICOMDIR`.
- Per ogni supporto espanso con istanze leggibili viene creato un media DICOM
  condiviso con `DICOMDIR`; non viene duplicato una volta per ciascuno studio.
- Quando le istanze di uno studio sono aggregate dai membri estratti di un
  supporto, lo studio clinico conserva il collegamento al supporto: usa le sue
  istanze per l'anteprima e riceve il link al relativo `DICOMDIR`.
- Il media e' copiato in `patients/<id>/dicom-media/` e puo' essere aperto o
  importato da un lettore DICOM professionale gia' installato sul PC.
- Quando non esiste un viewer HTML nativo, SaniKey genera una pagina statica
  con anteprime JPEG in `patients/<id>/dicom-previews/`. Le anteprime sono
  esplicitamente non diagnostiche: servono a identificare lo studio, non a
  svolgere una valutazione clinica.

## Differenze rispetto all'inserimento del CD

- SaniKey non avvia dal browser autorun nativi del CD o viewer `.exe`.
- Le applicazioni viewer native Windows, macOS o Linux presenti nel CD non sono
  in generale eseguibili in modo affidabile o sicuro da un frontend statico
  `file://`.
- SaniKey non emula l'intero ambiente originale del CD.
- SaniKey offre un flusso vicino al CD soltanto quando il CD include un viewer
  HTML statico direttamente apribile dal browser.
- Se il CD contiene soltanto un viewer eseguibile, SaniKey conserva e cataloga
  il supporto ma non richiede né distribuisce l'applicazione sul PC di
  consultazione. Lo studio resta un'anomalia finché non esiste un viewer HTML
  statico compatibile.
- Se il viewer o un suo entrypoint corrisponde a `exclude_patterns`, non viene
  rilevato né copiato attraverso `dicom-viewers`. Per recuperarlo occorre un
  `include_patterns` esplicito in configurazione.

## Flusso corrente

Il flusso previsto per il medico e':

1. Open USB `index.html`.
2. Search or open `Studi DICOM` when the section is available.
3. Click `Apri studio DICOM`.
4. Se è stato riconosciuto un viewer HTML, si apre direttamente in una nuova
   scheda del browser.
5. Se non e' stato riconosciuto, aprire l'anteprima non diagnostica quando
   disponibile.
6. Per la valutazione clinica, importare il collegamento `DICOMDIR per viewer
   professionale` nel lettore DICOM gia' disponibile sul PC.
7. Se non sono disponibili ne' anteprima ne' `DICOMDIR`, lo studio resta
   visibile come anomalia da verificare e il supporto originale resta
   disponibile per verifica tecnica.
