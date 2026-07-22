# Prima Chiavetta USB

Questa pagina descrive il percorso completo per chi parte da un clone pulito e
vuole preparare una prima chiavetta da consegnare a un medico. Tutto il lavoro
di cura dei dati avviene localmente; non copiare mai documenti clinici nel
repository Git.

## 1. Preparare il computer

SaniKey costruisce l'archivio su Linux. Servono:

- [uv](https://docs.astral.sh/uv/), che installa Python e dipendenze del
  progetto;
- Git, per scaricare il repository;
- Pandoc per leggere documenti Office supportati; LibreOffice o `soffice` solo
  per file `.doc` storici;
- facoltativamente OCRmyPDF per estrarre testo dai PDF scannerizzati.

Scaricare e inizializzare il repository:

```bash
git clone https://github.com/marco0560/sanikey.git
cd sanikey
uv run python scripts/bootstrap_dev_environment.py
```

Se il bootstrap termina senza errori, verificare il programma:

```bash
uv run sanikey --help
```

## 2. Creare la configurazione privata

Creare il file personale, che Git ignora volutamente:

```bash
mkdir -p config
cp docs/config-example/accounts.toml config/accounts.toml
```

Aprire `config/accounts.toml` e, per ogni paziente, compilare:

- `id`: un identificativo tecnico stabile, per esempio `mario-rossi`;
- `display_name`: il nome mostrato nella chiavetta;
- `source_documents`: la cartella privata con gli originali;
- `metadata_directory`: la cartella privata con i file TOML curati;
- `local_build`: una cartella privata per gli artefatti rigenerabili.

Per una chiavetta fisica indicare anche l'UUID, il filesystem richiesto e lo
spazio minimo in `[global.usb]`. Le opzioni e un esempio completo sono nella
[Guida utente](user-guide.md#configurare-i-pazienti).

Non proseguire finché questo controllo non è positivo:

```bash
uv run sanikey validate-config
uv run sanikey list-patients
```

## 3. Raccogliere e curare i dati

Mettere gli originali in `source_documents`, senza rinominarli quando il nome
fa parte della loro provenienza. La convenzione consigliata è
`AAAAMMGG Titolo leggibile.estensione`.

Nella `metadata_directory` curare almeno le informazioni richieste dalla
configurazione. Se esiste una terapia, completare `medications.toml` e
`therapies.toml`; se si importano misurazioni, completare anche
`observation_imports.toml`. I modelli sintetici in
`docs/patients-example/` mostrano la struttura. Per cartelle, archivi e DICOM,
seguire [Organizzare l'archivio sanitario](organizzare-archivio-sanitario.md).

Fare una prima lettura automatica prima della build:

```bash
uv run sanikey scan-documents --preflight
```

Correggere gli errori bloccanti. Valutare manualmente duplicati, file non
supportati e avvisi sui container: un avviso non modifica né elimina mai
l'originale.

## 4. Verificare i fogli illustrativi della terapia

Per le terapie soggette ad AIFA, con Internet disponibile, confermare i fogli
illustrativi prima della build:

```bash
uv run sanikey resolve-medication-leaflets ID_PAZIENTE
```

Controllare con attenzione principio attivo, forma e dosaggio proposti. Per un
integratore o un prodotto senza foglio AIFA si può registrare esplicitamente lo
stato `non_aifa`; non selezionare un farmaco simile solo per superare il
controllo. La procedura dettagliata è nella sezione
[Fogli illustrativi della terapia](user-guide.md#fogli-illustrativi-della-terapia).

## 5. Costruire l'archivio locale

Per una prima esecuzione completa:

```bash
uv run sanikey build-all --mode full
```

Il comando crea database, export, pagina web e report nelle cartelle
`local_build`. Controllare gli avvisi indicati nel report. Se si importano
osservazioni, eseguire prima `uv run sanikey import-observations ID_PAZIENTE`.

## 6. Preparare e scrivere la chiavetta

Montare una chiavetta vuota o dedicata e verificare con attenzione il suo
percorso. L'export modifica il contenuto del target scelto.

```bash
uv run sanikey export-usb /media/NOME_CHIAVETTA
uv run sanikey validate-usb /media/NOME_CHIAVETTA
```

In alternativa `deploy-usb` costruisce e poi esporta in un solo passaggio:

```bash
uv run sanikey deploy-usb /media/NOME_CHIAVETTA
```

La validazione deve terminare con successo prima della consegna. Aprire anche
`index.html` dalla chiavetta in un browser e provare almeno ricerca, terapia,
un documento, un foglio AIFA e ogni studio DICOM presente.

## 7. Consegnare e aggiornare

Espellere la chiavetta correttamente dopo la validazione. Per un aggiornamento,
conservare gli originali e i metadati, ripetere i controlli e rigenerare
l'archivio: i file in `local_build` e sulla chiavetta sono artefatti derivati,
non la sola copia dei dati sanitari.

Prima di ogni consegna importante, ripetere la verifica funzionale sul browser
del computer di consultazione. Per i limiti noti, in particolare DICOM senza
viewer HTML e funzioni sperimentali, leggere [Limiti e sviluppi futuri](limits-and-future-work.md).
