# SaniKey * Specifiche Dettagliate

## 1. Introduzione

### 1.1 Scopo del progetto

SaniKey è un sistema software destinato alla gestione, indicizzazione, consultazione e distribuzione di documentazione medica personale mediante supporto rimovibile.

L'obiettivo principale del progetto è consentire a un medico di consultare rapidamente la documentazione clinica di uno o più pazienti utilizzando una semplice chiavetta USB, senza richiedere installazioni, configurazioni o accesso a servizi online.

SaniKey non è una cartella clinica elettronica, non sostituisce sistemi ospedalieri o gestionali sanitari e non ha finalità diagnostiche. Il sistema opera esclusivamente come archivio documentale avanzato e strumento di consultazione.

Il progetto è progettato per durare nel tempo e privilegia:

* semplicità di utilizzo;
* conservazione dei documenti originali;
* indipendenza da servizi cloud;
* portabilità;
* trasparenza dei dati;
* possibilità di rigenerare completamente tutti gli artefatti derivati.

---

### 1.2 Obiettivi

SaniKey deve consentire di:

#### Conservare la documentazione originale

I documenti originali costituiscono la fonte primaria delle informazioni.

Il sistema deve conservare senza alterazioni:

* referti PDF;
* lettere di dimissione;
* prescrizioni;
* documentazione amministrativa;
* immagini disco DICOM;
* eventuali altri documenti associati al percorso clinico.

Nessuna elaborazione automatica deve modificare o sovrascrivere i documenti originali.

---

#### Rendere immediatamente consultabile la documentazione

Il medico deve poter accedere rapidamente alle informazioni rilevanti senza navigare manualmente centinaia di file.

Il sistema deve fornire:

* ricerca full-text;
* consultazione cronologica;
* consultazione per categoria;
* consultazione per problema clinico;
* consultazione per serie documentale.

---

#### Supportare archivi familiari

Una singola chiavetta USB può contenere la documentazione di più persone appartenenti allo stesso nucleo familiare.

Il sistema deve consentire:

* completa separazione logica degli archivi;
* selezione esplicita del paziente all'avvio;
* consultazione indipendente dei singoli archivi.

---

#### Generare viste cliniche sintetiche

A partire dalla documentazione disponibile il sistema deve produrre:

* timeline clinica;
* elenco problemi clinici;
* elenco farmaci;
* storia clinica sintetica.

Tali informazioni sono considerate ausiliarie rispetto ai documenti originali.

---

#### Ridurre il lavoro manuale

Le attività ripetitive devono essere automatizzate.

In particolare:

* OCR;
* indicizzazione;
* estrazione testo;
* costruzione timeline;
* generazione bozze di sintesi clinica.

Le informazioni generate automaticamente devono poter essere revisionate e corrette dall'utente.

---

#### Operare completamente offline

La consultazione dell'archivio deve essere possibile senza:

* connessione Internet;
* servizi cloud;
* database remoti;
* installazione di software aggiuntivo.

---

### 1.3 Requisiti non obiettivo

Le seguenti funzionalità sono esplicitamente escluse dal perimetro del progetto.

#### Sistema diagnostico

SaniKey non fornisce:

* diagnosi;
* raccomandazioni terapeutiche;
* supporto decisionale clinico.

Qualunque informazione generata automaticamente ha carattere puramente informativo.

---

#### Cartella clinica elettronica

SaniKey non intende sostituire:

* sistemi ospedalieri;
* sistemi regionali;
* fascicolo sanitario elettronico;
* software gestionali medici.

---

#### Modifica dei documenti originali

Il sistema non modifica:

* PDF originali;
* studi DICOM originali;
* immagini disco originali.

Tutti i documenti vengono trattati in sola lettura.

---

#### Collaborazione multiutente

Il sistema non prevede:

* accesso concorrente;
* sincronizzazione tra utenti;
* gestione permessi;
* flusso operativo collaborativi.

L'archivio è gestito da un singolo proprietario.

---

#### Servizi online obbligatori

Nessuna funzione essenziale deve dipendere da:

* API cloud;
* servizi SaaS;
* account esterni;
* connessione Internet.

L'utilizzo di servizi AI remoti può essere previsto come funzionalità opzionale durante la fase di generazione degli artefatti.

---

### 1.4 Terminologia

#### Archivio

Insieme completo dei documenti e dei metadati relativi a un singolo paziente.

---

#### Paziente

Persona fisica a cui appartiene un archivio documentale.

Un repository SaniKey può contenere uno o più pazienti.

---

### Documento

Qualunque elemento informativo archiviato dal sistema.

Esempi:

* PDF;
* referti;
* lettere;
* immagini disco;
* studi DICOM.

---

#### Serie documentale

Raggruppamento logico di documenti appartenenti alla stessa tipologia clinica.

Esempi:

* Analisi;
* Ecocardiogrammi;
* Visite cardiologiche;
* RMN anca.

---

#### Evento clinico

Elemento cronologico utilizzato per costruire la timeline del paziente.

Un evento clinico può essere associato a uno o più documenti.

---

#### Problema clinico

Condizione clinica rilevante utilizzata per classificare la documentazione.

Esempi:

* Diabete tipo 2;
* OSAS;
* Obesità;
* Artrosi.

---

#### Metadati curati

Informazioni mantenute manualmente dall'utente e considerate autorevoli.

Esempi:

* classificazioni;
* correzioni;
* conferme delle proposte AI.

---

#### Artefatto generato

Qualunque elemento ricostruibile automaticamente a partire dai documenti e dai metadati curati.

Esempi:

* database SQLite;
* indice full-text;
* timeline;
* frontend statico;
* esportazione USB.

---

#### Repository SaniKey

Directory sorgente contenente documenti, configurazione, metadati, script e artefatti necessari alla generazione degli archivi consultabili.

---

#### Chiavetta SaniKey

Supporto USB generato dal repository e destinato alla consultazione da parte del medico.

## 2. Architettura Generale

### 2.1 Visione d'insieme

SaniKey è composto da tre ambienti distinti:

1. Repository sorgente
2. Ambiente di costruzione locale
3. Chiavetta USB di consultazione

```text
                 ┌──────────────────┐
                 │ Repository       │
                 │ SaniKey          │
                 └────────┬─────────┘
                          │
                          │ Costruzione
                          ▼
                 ┌──────────────────┐
                 │ Costruzione Locale │
                 │ Artefatti        │
                 │ per paziente     │
                 └────────┬─────────┘
                          │
                          │ Deploy
                          ▼
                 ┌──────────────────┐
                 │ Chiavetta USB    │
                 │ Consultazione    │
                 └──────────────────┘
```

I tre ambienti hanno responsabilità differenti e non devono essere confusi.

---

### 2.2 Repository sorgente

Il repository rappresenta la sorgente autorevole dell'intero sistema.

Contiene:

* documenti originali;
* configurazione;
* metadati curati;
* script;
* codice applicativo.

Il repository è l'unico luogo nel quale vengono effettuate modifiche permanenti.

Nessuna modifica effettuata sugli artefatti generati deve essere considerata persistente.

---

### 2.3 Ambiente di build

L'ambiente di build è una rappresentazione elaborata del repository.

Contiene:

* database SQLite;
* testo OCR;
* metadati estratti;
* timeline;
* embedding;
* frontend statico.

Tutti gli elementi presenti nell'ambiente di build sono rigenerabili.

L'ambiente di build costituisce il punto di separazione tra:

* documenti originali;
* artefatti di consultazione.

---

### 2.4 Chiavetta USB

La chiavetta USB è un artefatto distribuito.

La chiavetta:

* non contiene strumenti di generazione;
* non contiene sorgenti;
* non contiene codice di manutenzione.

La chiavetta contiene esclusivamente:

* documentazione;
* database eventualmente necessari alla consultazione;
* frontend statico;
* manifest di distribuzione.

Il contenuto deve essere consultabile senza installazioni aggiuntive.

---

### 2.5 Flusso operativo generale

Il ciclo di vita del sistema è il seguente:

```text
Documenti nuovi
        │
        ▼
Scansione archivio
        │
        ▼
Estrazione testo
        │
        ▼
OCR
        │
        ▼
Elaborazione DICOM
        │
        ▼
Database SQLite
        │
        ▼
Timeline
        │
        ▼
Storia clinica
        │
        ▼
Frontend statico
        │
        ▼
Deploy USB
```

Tutte le elaborazioni avvengono prima del deploy.

La chiavetta non esegue alcuna elaborazione.

---

### 2.6 Separazione delle responsabilità

#### Repository

Responsabilità:

* conservazione documenti;
* conservazione metadati;
* configurazione;
* gestione versioni.

Non deve:

* contenere dati temporanei;
* dipendere dalla chiavetta.

---

#### Costruzione

Responsabilità:

* trasformazione;
* indicizzazione;
* generazione artefatti.

Non deve:

* contenere dati manualmente modificati;
* essere considerata sorgente autorevole.

---

#### USB

Responsabilità:

* consultazione.

Non deve:

* effettuare scritture;
* effettuare indicizzazioni;
* richiedere software aggiuntivo.

---

### 2.7 Modello Multi-Paziente

L'unità fondamentale del sistema è il paziente.

Ogni paziente possiede un archivio indipendente.

```text
Paziente
 ├─ Documenti
 ├─ Database
 ├─ Timeline
 ├─ Frontend
 └─ Storia clinica
```

Gli archivi di pazienti differenti non condividono dati operativi.

L'isolamento degli archivi semplifica:

* manutenzione;
* backup;
* rigenerazione;
* esportazione.

---

### 2.8 Architettura logica del paziente

Per ogni paziente il sistema costruisce una pipeline indipendente.

```text
                 Documenti
                      │
                      ▼
              Estrazione Testo
                      │
                      ▼
                   OCR
                      │
                      ▼
                 Metadati
                      │
                      ▼
                 SQLite
                 /     \
                /       \
               ▼         ▼
         Timeline    Ricerca
               \         /
                \       /
                 ▼     ▼
                 Frontend
```

La pipeline è deterministica.

A parità di:

* documenti;
* configurazione;
* metadati curati;

deve produrre sempre gli stessi risultati.

---

### 2.9 Componenti principali

#### Scanner

Responsabile dell'individuazione dei documenti.

Funzioni:

* scansione directory;
* calcolo hash;
* rilevamento modifiche.

---

#### Extractor

Responsabile dell'estrazione del contenuto.

Funzioni:

* lettura PDF;
* OCR;
* normalizzazione testo.

---

#### DICOM Processor

Responsabile dell'elaborazione degli studi radiologici.

Funzioni:

* estrazione ISO;
* lettura DICOMDIR;
* raccolta metadati.

---

#### Database Builder

Responsabile della costruzione del database SQLite.

Funzioni:

* popolamento tabelle;
* aggiornamento FTS;
* aggiornamento relazioni.

---

#### AI Assistant

Responsabile delle elaborazioni intelligenti.

Funzioni:

* proposta timeline;
* proposta problemi clinici;
* proposta farmaci;
* proposta storia clinica.

L'AI non è coinvolta nella consultazione.

---

#### Frontend Builder

Responsabile della generazione del sito statico.

Funzioni:

* esportazione JSON;
* generazione pagine HTML;
* generazione indici.

---

#### USB Deployer

Responsabile della distribuzione.

Funzioni:

* verifica dispositivo;
* sincronizzazione;
* validazione finale.

---

### 2.10 Modalità operative

Il sistema opera in tre modalità.

#### Modalità aggiornamento

Utilizzata quando vengono aggiunti nuovi documenti.

Produce:

* database aggiornato;
* timeline aggiornata;
* proposte AI aggiornate.

---

#### Modalità build

Produce gli artefatti destinati alla consultazione.

Produce:

* frontend;
* JSON;
* documentazione sintetica.

---

#### Modalità deploy

Trasferisce gli artefatti sulla chiavetta.

Produce:

* archivio consultabile;
* manifest aggiornato.

---

### 2.11 Principi architetturali

### Documenti originali immutabili

I documenti originali non vengono modificati.

Ogni elaborazione produce artefatti separati.

---

#### Rigenerabilità degli artefatti

Qualunque artefatto derivato deve poter essere eliminato e ricostruito.

---

#### Consultazione offline

La consultazione non deve richiedere accesso a Internet.

---

#### Compatibilità tra sistemi

La consultazione deve funzionare su:

* Windows;
* macOS;

utilizzando browser comuni e non necessariamente aggiornati all'ultima versione disponibile.

La pipeline di ingestione e build è supportata su Linux nello slice corrente.
La compatibilità di ingestione su Windows è una fase successiva e non fa parte
del contratto operativo iniziale.

---

#### Degrado controllato

Funzionalità opzionali come:

* ricerca semantica;
* AI;

non devono compromettere il funzionamento delle funzionalità fondamentali.

Il sistema deve rimanere pienamente utilizzabile anche in loro assenza.

---

### 2.12 Diagramma architetturale finale

```text
                   Repository
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
     Documenti      Configurazione   Metadati
         │               │               │
         └───────────────┼───────────────┘
                         │
                         ▼
                 Pipeline di Costruzione
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
        OCR          Database       AI Assist
         │               │               │
         └───────────────┼───────────────┘
                         │
                         ▼
                  Frontend Statico
                         │
                         ▼
                    Deploy USB
                         │
                         ▼
                 Consultazione
```

## 3. Modello Multi-Paziente

### 3.1 Scopo

SaniKey è progettato per gestire la documentazione sanitaria di più persone all'interno dello stesso repository e della stessa chiavetta USB.

Il caso d'uso principale è il nucleo familiare.

Esempi:

* coniuge;
* figli;
* genitori anziani;
* altri familiari seguiti dallo stesso amministratore dell'archivio.

L'obiettivo è consentire la distribuzione di un unico supporto fisico contenente archivi distinti e indipendenti.

---

### 3.2 Principi fondamentali

Il modello multi-paziente si basa sui seguenti principi.

#### Isolamento logico

Ogni paziente possiede un archivio indipendente.

L'elaborazione di un archivio non deve influenzare gli altri archivi.

---

#### Assenza di dati condivisi

Documenti, timeline, database e frontend appartengono sempre a un singolo paziente.

Non esistono documenti condivisi tra più pazienti.

Qualora un documento riguardi più persone, esso dovrà essere archiviato separatamente negli archivi interessati.

---

#### Costruzione indipendente

Ogni archivio deve poter essere generato individualmente.

Esempi:

```bash
build_patient.py patient-a
```

```bash
build_patient.py patient-b
```

La build di un paziente non richiede la presenza degli altri.

---

#### Deploy aggregato

La chiavetta USB può contenere uno o più archivi.

L'insieme degli archivi presenti sulla chiavetta viene determinato dalla configurazione del repository.

---

### 3.3 Identità del paziente

Ogni paziente è identificato da:

* identificatore tecnico (`id`);
* nome visualizzato (`display_name`).

Esempio:

```toml
[[person]]
id = "patient-a"
display_name = "Paziente A"
```

L'identificatore tecnico:

* deve essere univoco;
* deve essere stabile nel tempo;
* viene utilizzato nei percorsi e nelle configurazioni.

Il nome visualizzato:

* può contenere spazi;
* può essere modificato;
* viene mostrato all'utente finale.

---

### 3.4 Archivio del paziente

L'archivio di un paziente comprende:

* documenti originali;
* database SQLite;
* metadati curati;
* timeline;
* storia clinica;
* frontend statico.

Concettualmente:

```text
Paziente
 ├── Documenti
 ├── Metadati
 ├── Database
 ├── Timeline
 ├── Frontend
 └── Storia Clinica
```

L'archivio costituisce l'unità minima di build e distribuzione.

---

### 3.5 Struttura logica del repository

Ogni paziente possiede un proprio insieme di directory.

Esempio:

```text
patients/
├── patient-a/
│   ├── documents/
│   └── metadata/
│
├── patient-b/
│   ├── documents/
│   └── metadata/
│
└── patient-c/
    ├── documents/
    └── metadata/
```

Le directory sono completamente indipendenti.

---

### 3.6 Struttura logica della build

La build genera un archivio autonomo per ciascun paziente.

Esempio:

```text
build/
├── patient-a/
│   ├── medical_archive.db
│   ├── web/
│   └── documents/
│
├── patient-b/
│   ├── medical_archive.db
│   ├── web/
│   └── documents/
│
└── patient-c/
    ├── medical_archive.db
    ├── web/
    └── documents/
```

Ogni build deve poter essere eliminata e rigenerata indipendentemente.

---

### 3.7 Struttura della chiavetta USB

La chiavetta contiene tutti gli archivi selezionati.

Esempio:

```text
USB/
├── index.html
│
├── patients/
│
│   ├── patient-a/
│   │   ├── medical_archive.db
│   │   ├── web/
│   │   └── documents/
│   │
│   ├── patient-b/
│   │   ├── medical_archive.db
│   │   ├── web/
│   │   └── documents/
│   │
│   └── patient-c/
│       ├── medical_archive.db
│       ├── web/
│       └── documents/
│
└── SANIKEY-MANIFEST.toml
```

---

### 3.8 Selezione del paziente

La selezione del paziente deve essere immediata e comprensibile anche per utenti poco esperti.

Per questo motivo il sistema utilizza una pagina di avvio unica alla radice USB.

Esempio:

```text
index.html
```

Con un solo paziente la pagina apre direttamente l'archivio corrispondente.
Con più pazienti mostra una lista di scelta.

---

### 3.9 Motivazione della scelta

L'utilizzo di file distinti presenta diversi vantaggi.

#### Semplicità

Il medico individua immediatamente il paziente corretto.

---

#### Compatibilità

Non richiede:

* Javascript complesso;
* routing;
* logica applicativa iniziale.

---

#### Robustezza

Ogni archivio rimane consultabile anche in presenza di problemi negli altri archivi.

---

### 3.10 Relazioni tra pazienti

Nella versione iniziale del sistema non esistono relazioni formali tra pazienti.

Non sono previsti:

* collegamenti familiari;
* alberi genealogici;
* documenti condivisi;
* timeline condivise.

Ogni archivio viene trattato come entità indipendente.

---

### 3.11 Configurazione del paziente

Ogni paziente possiede una definizione all'interno del file:

```text
config/accounts.toml
```

La configurazione minima comprende:

```toml
[[person]]
id = "patient-a"

display_name = "Paziente A"

source_documents = "local-data/patient-a/documents"

metadata_directory = "local-data/patient-a/metadata"

local_build = "local-data/generated/patient-a"

usb_uuid = "1A2B-3C4D"
```

I significati dei campi saranno definiti dettagliatamente nel Capitolo 5.

---

### 3.12 Ciclo di vita di un archivio

Il ciclo di vita di un archivio è il seguente.

```text
Configurazione
       │
       ▼
Documenti
       │
       ▼
Costruzione
       │
       ▼
Database
       │
       ▼
Frontend
       │
       ▼
Deploy USB
```

Tutte le operazioni sono eseguite a livello di singolo paziente.

---

### 3.13 Scalabilità

L'architettura non impone limiti sul numero di pazienti.

Le limitazioni pratiche dipendono esclusivamente da:

* spazio disco;
* capacità della chiavetta USB;
* tempi di build.

L'obiettivo principale rimane comunque il supporto di piccoli gruppi familiari.

## 4. Layout del Repository

### 4.1 Scopo

Questo capitolo definisce la struttura fisica del repository SaniKey.

Gli obiettivi principali sono:

