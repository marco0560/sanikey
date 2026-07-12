# ADR: Default globale UUID USB

## Stato

Accettata.

## Contesto

La configurazione USB espone due campi con lo stesso significato operativo:

- `[global.usb].required_filesystem_uuid`, che identifica il filesystem USB
  autorizzato per l'export fisico;
- `[[person]].usb_uuid`, nato come identificatore di deploy per singolo
  paziente.

Quando tutti i pazienti abilitati vengono esportati sulla stessa chiavetta,
richiedere `usb_uuid` in ogni blocco `[[person]]` duplica il valore globale e
introduce drift manuale. La presenza del valore globale deve essere sufficiente
per definire l'UUID atteso della chiavetta.

## Decisione

`[global.usb].required_filesystem_uuid` è il default autorevole per
`[[person]].usb_uuid`.

`[[person]].usb_uuid` diventa opzionale quando il valore globale è impostato. Se
presente, resta un override esplicito e deve essere coerente con il valore
globale per i pazienti abilitati. Se il valore globale manca, ogni paziente deve
continuare a dichiarare `usb_uuid` e i pazienti abilitati devono condividere lo
stesso valore.

## Conseguenze

La configurazione canonica per una singola chiavetta contiene l'UUID una sola
volta in `[global.usb].required_filesystem_uuid`. La sostituzione della
chiavetta richiede l'aggiornamento del valore globale e solo degli eventuali
override per paziente presenti.

Il loader continua a esporre `PersonConfig.usb_uuid` come valore risolto, così
gli export e i manifest non devono distinguere tra valore ereditato e valore
esplicito.
