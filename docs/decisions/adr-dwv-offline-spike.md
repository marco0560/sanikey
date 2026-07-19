# ADR: Esito dello spike DWV offline

## Stato

Respinta.

## Contesto

SaniKey deve essere consultabile aprendo direttamente `index.html` dalla
chiavetta USB, senza rete, server locale, installazioni o configurazioni del
browser sul PC del medico. Per gli studi DICOM senza viewer HTML nativo si e'
valutato DWV come possibile viewer HTML generale.

DWV e' distribuito con licenza GPL-3.0 e supporta formati DICOM rilevanti,
compreso JPEG Lossless. Lo spike ha usato DWV 0.36.0 e Chrome headless con
accesso ordinario a file locali, senza `--allow-file-access-from-files`.

## Verifica eseguita

Lo spike ha confermato che:

- il pacchetto DWV pubblicato dichiara `konva`, `jszip` e
  `magic-wand-tool` come dipendenze esterne;
- un bundle statico completo e' realizzabile, con dimensione di circa 876 KiB
  piu' i worker di decodifica;
- un viewer aperto con `file://` non puo' caricare una istanza DICOM tramite
  `XMLHttpRequest`: il browser blocca l'origine `null`;
- anche quando l'utente seleziona esplicitamente un file DICOM, i worker DWV
  necessari alla decodifica non sono caricabili da `file://` e il browser
  solleva `SecurityError`;
- il flag Chrome `--allow-file-access-from-files` aggirerebbe il limite, ma
  non e' impostabile in modo affidabile sui PC di consultazione.

## Decisione

DWV non viene integrato nell'export USB. Un viewer DWV richiederebbe almeno un
server HTTP locale, un'estensione/browser configurato oppure un'applicazione
installata: tutte opzioni incompatibili con il contratto di consultazione.

Resta valido il fallback corrente:

- viewer HTML statico fornito dal supporto originale, quando apribile;
- anteprime JPEG non diagnostiche generate da SaniKey;
- `DICOMDIR` e media DICOM standard per un lettore professionale gia'
  installato dal medico.

Cornerstone3D resta una riserva soltanto se uno spike dimostra la compatibilita'
con `file://` e senza software aggiuntivo; non deve essere implementato per
analogia con DWV.

## Conseguenze

L'export non acquisisce dipendenze JavaScript GPL-3.0 ne' un viewer che
funzionerebbe solo in condizioni non garantite. La valutazione clinica resta
affidata al lettore DICOM professionale gia' disponibile sul PC del medico;
le anteprime hanno funzione orientativa.