* separazione chiara delle responsabilità;
* facilità di backup;
* facilità di rigenerazione;
* semplicità di manutenzione;
* supporto naturale al modello multi-paziente.

La struttura del repository deve rimanere stabile nel tempo per evitare la necessità di modificare script, configurazioni e procedure operative.

---

### 4.2 Principi di organizzazione

La struttura del repository è basata sui seguenti principi.

#### Separazione tra sorgenti e artefatti

I documenti originali e i metadati curati costituiscono la sorgente autorevole.

Gli artefatti generati devono essere conservati separatamente.

---

#### Isolamento per paziente

Ogni paziente possiede una propria area logica.

L'elaborazione di un archivio non deve richiedere accesso ai dati di altri pazienti.

---

#### Rigenerabilità

Qualunque directory generata deve poter essere eliminata completamente e ricostruita senza perdita di informazioni.

---

#### Deploy indipendente

La struttura della build locale deve essere il più possibile simile alla struttura finale della chiavetta USB.

---

### 4.3 Struttura generale del repository

```text
sanikey/
│
├── exports/
│
├── scripts/
│
├── web/
│
├── models/
│
├── docs/
│   ├── config-example/
│   ├── patients-example/
│   └── generated-example/
│
└── logs/
```

Il repository pubblicato su GitHub non contiene dati personali, configurazioni
reali, nomi di persone, nomi di strutture sanitarie o percorsi locali esterni.

Le directory locali:

```text
config/
patients/
generated/
exports/
logs/
```

sono escluse dal controllo versione tramite `.gitignore`.

Gli esempi documentali destinati al repository pubblico risiedono
esclusivamente sotto:

```text
docs/config-example/
docs/patients-example/
docs/generated-example/
```

---

### 4.4 Directory config

Contiene la configurazione reale locale del sistema.

Questa directory non deve essere caricata su GitHub.

```text
config/
│
├── accounts.toml
│
├── ai.toml
│
├── search.toml
│
└── deployment.toml
```

Gli esempi pubblicabili della configurazione risiedono in:

```text
docs/config-example/
```

---

#### accounts.toml

Definisce:

* pazienti;
* percorsi sorgente;
* percorsi build;
* chiavette autorizzate.

È la configurazione principale del sistema.

---

#### ai.toml

Definisce:

* provider AI;
* modelli;
* parametri;
* policy di generazione.

---

#### search.toml

Definisce:

* configurazione FTS;
* configurazione ricerca semantica;
* ranking.

---

#### deployment.toml

Definisce:

* comportamento deploy;
* politiche di sincronizzazione;
* margini minimi di spazio libero.

---

### 4.5 Directory patients

Contiene le informazioni autorevoli locali relative ai pazienti.

Questa directory non deve essere caricata su GitHub.

```text
patients/
│
├── patient-a/
│
├── patient-b/
│
├── patient-c/
│
└── patient-d/
```

Gli esempi pubblicabili della struttura paziente risiedono in:

```text
docs/patients-example/
```

---

### 4.6 Struttura di un paziente

```text
patients/
└── patient-a/
    │
    ├── documents/
    │
    └── metadata/
```

---

### 4.7 Directory documents

Contiene esclusivamente documenti originali locali.

La struttura riportata di seguito è un esempio neutro, privo di dati personali.

SaniKey non impone alcun insieme predefinito di categorie documentali. Ogni paziente può organizzare i propri documenti secondo una struttura di directory differente, adattata alle proprie esigenze cliniche e amministrative.

Le categorie vengono trattate dal sistema come metadati derivati e non costituiscono parte del modello dati fondamentale. Di conseguenza, categorie differenti possono coesistere tra pazienti diversi senza richiedere modifiche alla configurazione, al database o agli strumenti di elaborazione.

```text
patients/patient-a/documents/
│
├── laboratory/
├── imaging/
├── specialist-visits/
├── emergency/
└── administrative/
```

I documenti originali non devono essere modificati dal sistema.

---

### 4.8 Directory metadata

Contiene esclusivamente dati curati.

```text
patients/patient-a/metadata/
│
├── document_tags.toml
├── problems.toml
├── medications.toml
├── clinical_summary.toml
│
├── timeline_overrides.toml
│
└── aliases.toml
```

---

#### timeline_overrides.toml

Contiene:

* correzioni eventi timeline;
* titoli manuali;
* livelli di importanza.

---

#### aliases.toml

Contiene:

* alias documentali;
* alias serie;
* normalizzazioni.

Esempio:

```toml
[[series_alias]]
match = "Eco Cuore"

series = "Ecocardiogramma"
```

---

### 4.9 Directory generated

Contiene artefatti rigenerabili.

Questa directory non deve essere caricata su GitHub.

```text
generated/
│
├── patient-a/
│
├── patient-b/
│
├── patient-c/
│
└── patient-d/
```

Può essere eliminata completamente.

Gli esempi pubblicabili degli artefatti generati risiedono in:

```text
docs/generated-example/
```

---

### 4.10 Struttura build di un paziente

```text
generated/patient-a/
│
├── database/
│
├── extracted_text/
│
├── dicom/
│
├── embeddings/
│
├── timeline/
│
└── web/
```

---

### 4.11 Directory database

Contiene il database SQLite.

```text
generated/patient-a/database/
│
└── medical_archive.db
```

Questo database è considerato rigenerabile.

---

### 4.12 Directory extracted_text

Contiene il testo estratto.

```text
generated/patient-a/extracted_text/
```

Può contenere:

* cache OCR;
* cache parsing PDF;
* testo normalizzato.

Lo scopo principale è evitare elaborazioni ripetute.

---

### 4.13 Directory dicom

Contiene gli studi estratti.

```text
generated/patient-a/dicom/
│
└── 20250318_RMN_Anca/
```

Contiene:

* DICOMDIR;
* file DICOM;
* viewer eventualmente presente;
* metadati estratti.

---

### 4.14 Directory embeddings

Contiene dati per ricerca semantica.

```text
generated/patient-a/embeddings/
```

La presenza di questa directory è opzionale.

---

### 4.15 Directory timeline

Contiene artefatti intermedi.

```text
generated/patient-a/timeline/
```

Esempi:

* timeline generata;
* proposte AI;
* cache elaborazione.

---

### 4.16 Directory web

Contiene il frontend generato.

```text
generated/patient-a/web/
│
├── index.html
├── app.js
│
├── data/
│
└── assets/
```

Questa directory rappresenta la sorgente immediata del deploy.

---

### 4.17 Directory exports

Contiene le immagini complete destinate alla distribuzione.

```text
exports/
│
├── usb-image/
│
└── staging/
```

---

#### staging

Area temporanea di preparazione.

```text
exports/staging/
```

Viene utilizzata dal processo di deploy.

---

#### usb-image

Rappresentazione completa della chiavetta.

```text
exports/usb-image/
```

Può essere utilizzata:

* per test;
* per validazione;
* per deploy.

---

### 4.18 Directory scripts

Contiene gli strumenti di manutenzione.

```text
scripts/
│
├── scan_documents.py
├── extract_text.py
├── process_dicom.py
├── build_database.py
├── generate_embeddings.py
├── generate_timeline.py
├── generate_clinical_summary.py
├── build_web.py
├── build_patient.py
├── build_all.py
├── validate_usb.py
├── deploy_usb.py
└── update_archive.py
```

Le responsabilità verranno definite nel Capitolo 16.

---

### 4.19 Directory models

Contiene:

* modelli dati;
* schemi;
* definizioni condivise.

```text
models/
```

Nessun dato paziente deve essere conservato qui.

---

### 4.20 Directory web

Contiene risorse frontend comuni.

```text
web/
│
├── templates/
│
├── css/
│
├── js/
│
└── assets/
```

Questa directory rappresenta la sorgente del frontend generato.

---

### 4.21 Directory docs

Contiene:

* specifiche;
* ADR;
* documentazione tecnica.

```text
docs/
```

---

### 4.22 Directory logs

Contiene log di esecuzione.

```text
logs/
```

I log non sono considerati sorgente autorevole.

Possono essere eliminati periodicamente.

---

### 4.23 Convenzioni di naming

#### Directory pazienti

Utilizzare:

```text
patient-a
patient-b
patient-c
patient-d
```

Non utilizzare:

```text
Paziente A
patient a
```

I nomi directory devono essere:

* stabili;
* privi di spazi;
* utilizzabili nei percorsi.

---

#### Documenti

Convenzione obbligatoria:

```text
AAAAMMGG Titolo.pdf
```

Esempio:

```text
20260921 Operazione Cataratta.pdf
```

---

#### Studi DICOM

Convenzione consigliata:

```text
AAAAMMGG_TipoEsame.iso
```

Esempio:

```text
20250318_RMN_Anca.iso
```

---

### 4.24 Artefatti autorevoli

Le seguenti directory locali costituiscono la sorgente autorevole.

```text
config/
patients/
```

Sono escluse dal repository pubblico tramite `.gitignore`.

---

### 4.25 Artefatti rigenerabili

Le seguenti directory sono completamente rigenerabili.

```text
generated/
exports/
logs/
```

La loro eliminazione non deve comportare perdita di informazioni.

## 5. Configurazione

### 5.1 Scopo

La configurazione di SaniKey definisce:

* gli archivi gestiti;
* i percorsi sorgente;
* i percorsi di build;
* le chiavette autorizzate;
* il comportamento dei componenti opzionali.

L'obiettivo principale è consentire la personalizzazione del sistema senza richiedere modifiche al codice.

Tutta la configurazione è conservata in formato TOML.

---

### 5.2 Principi di configurazione

La configurazione deve rispettare i seguenti principi.

#### Esplicita

Ogni comportamento significativo deve essere configurato esplicitamente.

Il sistema deve evitare inferenze non documentate.

---

#### Versionabile

Gli esempi di configurazione devono essere conservati sotto controllo versione.

La configurazione reale locale contiene dati sensibili e deve essere esclusa
dal controllo versione.

---

#### Leggibile

La configurazione deve poter essere letta e modificata manualmente.

---

#### Validabile

Ogni file di configurazione deve essere validato prima dell'avvio della pipeline.

Errori di configurazione devono interrompere l'esecuzione.

---

### 5.3 Directory di configurazione

La configurazione reale si trova in:

```text
config/
│
├── accounts.toml
├── ai.toml
├── search.toml
└── deployment.toml
```

La directory `config/` deve essere esclusa dal repository pubblico tramite
`.gitignore`.

Gli esempi pubblicabili si trovano in:

```text
docs/config-example/
```

---

### 5.4 accounts.toml

`accounts.toml` è il file di configurazione principale del sistema.

Definisce:

* i pazienti;
* i percorsi;
* le chiavette autorizzate.

Deve contenere esplicitamente tutti i percorsi relativi ai dati reali.

Non esistono percorsi predefiniti.

---

### 5.5 Configurazione globale

Esempio:

```toml
[global]

config_version = 1
```

---

#### config_version

Versione dello schema di configurazione.

Utilizzata per:

* compatibilità;
* migrazioni;
* validazione.

---

### 5.6 Definizione di un paziente

Esempio completo:

```toml
[[person]]

id = "patient-a"

display_name = "Paziente A"

source_documents =
"local-data/patient-a/documents"

metadata_directory =
"local-data/patient-a/metadata"

local_build =
"local-data/generated/patient-a"

usb_uuid =
"1A2B-3C4D"

enabled = true
```

---

### 5.7 id

Identificatore tecnico del paziente.

Requisiti:

* univoco;
* stabile;
* minuscolo;
* senza spazi.

Esempi validi:

```text
patient-a
patient-b
```

Esempi non validi:

```text
Paziente A
patient a
```

L'identificatore viene utilizzato:

* nei percorsi;
* nel database;
* nei manifest.

---

### 5.8 display_name

Nome mostrato all'utente.

Può contenere:

* spazi;
* lettere accentate;
* maiuscole.

Esempio:

```toml
display_name = "Paziente A"
```

---

### 5.9 source_documents

Percorso sorgente dei documenti.

Esempio:

```toml
source_documents =
"local-data/patient-a/documents"
```

Questo campo è obbligatorio.

Il valore puo' essere assoluto oppure relativo alla root del repository quando
la configurazione e' `config/accounts.toml`. La directory deve restare fuori
dai contenuti versionati; `local-data/...` e' accettato per dati locali ignorati
da Git.

---

### 5.10 Motivazione di source_documents

I documenti originali possono essere conservati:

* su NAS;
* su disco esterno;
* in una directory dedicata.

SaniKey non impone una collocazione fisica specifica.

Il percorso reale non deve essere versionato nel repository pubblico.

---

### 5.11 metadata_directory

Percorso dei metadati curati.

Esempio:

```toml
metadata_directory =
"local-data/patient-a/metadata"
```

Contiene:

* tag;
* problemi clinici;
* farmaci;
* storia clinica.

---

### 5.12 local_build

Directory di build del paziente.

Esempio:

```toml
local_build =
"local-data/generated/patient-a"
```

Contiene:

* database;
* frontend;
* timeline;
* OCR;
* embeddings.

Può essere eliminata e rigenerata.

---

### 5.13 usb_uuid e usb_uuid

`[global.usb].usb_uuid` è l'UUID della chiavetta autorizzata e
funge da default per i pazienti.

Esempio:

```toml
[global.usb]
usb_uuid = "1A2B-3C4D"
```

`[[person]].usb_uuid` è opzionale quando il valore globale è impostato. Se
presente, è un override esplicito e deve restare coerente con il valore globale
per i pazienti abilitati. Se il valore globale manca, ogni paziente deve
dichiarare `usb_uuid`.

---

### 5.14 Motivazione dell'UUID

L'UUID identifica fisicamente il dispositivo.

È preferibile a:

```text
/media/user/SANIKEY
```

poiché:

* i mountpoint cambiano;
* le lettere di unità cambiano;
* l'UUID rimane stabile.

---

### 5.15 enabled

Abilita o disabilita il paziente.

Esempio:

```toml
enabled = true
```

Oppure:

```toml
enabled = false
```

Gli archivi disabilitati vengono ignorati.

---

### 5.16 ai.toml

Configura i componenti AI.

Esempio:

```toml
[provider]

type = "local"

model =
"qwen3:8b"
```

---

### 5.17 Modalità AI supportate

#### Local

Modelli eseguiti localmente.

Esempi:

* Ollama;
* llama.cpp;
* vLLM locale.

---

#### Remote

Servizi esterni.

Esempi:

* OpenAI;
* Anthropic;
* altri provider.

---

### 5.18 search.toml

Configura la ricerca.

Esempio:

```toml
[fts]

enabled = true

[semantic]

enabled = false
```

---

### 5.19 Ricerca lessicale

La ricerca lessicale deve essere sempre disponibile.

Non può essere disabilitata.

---

### 5.20 Ricerca semantica

Può essere:

```toml
enabled = true
```

oppure:

```toml
enabled = false
```

La disattivazione non deve influire sul resto del sistema.

---

### 5.21 deployment.toml

Configura il deploy.

Esempio:

```toml
[usb]

required_free_space_mb = 512

verify_hashes = true

use_rsync = true
```

---

### 5.22 required_free_space_mb

Spazio minimo libero che deve rimanere disponibile dopo il deploy.

Serve a evitare chiavette completamente saturate.

---

### 5.23 verify_hashes

Se abilitato:

```toml
verify_hashes = true
```

il deploy verifica la correttezza dei file copiati.

---

### 5.24 use_rsync

Se disponibile:

```toml
use_rsync = true
```

viene utilizzato rsync.

In caso contrario il sistema utilizza un meccanismo alternativo.

---

### 5.25 Validazione

Tutti i file di configurazione vengono validati all'avvio.

La validazione controlla:

* sintassi TOML;
* campi obbligatori;
* unicità degli identificatori;
* esistenza dei percorsi;
* consistenza dei valori.

Gli script devono inoltre verificare che:

* `config/accounts.toml` esista prima di accedere a dati reali;
* tutti i percorsi relativi ai pazienti siano esplicitamente configurati;
* i file e le directory contenenti dati reali siano esclusi da Git;
* nessun dato personale venga scritto sotto directory versionate.

---

### 5.26 Errori di configurazione

Gli errori di configurazione sono considerati fatali.

Esempi:

* UUID mancante;
* id duplicato;
* percorso inesistente;
* sintassi TOML non valida.

In tali casi la pipeline deve interrompersi immediatamente.

---

### 5.27 Configurazione effettiva

Durante l'avvio il sistema costruisce una configurazione effettiva risultante da:

```text
config/*.toml
        ↓
Parametri CLI
```

Le opzioni specificate tramite CLI hanno precedenza massima.

I percorsi relativi a dati reali non possiedono default interni.

## 6. Modello Documentale

### 6.1 Scopo

Il modello documentale definisce come SaniKey rappresenta, identifica, classifica e collega i documenti sanitari.

Il modello deve supportare:

* documenti PDF;
* immagini disco DICOM;
* contenuti DICOM estratti;
* documenti amministrativi;
* documenti clinici ripetuti nel tempo;
* documenti collegati tra loro;
* serie documentali longitudinali.

Il modello documentale non interpreta clinicamente il contenuto dei documenti.

L'interpretazione clinica appartiene al modello di identità e ai metadati curati.

---

### 6.2 Documento

Un documento è qualunque file originale inserito nell'archivio del paziente.

Esempi:

* referto PDF;
* lettera di dimissione;
* prescrizione;
* certificato;
* immagine disco ISO;
* archivio ZIP contenente immagini diagnostiche;
* file DICOM estratto.

Ogni documento deve essere trattato come immutabile.

---

### 6.3 Identità del documento

L'identità tecnica di un documento è basata sul suo hash crittografico.

Il campo principale è:

```text
sha256
```

Il percorso del file non è sufficiente a identificare un documento perché:

* un file può essere spostato;
* un file può essere rinominato;
* directory e categorie possono cambiare;
* archivi storici possono essere riorganizzati.

Lo SHA256 consente invece di riconoscere lo stesso documento anche in caso di spostamento.

---

### 6.4 Percorso del documento

Il percorso del documento rimane comunque rilevante.

Il sistema memorizza:

* percorso relativo;
* nome file;
* directory padre;
* categoria derivata.

Esempio:

```text
Analisi/20240312 Analisi.pdf
```

Produce:

```text
category = "Analisi"
document_date = "2024-03-12"
title = "Analisi"
```

---

### 6.5 Data del documento

La data principale del documento viene normalmente derivata dal nome file.

Formato previsto:

```text
AAAAMMGG Titolo.ext
```

Esempio:

```text
20240312 Analisi.pdf
```

produce:

```text
document_date = "2024-03-12"
```

Se la data non è presente nel nome file, il sistema può tentare di derivarla da:

* metadati PDF;
* metadati DICOM;
* testo estratto;
* override manuali.

La data derivata dal nome file ha precedenza sulle inferenze automatiche.

---

### 6.6 Titolo del documento

Il titolo viene derivato dal nome file rimuovendo:

* data iniziale;
* estensione;
* separatori tecnici.

Esempio:

```text
20260921 Operazione Cataratta.pdf
```

produce:

```text
title = "Operazione Cataratta"
```

Il titolo può essere corretto tramite override manuale.

---

### 6.7 Categoria documentale

La categoria documentale è derivata dalla directory in cui il documento si trova.

Esempio:

```text
Cardiologo/20250410 Ecocardiogramma.pdf
```

produce:

```text
category = "Cardiologo"
```

Le categorie non sono predefinite dal sistema.

