# ADR: Immagini sorgente senza OCR diretto

## Stato

Accettata.

## Contesto

I file `.jpg`, `.jpeg` e `.png` presenti tra i documenti sorgente possono
essere fotografie cliniche, scansioni, allegati tecnici o immagini diagnostiche
non DICOM. Il riconoscimento OCR diretto con Tesseract produce spesso testo
rumoroso, aumenta i tempi di build e introduce una dipendenza di sistema che
non serve per la consultazione primaria dell'immagine.

I PDF scansionati sono un caso diverso: rappresentano referti o documenti
testuali impaginati e restano gestiti dalla pipeline PDF con OCRmyPDF quando il
testo digitale non e' sufficiente.

## Decisione

Le immagini sorgente `.jpg`, `.jpeg` e `.png` sono documenti consultabili, ma
non vengono inviate a OCR diretto tramite Tesseract. La build le cataloga,
conserva il link al file originale esportato e le rende disponibili nella
ricerca rapida tramite metadati documentali, ma non produce testo estratto per
la ricerca avanzata.

Il preflight non deve richiedere Tesseract per queste immagini e non deve
emettere warning per provider OCR immagine mancante.

## Conseguenze

- La build non avvia processi Tesseract per immagini sorgente isolate.
- Le immagini restano nel catalogo e nella consultazione come documenti
  apribili.
- La ricerca avanzata non cerca testo interno a `.jpg`, `.jpeg` o `.png`.
- L'OCR dei PDF scansionati resta invariato e continua a passare da OCRmyPDF.
