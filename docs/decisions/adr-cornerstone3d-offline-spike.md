# ADR: Esito dello spike Cornerstone3D offline

## Stato

Respinta.

## Contesto

Dopo l'esclusione di DWV, Cornerstone3D e' stato valutato come possibile
viewer DICOM HTML generale. La licenza MIT e il supporto dichiarato per JPEG
Lossless lo rendono tecnicamente interessante, ma SaniKey deve essere aperto
da `file://` senza server locale, installazione, estensioni o flag del browser.

## Verifica eseguita

Lo spike ha usato `@cornerstonejs/core` e
`@cornerstonejs/dicom-image-loader` 5.6.7. E' stata costruita una pagina
statica minima che crea uno stack viewport e carica un file DICOM selezionato
esplicitamente dall'utente.

La build richiede configurazione dedicata: i codec introducono rami Node
(`fs`, `path`, `url`) da escludere nel bundle browser. Il risultato include:

- circa 3,0 MiB di JavaScript principale;
- circa 2,55 MiB di codec WebAssembly;
- chunk JavaScript aggiuntivi, incluso un worker di decodifica;
- circa 5,8 MiB complessivi prima dei dati dello studio.

Con Chrome headless aperto normalmente da `file://`, Cornerstone3D fallisce
prima della selezione del file:

```text
SecurityError: Failed to construct 'Worker': Script at
'file:///.../assets/...js' cannot be accessed from origin 'null'.
```

Con `--allow-file-access-from-files` il medesimo bundle inizializza il canvas
e carica il DICOM JPEG Lossless. Il flag non e' configurabile in modo
affidabile sui PC di consultazione e pertanto non e' un percorso valido.

## Decisione

Cornerstone3D non viene integrato nell'export USB. Il suo viewer dipende da
worker e WASM caricati come asset separati, incompatibili con il modello
`file://` richiesto da SaniKey. Inoltre il percorso funzionale provato richiede
la selezione manuale dei file, mentre l'interfaccia deve aprire
automaticamente lo studio dalla propria scheda.

Non sono necessari test di `DICOMDIR`, studi reali multi-istanza, WebGL o
layout: il primo criterio eliminatorio fallisce prima del caricamento delle
immagini. L'uso di HTTP locale, di un'applicazione o di una configurazione del
browser richiederebbe una nuova decisione architetturale.

## Conseguenze

SaniKey mantiene esclusivamente:

- viewer HTML statici nativi del supporto quando sono compatibili con
  `file://`;
- anteprime JPEG non diagnostiche generate durante la build;
- `DICOMDIR` e media DICOM standard per i lettori professionali gia'
  installati dal medico.

L'ipotesi di un viewer HTML generico e' chiusa finche' non cambiera' il
contratto operativo della consultazione.