Ogni paziente può utilizzare categorie differenti.

---

### 6.8 Tipo documento

Ogni documento possiede un tipo tecnico.

Tipi iniziali:

```text
pdf
dicom_iso
dicom_directory
image
text
archive
office
other
```

---

### 6.9 PDF

I PDF sono il tipo documentale principale.

Per ogni PDF il sistema deve:

* calcolare SHA256;
* estrarre metadati;
* estrarre testo;
* eseguire OCR se necessario;
* indicizzare contenuto e metadati.

Il PDF originale non deve essere modificato.

---

### 6.10 PDF nativo e PDF scansionato

Il sistema distingue tra:

```text
PDF nativo
PDF scansionato
```

Un PDF nativo contiene testo estraibile.

Un PDF scansionato richiede OCR.

Questa distinzione serve esclusivamente a determinare il metodo di estrazione del testo.

---

### 6.10.1 Immagini sorgente

I file immagine `.jpg`, `.jpeg` e `.png` presenti nei documenti sorgente sono
documenti di tipo `image`.

Durante l'ingestione Linux il testo viene estratto tramite il comando di sistema
`tesseract`. Quando i language pack `ita` ed `eng` sono disponibili, la pipeline
usa `ita+eng`; in caso contrario usa la lingua predefinita di Tesseract.

Se Tesseract non e' disponibile o fallisce, l'immagine resta catalogata e il
problema viene registrato come warning di OCR immagine saltato.

---

### 6.11 Supporti DICOM

Un documento `dicom_iso` rappresenta un supporto consegnato da una struttura
sanitaria e contenente uno studio diagnostico. Gli archivi `.zip`, `.7z` e
`.rar` rappresentano inizialmente archivi generici e sono promossi a supporti
DICOM solo quando il contenuto indica uno studio diagnostico.

I file DICOM interni sono catalogati come istanze diagnostiche e non sono
inviati alla pipeline OCR o all'estrazione testo ordinaria. Questa condizione
non costituisce warning: e' il comportamento atteso per i DICOM catalog-only.

Esempio:

```text
20250318_RMN_Anca.iso
20250318_RMN_Anca.zip
20250318_RMN_Anca.7z
20250318_RMN_Anca.rar
```

Il sistema deve:

* conservare il supporto originale;
* trattare il contenuto estratto come artefatto generato;
* cercare DICOMDIR;
* raccogliere metadati;
* rilevare eventuali viewer inclusi.

La scelta se espandere automaticamente i supporti DICOM, espanderli come
opzione durante l'ingestion oppure richiedere espansione manuale da parte
dell'operatore non fa parte delle decisioni iniziali.

#### 6.11.1 Archivi

Gli archivi `.zip`, `.7z` e `.rar` possono comparire tra i documenti sorgente.

L'estensione dell'archivio non e' sufficiente per classificarlo come DICOM.
Il sistema deve riconoscere un archivio DICOM da segnali di contenuto, come
`DICOMDIR`, file `.dcm`, immagini disco `.iso`/`.img`, ZIP annidati con file
DICOM, path con segmento `DICOM` o magic bytes DICOM quando leggibili senza
estrazione completa.

Il sistema deve:

* conservare l'archivio originale;
* calcolare SHA256 sull'archivio originale;
* estrarre un inventario testuale dei file contenuti;
* estrarre i membri in una staging area generata durante la build;
* calcolare SHA256 dei membri estratti;
* registrare provenance verso il contenitore originale e il path interno;
* segnalare con warning archivi cifrati, corrotti o non leggibili.

Il contenitore originale resta la sorgente autorevole. I membri estratti sono
artefatti generati e possono entrare nella pipeline documentale ordinaria come
documenti derivati.

I membri tecnici non clinici, per esempio runtime Java, DLL, help HTML o asset
dei viewer inclusi nei supporti, devono essere esclusi tramite pattern di
ingestione espliciti. Tali membri restano nel manifest di staging ma non devono
essere trattati come documenti clinici da indicizzare o da inviare
all'estrazione testo ordinaria.

I path tecnici dei viewer, inclusi segmenti come `Help`, `Manual`,
`Viewer-Windows`, `jre` e `assets`, sono manifest-only solo quando corrispondono
a `exclude_patterns` configurati; eventuali eccezioni puntuali possono essere
recuperate con `include_patterns`. PDF esterni a tali path continuano a essere
trattati come documenti derivati ordinari.

#### 6.11.2 Documenti Office e OpenDocument

Il sistema può estrarre testo da documenti `.docx`, `.xlsx`, `.odt` e `.ods`.

Per documenti legacy `.doc` e `.xls`, l'estrazione richiede LibreOffice o
`soffice` disponibile come comando di sistema.

Se l'estrazione non è possibile, il documento deve restare catalogato e il
problema deve essere registrato come warning.

#### 6.11.3 DICOM nei contenitori

I file DICOM rilevati dentro archivi o immagini disco estratte in staging devono
essere catalogati come documenti DICOM derivati.

Non devono essere inviati alla pipeline OCR o all'estrazione testo ordinaria.
La provenance deve collegare ogni file DICOM interno al contenitore originale.

---

### 6.12 Directory DICOM estratta

Una directory DICOM estratta è un artefatto generato.

Non è considerata documento originale.

È rigenerabile a partire dal supporto originale quando l'espansione è prevista
dal flusso operativo scelto.

La directory estratta serve per:

* indicizzazione;
* accesso rapido;
* consultazione manuale;
* rilevamento viewer.

---

### 6.13 Studio diagnostico

Uno studio diagnostico è un'entità logica che può collegare:

* referto PDF;
* supporto DICOM originale;
* directory DICOM estratta;
* metadati DICOM.

Esempio:

```text
20250318 RMN Anca.pdf
20250318_RMN_Anca.iso
```

possono rappresentare lo stesso studio.

---

### 6.14 Relazioni documentali

Il sistema deve supportare relazioni tra documenti.

Relazioni iniziali:

```text
same_study
supersedes
related
attachment
```

---

#### same_study

Indica che due documenti rappresentano lo stesso esame.

Esempio:

```text
Referto PDF
ISO DICOM
```

---

#### supersedes

Indica che un documento sostituisce una versione precedente.

Esempio:

```text
Referto corretto
Referto originale
```

---

#### related

Indica una relazione generica.

Esempio:

```text
Prescrizione
Referto conseguente
```

---

#### attachment

Indica un allegato.

Esempio:

```text
Modulo consenso
Documento principale
```

---

### 6.15 Serie documentale

Una serie documentale raggruppa documenti dello stesso tipo clinico o amministrativo ripetuti nel tempo.

Esempi:

* Analisi;
* Ecocardiogrammi;
* Visite cardiologiche;
* RMN anca;
* Diario pressorio;
* Rinnovi invalidità.

La serie consente una visualizzazione longitudinale.

---

### 6.16 Identificazione della serie

La serie può essere derivata da:

* titolo documento;
* categoria;
* alias manuali;
* regole euristiche;
* override manuali.

Esempio:

```text
20240312 Analisi.pdf
20240630 Analisi.pdf
20240918 Analisi.pdf
```

appartengono alla serie:

```text
Analisi
```

---

### 6.17 Alias di serie

Gli alias permettono di normalizzare titoli differenti.

Esempio:

```toml
[[series_alias]]
match = "Eco Cuore"
series = "Ecocardiogramma"

[[series_alias]]
match = "Ecografia cardiaca"
series = "Ecocardiogramma"
```

---

### 6.18 Serie e categorie

Serie e categorie sono concetti distinti.

La categoria deriva dalla directory.

La serie deriva dal contenuto logico del documento.

Esempio:

```text
Categoria: Cardiologo
Serie: Ecocardiogramma
```

oppure:

```text
Categoria: Analisi
Serie: Controlli Ematochimici
```

---

### 6.19 Documento amministrativo

I documenti amministrativi sono documenti non direttamente clinici ma rilevanti per il percorso sanitario.

Esempi:

* invalidità;
* contrassegno disabili;
* pratiche ASL;
* esenzioni;
* autorizzazioni.

Devono essere indicizzati e consultabili come gli altri documenti.

---

### 6.20 Documento clinico

Un documento clinico contiene informazioni sanitarie.

Esempi:

* referto specialistico;
* lettera di dimissione;
* esame di laboratorio;
* diagnostica per immagini;
* prescrizione.

La distinzione tra clinico e amministrativo può essere automatica o manuale.

---

### 6.21 Documenti senza data

I documenti privi di data devono essere accettati, ma segnalati.

Il sistema deve:

* inserirli nell'indice;
* renderli ricercabili;
* escluderli dalla timeline ordinata;
* produrre warning di validazione.

La data può essere aggiunta tramite override manuale.

---

### 6.22 Documenti duplicati

Due file con lo stesso SHA256 sono duplicati tecnici.

Il sistema deve rilevarli.

Politiche possibili:

```text
keep_all
warn
deduplicate
```

La politica predefinita è:

```text
warn
```

Il sistema segnala il duplicato ma non elimina file.

---

### 6.23 Documenti modificati

Se un file mantiene lo stesso percorso ma cambia SHA256, viene trattato come documento modificato.

Il sistema deve:

* registrare il nuovo hash;
* invalidare cache OCR;
* rigenerare testo estratto;
* aggiornare database e indici.

---

### 6.24 Metadati derivati

Per ogni documento il sistema può derivare:

* data;
* titolo;
* categoria;
* tipo tecnico;
* dimensione;
* hash;
* testo;
* serie;
* relazioni.

I metadati derivati sono rigenerabili.

---

### 6.25 Metadati curati

I metadati curati possono correggere o integrare i metadati derivati.

Esempi:

* titolo manuale;
* data corretta;
* serie corretta;
* relazioni documentali;
* tag clinici.

I metadati curati hanno precedenza sui metadati derivati.

---

### 6.26 Errori documentali

Il sistema deve rilevare e segnalare:

* file illeggibili;
* PDF corrotti;
* ISO non montabili;
* DICOMDIR mancante;
* data non interpretabile;
* nome file non conforme;
* duplicati.

Gli errori non bloccanti devono essere inclusi in un report di validazione.

## 7. Modello di Identità

### 7.1 Scopo

Il modello di identità definisce le entità concettuali fondamentali utilizzate da SaniKey.

A differenza del modello documentale, che descrive i file e i loro metadati, il modello di identità descrive gli elementi clinici e amministrativi che emergono dall'insieme dei documenti.

Esempi:

* problemi clinici;
* farmaci;
* terapie;
* eventi;
* osservazioni;
* monitoraggi.

Queste entità rappresentano il linguaggio comune utilizzato dal database, dalla timeline, dalla ricerca e dagli strumenti AI.

---

### 7.2 Principi fondamentali

#### Separazione tra documento e conoscenza

Un documento rappresenta una fonte informativa.

Un'entità clinica rappresenta una conoscenza derivata.

Esempio:

```text
Documento
    ↓
Referto diabetologico

Problema clinico
    ↓
Diabete Tipo 2
```

Il problema clinico non coincide con il documento che lo menziona.

---

#### Tracciabilità delle entità derivate

Ogni entità derivata deve poter essere ricondotta alla propria origine.

---

#### Persistenza temporale

Il sistema deve poter rappresentare:

* stati permanenti;
* condizioni temporanee;
* eventi puntuali;
* periodi.

---

#### Neutralità clinica

SaniKey archivia informazioni.

Non produce diagnosi né raccomandazioni terapeutiche.

---

### 7.3 Entità fondamentali

Il modello utilizza le seguenti entità.

```text
Patient
Document
Document Series
Clinical Event
Clinical Problem
Procedure
Medication
Therapy Episode
Observation Series
Observation Point
Observation Campaign
Source
```

---

### 7.4 Patient

Rappresenta una persona fisica.

Ogni paziente possiede:

* documenti;
* timeline;
* problemi clinici;
* terapie;
* osservazioni.

Il paziente costituisce il confine di isolamento principale del sistema.

---

### 7.5 Clinical Problem

Rappresenta una condizione clinica rilevante.

Esempi:

```text
Diabete Tipo 2
OSAS
Obesità
Artrosi Anca Destra
Ipertensione
```

Un problema clinico:

* può essere attivo o risolto;
* può comparire in più documenti;
* può essere associato a farmaci e osservazioni.

---

### 7.6 Stato del problema clinico

Valori iniziali:

```text
active
resolved
suspected
historical
```

---

#### active

Condizione attualmente presente.

---

#### resolved

Condizione risolta.

---

#### suspected

Condizione ipotizzata ma non confermata.

---

#### historical condition

Condizione rilevante dal punto di vista storico ma non più attiva.

---

### 7.7 Procedure

Rappresenta un intervento, una procedura invasiva o un atto clinico rilevante.

Esempi:

```text
Gastroplastica verticale
Intervento cataratta
Protesi d'anca
Colonscopia operativa
Infiltrazione articolare
```

Una procedura può essere:

* programmata;
* eseguita;
* annullata;
* storica.

La procedura è distinta dal documento che la descrive.

Esempio:

```text
Documento:
20260921 Operazione Cataratta.pdf

Procedura:
Intervento cataratta
```

La procedura può essere collegata a:

* uno o più documenti;
* uno o più problemi clinici;
* uno o più eventi timeline;
* una struttura sanitaria;
* uno specialista;
* eventuali complicanze o follow-up.

---

### 7.8 Stato della procedura

Valori iniziali:

```text
planned
completed
cancelled
historical
```

#### planned

Procedura programmata ma non ancora eseguita.

#### completed

Procedura eseguita.

#### cancelled

Procedura programmata e poi annullata.

#### historical

Procedura avvenuta prima dell'inizio dell'archivio o ricostruita retrospettivamente.

### 7.9 Medication

Rappresenta un principio attivo o farmaco.

Esempi:

```text
Metformina
Semaglutide
Bisoprololo
Ramipril
```

Il farmaco è una definizione stabile.

Non contiene informazioni temporali.

---

### 7.10 Therapy Episode

Rappresenta un periodo di trattamento.

Esempio:

```text
Metformina
1000 mg
dal 2024-01-01
al 2025-06-30
```

Un episodio terapeutico collega:

* farmaco;
* dosaggio;
* periodo;
* motivazione.

---

### 7.11 Motivazione terapeutica

Un episodio terapeutico può essere collegato a uno o più problemi clinici.

Esempio:

```text
Metformina
    ↓
Diabete Tipo 2
```

---

### 7.12 Terapie attive

Una terapia è considerata attiva quando:

```text
end_date = null
```

oppure:

```text
end_date > oggi
```

---

### 7.13 Clinical Event

Rappresenta un evento puntuale nella storia del paziente.

Esempi:

```text
Intervento Cataratta
Visita Cardiologica
Accesso PS
Dimissione Ospedaliera
```

Un evento possiede una data specifica.

---

### 7.14 Observation Series

Rappresenta una grandezza misurabile nel tempo.

Esempi:

```text
Peso
Pressione Arteriosa
Glicemia
HbA1c
Creatinina
```

La serie definisce:

* significato;
* unità di misura;
* tipo di valore.

---

### 7.15 Observation Point

Rappresenta una singola misurazione.

Esempio:

```text
Peso

2026-06-10
138.4 kg
```

oppure:

```text
Pressione

2026-05-03
135 / 82
```

---

### 7.16 Observation Campaign

Rappresenta un periodo di osservazione strutturata.

Esempi:

```text
Diario Pressorio
```

```text
Monitoraggio Peso Pre-Operatorio
```

```text
Monitoraggio Glicemico
```

Una campagna contiene molte osservazioni.

---

### 7.17 Differenza tra serie e campagna

Esempio:

```text
Serie:
Peso
```

esiste per tutta la vita del paziente.

Mentre:

```text
Campagna:
Monitoraggio Peso Pre-Operatorio
```

è limitata a uno specifico intervallo temporale.

---

### 7.18 Document Series

Rappresenta una successione di documenti omogenei.

Esempi:

```text
Analisi
Ecocardiogrammi
RMN Anca
```

Serve principalmente alla consultazione.

Non deve essere confusa con una Observation Series.

---

### 7.19 Source

Indica la provenienza di un'informazione.

Valori iniziali:

```text
manual
document
ai
import
```

---

#### manual

Inserita manualmente.

---

#### document

Derivata direttamente da un documento.

---

#### ai

Generata da un modello AI.

---

#### import

Importata da sorgenti esterne.

---

### 7.20 Provenienza

Ogni entità derivata deve registrare:

```text
source_type
source_reference
```

Esempio:

```text
source_type = document
source_reference = SHA256 documento
```

oppure:

```text
source_type = ai
source_reference = modello utilizzato
```

---

### 7.21 Confidence

Le entità generate automaticamente possono avere un livello di confidenza.

Intervallo:

```text
0.0 * 1.0
```

Esempio:

```text
0.95
```

indica alta probabilità di correttezza.

---

### 7.22 Stato di approvazione

Le entità derivate possono essere:

```text
proposed
approved
rejected
```

---

#### proposed

In attesa di revisione.

---

#### approved

Confermata.

---

#### rejected

Respinta.

---

### 7.23 Metadati curati

I metadati curati rappresentano la sorgente autorevole delle entità cliniche.

Essi hanno precedenza su:

* inferenze AI;
* estrazioni automatiche;
* euristiche.

---

### 7.24 Organizzazione dei metadati

I metadati curati non devono essere raccolti in un singolo file.

Devono essere organizzati per dominio funzionale.

Esempio:

```text
metadata/
│
├── problems.toml
├── allergies.toml
├── clinical_summary.toml
│
├── medications/
│
├── observations/
│
└── timeline/
```

---

### 7.25 Partizionamento temporale

Quando il volume dei dati cresce, i file possono essere suddivisi temporalmente.

Esempio:

```text
medications/
├── therapy_episodes_2012.toml
├── therapy_episodes_2013.toml
...
└── therapy_episodes_2026.toml
```

oppure:

```text
observations/
├── weight_2025.toml
├── weight_2026.toml
└── blood_pressure_2026.toml
```

---

### 7.26 Motivazione del partizionamento

Il partizionamento evita:

* file monolitici;
* merge difficili;
* revisioni complesse;
* degrado della leggibilità.

È particolarmente importante per archivi:

* pluridecennali;
* multi-paziente;
* ad alta frequenza di osservazione.

---

### 7.27 Evoluzione del modello

Nuove entità possono essere aggiunte senza modificare quelle esistenti.

Esempi futuri:

```text
Allergy
Procedure
Implant
Vaccination
Specialist
Healthcare Facility
```

## 8. Pipeline di Ingestione

### 8.1 Scopo

La Pipeline di Ingestione è responsabile della trasformazione dei documenti originali in informazioni strutturate utilizzabili dal resto del sistema.

La pipeline costituisce il punto di ingresso di tutti i dati presenti in SaniKey.

I suoi obiettivi sono:

* individuare i documenti;
* estrarre il contenuto;
* produrre metadati;
* costruire gli artefatti necessari alla consultazione;
* mantenere la coerenza tra repository, database e frontend.

---

### 8.2 Principi fondamentali

#### Incrementalità

La pipeline deve elaborare esclusivamente gli elementi modificati.

L'aggiunta di un nuovo documento non deve comportare la rielaborazione completa dell'archivio.

---

#### Determinismo

A parità di:

* documenti;
* configurazione;
* metadati curati;

la pipeline deve produrre risultati identici.

---

#### Ripetibilità

