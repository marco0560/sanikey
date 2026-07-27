# Piano di Implementazione di SaniKey Desktop

Stato: approvato il 25 luglio 2026.

Issue di riferimento:
[#12 — Build SaniKey Desktop as a secure cross-platform application][issue-12].

Questo documento definisce il piano approvato per realizzare SaniKey Desktop
senza ridurre la funzionalità della CLI esistente. L'issue #12 resta l'epic di
prodotto; ogni fase deve essere eseguita mediante sotto-issue e branch brevi,
con evidenze, documentazione, validazione e commit coerenti.

L'implementazione approvata della
[#11 — Extract and visualize longitudinal clinical parameter slices][issue-11]
è un prerequisito della issue #12. La baseline Desktop comprende quindi anche
discovery deterministica, regole curate, modelli longitudinali, export, report
e consultazione offline delle slice. La migrazione Desktop deve conservarne i
contratti e trasferirne l'orchestrazione negli application service senza
reimplementare la logica clinica nella GUI.

[issue-12]: https://github.com/marco0560/sanikey/issues/12
[issue-11]: https://github.com/marco0560/sanikey/issues/11

## Decisioni Approvate

| ID | Decisione |
| --- | --------- |
| D1 | Issue epic, sotto-issue e branch brevi per fase |
| D2 | Extra `desktop`, entry point separato e Semgrep bloccante |
| D3 | TOML round-trip con backup e sostituzione atomica |
| D4 | Application services asincroni basati su `asyncio` |
| D5 | `portalocker` dietro un protocollo applicativo |
| D6 | Artefatti e installer distinti per sistema e architettura |
| D7 | CI multipiattaforma e accettazione su hardware fisico |
| D8 | ARM64 costruito in CI, ma pubblicato solo dopo test fisici |
| D9 | Helper USB privilegiato minimo, firmato e one-shot |
| D10 | Issue #11 completata e validata prima dell'avvio della issue #12 |

## Prerequisito — Chiusura della Issue #11

La fase 0 della issue #12 può iniziare soltanto quando:

- l'implementazione della issue #11 è completa;
- `discover-parameters` e `build-parameter-slices` rispettano i contratti
  approvati;
- `build-patient` rigenera automaticamente le slice quando esistono regole
  abilitate;
- modelli, report, export JSON/JavaScript, database e frontend statico sono
  sincronizzati;
- tabella, grafico e apertura del documento originale funzionano tramite
  `file://`;
- la convivenza tra osservazioni curate e punti estratti è coperta da test;
- output deterministici, privacy e provenienza sono verificati;
- la validazione autorevole del repository è verde;
- il commit di chiusura e le evidenze della issue #11 sono registrati.

Il riferimento operativo è il
[piano approvato delle slice longitudinali][issue-11-plan]. Se uno dei criteri
precedenti manca, la issue #12 resta bloccata al proprio gate di ingresso.

[issue-11-plan]: longitudinal-clinical-parameter-slices-implementation-plan.md

## Obiettivi

- fornire una GUI PySide6 e Qt Quick completa su Linux, Windows 11 e macOS;
- conservare la CLI e il relativo comportamento pubblico;
- conservare integralmente discovery, regole, slice, report ed export
  introdotti dalla issue #11;
- condividere application services, core, provider e adapter tra GUI e CLI;
- includere inventario, preparazione, export e validazione USB nella GUI;
- isolare documenti non fidati, programmi esterni e operazioni privilegiate;
- produrre installer firmati e separati per piattaforma e architettura;
- conservare determinismo, privacy, provenienza e ricostruibilità degli
  artefatti.

## Contratto di Compatibilità

- L'entry point `sanikey` rimane disponibile e supportato.
- Vengono aggiunti l'extra `desktop` e l'entry point `sanikey-desktop`.
- PySide6 e `qasync` non possono essere importati dal core o dalla CLI.
- Gli script esistenti restano wrapper compatibili durante la migrazione.
- `scripts/prepare_usb.py` conserva opzioni, output, codici di uscita e
  protezioni correnti.
- `discover-parameters`, `build-parameter-slices` e l'integrazione in
  `build-patient` conservano opzioni, output aggregato, codici di uscita e
  comportamento deterministico.
- `ObservationSeries`, `ObservationPoint`, `parameters.toml`, reason code,
  digest, identificatori stabili ed export delle slice cambiano soltanto
  mediante migrazioni versionate e documentate.
- Il frontend statico con Chart.js locale resta supportato e compatibile con
  `file://`; la GUI Desktop consuma gli stessi dati tipizzati mediante una
  vista nativa e non tramite WebView.
- Le regole curate restano autorevoli e i punti estratti restano artefatti
  derivati; la GUI non introduce correzioni manuali per singolo punto.
- La configurazione versione 1 resta leggibile.
- La migrazione al nuovo modello USB è esplicita, mostrata in anteprima e
  reversibile.
- Layout USB, manifest e output CLI cambiano soltanto mediante migrazioni
  versionate e documentate.
- Nessun dato reale dei pazienti entra in repository, fixture, log CI o
  screenshot.

## Architettura di Destinazione

```text
src/sanikey/
    application/
        contracts.py
        events.py
        cancellation.py
        services/
    core/
    jobs/
    providers/
    platform/
    privileged/
    desktop/
        controllers/
        models/
        qml/
        resources/
    cli.py
```

I confini hanno le responsabilità seguenti:

- `sanikey.application`: richieste, risultati, eventi, cancellazione, servizi
  e orchestrazione;
- `sanikey.core`: logica deterministica indipendente da UI, sistema operativo
  e programmi esterni;
- `sanikey.jobs`: esecuzione controllata del lavoro bloccante e dei processi
  esterni;
- `sanikey.providers`: capacità, probe, resolver, provenienza e
  implementazioni;
- `sanikey.platform`: adapter Linux, Windows e macOS;
- `sanikey.privileged`: protocollo e client del helper USB;
- `sanikey.desktop`: controller, modelli Qt, QML e risorse incorporate;
- `sanikey.cli`: adapter testuale sopra gli application services.

La logica pura di riconoscimento e applicazione delle regole della issue #11
confluisce in `sanikey.core`. Discovery, build delle slice, lettura della cache
di estrazione e produzione dei report confluiscono negli application service.
CLI, frontend statico e GUI Desktop sono adapter distinti sopra gli stessi
contratti e non duplicano la grammatica o le regole cliniche.

Non deve essere eseguito uno spostamento indiscriminato dei moduli esistenti.
Ogni sottosistema viene migrato separatamente. Quando un percorso di import
esistente deve cambiare, un modulo di compatibilità riesporta i simboli
precedenti finché la rimozione non viene autorizzata e documentata.

## Modello Asincrono

- Gli application services espongono API `async`.
- La CLI li esegue con `asyncio.run`.
- La GUI integra l'event loop Qt tramite `qasync`, confinato nell'extra
  `desktop`.
- Il core rimane prevalentemente sincrono e deterministico.
- Il lavoro bloccante viene eseguito mediante il job layer.
- I processi esterni vengono supervisionati senza bloccare l'event loop.
- Ogni operazione espone eventi, risultato finale e richiesta di
  cancellazione.
- Ogni fase dichiara uno stato tra `cancellable`, `deferred-cancellation` e
  `non-cancellable`.
- La cancellazione non interrompe scritture autorevoli o sostituzioni
  atomiche.

`PySide6.QtAsyncio` può sostituire `qasync` soltanto dopo una nuova decisione
documentata e test equivalenti su Python 3.13, sui tre sistemi operativi e
negli installer.

## Contratto Semgrep

Semgrep diventa parte del validation gate e della CI:

- la dipendenza entra nel gruppo di sviluppo;
- regole e test sono conservati sotto `.semgrep/`;
- i rule test e la scansione bloccante sono eseguiti da
  `scripts/validate_repo.py`;
- `semgrep scan --error` rende ogni finding non autorizzato bloccante;
- la CI può produrre SARIF come artefatto aggiuntivo.

Le regole devono almeno:

- vietare PySide6, QML e `qasync` fuori da `sanikey.desktop`;
- vietare l'import della CLI da GUI, core, provider e adapter;
- vietare alla GUI di invocare `sanikey` tramite sottoprocesso;
- vietare l'accesso diretto della presentazione a database, pipeline e
  provider;
- limitare `subprocess`, `shutil.which` e discovery degli eseguibili ai layer
  autorizzati;
- vietare `shell=True` nell'intero package;
- vietare `fcntl`, `curses`, API Win32 e API macOS nel core portabile;
- vietare scritture TOML dalla GUI fuori dal configuration service;
- vietare operazioni distruttive sui dischi fuori dal helper privilegiato;
- vietare il caricamento QML da path controllabili dall'utente;
- vietare il caricamento di asset GUI da directory esterne scrivibili;
- vietare eccezioni Semgrep non motivate.

Le regole universali entrano subito. Le regole architetturali coprono
inizialmente i nuovi package e si estendono ai moduli legacy durante la
migrazione. Il registro di fase indica i path legacy non ancora coperti.
Alla fine delle fasi application/provider, l'intero `src/sanikey` deve essere
coperto.

Non sono ammesse whitelist globali. Ogni eccezione deve indicare:

- rule ID e posizione precisa;
- necessità dimostrata;
- rischio residuo;
- test che protegge il caso;
- condizione e fase di rimozione.

## Fase 0 — Baseline, Decomposizione e Guardrail

Branch proposto: `chore/desktop-foundation-ledger`.

### Obiettivi

- trasformare issue #12 in un epic eseguibile;
- congelare il comportamento pubblico corrente, inclusa la baseline della
  issue #11;
- definire confini, minacce e matrice di portabilità.

### Lavoro

1. Verificare e registrare il gate di chiusura della issue #11.
2. Creare sotto-issue per ogni fase e collegarne dipendenze e criteri di
   chiusura.
3. Creare un registro di esecuzione con stato, branch, commit ed evidenze.
4. Inventariare comandi CLI, output, JSON, exit status e wrapper sotto
   `scripts/`.
5. Inventariare specificamente `discover-parameters`,
   `build-parameter-slices`, `parameters.toml`, modelli, reason code, report,
   export, database e frontend delle slice.
6. Classificare ogni modulo come presentation, application, core, job,
   provider o platform.
7. Inventariare import specifici OS, programmi esterni, subprocess, cache e
   directory temporanee.
8. Definire la matrice OS × capacità × provider × formato.
9. Estendere il corpus sintetico comune con candidati, regole, unità,
   qualificatori, conflitti e documenti senza data della issue #11.
10. Definire equivalenza funzionale e differenze ammesse tra provider.
11. Definire il modello di minaccia per documenti, QML, provider, log, USB e
   supply chain.
12. Scrivere ADR per layer, modello asincrono, provider, identità USB, helper
    privilegiato e packaging.
13. Introdurre Semgrep, rule test e integrazione nel validation gate.
14. Registrare tempi e dimensioni di base per discovery, build delle slice,
    build completa, export e installer.

### Test ed Evidenze

- snapshot di help, output e codici di uscita CLI;
- snapshot byte-stabili di candidati, report, slice, export e collegamenti
  relativi della issue #11;
- rule test Semgrep positivi e negativi;
- prova che il validation gate fallisca su una violazione sintetica;
- controllo che corpus e fixture non contengano dati reali.

### Criteri di Uscita

- nessuna decisione architetturale aperta;
- gate della issue #11 soddisfatto e baseline registrata;
- tutti i moduli correnti classificati;
- matrice di portabilità completa;
- Semgrep bloccante e coperto da test;
- validazione autorevole superata.

Commit suggeriti:

```text
chore(process): add desktop implementation ledger
chore(validation): enforce desktop architecture boundaries
```

## Fase 1 — Portabilità del Core e Configurazione

Branch proposto: `refactor/desktop-portable-core`.

Dipendenza: fase 0.

### Lavoro

1. Definire `PlatformAdapter`, `StorageAdapter`, `ApplicationLocator` e
   `LockService`.
2. Implementare registry e selezione deterministica dell'adapter corrente.
3. Integrare `portalocker` con timeout e diagnostica italiana.
4. Rimuovere l'import incondizionato di `fcntl`.
5. Isolare `curses` come adapter CLI opzionale.
6. Introdurre directory utente portabili per config, cache, log e staging.
7. Rendere portabili apertura path, discovery applicazioni e copia file.
8. Introdurre `StorageDevice`, `StorageVolume` e `StorageIdentity`.
9. Generalizzare `usb_uuid` in un'identità tipizzata.
10. Definire lo schema di configurazione v2 e la lettura compatibile della v1.
11. Aggiungere la preview della migrazione v1→v2 senza migrazione automatica.
12. Implementare il writer `tomlkit` con lock, backup, file temporaneo, fsync,
    replace e validazione successiva.
13. Conservare la copia Python come implementazione portabile.
14. Confinare `rsync`, `findmnt` e `lsblk` nell'adapter Linux.
15. Attivare unit test richiesti su Ubuntu, Windows, macOS Intel e macOS ARM64
    ospitato.

### Test

- contract suite comune per tutti gli adapter;
- round-trip TOML con commenti, ordine e campi sconosciuti;
- migrazione e rollback della configurazione;
- lock concorrenti, timeout e rilascio dopo eccezione;
- path Unicode e directory con spazi;
- import smoke sui tre OS.

### Criteri di Uscita

- nessun import specifico OS nel core;
- configurazione v1 leggibile e v2 scrivibile;
- CI verde sui runner dei tre OS;
- CLI Linux invariata.

Commit suggeriti:

```text
refactor(core): introduce portable platform adapters
feat(config): add typed USB identity migration
```

## Fase 2 — Application Services e Job Engine Asincrono

Branch proposto: `refactor/desktop-application-services`.

Dipendenza: fase 1.

### Lavoro

1. Introdurre request dataclass immutabili per ogni operazione.
2. Introdurre `OperationResult`, warning, artifact e diagnostic tipizzati.
3. Introdurre eventi con operation ID, fase, contatori e messaggio italiano.
4. Introdurre cancellation token e policy per ogni fase.
5. Implementare job supervisor per thread, processi e staging.
6. Implementare timeout, terminazione graduale, kill del solo figlio e cleanup.
7. Implementare environment allowlist ed esclusione delle variabili sensibili.
8. Limitare e sanitizzare stdout e stderr dei processi.
9. Separare log operativo e diagnostica sensibile opt-in.
10. Aggiungere servizi per configurazione, scansione, integrità, metadati,
    osservazioni, discovery dei parametri, build delle slice, DICOM, FI/RCP,
    build, export, frontend, USB e proposte.
11. Migrare i comandi CLI uno alla volta agli application services.
12. Migrare `discover-parameters` e `build-parameter-slices` senza consentire
    ai comandi standalone di rieseguire estrazione o OCR.
13. Conservare integrazione e ordinamento della derivazione delle slice in
    `build-patient`.
14. Eliminare stampe, lettura stdin e assunzioni TTY dai servizi.
15. Conservare output e exit status mediante adapter CLI.

### Test

- contract test per ogni request e result;
- sequenza e ordinamento deterministico degli eventi;
- cancellazione prima, durante e dopo le fasi autorevoli;
- timeout e cleanup dei job;
- sanitizzazione di nomi, path e contenuti clinici;
- snapshot e test end-to-end della CLI;
- contract test per candidati, regole, punti, slice e report;
- parità byte per byte degli output della issue #11 prima e dopo la migrazione;
- test che GUI e CLI non possano importarsi.

### Criteri di Uscita

- tutti i comandi CLI usano application services;
- nessuna business rule rimane nella CLI;
- nessuna regressione della suite CLI;
- eventi e cancellazione sono disponibili per ogni operazione lunga.

Commit suggeriti:

```text
feat(core): add typed asynchronous operation contracts
refactor(cli): route commands through application services
```

## Fase 3 — Provider, Isolamento e Provenienza

Branch proposto: `feat/desktop-capability-providers`.

Dipendenza: fase 2.

### Lavoro

1. Definire capability, probe, support result, execution request e result.
2. Implementare registry e resolver deterministici.
3. Implementare strategie `auto` e `fixed`.
4. Produrre un execution plan prima di ogni build.
5. Convertire PyMuPDF, Calamine, Pandoc, LibreOffice, OCR e archivi in
   provider.
6. Implementare provider Python, 7-Zip e bsdtar per i container.
7. Implementare Microsoft Word, Excel e PowerPoint su Windows.
8. Implementare Office macOS soltanto dove macro, link e istanza possono
   essere controllati.
9. Rifiutare l'operazione quando le garanzie di sicurezza non sono
   dimostrabili.
10. Eseguire LibreOffice con un profilo temporaneo dedicato.
11. Applicare timeout, ambiente ridotto, output limitato e staging privato.
12. Validare magic bytes, dimensione, digest e struttura degli output.
13. Registrare provider, versione, digest, sorgente, configurazione, tempi e
    fallback.
14. Estendere la cache key con provider, versione, configurazione e adapter.
15. Impedire fallback silenziosi.
16. Esporre capacità mancanti e alternative a CLI e futura GUI.

### Test

- contract suite comune per provider;
- probe senza documenti reali;
- resolver deterministico con motivazione della scelta;
- invalidazione cache per ogni dimensione prevista;
- fallimento senza fallback implicito;
- macro sintetiche, link esterni, OLE e documenti corrotti;
- timeout, output eccessivo e path traversal;
- originali immutati dopo successo e fallimento.

### Criteri di Uscita

- nessuna discovery diretta fuori da provider e platform;
- nessuna conversione diretta nel core;
- provenienza completa per gli artefatti derivati;
- parità dimostrata sul corpus sintetico.

Commit suggeriti:

```text
feat(generation): introduce capability provider registry
feat(generation): record conversion provenance
```

## Fase 4 — Preparazione USB e Helper Privilegiato

Branch proposto: `feat/desktop-usb-preparation`.

Dipendenze: fasi 1–3.

### Lavoro

1. Estrarre modelli, planning e verifica USB da `scripts/prepare_usb.py`.
2. Aggiungere application services per list, inspect, plan, prepare e verify.
3. Conservare `scripts/prepare_usb.py` come wrapper compatibile.
4. Aggiungere il comando CLI `prepare-usb`.
5. Definire un protocollo helper versionato con request e result JSON chiusi.
6. Accettare soltanto identità device, layout, label, nonce e confirmation
   token.
7. Vietare comandi, path e argomenti arbitrari nel protocollo.
8. Fare rieseguire al helper l'inventario live prima di ogni modifica.
9. Rifiutare mismatch tra device selezionato e device corrente.
10. Rifiutare disco di sistema, device fisso non autorizzato e target anomalo.
11. Preservare la doppia conferma per operazioni distruttive.
12. Lasciare il volume non montato al termine.
13. Restituire l'identità tipizzata e una proposta di modifica TOML.
14. Applicare la modifica TOML soltanto dopo una nuova conferma.
15. Migrare nell'adapter Linux `lsblk`, `blkid`, `findmnt`, `parted`,
    `mkfs.exfat`, `fsck.exfat` ed `exfatlabel`.
16. Su Windows usare API Storage/Win32 o comandi PowerShell fissi e firmati,
    senza shell costruita.
17. Su macOS usare Disk Arbitration e output plist di `diskutil`.
18. Integrare elevazione Linux, UAC Windows e autorizzazione macOS.
19. Verificare firma e posizione del helper prima dell'avvio.
20. Non trasmettere configurazione completa o dati dei pazienti al helper.

### Invarianti Ereditati da `prepare_usb.py`

- inventario live dei dispositivi;
- selezione esplicita, mai il primo volume disponibile;
- visualizzazione di modello, capacità, filesystem, label, UUID, partizioni,
  start sector e mountpoint;
- profilo standard DOS/MBR, una partizione, exFAT e inizio a 1 MiB;
- controllo exFAT non distruttivo;
- relabel senza formattazione quando il layout è conforme;
- due conferme esatte prima di sostituire la tabella delle partizioni;
- verifica completa dopo la preparazione;
- nessun remount automatico;
- restituzione dell'identità pronta per la configurazione.

### Test

- parser e contract del protocollo privilegiato;
- replay, nonce errato, identità cambiata e request manomessa;
- tentativi di path traversal e command injection;
- rifiuto del disco di sistema;
- doppia conferma e cancellazione;
- relabel senza formattazione;
- MBR, singola partizione, exFAT e allineamento a 1 MiB;
- test distruttivi opt-in soltanto su device esplicitamente autorizzato.

### Criteri di Uscita

- parità completa con lo script Linux corrente;
- helper come unico punto autorizzato alle modifiche distruttive;
- test reali riusciti su USB exFAT per ogni OS disponibile;
- nessuna elevazione dell'intera GUI.

Commit suggeriti:

```text
feat(core): add portable USB preparation service
feat(build): add signed privileged USB helper
```

## Fase 5 — Spike Verticale Obbligatorio

Branch proposto: `test/desktop-vertical-spike`.

Dipendenze: fasi 1–4.

### Lavoro

1. Costruire una GUI minima con configurazione, avvio operazione, eventi,
   cancellazione e riepilogo.
2. Eseguire il percorso completo su Windows 11 x64 e Mac Intel fisici.
3. Costruire e testare nativamente ARM64 sul runner macOS ospitato.
4. Usare DOCX, DOC, XLSX, PDF immagine, archivio e supporto DICOM sintetico.
5. Includere testi già estratti con parametri sintetici, sinonimi, unità,
   qualificatori, conflitti e regole curate.
6. Verificare Microsoft Office e un provider alternativo dove disponibili.
7. Preparare una USB exFAT reale tramite helper.
8. Eseguire discovery, build delle slice, build completa, export e
   `validate-usb`.
9. Confrontare struttura, record, link, manifest, provenienza, report e slice.
10. Aprire il frontend statico tramite `file://` e verificare grafico, tabella
    e documenti originali.
11. Provare cancellazione, crash recovery e provider bloccato.

### Criteri di Uscita

- spike completo su Windows e Mac Intel;
- nessuna perdita silenziosa;
- GUI sempre reattiva;
- USB reale preparata, esportata e validata;
- report di equivalenza persistito;
- fase 6 bloccata se uno dei criteri fallisce.

Commit suggerito:

```text
test(validation): prove desktop vertical portability
```

## Fase 6 — GUI Completa

Branch previsti:

```text
feat/desktop-shell
feat/desktop-patient-workflows
feat/desktop-build-workflows
feat/desktop-usb-workflows
```

Dipendenza: fase 5.

### Slice Funzionali

#### Shell

- entry point `sanikey-desktop`;
- risorse QML incorporate;
- navigazione, tema, lingua e accessibilità;
- stile macOS, FluentWinUI3 e stile Linux appropriato;
- nessuna personalizzazione diretta dei controlli nativi.

#### Primo Avvio

- scelta della directory privata;
- configurazione del primo paziente;
- directory documenti e metadati;
- probe dei provider;
- preflight e validazione.

#### Pazienti e Documenti

- gestione dei pazienti;
- inventario e problemi documentali;
- staging, DICOM e rappresentazioni consultabili.

#### Metadati e AIFA

- editor dei metadati;
- revisione AIFA a due pannelli;
- ricerca manuale, conferma, esclusione, motivo e provenienza.

#### Parametri Longitudinali

- esecuzione della discovery deterministica sul testo già estratto;
- consultazione del report di proposta senza promozione automatica;
- editor delle regole curate con preview, validazione, backup e sostituzione
  atomica tramite configuration service;
- elenco e ricerca delle slice per nome, sigla e sinonimo;
- grafico temporale nativo, tabella accessibile, filtri e avvisi;
- distinzione visiva tra osservazioni curate e punti estratti;
- rappresentazione prudente dei valori qualificati;
- dettaglio completo della provenienza e apertura del documento originale;
- nessuna modifica manuale del singolo punto derivato;
- nessun WebView e nessuna duplicazione della grammatica in QML.

#### Build e Report

- build completa e incrementale;
- rigenerazione delle slice e relativi report;
- eventi, contatori, cancellazione e riepilogo;
- avvisi utente separati dalla diagnostica tecnica.

#### USB

- inventario dei volumi;
- preparazione privilegiata;
- selezione, export, validazione ed eject;
- conferma rafforzata per target senza manifest.

#### Impostazioni

- provider e componenti;
- diagnostica sensibile opt-in;
- retention e pulizia;
- controllo facoltativo degli aggiornamenti.

### Test

- controller e model testabili senza motore QML;
- smoke test QML su ogni OS;
- navigazione tastiera, focus e metadati per screen reader;
- errori e testi visibili in italiano;
- nessun blocco del thread GUI;
- nessun caricamento QML o asset da filesystem utente;
- parità tra GUI e CLI per discovery, regole, slice e reason code;
- regressione del frontend statico Chart.js tramite `file://`;
- parità GUI/CLI sugli stessi request e result.

### Criteri di Uscita

- tutte le funzioni operative della CLI sono disponibili nella GUI;
- nessuna logica clinica è implementata in QML;
- nessun accesso diretto GUI a database, core o provider;
- nessun WebView.

Commit suggeriti:

```text
feat(bootstrap): add SaniKey Desktop shell
feat(core): add complete desktop workflows
```

## Fase 7 — Packaging, Firma e Supply Chain

Branch proposto: `feat/release-desktop-installers`.

Dipendenza: fase 6.

### Lavoro

1. Aggiungere l'extra `desktop` con PySide6 e `qasync` bloccati.
2. Configurare `pyside6-deploy` e Nuitka per ogni piattaforma.
3. Usare distribuzione standalone/app-directory.
4. Incorporare QML, schemi, immagini e asset.
5. Incorporare Chart.js, licenza e asset statici introdotti dalla issue #11
   senza richieste di rete.
6. Creare un installer Windows `.exe` per utente, firmato Authenticode.
7. Creare `.app` Intel, DMG, hardened runtime, firma, notarizzazione e
   stapling.
8. Costruire e verificare ARM64 in CI senza pubblicarlo.
9. Creare AppImage Linux x86_64 e preservare installazione PyPI/uv.
10. Incorporare soltanto componenti redistribuibili verificati.
11. Gestire OCR e componenti pesanti separatamente quando opportuno.
12. Generare inventario licenze, SBOM e checksum.
13. Aggiungere scansione delle vulnerabilità.
14. Separare build, firma e pubblicazione.
15. Limitare permessi e accesso ai certificati.
16. Pubblicare ogni installer come download distinto.
17. Implementare soltanto il controllo versione e l'apertura della release
    ufficiale.

### Artefatti

Pubblicati nella prima release:

```text
SaniKey-<version>-Windows-x64.exe
SaniKey-<version>-macOS-x86_64.dmg
SaniKey-<version>-Linux-x86_64.AppImage
```

Costruito in CI, ma trattenuto:

```text
SaniKey-<version>-macOS-arm64.dmg
```

### Criteri di Uscita

- nessun installer richiede Python, uv o terminale;
- risorse QML disponibili offline;
- firma e checksum verificabili;
- SBOM e licenze associate agli artefatti.

Commit suggeriti:

```text
feat(build): package native desktop installers
feat(release): sign and attest desktop artifacts
```

## Fase 8 — Stabilizzazione e Prima Release Desktop

Branch proposto: `test/desktop-release-acceptance`.

Dipendenza: fase 7.

### Campagne di Accettazione

- macchine pulite Windows, Mac Intel e Linux;
- Microsoft Office presente e assente;
- LibreOffice presente e assente;
- OCR completo e capacità mancanti;
- DOC legacy, fogli, PDF immagine, container e DICOM;
- build completa e incrementale;
- discovery e build delle slice con cache valida e cache stale;
- ricerca, grafico, tabella, filtri e apertura dell'originale;
- convivenza tra osservazioni curate e punti estratti;
- output byte-stabili e reason code invariati;
- cache invalidata da provider e configurazione;
- USB exFAT corretta, errata, insufficiente e disco di sistema;
- cancellazione in ogni fase;
- crash recovery e cleanup;
- path Unicode, lunghi e con spazi;
- documenti e container malevoli sintetici;
- log operativo privo di dati clinici;
- installazione, upgrade e disinstallazione.

### Criteri di Uscita

- criteri Windows, macOS Intel, Linux e sicurezza soddisfatti;
- installer iniziali pubblicabili;
- ARM64 documentato come non ancora pubblicato;
- issue #12 ancora aperta esclusivamente per il gate ARM64.

Commit suggerito:

```text
test(validation): record desktop release acceptance
```

## Fase 9 — Gate Fisico Apple Silicon

Branch proposto: `test/desktop-arm64-acceptance`.

Dipendenza esterna: disponibilità futura di un Mac Apple Silicon fisico.

### Lavoro

1. Installare il DMG ARM64 su un Mac pulito.
2. Eseguire lo stesso corpus dello spike.
3. Verificare provider, cancellazione, USB exFAT e helper privilegiato.
4. Firmare, notarizzare e pubblicare il DMG ARM64.
5. Aggiornare la matrice delle architetture supportate.

### Criteri di Uscita

- accettazione fisica ARM64 completa;
- tutti e quattro gli artefatti pubblicati;
- tutti i criteri dell'issue #12 soddisfatti;
- issue #12 chiudibile.

Commit suggerito:

```text
test(validation): certify macOS ARM64 desktop release
```

## Documentazione Trasversale

Ogni slice deve:

- aggiornare `docs/architecture.md` quando cambia un confine;
- aggiornare specifica, ADR e user guide insieme al comportamento;
- conservare allineato il piano della issue #11 quando cambia un contratto
  condiviso;
- documentare config v2 e migrazione USB;
- documentare provider, limitazioni e fallback;
- documentare log e diagnostica sensibile;
- documentare installazione e troubleshooting per ogni OS;
- aggiornare checklist e processo di release;
- mantenere i testi destinati all'utente in italiano;
- aggiornare questo registro con branch, commit ed evidenze.

## Gerarchia di Validazione

### Durante l'Iterazione

- test focalizzati sul sottosistema modificato;
- Ruff e mypy sulle superfici coinvolte;
- rule test Semgrep quando cambia una regola.

### Prima di Ogni Commit

- scansione Semgrep bloccante;
- test focalizzati e contract test interessati;
- refresh Codira prima di nuove query indicizzate.

### Chiusura di Ogni Fase

```bash
uv run python scripts/validate_repo.py
```

Inoltre:

- matrice CI richiesta dalla fase;
- suite di regressione della issue #11, inclusi determinismo, provenienza,
  compatibilità `file://` e parità tra dati curati ed estratti;
- documentazione e registro aggiornati;
- commit coerente con il contratto Conventional Commit.

### Chiusura del Branch

- full validation;
- zero finding Semgrep non autorizzati;
- nessuna eccezione temporanea scaduta;
- evidenze native richieste collegate al registro.

### Release

- installazione su macchina pulita;
- verifica di firme, notarizzazione, checksum, SBOM e licenze;
- test USB fisico e provider reali;
- nessun artefatto pubblicato senza il relativo gate nativo.

## Registro dei Rischi

| Rischio | Mitigazione |
| ------- | ----------- |
| Ampiezza dell'issue | Epic, sotto-issue, branch brevi e gate per fase |
| Regressione CLI | Snapshot, wrapper e migrazione comando per comando |
| Regressione delle slice della issue #11 | Gate di ingresso, snapshot byte-stabili, contract test e parità GUI/CLI |
| Integrazione `qasync` | Spike Python 3.13 precoce su ogni OS |
| Automazione Office | Provider separati e rifiuto se non controllabile |
| Operazioni USB distruttive | Helper minimo, identità live e doppia conferma |
| Divergenza cache/provider | Piano esplicito e cache key completa |
| Dati clinici nei log | Sanitizzazione centralizzata e test negativi |
| Supply chain | Lock, SBOM, firme, checksum e permessi CI minimi |
| ARM64 non validato | Build CI, pubblicazione trattenuta e fase 9 |
| Regole Semgrep rumorose | Rule test, rollout progressivo, no ignore globale |

## Regola di Completamento

Una fase è completata soltanto quando:

1. il codice previsto è implementato;
2. i test richiesti sono verdi;
3. Semgrep non produce finding non autorizzati;
4. la documentazione è aggiornata;
5. le evidenze native richieste sono registrate;
6. `uv run python scripts/validate_repo.py` è superato;
7. il commit o i commit della fase sono registrati nel ledger.