La pipeline deve poter essere eseguita più volte senza effetti collaterali.

---

#### Tracciabilità

Ogni informazione prodotta deve essere riconducibile alla propria origine.

---

### 8.3 Livelli della pipeline

La pipeline è organizzata in livelli successivi.

```text
Documenti Originali
        │
        ▼
Scansione
        │
        ▼
Identificazione
        │
        ▼
Estrazione Testo
        │
        ▼
OCR
        │
        ▼
Elaborazione DICOM
        │
        ▼
Metadati Derivati
        │
        ▼
Entità Cliniche
        │
        ▼
Database
        │
        ▼
Frontend
```

Ogni livello produce artefatti utilizzati dai livelli successivi.

---

### 8.4 Fase 1 * Scansione

La scansione individua i documenti presenti nelle directory sorgente.

Input:

```text
source_documents
```

Output:

```text
lista documenti
```

Per ogni file vengono rilevati:

* percorso;
* dimensione;
* timestamp;
* SHA256.

---

### 8.5 Fase 2 * Identificazione

Ogni documento viene identificato mediante hash.

```text
SHA256
```

L'identificazione serve per:

* rilevare modifiche;
* rilevare duplicati;
* preservare identità durante rinomina o spostamento.

---

### 8.6 Stati del documento

Un documento può trovarsi in uno dei seguenti stati.

```text
new
unchanged
modified
removed
```

---

#### new

Documento mai visto prima.

---

#### unchanged

Documento già noto e invariato.

---

#### modified

Documento esistente con hash differente.

---

#### removed

Documento precedentemente presente e successivamente eliminato.

---

### 8.7 Fase 3 * Parsing preliminare

La pipeline tenta di derivare:

* data;
* titolo;
* categoria;
* tipo documento.

dal nome file e dalla struttura directory.

Esempio:

```text
20240312 Analisi.pdf
```

produce:

```text
date = 2024-03-12
title = Analisi
```

---

### 8.8 Fase 4 * Estrazione PDF

I PDF vengono analizzati per determinare:

* presenza di testo;
* numero pagine;
* metadati disponibili.

Output:

```text
pdf_metadata
```

---

### 8.9 PDF con testo

Se il PDF contiene testo estraibile:

```text
PDF
    ↓
Text Extraction
```

non viene eseguito OCR.

---

### 8.10 PDF scansionato

Se il PDF non contiene testo:

```text
PDF
    ↓
OCR
```

la pipeline genera testo ricercabile.

---

### 8.11 Politica OCR

L'OCR viene eseguito esclusivamente quando necessario.

Motivazioni:

* tempi inferiori;
* minore occupazione disco;
* risultati più affidabili.

---

### 8.12 Cache OCR

I risultati OCR devono essere memorizzati.

La modifica di un documento invalida automaticamente la cache associata.

---

### 8.13 Fase 5 * Elaborazione DICOM

Gli archivi DICOM vengono analizzati separatamente quando è disponibile una
directory DICOM estratta.

Tipologie supportate:

```text
dicom_iso
dicom_archive
dicom_directory
```

---

### 8.14 Supporti DICOM originali

I supporti DICOM originali possono essere immagini ISO o archivi consegnati da
strutture sanitarie. Gli archivi sono classificati come DICOM solo in base al
contenuto, non al suffisso.

Il flusso operativo di espansione potrà essere definito in seguito scegliendo tra:

* espansione automatica;
* espansione opzionale durante l'ingestion;
* espansione manuale da parte dell'operatore.

Schema logico:

```text
ISO o ZIP
    ↓
Estrazione
    ↓
Analisi
```

Il supporto originale non viene modificato.

---

### 8.15 DICOMDIR

Se presente:

```text
DICOMDIR
```

viene utilizzato come sorgente primaria dei metadati.

---

### 8.16 Metadati DICOM

La pipeline tenta di estrarre:

* modalità;
* data esame;
* struttura;
* numero immagini;
* serie presenti.

---

### 8.17 Viewer DICOM

Se la ISO contiene un viewer:

```text
viewer.exe
viewer.app
```

l'informazione viene registrata come metadato.

---

### 8.18 Fase 6 * Metadati derivati

La pipeline costruisce i metadati documentali.

Esempi:

```text
data
titolo
categoria
tipo
serie documentale
```

Questi metadati sono rigenerabili.

---

### 8.19 Fase 7 * Classificazione serie documentali

I documenti vengono assegnati a una serie.

Esempio:

```text
Analisi
```

oppure:

```text
Ecocardiogramma
```

La classificazione può utilizzare:

* regole;
* alias;
* override manuali.

---

### 8.20 Fase 8 * Estrazione entità cliniche

La pipeline può estrarre:

* problemi clinici;
* farmaci;
* procedure;
* osservazioni;
* eventi.

Questa fase può utilizzare:

* regole;
* AI;
* entrambi.

---

### 8.21 Estrazione deterministica

Le regole deterministiche hanno priorità.

Esempi:

```text
data documento
categoria
titolo
```

---

### 8.22 Estrazione AI

L'AI viene utilizzata per:

* sintesi;
* classificazione;
* identificazione concetti clinici.

Le inferenze AI non sono considerate autorevoli fino all'approvazione.

---

### 8.23 Provenienza

Ogni entità derivata deve registrare:

```text
source_type
source_reference
```

---

### 8.24 Confidence

Le estrazioni automatiche possono includere:

```text
confidence
```

nell'intervallo:

```text
0.0 * 1.0
```

---

### 8.25 Fase 9 * Consolidamento

Le informazioni derivate vengono combinate con:

* metadati curati;
* override;
* correzioni manuali.

In caso di conflitto prevale sempre il dato curato.

---

### 8.26 Fase 10 * Persistenza

Le informazioni consolidate vengono scritte nel database SQLite.

La scrittura deve essere atomica.

---

### 8.27 Fase 11 * Generazione Timeline

A partire dalle entità consolidate vengono generati:

* eventi timeline;
* relazioni temporali;
* periodi terapeutici.

---

### 8.28 Fase 12 * Generazione Storia Clinica

La pipeline genera una proposta aggiornata di:

```text
clinical_summary
```

La proposta può essere revisionata dall'utente.

---

### 8.29 Fase 13 * Generazione Frontend

Vengono prodotti:

* JSON;
* HTML;
* asset statici.

---

### 8.30 Fase 14 * Costruzione Finale

La build finale produce l'archivio consultabile del paziente.

Output:

```text
generated/<patient>/
```

---

### 8.31 Modalità operative

La pipeline supporta:

```text
full
incremental
validation
```

---

#### full

Ricostruzione completa.

---

#### incremental

Aggiornamento incrementale dei passaggi costosi supportati. La build riusa il
testo estratto per documenti invariati e rigenera gli artefatti finali
dall'inventario corrente.

---

#### validation

Verifica senza modifica degli artefatti.

---

### 8.32 Gestione errori

Gli errori vengono classificati come:

```text
warning
error
fatal
```

---

#### Ingestion warning

L'elaborazione continua.

---

#### Ingestion error

Il documento viene escluso.

---

#### Ingestion fatal

La pipeline si interrompe.

---

### 8.33 Report finale

Ogni esecuzione produce un report contenente:

* documenti analizzati;
* documenti nuovi;
* documenti modificati;
* errori;
* warning;
* statistiche OCR;
* statistiche AI.

---

### 8.34 Logging

La pipeline deve produrre log strutturati.

I log devono consentire:

* audit;
* diagnostica;
* riproduzione problemi.

## 9. Database SQLite

### 9.1 Scopo

Il database SQLite rappresenta il modello persistente dell'archivio.

Costituisce il punto di convergenza di:

* documenti;
* metadati curati;
* metadati derivati;
* entità cliniche;
* timeline;
* ricerca.

Tutte le funzionalità di consultazione devono poter essere ricostruite a partire dal database e dai documenti originali.

---

### 9.2 Obiettivi

Il database deve:

* supportare archivi pluridecennali;
* supportare grandi quantità di documenti;
* supportare lunghi storici clinici
* consentire ricerca veloce;
* essere facilmente interrogabile;
* essere facilmente esportabile;
* rimanere comprensibile anche dopo molti anni.

---

### 9.3 Filosofia

SQLite viene utilizzato come:

```text
Single Source of Truth
degli artefatti generati
```

I documenti originali e i metadati curati rimangono comunque la sorgente autorevole primaria.

---

### 9.4 Database per paziente

Ogni paziente possiede un database indipendente.

Esempio:

```text
generated/patient-a/database/
└── medical_archive.db

generated/patient-b/database/
└── medical_archive.db
```

Lo stesso database viene successivamente esportato sulla chiavetta USB.

---

### 9.4.1 Ambito del database

Ogni database SQLite rappresenta un singolo paziente.

Non esistono database condivisi tra pazienti differenti.

Tutte le entità presenti nel database sono implicitamente riferite al paziente proprietario dell'archivio.

Di conseguenza non esistono tabelle:

* patients
* patient_documents
* patient_problems

poiché il paziente è già definito dal contesto del database stesso.

Esempio:

generated/patient-a/database/medical_archive.db

contiene esclusivamente dati relativi a Paziente A.

generated/patient-b/database/medical_archive.db

contiene esclusivamente dati relativi a Paziente B.

---

### 9.5 Motivazione

La separazione per paziente:

* semplifica backup;
* semplifica deploy;
* riduce complessità;
* evita contaminazioni accidentali.

---

### 9.6 Versionamento schema

Il database deve contenere una tabella:

```sql
schema_version
```

con:

* versione schema;
* data migrazione;
* versione SaniKey.

---

### 9.7 Convenzioni

#### Chiavi primarie

Tutte le entità principali utilizzano:

```sql
INTEGER PRIMARY KEY
```

come identificatore interno.

---

#### Identificatori esterni

Le entità persistenti utilizzano inoltre:

```text
stable_id
```

per riferimenti esterni.

---

#### Date

Le date vengono archiviate in formato:

```text
YYYY-MM-DD
```

---

#### Timestamp

I timestamp vengono archiviati in formato:

```text
ISO-8601 UTC
```

---

### 9.8 Tabella documents

Contiene i documenti originali.

Campi principali:

```text
id
sha256
relative_path
filename
document_date
title
category
document_type
file_size
created_at
updated_at
```

---

### 9.9 Tabella document_series

Definisce le serie documentali.

Esempi:

```text
Analisi
Ecocardiogrammi
RMN Anca
```

Campi:

```text
id
name
description
created_at
```

---

### 9.10 Tabella document_series_members

Relazione molti-a-molti.

```text
document
      ↔
document_series
```

---

### 9.11 Tabella document_relationships

Definisce relazioni documentali.

Tipi iniziali:

```text
same_study
supersedes
related
attachment
```

---

### 9.12 Tabella extracted_text

Contiene il testo estratto.

Campi:

```text
document_id
text
extraction_method
created_at
```

---

### 9.13 Tabella clinical_problems

Rappresenta i problemi clinici.

Campi principali:

```text
id
stable_id
name
status
source_type
source_reference
confidence
approved
created_at
updated_at
```

---

### 9.14 Tabella procedures

Rappresenta procedure e interventi.

Esempi:

```text
Gastroplastica verticale
Intervento cataratta
Protesi d'anca
```

Campi:

```text
id
stable_id
name
status
procedure_date
notes
source_type
source_reference
```

---

### 9.15 Relazione procedure-documenti

Una procedura può essere collegata a molti documenti.

Esempio:

```text
Intervento cataratta
        │
        ├── consenso informato
        ├── referto operatorio
        └── controllo post operatorio
```

Per questo motivo è necessaria una tabella ponte.

```text
procedure_documents
```

---

### 9.16 Tabella medications

Catalogo farmaci.

Campi:

```text
id
stable_id
name
atc_code
notes
```

---

### 9.17 Motivazione della separazione

Il farmaco:

```text
Metformina
```

non coincide con:

```text
Metformina 1000 mg
dal 2024 al 2026
```

La seconda informazione appartiene a un episodio terapeutico.

---

### 9.18 Tabella therapy_episodes

Campi:

```text
id
stable_id
medication_id
start_date
end_date
dosage
schedule
reason
status
source_type
source_reference
```

---

### 9.19 Relazione terapia-problema

Una terapia può essere collegata a:

* uno;
* molti;

problemi clinici.

Serve quindi una tabella:

```text
therapy_problem_links
```

---

### 9.20 Tabella clinical_events

Eventi puntuali.

Esempi:

```text
Accesso PS
Visita Cardiologica
Dimissione
```

Campi:

```text
id
stable_id
title
event_date
event_type
notes
source_type
source_reference
```

---

### 9.21 Tabella observation_series

Definizione delle serie osservative.

Esempi:

```text
Peso
Pressione
Glicemia
```

Campi:

```text
id
stable_id
name
unit
value_type
description
```

---

### 9.22 value_type

Valori iniziali:

```text
numeric
blood_pressure
text
categorical
```

---

### 9.23 Tabella observation_points

Contiene le misurazioni.

Campi comuni:

```text
id
series_id
observation_date
source_type
source_reference
```

Campi numerici:

```text
numeric_value
```

Campi pressione:

```text
systolic
diastolic
pulse
```

---

### 9.24 Motivazione

Non tutte le osservazioni sono scalari.

Esempio:

```text
Peso
→ 138.4
```

ma:

```text
Pressione
→ 135 / 82
```

richiede più valori.

---

### 9.25 Tabella observation_campaigns

Rappresenta campagne di monitoraggio.

Esempi:

```text
Diario pressorio
Monitoraggio peso
Monitoraggio glicemico
```

Campi:

```text
id
stable_id
title
start_date
end_date
description
```

---

### 9.26 Relazione campagna-osservazioni

Una campagna contiene molte osservazioni.

Serve una tabella:

```text
campaign_observations
```

---

### 9.27 Tabella timeline_events

Rappresenta gli eventi visualizzati nella timeline.

Attenzione:

```text
timeline_event
```

non è necessariamente:

```text
clinical_event
```

La timeline è una vista aggregata.

---

### 9.28 Motivazione

Un elemento timeline può derivare da:

* documento;
* procedura;
* terapia;
* osservazione;
* evento clinico.

---

### 9.29 Tabella timeline_events

Campi:

```text
id
event_date
title
event_type
source_table
source_id
importance
```

---

### 9.30 Tabella tags

Catalogo tag.

Esempi:

```text
Cardiologia
Diabete
Preoperatorio
Follow-up
```

---

### 9.31 Tabella document_tags

Relazione molti-a-molti.

```text
document
      ↔
tag
```

---

### 9.32 Tabella facilities

Strutture sanitarie.

Esempi:

```text
Ospedale Molinette
ASL Torino
```

---

### 9.33 Tabella specialists

Specialisti.

Esempi:

```text
Cardiologo
Ortopedico
Dermatologo
```

In questa fase non vengono memorizzati dati personali dettagliati.

---

### 9.34 Tabella attachments

Allegati generici.

Permette di collegare:

* immagini;
* documenti accessori;
* materiale aggiuntivo.

---

### 9.35 Full Text Search

La ricerca testuale utilizza:

```text
FTS5
```

---

### 9.36 Tabella FTS

Tabella virtuale:

```sql
documents_fts
```

Indicizza:

* titolo;
* categoria;
* testo OCR;
* testo PDF.

---

### 9.37 Ricerca semantica

Opzionale.

Le informazioni semantiche non vengono memorizzate in FTS.

---

### 9.38 Tabella embeddings

Campi:

```text
id
entity_type
entity_id
model
vector_hash
created_at
```

I vettori possono essere conservati:

* nel database;
* in file esterni.

La scelta verrà definita nel capitolo dedicato alla ricerca.

---

### 9.39 Provenienza

Le entità derivate devono registrare:

```text
source_type
source_reference
```

come definito nel Modello di Identità.

---

### 9.40 Approvazione

Le entità derivate possono registrare:

```text
approval_status
```

Valori:

```text
proposed
approved
rejected
```

---

### 9.41 Integrità referenziale

Le chiavi esterne devono essere abilitate.

```sql
PRAGMA foreign_keys = ON;
```

è obbligatorio.

---

### 9.42 Indici

Devono essere presenti almeno:

```text
documents.sha256
documents.document_date

clinical_problems.name

procedures.procedure_date

therapy_episodes.start_date

observation_points.observation_date

timeline_events.event_date
```

---

### 9.43 Migrazioni

Le migrazioni devono essere:

* incrementali;
* reversibili quando possibile;
* versionate.

---

### 9.44 Esportazione USB

Il database esportato sulla chiavetta è identico al database locale.

Non vengono effettuate trasformazioni.

---

### 9.45 Utilizzo sulla chiavetta

Il frontend non interroga direttamente SQLite.

Il database viene mantenuto per:

* diagnostica;
* verifiche;
* future evoluzioni;
* rigenerazione artefatti.

## 10. Metadati Curati

### 10.1 Scopo

I metadati curati costituiscono la sorgente autorevole delle informazioni strutturate presenti in SaniKey.

Essi rappresentano la conoscenza consolidata che non può essere derivata in modo affidabile dai documenti originali o che richiede validazione umana.

I metadati curati sono utilizzati per:

* classificazione;
* consolidamento;
* correzione;
* integrazione;
* contestualizzazione.

Tutti gli artefatti generati dal sistema devono derivare dai documenti originali e dai metadati curati.

---

### 10.2 Posizione nell'architettura

I metadati curati occupano una posizione centrale.

```text
Documenti Originali
         │
         ▼
 Pipeline di Ingestione
         │
         ▼
  Proposte AI
         │
         ▼
 Revisione Umana
         │
         ▼
 Metadati Curati
         │
         ▼
 Database SQLite
         │
         ▼
 Timeline
         │
         ▼
 Frontend
```

---

### 10.3 Sorgente autorevole

Per tutto il sistema valgono le seguenti priorità.

```text
1. Documenti originali

2. Metadati curati

3. Informazioni derivate

4. Informazioni AI
```

In caso di conflitto prevale sempre il livello superiore.

---

### 10.4 Obiettivi

I metadati curati devono consentire:

* correzione delle inferenze automatiche;
* integrazione delle informazioni mancanti;
* normalizzazione dei dati;
* consolidamento delle informazioni cliniche;
* gestione di dati non presenti nei documenti.

---

### 10.5 Formato

Tutti i metadati curati sono conservati in formato TOML.

Motivazioni:

* sintassi rigorosa;
* leggibilità;
* assenza di problemi di indentazione;
* facilità di validazione;
* compatibilità con il controllo versione.

---

### 10.6 Organizzazione

I metadati non devono essere raccolti in un singolo file.

Devono essere organizzati per dominio funzionale.

Esempio:

```text
metadata/
│
├── identity.toml
├── problems.toml
├── allergies.toml
├── clinical_summary.toml
│
├── medications/
│
├── observations/
│
├── timeline/
│
└── proposed/
```

---

### 10.7 identity.toml

Contiene le informazioni stabili del paziente.

Esempi:

* nome visualizzato;
* data di nascita;
* sesso;
* note permanenti.

Non deve contenere informazioni cliniche dinamiche.

---

### 10.8 problems.toml

Contiene i problemi clinici consolidati.

Esempio:

```toml
[[problem]]

id = "diabetes_t2"

name = "Diabete Tipo 2"

status = "active"

since = "2016-04-01"
```

I problemi clinici definiti qui sono considerati autorevoli.

---

### 10.9 allergies.toml

Contiene:

* allergie;
* intolleranze;
* reazioni avverse rilevanti.

Esempio:

```toml
[[allergy]]

substance = "Curcuma"

severity = "moderate"

status = "active"
```

---

### 10.10 clinical_summary.toml

Contiene la sintesi clinica consolidata.

Non deve essere generata automaticamente.

Può essere inizialmente proposta dall'AI ma deve essere revisionata.

La sintesi finale viene mantenuta manualmente.

Il campo `summary` supporta Markdown CommonMark. Durante la build SaniKey
genera HTML statico per la consultazione frontend e disabilita l'HTML grezzo
contenuto nel Markdown.

---

### 10.11 Directory medications

Contiene la storia terapeutica.

Esempio:

```text
medications/
│
├── catalog.toml
│
├── therapy_episodes_2015.toml
├── therapy_episodes_2016.toml
...
└── therapy_episodes_2030.toml
```

---

### 10.12 catalog.toml

Definisce i farmaci conosciuti.

Esempio:

```toml
[[drug]]

id = "metformin"

name = "Metformina"
```

---

### 10.13 Episodi terapeutici

Gli episodi terapeutici descrivono:

* inizio;
* fine;
* dosaggio;
* ruolo clinico o indicazione;
* schema di assunzione.

Esempio:

```toml
[[therapy]]
medication_id = "metformin"
start_date = "2024-01-01"
dosage = "1000 mg"
role = "antidiabetico"
schedule = ["mattino", "sera"]
```

L'identificativo dell'episodio è opzionale. Se fornito manualmente deve essere
univoco; se omesso viene generato dalla pipeline. Il ruolo clinico non è un
identificativo: più terapie possono condividere lo stesso ruolo.

---

### 10.14 Partizionamento temporale delle terapie

Gli episodi terapeutici possono coprire decenni.

Per questo motivo vengono partizionati temporalmente.

Obiettivi:

* mantenere file piccoli;
* semplificare manutenzione;
* migliorare leggibilità.

---

### 10.15 Directory observations

Contiene osservazioni longitudinali.

Esempio:

```text
observations/
│
├── series.toml
│
├── weight_2025.toml
├── weight_2026.toml
│
├── blood_pressure_2025.toml
└── blood_pressure_2026.toml
```

---

### 10.16 Serie osservative

Le serie definiscono:

* nome;
* unità;
* tipo.

Esempio:

```toml
[[series]]

id = "weight"

name = "Peso"

unit = "kg"
```

---

### 10.17 Punti osservativi

Esempio:

```toml
[[point]]

date = "2026-06-10"

value = 138.4
```

---

### 10.18 Osservazioni complesse

Alcune osservazioni richiedono più valori.

Esempio:

```toml
[[point]]

date = "2026-05-03"

systolic = 135

diastolic = 82

pulse = 74
```

---

### 10.19 Campagne osservative

Le campagne vengono definite separatamente.

Esempio:

```text
observations/
└── campaigns.toml
```

---

### 10.20 Esempio campagna

```toml
[[campaign]]

id = "bp_2026_05"

title = "Diario pressorio"

start_date = "2026-05-01"

end_date = "2026-05-07"
```

---

### 10.21 Directory timeline

Contiene dati cronologici mantenuti manualmente.

Esempio:

```text
timeline/
│
├── manual_events.toml
└── overrides.toml
```

---

### 10.22 Eventi manuali

Consentono di registrare eventi non documentati.

Esempi:

* cambio terapia;
* insorgenza sintomi;
* informazioni storiche.

---

### 10.23 Override timeline

Consentono di:

* correggere titoli;
* correggere date;
* modificare importanza;
* sopprimere eventi generati.

---

### 10.24 Document tags

I tag manuali sono conservati in:

```text
document_tags.toml
```

---

### 10.25 Scopo dei tag

I tag consentono:

* classificazione trasversale;
* ricerca;
* navigazione.

Esempi:

```text
Cardiologia
Diabete
Preoperatorio
Follow-up
```

---

### 10.26 Alias

Gli alias documentali sono conservati in:

```text
aliases.toml
```

Consentono la normalizzazione.

---

### 10.27 Directory proposed

Contiene esclusivamente proposte.

Esempio:

```text
proposed/
│
├── problems.toml
├── procedures.toml
├── therapies.toml
├── observations.toml
└── timeline.toml
```

---

### 10.28 Stato delle proposte

Le proposte non sono autorevoli.

Possono essere:

* approvate;
* rifiutate;
* archiviate.

---

### 10.29 Promozione

La promozione trasferisce una proposta nella corrispondente area curata.

Esempio:

```text
proposed/problems.toml

        ↓

problems.toml
```

---

### 10.30 Provenienza

Ogni elemento curato può registrare:

```text
source_type

source_reference
```

per mantenere la tracciabilità.

---

### 10.31 Validazione

I metadati devono essere validati.

Controlli minimi:

* sintassi TOML;
* riferimenti esistenti;
* date valide;
* identificatori univoci.

I controlli sui metadati curati devono avvenire in `validate-config` e, per i
pazienti selezionati, anche prima di `scan-documents`, in modo da intercettare
errori bloccanti prima di una build lunga.

---

### 10.32 Errori

Errori nei metadati curati sono considerati fatali.

La pipeline deve interrompersi.

---

### 10.33 Backup

I metadati curati devono essere inclusi nei backup.

Essi rappresentano il patrimonio informativo più prezioso del sistema dopo i documenti originali.

---

### 10.34 Rigenerabilità

I metadati curati non sono rigenerabili.

Devono essere preservati.

Tutti gli altri artefatti possono essere ricostruiti a partire da:

* documenti originali;
* metadati curati.

---

### 10.35 Evoluzione

Nuovi domini possono essere aggiunti senza modificare quelli esistenti.

Esempi futuri:

```text
vaccinations/
implants/
devices/
rehabilitation/
```

## 11. Generazione e Assistenza AI

### 11.1 Scopo

I componenti AI di SaniKey hanno lo scopo di ridurre il lavoro manuale necessario alla costruzione e manutenzione dell'archivio.

L'AI viene utilizzata esclusivamente durante la fase di build.

Nessun componente AI è richiesto durante la consultazione della chiavetta USB.

---

### 11.2 Principi fondamentali

#### Assistenza e non automazione

L'AI assiste l'utente.

Non sostituisce il controllo umano.

---

#### Nessuna autorità clinica

Le informazioni prodotte dall'AI non sono considerate clinicamente autorevoli.

L'autorità finale appartiene sempre:

* ai documenti originali;
* ai metadati curati.

---

#### Riproducibilità

Ogni informazione generata deve essere tracciabile.

Il sistema deve registrare:

* modello utilizzato;
* versione;
* data generazione;
* prompt o strategia utilizzata.

---

#### Separazione delle responsabilità

L'AI può proporre.

Non può approvare.

---

### 11.3 Ambiti di utilizzo

L'AI può essere utilizzata per:

* estrazione di entità;
* consolidamento informazioni;
* sintesi cliniche;
* classificazione documentale;
* generazione timeline;
* ricerca semantica.

---

### 11.4 Estrazione di entità

L'AI può proporre:

* problemi clinici;
* farmaci;
* procedure;
* specialisti;
* strutture sanitarie;
* osservazioni cliniche.

Esempio:

```text id="b8v8wv"
Documento

Referto diabetologico

        ↓

Problema clinico

Diabete Tipo 2
```

---

### 11.5 Consolidamento

L'AI può aggregare informazioni provenienti da documenti differenti.

Esempio:

```text id="n2hztw"
15 documenti

        ↓

Problema clinico consolidato

Ipertensione arteriosa
```

---

### 11.6 Sintesi clinica

L'AI può generare:

* storia clinica generale;
* sintesi specialistiche;
* riassunti temporali;
* panoramiche terapeutiche.

Tali sintesi sono sempre considerate bozze.

---

### 11.7 Classificazione

L'AI può proporre:

* tag;
* serie documentali;
* collegamenti tra documenti;
* relazioni cliniche.

---

### 11.8 Generazione Timeline

L'AI può suggerire:

* eventi clinici;
* procedure;
* inizio o fine terapie;
* campagne osservative.

Gli eventi proposti richiedono approvazione.

---

### 11.9 Ricerca semantica

L'AI può generare:

* embeddings;
* rappresentazioni vettoriali;
* collegamenti semantici.

La ricerca semantica è opzionale.

---

### 11.10 Attività proibite

L'AI non può:

* modificare documenti originali;
* eliminare documenti;
* modificare metadati approvati;
* approvare modifiche;
* eliminare eventi timeline approvati;
* alterare dati clinici curati.

---

### 11.11 Modello di approvazione

Tutte le informazioni generate dall'AI seguono il medesimo ciclo di vita.

```text id="o6w8yr"
AI
 │
 ▼
Proposta
 │
 ▼
Revisione umana
 │
 ├── Approvazione
 │
 └── Rifiuto
```

---

### 11.12 Nessuna scrittura diretta

Le proposte AI non vengono scritte direttamente nei metadati curati.

Le proposte vengono memorizzate separatamente.

---

### 11.13 Directory delle proposte

Ogni paziente possiede una directory dedicata.

Esempio:

```text id="i2m7xh"
metadata_directory/
└── patient-a/
    └── metadata/
        └── proposed/
```

---

### 11.14 Struttura delle proposte

Esempio:

```text id="g8z6dj"
proposed/
│
├── problems.toml
├── procedures.toml
├── therapies.toml
├── observations.toml
└── timeline.toml
```

---

### 11.15 Motivazione

Le proposte devono essere:

* leggibili;
* versionabili;
* revisionabili;
* confrontabili.

I file TOML soddisfano questi requisiti.

---

### 11.16 Promozione delle proposte

Una proposta approvata viene trasferita nei metadati curati.

Esempio:

```text id="2s1e6h"
proposed/problems.toml

        ↓

metadata/problems.toml
```

La promozione può essere:

* manuale;
* assistita da script.

---

### 11.17 Rifiuto delle proposte

Una proposta rifiutata:

* non viene cancellata immediatamente;
* può essere archiviata;
* può essere utilizzata per audit.

---

### 11.18 Provenienza

Ogni proposta deve registrare:

```text id="6wwk7w"
source_type
source_reference
model
generated_at
```

---

### 11.19 Confidence

Ogni proposta può contenere:

```text id="6bztjt"
confidence
```

nell'intervallo:

```text id="q7k7bh"
0.0 * 1.0
```

La confidence non sostituisce la revisione umana.

---

### 11.20 Cache AI

Le elaborazioni AI possono essere costose.

Per questo motivo il sistema mantiene una cache.

---

### 11.21 Directory cache

```text id="wwly4s"
generated/
└── <patient>/
    └── ai/
```

---

### 11.22 Contenuto della cache

La cache può contenere:

* estrazioni;
* sintesi;
* classificazioni;
* embeddings;
* risultati intermedi.

---

### 11.23 Invalidazione

La cache deve essere invalidata quando cambia:

* documento sorgente;
* metadato curato rilevante;
* configurazione AI;
* modello AI.

---

### 11.24 Modalità AI

Il sistema supporta due modalità.

---

#### AI Locale

Modelli eseguiti localmente.

Esempi:

* Ollama;
* llama.cpp;
* vLLM locale.

---

#### AI Remota

Servizi esterni.

Esempi:

* OpenAI;
* Anthropic;
* altri provider compatibili.

---

### 11.25 Modalità offline

Tutte le funzionalità fondamentali del sistema devono continuare a funzionare anche in assenza di AI.

---

### 11.26 Rigenerazione

Gli artefatti AI sono considerati rigenerabili.

La loro eliminazione non deve comportare perdita di informazioni curate.

---

### 11.27 Auditabilità

Il sistema deve consentire di rispondere alle seguenti domande:

```text id="s18xsn"
Perché questa informazione esiste?

Da quale documento deriva?

Quale modello l'ha generata?

Quando è stata approvata?
```

---

### 11.28 Versionamento modelli

Le informazioni generate devono registrare:

* nome modello;
* versione modello;
* configurazione significativa.

---

### 11.29 Gestione errori

Errori AI non devono interrompere le funzionalità fondamentali.

In caso di errore:

* la pipeline continua;
* la funzionalità AI viene segnalata come fallita;
* il report finale registra il problema.

---

### 11.30 Qualità delle proposte

Il sistema deve privilegiare:

* precisione;
* spiegabilità;
* tracciabilità;

rispetto alla quantità di proposte generate.

## 12. Ricerca

### 12.1 Scopo

Il sistema di ricerca costituisce il principale meccanismo di accesso alle informazioni contenute nell'archivio.

L'obiettivo è consentire al medico di individuare rapidamente:

* documenti;
* eventi clinici;
* procedure;
* terapie;
* osservazioni;
* problemi clinici;

senza dover conoscere la struttura dell'archivio.

---

### 12.2 Principi fondamentali

#### Immediatezza

Le ricerche devono produrre risultati in tempi percepiti come istantanei.

Obiettivo:

```text
< 1 secondo
```

per archivi completi pluridecennali.

---

#### Tolleranza alla struttura

L'utente non deve conoscere:

* categorie;
* percorsi;
* nomi file.

La ricerca deve funzionare principalmente sul contenuto.

---

#### Tracciabilità dei risultati

Ogni risultato deve consentire di risalire al documento originale.

---

#### Degrado controllato della ricerca

La ricerca lessicale deve funzionare anche in assenza di:

* embeddings;
* AI;
* ricerca semantica.

---

### 12.3 Architettura della ricerca

Il sistema è composto da due livelli indipendenti.

```text
Ricerca
│
├── Ricerca Lessicale
│
└── Ricerca Semantica (opzionale)
```

---

### 12.4 Ricerca lessicale

La ricerca lessicale è obbligatoria.

È implementata tramite:

```text
SQLite FTS5
```

ed è disponibile in qualunque installazione di SaniKey.

---

### 12.5 Ambito della ricerca lessicale

La ricerca lessicale indicizza:

* titolo documento;
* categoria;
* testo PDF;
* testo OCR;
* tag;
* nomi procedure;
* problemi clinici;
* farmaci;
* specialisti;
* strutture sanitarie.

---

### 12.6 Obiettivo della ricerca lessicale

La ricerca lessicale deve essere sufficiente per la maggior parte dei casi d'uso.

Esempi:

```text
diabete
```

```text
cataratta
```

```text
ramipril
```

```text
pressione
```

```text
molinette
```

---

### 12.7 Ricerca semantica

La ricerca semantica è opzionale.

Utilizza:

* embeddings;
* similarità vettoriale;
* classificazione semantica.

La sua assenza non deve compromettere il funzionamento del sistema.

---

### 12.8 Motivazione

Molti medici formulano ricerche semplici.

Esempio:

```text
diabete
```

oppure:

```text
ecocardiogramma
```

La ricerca lessicale è generalmente sufficiente.

La ricerca semantica è utile soprattutto quando:

* la terminologia varia;
* il documento utilizza sinonimi;
* l'utente non ricorda il termine esatto.

---

### 12.9 Tipologie di ricerca

Il sistema supporta:

```text
simple
advanced
semantic
```

---

### 12.10 Ricerca semplice

Consiste in una singola casella di ricerca federata sui dati immediatamente
disponibili nel frontend.

Esempio:

```text
semaglutide
```

Il sistema restituisce risultati raggruppati per sezione: documenti, terapie,
farmaci, problemi, procedure, osservazioni, studi DICOM e timeline quando
applicabile. In testa ai risultati sono presenti link alle sezioni con conteggi.

---

### 12.11 Ricerca avanzata

Permette di cercare nel contenuto estratto dai documenti, nei metadati clinici
curati e di applicare filtri.
La consultazione offline espone la ricerca avanzata come sezione distinta dalla
ricerca semplice sui metadati documentali.

Esempi:

* testo OCR o testo PDF estratto;
* query booleane con `AND`, `OR`, `NOT` e parentesi;
* frasi tra virgolette;
* sinonimi e normalizzazioni configurabili;
* intervallo temporale;
* categoria;
* tipo documento;
* serie documentale;
* problema clinico;
* procedura.

---

### 12.12 Ricerca per periodo

Esempi:

```text
2024
```

```text
2024-01-01 → 2024-12-31
```

---

### 12.13 Ricerca per categoria

Esempio:

```text
Cardiologo
```

oppure:

```text
Analisi
```

Le categorie disponibili dipendono dall'archivio del paziente.

---

### 12.14 Ricerca per problema clinico

Esempi:

```text
OSAS
```

```text
Obesità
```

```text
Diabete Tipo 2
```

---

### 12.15 Ricerca per procedura

Esempi:

```text
Cataratta
```

```text
Protesi anca
```

```text
Gastroplastica
```

---

### 12.16 Ricerca per farmaco

Esempi:

```text
Metformina
```

```text
Ramipril
```

```text
Bisoprololo
```

---

### 12.17 Ricerca per osservazione

Esempi:

```text
Peso
```

```text
Pressione
```

```text
HbA1c
```

---

### 12.18 Ranking

I risultati devono essere ordinati secondo un punteggio di rilevanza.

Fattori iniziali:

* corrispondenza esatta;
* frequenza;
* vicinanza;
* tipo di entità.

---

### 12.19 Priorità delle corrispondenze

Ordine preferenziale:

```text
Titolo documento

Problema clinico

Procedura

Farmaco

Tag

Testo documento
```

---

### 12.20 Evidenziazione

I risultati devono evidenziare i termini trovati.

Esempio:

```text
... paziente affetto da [DIABETE] tipo 2 ...
```

---

### 12.21 Snippet

Ogni risultato deve mostrare un estratto contestuale.

Esempio:

```text
... aumento della terapia per diabete ...
```

---

### 12.22 Navigazione dei risultati

Ogni risultato deve permettere:

* apertura documento;
* apertura scheda documento;
* apertura evento timeline correlato.

---

### 12.23 Ricerca federata

Una singola ricerca deve interrogare simultaneamente:

* documenti;
* procedure;
* problemi clinici;
* terapie;
* osservazioni.

---

### 12.24 Gruppi di risultati

I risultati possono essere raggruppati per tipo.

Esempio:

```text
Documenti (12)

Problemi Clinici (2)

Procedure (1)

Farmaci (3)
```

---

### 12.25 Ricerca semantica: principi

La ricerca semantica opera esclusivamente su artefatti precomputati.

Durante la consultazione non devono essere generati embeddings.

---

### 12.26 Generazione embeddings

Gli embeddings vengono generati durante la pipeline di build.

Input possibili:

* documenti;
* sintesi cliniche;
* procedure;
* problemi clinici.

---

### 12.27 Cache embeddings

Gli embeddings devono essere riutilizzati quando possibile.

La rigenerazione completa deve essere evitata.

---

### 12.28 Ricerca semantica e privacy

La ricerca semantica deve poter operare:

* completamente offline;
* con modelli locali.

L'utilizzo di servizi remoti è opzionale.

---

### 12.29 Ricerca nella timeline

La timeline deve essere interrogabile.

Esempi:

```text
cataratta
```

```text
ramipril
```

```text
pressione
```

devono evidenziare anche gli eventi cronologici pertinenti.

---

### 12.30 Ricerca nelle osservazioni

Le osservazioni devono supportare ricerche per:

* tipo;
* intervallo temporale;
* intervallo valori.

Esempi:

```text
peso > 140 kg
```

```text
pressione sistolica > 150
```

Queste ricerche sono considerate funzionalità avanzate.

---

### 12.31 Ricerca nelle terapie

Le terapie devono poter essere ricercate sia per:

* farmaco;
* dosaggio;
* periodo.

Esempi:

```text
semaglutide
```

```text
ramipril 10 mg
```

---

### 12.32 Ricerca nelle procedure

Le procedure devono poter essere ricercate indipendentemente dai documenti associati.

Esempio:

```text
protesi anca
```

deve restituire:

* procedura;
* documenti correlati;
* eventi timeline correlati.

---

### 12.33 Ricerca e metadati curati

I metadati curati devono essere indicizzati.

Ciò include:

* tag;
* problemi clinici;
* procedure;
* osservazioni;
* terapie.

---

### 12.34 Ricerca e dati proposti

Per impostazione predefinita:

```text
approved only
```

Le proposte AI non approvate non devono comparire nei risultati.

---

### 12.35 Modalità esperto

Una modalità avanzata può consentire la visualizzazione anche di:

```text
proposed
```

e

```text
rejected
```

per attività di manutenzione.

---

### 12.36 Compatibilità browser

La ricerca deve funzionare:

* offline;
* senza backend;
* tramite frontend statico.

---

### 12.37 Evoluzioni future

Possibili estensioni:

* ricerca per linguaggio naturale;
* ricerca conversazionale;
* interrogazione RAG locale;
* ricerca multimodale.

Tali funzionalità non fanno parte della versione iniziale.

## 13. Timeline Clinica

### 13.1 Scopo

La Timeline Clinica rappresenta la vista cronologica unificata della storia sanitaria del paziente.

Il suo obiettivo è consentire una comprensione rapida dell'evoluzione clinica senza richiedere la lettura sequenziale dei documenti.

La timeline deve integrare:

* documenti;
* eventi clinici;
* procedure;
* terapie;
* campagne osservative;
* osservazioni rilevanti;
* eventi manuali.

---

### 13.2 Principi fondamentali

#### Centralità del tempo

Ogni elemento visualizzato nella timeline deve possedere una collocazione temporale esplicita.

---

#### Origine tracciabile

Ogni elemento deve essere riconducibile a:

* documento;
* metadato curato;
* proposta AI approvata.

---

#### Vista aggregata

La timeline non costituisce una sorgente autorevole.

È una vista derivata costruita a partire da:

* database;
* documenti;
* metadati curati.

---

#### Consultazione rapida

La timeline deve privilegiare:

* leggibilità;
* orientamento temporale;
* navigazione.

---

### 13.3 Tipologie di elementi

La timeline supporta due categorie fondamentali.

```text id="c4f4m8"
Eventi Puntuali

Intervalli Temporali
```

---

### 13.4 Eventi puntuali

Un evento puntuale possiede una singola data.

Esempi:

```text id="9ozrhe"
Visita cardiologica

Accesso PS

Intervento cataratta

Referto RMN

Dimissione ospedaliera
```

---

### 13.5 Intervalli temporali

Un intervallo possiede:

```text id="5s4m4e"
data inizio

data fine
```

Esempi:

```text id="0jsywk"
Terapia farmacologica

Diario pressorio

Monitoraggio peso

Attesa intervento
```

---

### 13.6 Motivazione

Una storia clinica contiene numerosi elementi che non possono essere rappresentati come semplici eventi puntuali.

Esempio:

```text id="s33nqn"
Semaglutide

01/01/2025
→
in corso
```

oppure:

```text id="6c4zhw"
Diario pressorio

01/05/2026
→
07/05/2026
```

---

### 13.7 Fonti timeline

Gli elementi timeline possono derivare da:

```text id="9s6k4m"
documents

clinical_events

procedures

therapy_episodes

observation_campaigns

manual_events
```

---

### 13.8 Priorità delle fonti

Ordine di affidabilità:

```text id="0o9m6f"
Metadati Curati

Documenti Originali

Informazioni Derivate

AI Approvata
```

---

### 13.9 Eventi documentali

Ogni documento può generare un evento timeline.

Esempio:

```text id="1k7s8m"
2024-03-12 Analisi.pdf
```

produce:

```text id="m6d6q5"
12 marzo 2024

Analisi
```

---

### 13.10 Eventi clinici

Gli eventi clinici generano direttamente elementi timeline.

Esempio:

```text id="g4f7c5"
Visita Cardiologica
```

---

### 13.11 Procedure

Le procedure devono avere una rappresentazione dedicata.

Esempio:

```text id="z8z4s7"
Intervento Cataratta
```

La procedura deve essere distinguibile visivamente dagli altri eventi.

---

### 13.12 Terapie

Le terapie vengono rappresentate come intervalli.

Esempio:

```text id="4e0q9j"
Ramipril

2020-05-01
→
2024-11-30
```

---

### 13.13 Terapie attive

Le terapie prive di data fine sono considerate attive.

Esempio:

```text id="8u9r8v"
Semaglutide

2025-03-01
→
In Corso
```

---

### 13.14 Campagne osservative

Le campagne vengono rappresentate come intervalli.

Esempio:

```text id="7n9d2r"
Diario Pressorio

01/05/2026
→
07/05/2026
```

---

### 13.15 Osservazioni rilevanti

La timeline può mostrare osservazioni particolarmente significative.

Esempi:

```text id="1j0o4m"
Peso minimo

Peso massimo

HbA1c elevata

Valore creatinina critico
```

La selezione avviene tramite regole configurabili.

---

### 13.16 Eventi manuali

L'utente può inserire eventi non derivabili dai documenti.

Esempi:

```text id="w5t5s8"
Inizio sintomatologia

Cambio stile alimentare

Sospensione volontaria terapia
```

---

### 13.17 Importanza

Ogni elemento può possedere un livello di importanza.

Valori iniziali:

```text id="6r2d0e"
low

normal

high

critical
```

---

### 13.18 Utilizzo dell'importanza

L'importanza può influenzare:

* evidenziazione;
* ordinamento;
* filtri;
* visualizzazione.

---

### 13.19 Collegamenti

Ogni elemento timeline deve poter aprire:

* documento sorgente;
* scheda procedura;
* scheda terapia;
* scheda osservazione.

---

### 13.20 Eventi composti

Più documenti possono contribuire allo stesso evento.

Esempio:

```text id="8u5u7w"
Protesi Anca

├── prenotazione
├── ricovero
├── intervento
└── dimissione
```

---

### 13.21 Aggregazione

La timeline può raggruppare eventi molto vicini temporalmente.

Esempio:

```text id="7s6v7p"
Controlli preoperatori
```

anziché mostrare decine di documenti consecutivi.

---

### 13.22 Vista cronologica

La vista predefinita è:

```text id="2j6m7e"
dal più recente
al più remoto
```

---

### 13.23 Vista storica

Deve essere disponibile anche una vista:

```text id="9j0s7e"
dal più remoto
al più recente
```

---

### 13.24 Filtri

La timeline deve supportare filtri per:

* periodo;
* categoria;
* problema clinico;
* procedura;
* terapia;
* importanza.

---

### 13.25 Zoom temporale

La timeline deve consentire diversi livelli di dettaglio.

Esempi:

```text id="4n7x8v"
Anno

Mese

Settimana

Giorno
```

---

### 13.26 Eventi senza data

Gli eventi privi di data certa non devono essere eliminati.

Possono essere collocati in una sezione:

```text id="0k6m4j"
Data Incerta
```

---

### 13.27 Correzioni manuali

La posizione timeline di un elemento può essere corretta tramite override.

I dati corretti prevalgono sui dati derivati.

---

### 13.28 Generazione

La timeline viene generata durante la pipeline di build.

Non richiede elaborazioni AI durante la consultazione.

---

### 13.29 Rigenerabilità

La timeline è completamente rigenerabile.

Può essere ricostruita a partire da:

* documenti;
* database;
* metadati curati.

---

### 13.30 Compatibilità offline

La timeline deve funzionare:

* offline;
* senza backend;
* tramite frontend statico.

---

### 13.31 Auditabilità

Per ogni elemento deve essere possibile determinare:

```text id="3v8n9w"
Origine

Data

Motivazione

Documenti correlati
```

---

### 13.32 Evoluzioni future

Possibili estensioni:

* timeline comparativa tra periodi;
* correlazione eventi-osservazioni;
* visualizzazione grafica delle terapie;
* sovrapposizione di campagne osservative.

## 14. Frontend

### 14.1 Scopo

Il Frontend costituisce l'interfaccia utente utilizzata dal medico e dal paziente per consultare l'archivio sanitario.

Deve consentire:

* consultazione documentale;
* ricerca;
* navigazione timeline;
* accesso alle informazioni cliniche consolidate;
* apertura dei documenti originali.

Il frontend è completamente statico.

Non richiede:

* installazione;
* backend;
* connessione Internet;
* privilegi amministrativi.

---

### 14.2 Principi fondamentali

#### Portabilità

Il frontend deve funzionare direttamente dalla chiavetta USB.

---

#### Offline First

Tutte le funzionalità devono essere disponibili senza accesso alla rete.

---

#### Installazione Zero

L'utente deve poter utilizzare il sistema semplicemente aprendo:

```text
index.html
```

---

#### Longevità

Il frontend deve rimanere utilizzabile per molti anni.

Le tecnologie adottate devono privilegiare:

* stabilità;
* standard aperti;
* compatibilità futura.

---

### 14.3 Architettura

Il frontend è composto esclusivamente da risorse statiche.

```text
web/
│
├── index.html
├── assets/
├── data/
├── js/
└── css/
```

Non sono previsti:

* server HTTP;
* API remote;
* servizi cloud.

---

### 14.3.1 Modello dati del frontend

Il frontend non interroga direttamente il database SQLite.

Durante la build, i dati necessari alla consultazione vengono esportati in file JSON statici ottimizzati per l'interfaccia.

Il database SQLite viene comunque copiato sulla chiavetta USB come artefatto tecnico per:

* diagnostica;
* verifica;
* audit;
* future evoluzioni;
* rigenerazione degli indici in caso di necessità.

La consultazione ordinaria utilizza esclusivamente:

```text id="m5f4zr"
HTML
CSS
JavaScript
JSON statici
documenti originali
```

Questa scelta evita dipendenze da SQLite WASM, riduce la complessità del frontend e migliora la compatibilità con browser eseguiti direttamente da file system locale.

---

### 14.4 Tecnologie

Versione iniziale:

```text
HTML5

CSS3

JavaScript ES2020+
```

Dipendenze esterne ridotte al minimo.

---

### 14.5 Compatibilità browser

Browser supportati:

* Google Chrome
* Microsoft Edge
* Mozilla Firefox
* Safari

Non è richiesto il supporto di browser obsoleti.

---

### 14.6 Modalità di esecuzione

Il frontend deve poter essere aperto tramite:

```text
file://
```

senza richiedere un web server locale.

---

### 14.7 Multi-paziente

La chiavetta può contenere più archivi indipendenti.

Esempio:

```text
index.html
```

La pagina root rappresenta il punto di ingresso della consultazione e indirizza
al frontend del paziente selezionato.

---

### 14.8 Isolamento

Il frontend di un paziente non deve accedere ai dati di altri pazienti.

Ogni archivio viene generato in modo indipendente.

---

### 14.9 Pagina Iniziale

La schermata iniziale deve mostrare:

* dati identificativi essenziali;
* riepilogo clinico;
* accesso alla ricerca;
* accesso alla timeline;
* accesso ai documenti.

---

### 14.10 Dashboard Clinica

La dashboard rappresenta una sintesi ad alto livello.

Contenuti tipici:

* problemi clinici attivi;
* terapie attive;
* procedure rilevanti;
* ultime visite;
* documenti recenti.

---

### 14.11 Ricerca

La ricerca deve essere accessibile da qualsiasi schermata.

La casella di ricerca costituisce il principale strumento di navigazione.

---

### 14.12 Risultati della ricerca

Per ogni risultato devono essere mostrati:

* titolo;
* data;
* categoria;
* estratto contestuale;
* collegamenti correlati.

---

### 14.13 Scheda documento

Ogni documento possiede una pagina dedicata.

Informazioni visualizzate:

* titolo;
* data;
* categoria;
* tag;
* testo estratto;
* collegamenti.

---

### 14.14 Apertura documenti

L'utente deve poter aprire il documento originale.

Esempio:

```text
Apri PDF originale
```

---

### 14.15 Navigazione documentale

La consultazione deve supportare:

* categorie;
* serie documentali;
* tag;
* ricerca.

---

### 14.16 Timeline

La timeline deve essere accessibile come sezione principale.

Deve supportare:

* eventi;
* intervalli;
* filtri;
* ricerca.

---

### 14.17 Visualizzazione intervalli

Gli intervalli devono essere distinguibili dagli eventi puntuali.

Esempi:

```text
Terapie

Campagne osservative

Periodi di monitoraggio
```

---

### 14.18 Scheda problema clinico

Per ogni problema clinico devono essere visualizzati:

* descrizione;
* stato;
* documenti correlati;
* terapie correlate;
* eventi correlati.

---

### 14.19 Scheda terapia

Per ogni terapia devono essere visualizzati:

* farmaco;
* dosaggio;
* periodo;
* motivazione;
* documenti correlati.

---

### 14.20 Scheda procedura

Per ogni procedura devono essere visualizzati:

* data;
* stato;
* documenti correlati;
* follow-up.

---

### 14.21 Osservazioni

Le osservazioni devono poter essere consultate sia in forma tabellare sia grafica.

Esempi:

```text
Peso

Pressione

Glicemia
```

---

### 14.22 Grafici

I grafici devono essere generati localmente.

Non devono dipendere da servizi esterni.

---

### 14.23 Campagne osservative

Le campagne devono essere consultabili separatamente.

Esempio:

```text
Diario Pressorio

01/05/2026
→
07/05/2026
```

---

### 14.24 Tag

I tag devono essere cliccabili.

La selezione di un tag deve mostrare:

* documenti correlati;
* procedure correlate;
* eventi correlati.

---

### 14.25 Accesso ai DICOM

Quando disponibile, il frontend deve consentire l'accesso rapido agli studi
diagnostici. La sezione clinica `Studi DICOM` mostra gli studi aggregati e
preferisce il viewer HTML esportato. Supporti, file tecnici e singole istanze
non devono comparire come documenti clinici ordinari. Uno studio catalogato
senza viewer HTML deve restare visibile come anomalia da verificare.

---

### 14.26 Studi diagnostici

Per uno studio diagnostico devono essere mostrati:

* referto PDF;
* supporto DICOM;
* eventuali note.

---

### 14.27 Viewer DICOM

Se il supporto diagnostico contiene un viewer fornito dalla struttura sanitaria, il frontend deve consentirne l'avvio.

Esempio:

```text
Apri Viewer Diagnostico
```

---

### 14.28 Assenza del viewer

L'assenza del viewer non deve compromettere la consultazione del referto associato.

---

### 14.29 Accessibilità

Il frontend deve privilegiare:

* caratteri leggibili;
* elevato contrasto;
* navigazione semplice;
* interfaccia non tecnica.

---

### 14.30 Stampa

Le principali schermate devono essere stampabili.

Esempi:

* riepilogo clinico;
* timeline;
* elenco terapie.

---

### 14.31 Responsività

Il frontend deve funzionare su:

* desktop;
* notebook;
* tablet.

Il desktop rimane il caso d'uso principale.

---

### 14.32 Gestione errori

Gli errori devono essere comprensibili.

Esempi:

```text
Documento non disponibile

Viewer DICOM non trovato

Indice ricerca non disponibile
```

---

### 14.33 Nessuna dipendenza cloud

Il frontend non deve effettuare chiamate verso:

* servizi AI;
* CDN;
* servizi di telemetria;
* servizi di analytics.

---

### 14.34 Modalità sola lettura

La chiavetta USB è considerata un supporto di sola consultazione.

Durante l'uso da parte del medico il frontend non deve scrivere:

* file;
* database;
* cache;
* log;
* preferenze utente;
* cronologia ricerche.

Anche la ricerca deve operare esclusivamente su indici pre-generati durante la build.

Non sono consentite indicizzazioni in tempo reale sulla chiavetta.

Questa scelta garantisce che il contenuto distribuito rimanga stabile, verificabile e identico a quello generato dal repository SaniKey.

---

### 14.35 Artefatti frontend

Il frontend viene generato dalla pipeline.

Nessun contenuto clinico viene modificato manualmente all'interno della build finale.

---

### 14.36 Rigenerabilità

L'intero frontend deve essere rigenerabile a partire da:

* documenti originali;
* metadati curati;
* configurazione.

---

### 14.37 Evoluzioni future

Possibili estensioni:

* visualizzazioni comparative;
* dashboard specialistiche;
* supporto PWA;
* consultazione assistita da AI locale.

Tali funzionalità non fanno parte della versione iniziale.

## 15. Costruzione Locale

### 15.1 Scopo

La Costruzione Locale è il processo mediante il quale i documenti originali e i metadati curati vengono trasformati negli artefatti utilizzati dal frontend e dalla distribuzione USB.

La build viene eseguita esclusivamente sul sistema dell'utente.

Nessuna fase della build richiede l'accesso alla chiavetta USB.

---

### 15.2 Obiettivi

La build deve:

* essere deterministica;
* essere incrementale;
* essere ripetibile;
* essere verificabile;
* produrre artefatti completamente rigenerabili.

---

### 15.3 Modalità di Costruzione

Sono supportate tre modalità operative:

```text
full
incremental
validation
```

#### costruzione completa

Rigenera completamente tutti gli artefatti.

Utilizzata:

* alla prima esecuzione;
* dopo modifiche strutturali;
* dopo aggiornamenti importanti.

#### costruzione incrementale

Riusa il testo estratto per documenti invariati e rigenera gli artefatti finali
dall'inventario corrente. La validita' della cache di estrazione dipende da
identita' documento, path, tipo, SHA256 e provenance.

È la modalità predefinita.

#### validazione della costruzione

Esegue esclusivamente verifiche senza produrre artefatti.

---

### 15.4 Costruzione Singolo Paziente

La costruzione normale opera su un singolo paziente.

Input:

```text
documents/
metadata/
config/
```

Output:

```text
generated/<patient>/
```

---

### 15.5 Costruzione Completa

La costruzione completa elabora tutti i pazienti configurati.

Esempio:

```text
Paziente A
Paziente B
Paziente C
Paziente D
```

Ogni paziente viene elaborato indipendentemente.

Un errore in un archivio non deve necessariamente impedire l'elaborazione degli altri.

---

### 15.6 Fasi della Costruzione

La costruzione esegue le seguenti fasi:

```text
Validazione Configurazione
        ↓
Scansione Documenti
        ↓
OCR
        ↓
Elaborazione DICOM
        ↓
Estrazione Entità
        ↓
Consolidamento
        ↓
Generazione Database
        ↓
Generazione Ricerca
        ↓
Generazione Timeline
        ↓
Generazione Frontend
        ↓
Generazione Artefatti
```

---

### 15.7 Incrementalità

La build deve rilevare:

* nuovi documenti;
* documenti modificati;
* documenti eliminati;
* modifiche ai metadati curati;
* modifiche alla configurazione.

Devono essere rigenerati solo gli artefatti interessati.

---

### 15.8 Cache

La build può utilizzare cache per:

* OCR;
* estrazioni AI;
* embeddings;
* elaborazioni DICOM.

Le cache sono considerate artefatti rigenerabili.

---

### 15.9 Validazione Configurazione

Prima dell'elaborazione devono essere verificati:

* file TOML;
* riferimenti;
* identificatori;
* percorsi;
* UUID delle chiavette configurate.

---

### 15.10 Validazione Documenti

Devono essere verificati:

* leggibilità;
* conformità del nome file;
* duplicati;
* date;
* integrità PDF;
* integrità DICOM.

---

### 15.11 Validazione Metadati

Devono essere verificati:

* sintassi;
* riferimenti incrociati;
* date;
* identificatori;
* consistenza interna.

Gli errori sono considerati fatali.

---

### 15.12 Gestione Errori

Gli errori sono classificati come:

```text
warning
error
fatal
```

#### warning

La build continua.

#### error

L'elemento viene escluso.

#### fatal

La build viene interrotta.

---

### 15.13 Report di Costruzione

Ogni build genera un report contenente:

* documenti elaborati;
* documenti nuovi;
* documenti modificati;
* errori;
* warning;
* statistiche OCR;
* statistiche AI;
* durata delle operazioni.

---

### 15.14 Manifest

Ogni build genera un manifest contenente:

* versione build;
* data build;
* versione schema;
* statistiche principali.

---

### 15.15 Verifiche Finali

Prima del completamento devono essere verificati:

* integrità database;
* integrità frontend;
* consistenza timeline;
* consistenza indici ricerca;
* presenza degli artefatti obbligatori.

---

### 15.16 Output

La build produce una directory completamente autonoma:

```text
generated/<patient>/
```

pronta per essere distribuita sulla chiavetta USB.

---

### 15.17 Rigenerabilità

La cancellazione della directory:

```text
generated/
```

non deve comportare perdita di dati.

Tutti gli artefatti devono essere ricostruibili a partire da:

* documenti originali;
* metadati curati;
* configurazione.

## 16. Artefatti Generati

### 16.1 Scopo

Gli artefatti generati rappresentano il risultato della Costruzione Locale.

Essi costituiscono tutti i dati e le strutture necessarie per:

* consultazione;
* ricerca;
* navigazione;
* distribuzione USB.

Gli artefatti non sono sorgenti autorevoli.

Possono essere eliminati e rigenerati in qualsiasi momento.

---

### 16.2 Principi fondamentali

#### Rigenerabilità artifatti

Qualunque artefatto deve poter essere ricostruito a partire da:

* documenti originali;
* metadati curati;
* configurazione.

---

#### Determinismo artefatti

A parità di input, la build deve produrre artefatti equivalenti.

---

#### Separazione

Gli artefatti generati non devono essere modificati manualmente.

---

#### Tracciabilità artefatti

Ogni artefatto deve poter essere ricondotto alla build che lo ha prodotto.

---

### 16.3 Struttura generale

Per ogni paziente viene generata una struttura autonoma.

```text
generated/
└── <patient>/
    │
    ├── database/
    ├── web/
    ├── search/
    ├── timeline/
    ├── ai/
    ├── dicom/
    ├── reports/
    ├── manifests/
    └── staging/
```

---

### 16.4 Database

Contiene il database SQLite completo.

```text
database/
└── medical_archive.db
```

Il database viene utilizzato per:

* audit;
* diagnostica;
* validazione;
* future migrazioni.

Non viene interrogato direttamente dal frontend.

---

### 16.5 Frontend

Contiene il frontend statico.

```text
web/
│
├── index.html
├── css/
├── js/
├── assets/
└── data/
```

Costituisce il punto di accesso principale dell'utente.

---

### 16.6 Data Export

Contiene i dataset JSON utilizzati dal frontend.

Esempio:

```text
data/
│
├── summary.json
├── problems.json
├── procedures.json
├── therapies.json
├── observations.json
├── timeline.json
├── documents.json
└── search.json
```

La build genera inoltre `web/data.js`, che incapsula i dataset essenziali in una
variabile JavaScript locale. Il frontend usa `data.js` per la prima
consultazione offline da `file://`; i JSON restano presenti come artefatti
ispezionabili e riprocessabili.

Quando è presente testo estratto, la build genera anche `web/content-search.js`.
Questo file contiene l'indice della ricerca avanzata e viene caricato dal
frontend solo quando l'utente usa la sezione dedicata. Anche questo artefatto è
JavaScript locale e non richiede `fetch()` o un server HTTP.

`web/data.js` contiene inoltre un blocco `clinical` con problemi, farmaci,
terapie, procedure, osservazioni e studi DICOM sintetici. Questi dati alimentano
la dashboard clinica del riepilogo, il bottone diretto `Terapia` quando sono
presenti terapie, la sezione autonoma `Studi DICOM` quando sono presenti studi
catalogati e i risultati federati della ricerca.

---

### 16.7 Motivazione

L'utilizzo di JSON statici:

* evita dipendenze da SQLite WASM;
* migliora la compatibilità;
* semplifica il frontend;
* riduce la complessità operativa.

Per la consultazione diretta da file manager, il frontend non deve dipendere da
`fetch()` sui JSON locali, perché alcuni browser bloccano queste richieste su
URL `file://`.

---

### 16.8 Summary Export

```text
summary.json
```

Contiene le informazioni visualizzate nella dashboard iniziale.

Esempi:

* problemi attivi;
* terapie attive;
* procedure rilevanti;
* ultime visite.

Quando `clinical_summary.toml` contiene `summary`, l'export include anche
`clinical_summary_html`, renderizzato a build-time da Markdown.

---

### 16.9 Documents Export

```text
documents.json
```

Contiene i metadati documentali necessari alla consultazione.

Non contiene il contenuto binario dei documenti.

Per i documenti `.md`, l'export include `markdown_html`, renderizzato a
build-time da Markdown con HTML grezzo disabilitato.

---

### 16.10 Timeline Export

```text
timeline.json
```

Contiene la rappresentazione ottimizzata della timeline.

Il frontend utilizza questo file senza dover ricostruire la cronologia.

---

### 16.11 Search Artifacts

Contiene gli indici utilizzati dalla ricerca.

```text
search/
│
├── lexical_index.json
├── tags_index.json
├── series_index.json
└── entities_index.json
```

Gli indici vengono generati durante la build.

Non vengono modificati durante la consultazione.

---

### 16.12 Ricerca Offline

La ricerca deve operare esclusivamente sugli indici pre-generati.

Non sono consentite:

* indicizzazioni runtime;
* ricostruzioni degli indici;
* scritture sulla chiavetta.

---

### 16.13 Timeline Artifacts

Contiene eventuali strutture ausiliarie dedicate alla timeline.

```text
timeline/
```

Questi file sono derivati da:

* eventi;
* procedure;
* terapie;
* campagne osservative.

---

### 16.14 AI Artifacts

Contiene risultati intermedi delle elaborazioni AI.

```text
ai/
│
├── extraction_cache/
├── summary_cache/
└── embeddings/
```

---

### 16.15 Embeddings

Gli embeddings sono opzionali.

Vengono generati solo se la ricerca semantica è abilitata.

---

### 16.16 Rigenerabilità degli artefatti AI

Gli artefatti AI non costituiscono dati autorevoli.

Possono essere eliminati senza perdita di informazioni curate.

---

### 16.17 OCR Artifacts

Contiene:

```text
ocr/
```

con:

* testo OCR;
* cache OCR;
* diagnostica OCR.

---

### 16.18 DICOM Artifacts

Contiene informazioni derivate dai supporti diagnostici.

```text
dicom/
│
├── extracted/
├── metadata/
└── viewers/
```

---

### 16.19 Estrazione DICOM

I contenuti estratti sono considerati artefatti rigenerabili.

I supporti originali consegnati dalla struttura sanitaria rimangono la sorgente
primaria.

La modalità di espansione dei supporti DICOM sarà definita da una decisione
successiva.

---

### 16.20 Viewer Rilevati

La build può individuare:

* viewer Windows;
* viewer macOS;
* documentazione allegata.

Le informazioni vengono registrate come metadati.

---

### 16.21 Reports

Contiene report tecnici.

```text
reports/
│
├── build_report.html
├── validation_report.html
├── statistics.json
└── duplicate_report.json
```

---

### 16.22 Report di Costruzione

Riporta:

* durata build;
* documenti elaborati;
* warning;
* errori;
* statistiche generali.

---

### 16.23 Report di Validazione

Riporta:

* documenti senza data;
* riferimenti mancanti;
* problemi OCR;
* errori DICOM;
* incoerenze metadati.

---

### 16.24 Statistics

Statistiche dell'archivio.

Esempi:

* numero documenti;
* numero problemi clinici;
* numero procedure;
* numero terapie;
* numero osservazioni.

---

### 16.25 Manifest

Ogni build genera un manifest.

```text
manifests/
└── manifest.json
```

---

### 16.26 Contenuto del Manifest

Il manifest contiene:

* versione build;
* data build;
* versione schema;
* versione configurazione;
* statistiche principali.

---

### 16.27 Checksums

Ogni build genera:

```text
checksums.sha256
```

contenente gli hash degli artefatti esportabili.

---

### 16.28 Scopo dei Checksums

I checksum consentono:

* verifiche di integrità;
* controlli post-copia;
* audit.

---

### 16.29 Staging

Area temporanea utilizzata durante la build.

```text
staging/
```

Può essere eliminata in qualsiasi momento.

---

### 16.30 Artefatti esportabili

Possono essere copiati sulla chiavetta:

```text
web/
database/
documents/
dicom/
manifests/
checksums.sha256
```

---

### 16.31 Artefatti non esportabili

Non devono essere copiati:

```text
staging/
working/
temporary/
```

ed eventuali cache locali non necessarie alla consultazione.

---

### 16.32 Relazione con la chiavetta USB

La distribuzione USB deve operare esclusivamente sugli artefatti esportabili.

Non deve mai accedere:

* ai documenti sorgente;
* ai metadati curati;
* ai file di lavoro.

---

### 16.33 Rigenerazione Completa

La cancellazione dell'intera directory:

```text
generated/
```

non deve comportare alcuna perdita informativa.

## 17. Distribuzione USB

### 17.1 Scopo

La Distribuzione USB trasferisce sulla chiavetta gli artefatti generati localmente.

La distribuzione deve:

* essere sicura;
* essere verificabile;
* essere incrementale;
* minimizzare i tempi di copia;
* evitare errori di destinazione.

---

### 17.2 Principi fondamentali

#### Separazione build

La build e la distribuzione sono processi distinti.

La distribuzione non deve rigenerare artefatti.

---

#### Verificabilità

Ogni copia deve poter essere verificata.

---

#### Incrementalità build

Devono essere trasferiti soltanto i file modificati.

---

#### Sicurezza operativa

Il sistema deve ridurre il rischio di copiare dati sulla chiavetta sbagliata.

---

### 17.3 Modello Operativo

Il flusso generale è:

```text
Costruzione Locale
      ↓
Artefatti Generati
      ↓
Validazione USB
      ↓
Distribuzione
      ↓
Verifica
```

---

### 17.4 Chiavette supportate

Ogni chiavetta viene identificata tramite:

```text
UUID filesystem
```

L'identificazione tramite lettera di unità o mountpoint non è considerata affidabile.

---

### 17.5 Associazione Chiavetta-Paziente

Ogni paziente eredita la chiavetta globale. Solo gli override espliciti usano
`usb_uuid`.

Esempio:

```toml
[global.usb]
usb_uuid = "1A2B-3C4D"

[[person]]
id = "patient-a"
```

---

### 17.6 Verifica UUID

Prima della copia il sistema deve verificare:

* presenza della chiavetta;
* UUID;
* accessibilità;
* spazio disponibile.

---

### 17.7 Errore di Identificazione

Se l'UUID non corrisponde:

```text
ATTENZIONE

La chiavetta collegata non corrisponde
a quella configurata.
```

La distribuzione deve essere interrotta.

---

### 17.8 Modalità Override

Può essere prevista una modalità esplicita di override.

L'override richiede una conferma esplicita dell'utente.

---

### 17.9 Controllo Spazio

Prima della copia il sistema deve calcolare:

* dimensione artefatti;
* spazio disponibile;
* margine residuo.

---

### 17.10 Spazio Minimo

Deve essere rispettata la soglia definita in configurazione.

Esempio:

```toml
required_free_space_mb = 512
```

---

### 17.11 Errore Spazio Insufficiente

Se lo spazio disponibile non è sufficiente:

* la copia non viene avviata;
* viene prodotto un report.

---

### 17.12 Struttura della Chiavetta

Esempio:

```text
USB/
│
├── index.html
│
├── patients/
│
│   ├── patient-a/
│   │   ├── medical_archive.db
│   │   ├── web/
│   │   └── documents/
│   │
│   └── patient-b/
│       ├── medical_archive.db
│       ├── web/
│       └── documents/
│
└── SANIKEY-MANIFEST.toml
```

La directory `web/` contiene il frontend statico generato per il paziente.

---

### 17.13 Multi-Paziente

Una singola chiavetta può contenere più archivi indipendenti.

Non esistono database condivisi.

Non esistono indici condivisi.

Non esistono frontend condivisi.

---

### 17.14 Pagina di Avvio

La chiavetta possiede una pagina di avvio alla radice.

Esempio:

```text
index.html
```

---

### 17.15 Scopo delle Pagine di Avvio

Consentono al medico di selezionare immediatamente il paziente corretto.

Non è richiesta alcuna navigazione manuale della struttura directory.

---

### 17.16 Modalità di Copia

La distribuzione supporta:

```text
full

incremental

verify
```

---

### 17.17 Full

Ricopia completamente tutti gli artefatti esportabili.

---

### 17.18 Incremental

Trasferisce soltanto:

* file nuovi;
* file modificati;
* file eliminati.

È la modalità predefinita.

---

### 17.19 Verify

Non copia alcun file.

Verifica solamente:

* integrità;
* checksum;
* consistenza.

---

### 17.20 Utilizzo di rsync

Se disponibile, il sistema utilizza:

```text
rsync
```

come meccanismo preferenziale.

---

### 17.21 Fallback

In assenza di rsync viene utilizzato un meccanismo alternativo implementato dall'applicazione.

La semantica deve rimanere equivalente.

---

### 17.22 Verifica Post-Copia

Al termine della distribuzione devono essere verificati:

* numero file;
* dimensione totale;
* checksum.

---

### 17.23 Checksum

I checksum vengono confrontati utilizzando:

```text
checksums.sha256
```

generato durante la build.

---

### 17.24 Report di Distribuzione

Ogni distribuzione genera un report contenente:

* chiavetta utilizzata;
* UUID;
* data;
* file copiati;
* file rimossi;
* durata;
* eventuali errori.

---

### 17.25 Rimozione File Obsoleti

La modalità incrementale può eliminare file non più presenti negli artefatti sorgente.

L'operazione deve essere eseguita in modo controllato.

---

### 17.26 Atomicità Logica

Una distribuzione fallita non deve lasciare lo stato della chiavetta ambiguo.

Deve essere possibile:

* rieseguire la distribuzione;
* verificare l'integrità finale.

---

### 17.27 File di Manifest

La radice della chiavetta deve contenere:

```text
manifest.json
```

contenente:

* versione build;
* data build;
* pazienti presenti;
* statistiche principali.

---

### 17.28 Compatibilità Filesystem

Versione iniziale:

```text
exFAT
```

è il filesystem raccomandato.

Motivazioni:

* Windows;
* macOS;
* file di grandi dimensioni;
* supporto diffuso.

---

### 17.29 File di Grandi Dimensioni

La distribuzione deve supportare:

* ISO diagnostiche;
* archivi DICOM;
* PDF molto grandi.

---

### 17.30 Modalità Sola Lettura

La chiavetta è considerata un supporto di consultazione.

Durante l'utilizzo:

* nessun file viene modificato;
* nessun indice viene rigenerato;
* nessuna cache viene creata.

---

### 17.31 Integrità

La consultazione non deve alterare il contenuto distribuito.

---

### 17.32 Aggiornamento Archivio

Gli aggiornamenti vengono effettuati esclusivamente tramite:

```text
Costruzione Locale
        ↓
Distribuzione USB
```

Non è prevista manutenzione diretta sulla chiavetta.

---

### 17.33 Ripristino

In caso di danneggiamento della chiavetta:

* si ricrea il filesystem;
* si riesegue la distribuzione.

Non è necessario alcun recupero complesso.

---

### 17.34 Evoluzioni Future

Possibili estensioni:

* distribuzione su SSD esterni;
* distribuzione su NAS;
* immagini ISO complete dell'archivio.

Tali funzionalità non fanno parte della versione iniziale.

## 18. Sicurezza e Privacy

### 18.1 Scopo

Questo capitolo definisce i requisiti di sicurezza e privacy del sistema SaniKey.

L'obiettivo è proteggere:

* i dati sanitari;
* i documenti clinici;
* i metadati curati;
* gli artefatti distribuiti.

senza compromettere la semplicità operativa richiesta per l'utilizzo quotidiano.

---

### 18.2 Principi fondamentali

#### Semplicità operativa

Le misure di sicurezza non devono impedire l'utilizzo pratico del sistema.

---

#### Privacy by Design

Le informazioni personali devono essere trattate come dati sensibili.

---

#### Offline First principle

La consultazione deve avvenire senza dipendere da servizi esterni.

---

#### Minimo privilegio

Ogni componente deve accedere esclusivamente ai dati necessari.

---

### 18.3 Modello di Minaccia

Versione iniziale.

Il sistema protegge principalmente contro:

* perdita accidentale dei dati;
* copia incompleta;
* corruzione degli artefatti;
* errori operativi;
* accessi involontari.

Non protegge contro:

* accesso fisico intenzionale alla chiavetta;
* attacchi forensi avanzati;
* compromissione del computer ospite.

---

### 18.4 Dati Sensibili

Sono considerati sensibili:

* documenti sanitari;
* diagnosi;
* terapie;
* osservazioni cliniche;
* dati anagrafici.

---

### 18.5 Assenza di Cloud

La consultazione non utilizza:

* servizi cloud;
* API esterne;
* servizi AI remoti;
* telemetria.

salvo esplicita configurazione dell'utente durante la fase di build.

---

### 18.6 Telemetria

Il sistema non deve raccogliere:

* statistiche d'uso;
* analytics;
* dati di navigazione;
* identificatori persistenti.

---

### 18.7 Cookie

Il frontend non deve utilizzare cookie.

---

### 18.8 Storage Locale

Il frontend non deve utilizzare:

* localStorage;
* sessionStorage;
* IndexedDB;

per memorizzare dati clinici.

---

### 18.9 Modalità Sola Lettura

La consultazione della chiavetta non deve produrre:

* log;
* cache;
* database modificati;
* file temporanei gestiti dall'applicazione.

---

### 18.10 Dati AI

I modelli AI possono elaborare dati clinici soltanto durante la build.

Le informazioni trasmesse a servizi remoti devono essere considerate una scelta esplicita dell'utente.

---

### 18.11 AI Locale

La modalità raccomandata è:

```text
AI locale
```

per minimizzare la diffusione dei dati sanitari.

---

### 18.12 Cifratura

La cifratura della chiavetta non fa parte dei requisiti della versione iniziale.

Motivazione:

* necessità di utilizzo immediato presso specialisti;
* assenza di garanzie sulla disponibilità della tastiera;
* semplicità operativa.

---

### 18.13 Conseguenze della Mancata Cifratura

La perdita della chiavetta comporta potenziale esposizione dei dati.

L'utente deve esserne consapevole.

---

### 18.14 Integrità

L'integrità viene verificata mediante:

* checksum;
* manifest;
* verifiche post-distribuzione.

---

### 18.15 Hash

Algoritmo iniziale:

```text
SHA256
```

---

### 18.16 Provenienza

Le entità derivate devono conservare:

* origine;
* data generazione;
* modello utilizzato;
* approvazione.

---

### 18.17 Separazione dei Pazienti

Ogni paziente possiede:

* frontend indipendente;
* database indipendente;
* dati indipendenti.

---

### 18.18 Isolamento Logico

La consultazione di un paziente non deve richiedere l'accesso ai dati di altri pazienti presenti sulla stessa chiavetta.

---

### 18.19 Backup

La sicurezza principale del sistema è basata sulla possibilità di rigenerazione.

Devono essere mantenute copie di:

* documenti originali;
* metadati curati;
* configurazione.

---

### 18.20 Disaster Recovery

In caso di perdita della chiavetta:

```text
Documenti Originali
        +
Metadati Curati
        +
Configurazione
        ↓
Nuova Costruzione
        ↓
Nuova Chiavetta
```

---

### 18.21 Sicurezza del Repository

I metadati curati rappresentano un patrimonio informativo critico.

Devono essere inclusi nei backup regolari.

---

### 18.22 Sicurezza degli Artefatti

Gli artefatti generati non sono considerati autorevoli.

La loro perdita non comporta perdita informativa.

---

### 18.23 Auditabilità

Il sistema deve consentire di determinare:

* origine delle informazioni;
* data di generazione;
* approvazioni effettuate;
* modifiche ai metadati curati.

---

### 18.24 Evoluzioni Future

Possibili estensioni:

* cifratura opzionale della chiavetta;
* firma digitale dei manifest;
* firma digitale degli artefatti;
* distribuzioni cifrate.

Tali funzionalità non fanno parte della versione iniziale.

## 19. Operazioni e Manutenzione

### 19.1 Scopo

Questo capitolo definisce le operazioni necessarie per mantenere un archivio SaniKey nel corso del tempo.

L'obiettivo è garantire che l'archivio rimanga:

* aggiornato;
* coerente;
* verificabile;
* utilizzabile per decenni.

---

### 19.2 Principi fondamentali

#### Manutenzione minima

Le operazioni ordinarie devono richiedere il minor lavoro possibile.

---

#### Incrementalità manutenzione

L'aggiunta di nuovi documenti non deve richiedere la ricostruzione manuale dell'intero archivio.

---

#### Ripetibilità manutenzione

Le operazioni devono essere ripetibili senza effetti collaterali.

---

#### Conservazione

Nessuna operazione ordinaria deve modificare i documenti originali.

---

### 19.3 Ciclo di vita tipico

L'uso ordinario del sistema segue il seguente schema.

```text
Nuovo Documento
        ↓
Importazione
        ↓
Costruzione Incrementale
        ↓
Revisione Proposte
        ↓
Distribuzione USB
```

---

### 19.4 Acquisizione Documenti

I nuovi documenti vengono copiati nelle directory sorgente del paziente.

Esempio:

```text
source_documents/
└── imaging/
    └── diagnostic-study/
        └── 20261110 Visita Cardiologica.pdf
```

---

### 19.5 Regole di Acquisizione

I documenti devono essere:

* conservati nel formato originale;
* rinominati secondo le convenzioni del sistema;
* collocati nella categoria appropriata.

---

### 19.6 Rinomina

Convenzione raccomandata:

```text
AAAAMMGG Titolo.pdf
```

Esempi:

```text
20240517 Analisi.pdf

20260921 Operazione Cataratta.pdf
```

---

### 19.7 Modifica Documenti

I documenti originali non devono essere modificati.

Se necessario:

* si conserva il documento originale;
* si sostituisce con una nuova versione;
* la modifica viene rilevata tramite SHA256.

---

### 19.8 Aggiornamento Metadati Curati

I metadati curati possono essere modificati per:

* aggiungere informazioni;
* correggere errori;
* consolidare dati clinici.

---

### 19.9 Revisione delle Proposte AI

Le proposte AI devono essere revisionate periodicamente.

Possibili azioni:

* approvazione;
* rifiuto;
* archiviazione.

---

### 19.10 Approvazione

Le informazioni approvate diventano parte dei metadati curati.

---

### 19.11 Rifiuto

Le informazioni rifiutate non devono influenzare:

* database;
* timeline;
* frontend.

---

### 19.12 Costruzione Incrementale

Modalità operativa raccomandata.

Rigenera esclusivamente:

* nuovi documenti;
* documenti modificati;
* artefatti interessati.

---

### 19.13 Costruzione Completa

Da utilizzare:

* dopo modifiche strutturali;
* dopo aggiornamenti software importanti;
* in caso di dubbi sulla consistenza.

---

### 19.14 Verifica Periodica

Si raccomanda una verifica completa periodica.

Controlli tipici:

* integrità documenti;
* validità metadati;
* consistenza database;
* consistenza frontend.

---

### 19.15 Gestione Duplicati

La pipeline può rilevare:

* duplicati identici;
* duplicati probabili.

I duplicati non vengono eliminati automaticamente.

---

### 19.16 Gestione Errori OCR

Documenti con OCR problematico devono essere segnalati.

La correzione è facoltativa.

---

### 19.17 Gestione DICOM

I supporti diagnostici devono essere conservati integralmente.

Non devono essere modificati.

---

### 19.18 Aggiornamento Configurazione

La configurazione può essere modificata per:

* aggiungere pazienti;
* modificare percorsi;
* sostituire chiavette USB;
* aggiornare preferenze.

---

### 19.19 Sostituzione Chiavetta

In caso di sostituzione:

* si registra il nuovo UUID;
* si esegue una nuova distribuzione completa.

---

### 19.20 Strategia di Backup

Il sistema distingue chiaramente tra:

* dati autorevoli;
* artefatti generati;
* distribuzioni USB.

La strategia di backup deve concentrarsi esclusivamente sui dati autorevoli.

---

### 19.21 Dati da Salvaguardare

I seguenti elementi sono considerati critici.

```text
documents/
metadata/
config/
```

La perdita di uno qualsiasi di questi elementi può comportare perdita permanente di informazioni.

---

### 19.22 Artefatti Rigenerabili

I seguenti elementi non richiedono backup obbligatorio.

```text
generated/
```

Essi possono essere ricostruiti integralmente mediante una nuova build.

---

### 19.23 La Chiavetta USB non è un Backup

La chiavetta USB non deve essere considerata una copia di sicurezza.

La chiavetta rappresenta esclusivamente un supporto di distribuzione e consultazione.

La perdita o il danneggiamento della chiavetta non deve compromettere la conservazione dell'archivio.

---

### 19.24 Strategia di Backup Raccomandata

La strategia minima raccomandata è:

```text
Repository SaniKey
        ↓
Backup Locale
        ↓
Backup Esterno
```

Dove:

* il backup locale protegge da errori operativi;
* il backup esterno protegge da guasti e disastri locali.

---

### 19.25 Verifica dei Backup

I backup devono essere verificati periodicamente.

La semplice presenza dei file non è considerata sufficiente.

La verifica deve includere almeno:

* accessibilità;
* leggibilità;
* completezza;
* possibilità di ripristino.

---

### 19.26 Procedura di Restore

Il ripristino standard consiste nel recupero di:

```text
documents/
metadata/
config/
```

su un nuovo sistema.

Successivamente viene eseguita una Costruzione Completa.

---

### 19.27 Disaster Recovery

In caso di perdita totale del sistema operativo o del computer:

```text
Backup
      ↓
Ripristino del Repository
      ↓
Costruzione Completa
      ↓
Nuova Distribuzione USB
```

Non è necessario recuperare gli artefatti generati.

---

### 19.28 Sostituzione della Chiavetta

La sostituzione della chiavetta segue la procedura:

```text
Nuova Chiavetta
      ↓
Formattazione exFAT
      ↓
Registrazione UUID
      ↓
Distribuzione Completa
      ↓
Verifica
```

---

### 19.29 Aggiornamento UUID

Dopo la sostituzione della chiavetta deve essere aggiornato il relativo UUID nella configurazione.

L'UUID precedente non deve essere riutilizzato.

---

### 19.30 Verifica Post-Sostituzione

Dopo una sostituzione devono essere verificati:

* correttezza della struttura directory;
* pagina root `index.html`;
* integrità dei documenti;
* integrità dei checksum;
* funzionamento del frontend.

---

### 19.31 Migrazione su Nuovo Computer

La migrazione su un nuovo sistema richiede esclusivamente:

```text
documents/
metadata/
config/
software SaniKey
```

Gli artefatti generati possono essere rigenerati localmente.

---

### 19.32 Test di Recuperabilità

Almeno periodicamente dovrebbe essere eseguito un test completo di recupero.

Obiettivo:

verificare che sia effettivamente possibile ricostruire l'intero archivio a partire dai backup disponibili.

---

### 19.33 Conservazione a Lungo Termine

La conservazione a lungo termine deve basarsi su:

* formati aperti;
* backup multipli;
* verifiche periodiche;
* capacità di rigenerazione.

La disponibilità degli artefatti generati non è un requisito di conservazione.

### 19.34 Backup

Devono essere inclusi nei backup:

```text
documents/
metadata/
config/
```

---

### 19.35 Backup degli Artefatti

Il backup degli artefatti generati è opzionale.

Essi sono completamente rigenerabili.

---

### 19.36 Migrazione Hardware

La migrazione su un nuovo computer richiede soltanto:

```text
documents/
metadata/
config/
software SaniKey
```

---

### 19.37 Migrazione Software

Le nuove versioni devono supportare:

* migrazione configurazione;
* migrazione schema database;
* migrazione metadati.

---

### 19.38 Archiviazione Storica

Documenti molto vecchi possono essere mantenuti senza alcuna distinzione operativa.

Il sistema non prevede archivi "freddi".

---

### 19.39 Rimozione Documenti

La rimozione di documenti deve essere un'operazione esplicita.

Non deve avvenire automaticamente.

---

### 19.40 Audit Operativo

Le operazioni principali devono essere registrate nei report.

Esempi:

* build;
* validazione;
* distribuzione;
* migrazione.

---

### 19.41 Conservazione a Lungo Termine

L'archivio deve poter essere mantenuto per decenni.

Per questo motivo:

* i formati devono essere aperti;
* i dati devono essere esportabili;
* gli artefatti devono essere rigenerabili.

---

### 19.42 Operazioni Automatizzabili

Possono essere automatizzate:

* build incrementale;
* validazione;
* distribuzione;
* generazione report.

---

### 19.43 Operazioni Manuali

Restano responsabilità dell'utente:

* acquisizione documenti;
* classificazione iniziale;
* revisione AI;
* manutenzione clinica.

---

### 19.44 Evoluzioni Future

Possibili estensioni:

* scheduler automatico;
* monitoraggio repository;
* sincronizzazione cloud opzionale;
* notifiche di manutenzione.

Tali funzionalità non fanno parte della versione iniziale.

## 20. Requisiti Tecnici

### 20.1 Scopo

Questo capitolo definisce i requisiti tecnici minimi necessari per implementare, eseguire e mantenere SaniKey.

I requisiti devono privilegiare:

* semplicità;
* portabilità;
* longevità;
* indipendenza da tecnologie proprietarie.

---

### 20.2 Linguaggio e Runtime

L'implementazione di riferimento utilizza:

```text
Python 3
```

Il sistema deve evitare dipendenze da versioni specifiche salvo quando strettamente necessario.

L'obiettivo è mantenere la compatibilità con le versioni supportate del linguaggio.

---

### 20.3 Motivazione

Python è stato scelto per:

* maturità dell'ecosistema;
* disponibilità di librerie documentali;
* disponibilità di librerie OCR;
* disponibilità di librerie AI;
* facilità di manutenzione a lungo termine.

---

### 20.4 Gestione Ambiente

L'ambiente di sviluppo e di esecuzione deve essere isolato.

Versione iniziale:

```text
uv
```

è il gestore raccomandato.

---

### 20.5 Librerie Fondamentali

Il sistema richiede componenti per:

* parsing PDF;
* OCR;
* SQLite;
* gestione TOML;
* generazione frontend;
* elaborazione DICOM.

Le librerie specifiche non costituiscono parte della specifica architetturale.

Possono essere sostituite senza modificare il modello del sistema.

---

### 20.6 OCR

Versione iniziale:

```text
Tesseract OCR
```

è la soluzione raccomandata.

Motivazioni:

* open source;
* supporto multilingua;
* ampia diffusione;
* longevità.

---

### 20.7 Database

Il database di riferimento è:

```text
SQLite
```

Motivazioni:

* assenza di server;
* portabilità;
* affidabilità;
* longevità.

---

### 20.8 Configurazione

I file di configurazione e metadati utilizzano:

```text
TOML
```

Motivazioni:

* leggibilità;
* sintassi rigorosa;
* assenza di problemi di indentazione.

---

### 20.9 Formati Strutturati

Il sistema utilizza:

```text
TOML
JSON
SQLite
```

come formati strutturati principali.

---

### 20.10 Formati Documentali

Versione iniziale:

```text
PDF
PDF/A
DICOM
DICOM ISO
ZIP
7Z
RAR
DOCX
XLSX
ODT
ODS
DOC
XLS
```

sono considerati formati supportati.

Per `ZIP`, `7Z`, `RAR` e `DICOM ISO`, il supporto include l'inventario del
contenitore e la staging dei membri estratti come artefatti generati.
Per `DOC` e `XLS` il supporto dipende dalla presenza di LibreOffice o `soffice`
nel sistema locale di build.

---

### 20.11 Formati Immagine

Possono essere supportati:

```text
JPEG
PNG
TIFF
```

principalmente per esigenze OCR.

---

### 20.12 Frontend

Il frontend utilizza esclusivamente:

```text
HTML
CSS
JavaScript
```

e file JSON statici.

---

### 20.13 Browser Supportati

La consultazione deve funzionare sui browser moderni.

Versione iniziale:

* Chrome;
* Edge;
* Firefox;
* Safari.

---

### 20.14 Modalità Offline

Tutte le funzionalità fondamentali devono operare senza connessione Internet.

---

### 20.15 Sistemi Operativi Supportati

Per la Costruzione Locale:

* Linux;
* Windows;
* macOS.

Per la consultazione:

* Windows;
* macOS.

---

### 20.16 Filesystem Raccomandato

Per la distribuzione USB il filesystem raccomandato è:

```text
exFAT
```

---

### 20.17 Motivazione

exFAT garantisce:

* compatibilità Windows;
* compatibilità macOS;
* supporto file di grandi dimensioni;
* semplicità operativa.

---

### 20.18 Dipendenze Opzionali

Possono essere presenti componenti opzionali per:

* AI locale;
* AI remota;
* ricerca semantica;
* elaborazioni avanzate DICOM.

---

### 20.19 Componenti AI

Versione iniziale:

```text
Ollama
```

costituisce il runtime AI locale raccomandato.

La specifica non impone un modello specifico.

---

### 20.20 Requisiti Hardware Indicativi

La build deve poter funzionare su un normale computer domestico.

Configurazione raccomandata:

```text
CPU multicore

16 GB RAM

SSD locale
```

---

### 20.21 Scalabilità

L'archivio deve supportare:

* decine di migliaia di documenti;
* più decenni di storia clinica;
* più pazienti indipendenti sulla stessa chiavetta.

---

### 20.22 Portabilità

Il sistema deve poter essere migrato su nuove piattaforme senza modificare:

* documenti;
* metadati curati;
* configurazione.

---

### 20.23 Formati da Preservare

I seguenti formati sono considerati parte del patrimonio informativo:

```text
PDF
DICOM
TOML
JSON
SQLite
```

---

### 20.24 Evoluzione Tecnologica

Le implementazioni future possono sostituire:

* librerie;
* framework;
* strumenti;

purché rimangano invariati:

* modello dati;
* metadati curati;
* formato degli archivi.

## 21. Questioni Aperte e Possibili Evoluzioni

### 21.1 Scopo

Questo capitolo raccoglie funzionalità e direzioni evolutive considerate interessanti ma non necessarie per la versione iniziale di SaniKey.

La loro presenza in questo capitolo non implica un impegno di implementazione.

---

### 21.2 Principi

Le evoluzioni future non devono compromettere:

* portabilità;
* semplicità;
* consultazione offline;
* longevità degli archivi.

---

### 21.3 Ricerca Semantica

Versione iniziale:

* opzionale;
* precomputata;
* completamente offline.

Questioni aperte:

* modello embedding;
* dimensione degli indici;
* strategia di aggiornamento.

---

### 21.4 Estrazione Strutturata degli Esami

Attualmente i documenti vengono trattati principalmente come testo.

Possibile evoluzione:

estrazione strutturata di:

* esami ematici;
* parametri vitali;
* valori clinici.

---

### 21.5 Serie Storiche Cliniche

Possibile generazione automatica di:

* curve peso;
* pressione;
* glicemia;
* funzione renale;
* altri indicatori.

a partire dai documenti clinici.

---

### 21.6 Integrazione FHIR

Possibile supporto futuro agli standard:

```text
FHIR
HL7
```

per:

* esportazione;
* interoperabilità;
* integrazione con sistemi sanitari.

---

### 21.7 Versione Mobile

Possibile generazione di una vista ottimizzata per:

* smartphone;
* tablet.

La consultazione desktop rimane il caso d'uso principale.

---

### 21.8 Cifratura Opzionale

Possibile introduzione di:

* cifratura della chiavetta;
* cifratura dei documenti;
* distribuzioni protette da password.

Non prevista nella versione iniziale.

---

### 21.9 Firma Digitale

Possibile introduzione di:

* firma dei manifest;
* firma degli artefatti;
* verifica della provenienza.

---

### 21.10 Consultazione Assistita da AI

Possibile introduzione di:

* interrogazione in linguaggio naturale;
* assistente locale;
* funzionalità RAG.

Tali funzionalità dovrebbero rimanere completamente opzionali.

---

### 21.11 Packaging Desktop

Possibile distribuzione come applicazione desktop autonoma.

Esempi:

```text
Windows Installer

macOS Application Bundle

AppImage
```

---

### 21.12 Supporti Alternativi

Oltre alle chiavette USB potrebbero essere supportati:

* SSD esterni;
* NAS;
* archivi distribuiti.

---

### 21.13 Esportazione Clinica

Possibile generazione automatica di:

* dossier clinici;
* riassunti specialistici;
* report cronologici;
* esportazioni standardizzate.

---

### 21.14 Integrazione Dispositivi

Possibile integrazione con:

* misuratori di pressione;
* bilance;
* glucometri;
* saturimetri.

per l'importazione automatica delle osservazioni.

---

### 21.15 Conservazione a Lungo Termine

Possibili strategie aggiuntive:

* archivi immutabili;
* supporti WORM;
* verifica periodica automatizzata.

---

### 21.16 Esclusioni della Versione Iniziale

Le seguenti funzionalità non fanno parte della versione iniziale:

* sincronizzazione cloud;
* backend remoto;
* consultazione multiutente;
* modifica dei dati sulla chiavetta;
* dipendenze obbligatorie da servizi AI remoti.

---

### 21.17 Criteri di Valutazione delle Evoluzioni

Una futura estensione dovrebbe essere adottata soltanto se:

* aggiunge valore concreto;
* non compromette la portabilità;
* non riduce la longevità;
* non aumenta significativamente la complessità operativa.
