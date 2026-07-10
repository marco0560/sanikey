# Decisioni Architetturali Iniziali

<!-- markdownlint-disable MD013 MD060 -->
<!-- pyml disable md013 -->

## Scopo

Questo documento raccoglie e indicizza le decisioni architetturali assunte durante la progettazione iniziale di SaniKey.

Le decisioni complete sono riportate in questo documento e sono state rimosse dalla specifica dettagliata.

---

## ADR per Numero

| ADR | Titolo | Capitolo | Status |
| ----- | -------- | ---------- | -------- |
| DA-001 | Ogni paziente possiede un archivio indipendente. | 3 |  |
| DA-002 | Ogni paziente possiede un database SQLite indipendente. | 3 |  |
| DA-003 | Ogni paziente possiede un frontend indipendente. | 3 |  |
| DA-004 | La chiavetta USB può contenere più pazienti. | 3 |  |
| DA-005 | La selezione del paziente avviene tramite file HTML dedicati. | 3 |  |
| DA-006 | Non esistono dati condivisi tra archivi di pazienti differenti. | 3 |  |
| DA-007 | La build e il deploy possono essere eseguiti sia per singolo paziente sia per l'intero insieme dei pazienti configurati. | 3 |  |
| DA-008 | I metadati curati risiedono nel percorso `metadata_directory` configurato per ciascun paziente. | 4 |  |
| DA-009 | Tutti gli artefatti generati risiedono nel percorso `local_build` configurato per ciascun paziente. | 4 |  |
| DA-010 | La chiavetta USB viene sempre costruita a partire da: `exports/usb-image/` | 4 |  |
| DA-011 | Le directory: `generated/`, `exports/`, `logs/` sono considerate completamente rigenerabili. | 4 |  |
| DA-012 | La struttura delle categorie documentali è definita dal percorso `source_documents` del singolo paziente e non è vincolata da SaniKey. | 4 |  |
| DA-013 | Il repository pubblico non contiene dati personali; configurazione reale, dati paziente, artefatti generati, export e log operativi sono esclusi da Git, mentre gli esempi pubblicabili risiedono sotto `docs/*-example`. | 4 |  |
| DA-014 | La configurazione è espressa esclusivamente in formato TOML. | 5 |  |
| DA-015 | Ogni paziente possiede una sezione dedicata in `accounts.toml`. | 5 |  |
| DA-016 | L'UUID della chiavetta è il meccanismo ufficiale di identificazione dei dispositivi di deploy. | 5 |  |
| DA-017 | Gli errori di configurazione interrompono sempre l'esecuzione. | 5 |  |
| DA-018 | I percorsi dei documenti originali sono configurabili e non devono essere vincolati alla struttura interna del repository. | 5 |  |
| DA-019 | L'identità tecnica del documento è basata su SHA256. | 6 |  |
| DA-020 | Il percorso del file è un metadato, non l'identità del documento. | 6 |  |
| DA-021 | I documenti originali non vengono modificati. | 6 |  |
| DA-022 | Le directory documentali sono categorie dinamiche. | 6 |  |
| DA-023 | La serie documentale è distinta dalla categoria. | 6 |  |
| DA-024 | Gli studi diagnostici possono collegare referti PDF, supporti DICOM originali e contenuti DICOM estratti. | 6 |  |
| DA-025 | I duplicati tecnici vengono segnalati ma non eliminati automaticamente. | 6 |  |
| DA-026 | Le entità cliniche sono distinte dai documenti che le descrivono. | 7 |  |
| DA-027 | Medication e Therapy Episode sono entità differenti. | 7 |  |
| DA-028 | Observation Series e Document Series sono entità differenti. | 7 |  |
| DA-029 | Le campagne di monitoraggio sono entità autonome. | 7 |  |
| DA-030 | Ogni entità derivata deve registrare la propria provenienza. | 7 |  |
| DA-031 | I metadati curati costituiscono la sorgente autorevole delle entità cliniche. | 7 |  |
| DA-032 | I metadati curati sono organizzati per dominio e possono essere partizionati temporalmente. | 7 |  |
| DA-033 | Il modello deve supportare archivi sanitari multi-decennali senza richiedere riorganizzazioni strutturali. | 7 |  |
| DA-034 | Le procedure cliniche sono entità di primo livello e devono essere distinte sia dai documenti che le descrivono sia dagli eventi timeline che le rappresentano cronologicamente. | 7 |  |
| DA-035 | La pipeline è incrementale per impostazione predefinita. | 8 |  |
| DA-036 | L'OCR viene eseguito solo quando necessario. | 8 |  |
| DA-037 | Le informazioni curate hanno sempre precedenza sulle informazioni derivate. | 8 |  |
| DA-038 | Le inferenze AI non sono autorevoli fino all'approvazione. | 8 |  |
| DA-039 | Ogni fase della pipeline deve poter essere rieseguita senza effetti collaterali. | 8 |  |
| DA-040 | Ogni informazione derivata deve conservare la propria provenienza. | 8 |  |
| DA-041 | Procedure e Clinical Events sono entità distinte. | 9 |  |
| DA-042 | Observation Series e Observation Campaign sono entità distinte. | 9 |  |
| DA-043 | SQLite viene esportato integralmente sulla chiavetta USB. | 9 |  |
| DA-044 | La ricerca full-text utilizza FTS5. | 9 |  |
| DA-045 | Le chiavi esterne SQLite sono obbligatorie. | 9 |  |
| DA-046 | I metadati curati costituiscono la sorgente autorevole delle informazioni strutturate. | 10 |  |
| DA-047 | I metadati curati sono conservati esclusivamente in formato TOML. | 10 |  |
| DA-048 | I metadati sono organizzati per dominio funzionale. | 10 |  |
| DA-049 | I dati longitudinali possono essere partizionati temporalmente. | 10 |  |
| DA-050 | Le proposte AI sono conservate separatamente dai dati curati. | 10 |  |
| DA-051 | I metadati curati non sono rigenerabili. | 10 |  |
| DA-052 | Errori nei metadati curati interrompono la pipeline. | 10 |  |
| DA-053 | Documenti originali e metadati curati costituiscono insieme la sorgente autorevole dell'intero sistema. | 10 |  |
| DA-054 | L'AI è utilizzata esclusivamente durante build e manutenzione. | 11 |  |
| DA-055 | L'AI non possiede autorità clinica. | 11 |  |
| DA-056 | Le proposte AI richiedono sempre approvazione umana. | 11 |  |
| DA-057 | Le proposte AI vengono memorizzate in file TOML separati dai metadati curati. | 11 |  |
| DA-058 | Le funzionalità fondamentali del sistema non dipendono dall'AI. | 11 |  |
| DA-059 | Ogni informazione generata dall'AI deve conservare informazioni complete di provenienza. | 11 |  |
| DA-060 | Le elaborazioni AI devono utilizzare una cache incrementale per evitare rigenerazioni inutili di archivi storici di grandi dimensioni. | 11 |  |
| DA-061 | La ricerca lessicale è obbligatoria. | 12 |  |
| DA-062 | La ricerca semantica è opzionale. | 12 |  |
| DA-063 | La ricerca deve funzionare completamente offline. | 12 |  |
| DA-064 | Gli embeddings vengono generati esclusivamente durante la build. | 12 |  |
| DA-065 | La ricerca interroga simultaneamente documenti ed entità cliniche. | 12 |  |
| DA-066 | I metadati curati sono indicizzati e ricercabili. | 12 |  |
| DA-067 | Le proposte AI non approvate non compaiono nei risultati standard. | 12 |  |
| DA-068 | La consultazione non richiede modelli AI attivi. | 12 |  |
| DA-069 | La ricerca deve rimanere utilizzabile anche in assenza completa di funzionalità semantiche. | 12 |  |
| DA-070 | La timeline è una vista derivata e non una sorgente autorevole. | 13 |  |
| DA-071 | La timeline supporta sia eventi puntuali sia intervalli temporali. | 13 |  |
| DA-072 | Le terapie sono rappresentate come intervalli temporali. | 13 |  |
| DA-073 | Le campagne osservative sono rappresentate come intervalli temporali. | 13 |  |
| DA-074 | Gli eventi manuali sono cittadini di prima classe della timeline. | 13 |  |
| DA-075 | Gli override manuali prevalgono sugli elementi generati automaticamente. | 13 |  |
| DA-076 | La timeline è completamente rigenerabile. | 13 |  |
| DA-077 | La consultazione della timeline non richiede componenti AI attivi. | 13 |  |
| DA-078 | La timeline deve funzionare completamente offline all'interno della chiavetta USB. | 13 |  |
| DA-079 | Il frontend è composto esclusivamente da risorse statiche. | 14 |  |
| DA-080 | Il frontend deve funzionare direttamente da file system senza backend. | 14 |  |
| DA-081 | Ogni paziente possiede un punto di ingresso HTML indipendente. | 14 |  |
| DA-082 | Il frontend deve funzionare completamente offline. | 14 |  |
| DA-083 | Nessuna dipendenza cloud è consentita durante la consultazione. | 14 |  |
| DA-084 | I grafici vengono generati localmente. | 14 |  |
| DA-085 | Il frontend costituisce un artefatto generato e completamente rigenerabile. | 14 |  |
| DA-086 | La consultazione degli studi diagnostici deve supportare l'apertura dei viewer DICOM eventualmente forniti con il supporto originale. | 14 |  |
| DA-087 | Il frontend utilizza file JSON statici generati durante la build e non interroga direttamente SQLite. | 14 |  |
| DA-088 | Il database SQLite viene comunque esportato sulla chiavetta come artefatto tecnico e diagnostico. | 14 |  |
| DA-089 | La chiavetta USB è considerata un supporto di sola lettura durante la consultazione. | 14 |  |
| DA-090 | La ricerca sulla chiavetta opera esclusivamente su indici pre-generati e non effettua indicizzazioni in tempo reale. | 14 |  |
| DA-091 | La build locale è l'unico meccanismo ufficiale di generazione degli artefatti. | 15 |  |
| DA-092 | La modalità incrementale è la modalità operativa predefinita. | 15 |  |
| DA-093 | Ogni paziente viene elaborato indipendentemente. | 15 |  |
| DA-094 | Le cache di build sono completamente rigenerabili. | 15 |  |
| DA-095 | I metadati curati vengono sempre validati prima dell'elaborazione. | 15 |  |
| DA-096 | La build genera un report e un manifest verificabili. | 15 |  |
| DA-097 | Gli artefatti generati non costituiscono sorgente autorevole. | 16 |  |
| DA-098 | SQLite viene conservato come artefatto tecnico indipendente. | 16 |  |
| DA-099 | Gli indici di ricerca vengono generati durante la build. | 16 |  |
| DA-100 | Gli artefatti AI sono opzionali e completamente rigenerabili. | 16 |  |
| DA-101 | Ogni build produce manifest e checksum verificabili. | 16 |  |
| DA-102 | Gli artefatti temporanei non vengono esportati sulla chiavetta USB. | 16 |  |
| DA-103 | La distribuzione USB opera esclusivamente sugli artefatti esportabili. | 16 |  |
| DA-104 | La distribuzione è separata dalla build. | 17 |  |
| DA-105 | Le chiavette sono identificate tramite UUID del filesystem. | 17 |  |
| DA-106 | La modalità incrementale è la modalità di distribuzione predefinita. | 17 |  |
| DA-107 | rsync è il meccanismo preferenziale di sincronizzazione. | 17 |  |
| DA-108 | Ogni paziente possiede un archivio completamente indipendente sulla chiavetta. | 17 |  |
| DA-109 | Le pagine START-HERE costituiscono il punto di ingresso ufficiale per la consultazione. | 17 |  |
| DA-110 | La distribuzione deve verificare l'integrità degli artefatti copiati. | 17 |  |
| DA-111 | Il filesystem raccomandato è exFAT. | 17 |  |
| DA-112 | L'intero contenuto della chiavetta deve poter essere rigenerato a partire dagli artefatti locali. | 17 |  |
| DA-113 | La consultazione deve funzionare completamente offline. | 18 |  |
| DA-114 | Il frontend non utilizza cookie né sistemi di telemetria. | 18 |  |
| DA-115 | La chiavetta è considerata un supporto di sola lettura. | 18 |  |
| DA-116 | La cifratura della chiavetta non fa parte dei requisiti iniziali. | 18 |  |
| DA-117 | La modalità AI locale è la soluzione raccomandata. | 18 |  |
| DA-118 | La perdita degli artefatti generati non comporta perdita di dati autorevoli. | 18 |  |
| DA-119 | Documenti originali, metadati curati e configurazione locale costituiscono il nucleo minimo da preservare per il disaster recovery. | 18 |  |
| DA-120 | Ogni paziente mantiene un isolamento logico completo anche quando più archivi convivono sulla stessa chiavetta. | 18 |  |
| DA-121 | I documenti originali non vengono modificati dalla manutenzione ordinaria. | 19 |  |
| DA-122 | La build incrementale è il flusso operativo raccomandato. | 19 |  |
| DA-123 | I supporti DICOM vengono conservati integralmente. | 19 |  |
| DA-124 | La manutenzione deve preservare la compatibilità con archivi clinici pluridecennali. | 19 |  |
| DA-125 | La chiavetta USB è un supporto di distribuzione e non costituisce un backup. | 19 |  |
| DA-126 | I dati autorevoli da salvaguardare sono i percorsi configurati per documenti originali, metadati curati e configurazione locale. | 19 |  |
| DA-127 | Gli artefatti generati sono completamente rigenerabili e non richiedono backup obbligatorio. | 19 |  |
| DA-128 | Il disaster recovery si basa sul ripristino dei dati autorevoli locali seguito da una Costruzione Completa. | 19 |  |
| DA-129 | La sostituzione di una chiavetta richiede la registrazione del nuovo UUID e una distribuzione completa. | 19 |  |
| DA-130 | La strategia raccomandata prevede almeno un backup locale e un backup esterno indipendente. | 19 |  |
| DA-131 | La recuperabilità dell'archivio deve essere verificata periodicamente mediante test di ripristino. | 19 |  |
| DA-132 | Python costituisce il linguaggio di riferimento dell'implementazione iniziale. | 20 |  |
| DA-133 | SQLite è il database di riferimento. | 20 |  |
| DA-134 | TOML è il formato standard per configurazione e metadati curati. | 20 |  |
| DA-135 | Il frontend utilizza esclusivamente tecnologie web standard. | 20 |  |
| DA-136 | exFAT è il filesystem raccomandato per la distribuzione USB. | 20 |  |
| DA-137 | Le librerie specifiche possono essere sostituite senza modificare l'architettura. | 20 |  |
| DA-138 | La longevità dei dati prevale sulle scelte tecnologiche di implementazione. | 20 |  |
| DA-139 | FHIR e HL7 sono considerati possibili standard di interoperabilità futura. | 21 |  |
| DA-140 | La consultazione assistita da AI non fa parte della versione iniziale. | 21 |  |
| DA-141 | La sincronizzazione cloud non fa parte della versione iniziale. | 21 |  |
| DA-142 | Le evoluzioni future non devono compromettere la consultazione offline. | 21 |  |
| DA-143 | Le evoluzioni future non devono compromettere la longevità degli archivi. | 21 |  |
| DA-144 | La semplicità operativa rimane un criterio prioritario nella valutazione delle nuove funzionalità. | 21 |  |
| DA-145 | I DICOM sono catalogati e non inviati alla pipeline OCR/testo ordinaria. | 8 |  |
| DA-146 | Le immagini sorgente sono documenti OCR tramite Tesseract durante l'ingestione Linux. | 8 |  |
| DA-147 | I path tecnici generici dei viewer restano manifest-only; gli entrypoint HTML DICOM consultabili vengono esportati come subtree relative dedicate. | 8 |  |
| DA-148 | Il riepilogo build distingue documenti sorgente, derivati, istanze DICOM e record totali. | 15 |  |
| DA-149 | L'OCR immagini preferisce `ita+eng` quando disponibile e ricade sul default Tesseract. | 20 |  |
| DA-150 | Gli archivi vengono promossi a supporti DICOM solo in base al contenuto. | 8 |  |
| DA-151 | Il progresso dei comandi lunghi e' diagnostica interattiva su `stderr`. | 15 |  |
| DA-152 | I supporti DICOM annidati nei contenitori vengono espansi ricorsivamente in staging. | 8 |  |
| DA-153 | Il testo estratto dai documenti viene persistito in SQLite e indicizzato in FTS5. | 9 |  |
| DA-154 | `scan-documents` crea lo staging dei container per verifica manuale, salvo opt-out esplicito. | 15 |  |
| DA-155 | Le istanze DICOM leggibili vengono raggruppate per StudyInstanceUID o DICOMDIR e coalescono record duplicati dello stesso studio. | 8 |  |
| DA-156 | La build incrementale riusa il testo estratto per documenti invariati e rigenera il database dall'inventario corrente. | 8 |  |
| DA-157 | Il frontend offline carica i dati essenziali come JavaScript locale per funzionare anche da `file://`. | 12 |  |
| DA-158 | L'export USB verso target esistenti sostituisce il contenuto del target senza rimuovere il mountpoint. | 17 |  |
| DA-159 | I contenuti Markdown vengono renderizzati in HTML statico durante la build con HTML grezzo disabilitato. | 12 |  |
| DA-160 | Il frontend di consultazione usa un layout statico responsive con split view sui monitor larghi, tab sugli schermi stretti e configurazione UI validata in `accounts.toml`. | 12 | [adr-frontend-consultation-ui.md](adr-frontend-consultation-ui.md) |
| DA-161 | La ricerca avanzata offline usa un indice contenuto separato, caricato on-demand da JavaScript locale, con parser booleano e sinonimi configurabili. | 12 | [adr-advanced-offline-search.md](adr-advanced-offline-search.md) |
| DA-162 | La UI di consultazione deve rendere cercabili e visibili documenti, metadati clinici curati e studi DICOM sintetici con risultati federati raggruppati. | 12 | [adr-federated-clinical-search-ui.md](adr-federated-clinical-search-ui.md) |

---

## ADR per Area Funzionale

### Modello Multi-Paziente

| ADR | Titolo | Status |
| ----- | -------- | -------- |
| DA-001 | Ogni paziente possiede un archivio indipendente. |  |
| DA-002 | Ogni paziente possiede un database SQLite indipendente. |  |
| DA-003 | Ogni paziente possiede un frontend indipendente. |  |
| DA-004 | La chiavetta USB può contenere più pazienti. |  |
| DA-005 | La selezione del paziente avviene tramite file HTML dedicati. |  |
| DA-006 | Non esistono dati condivisi tra archivi di pazienti differenti. |  |
| DA-007 | La build e il deploy possono essere eseguiti sia per singolo paziente sia per l'intero insieme dei pazienti configurati. |  |

### Layout del Repository

| ADR | Titolo | Status |
| ----- | -------- | -------- |
| DA-008 | I metadati curati risiedono nel percorso `metadata_directory` configurato per ciascun paziente. |  |
| DA-009 | Tutti gli artefatti generati risiedono nel percorso `local_build` configurato per ciascun paziente. |  |
| DA-010 | La chiavetta USB viene sempre costruita a partire da: `exports/usb-image/` |  |
| DA-011 | Le directory: `generated/`, `exports/`, `logs/` sono considerate completamente rigenerabili. |  |
| DA-012 | La struttura delle categorie documentali è definita dal percorso `source_documents` del singolo paziente e non è vincolata da SaniKey. |  |
| DA-013 | Il repository pubblico non contiene dati personali; configurazione reale, dati paziente, artefatti generati, export e log operativi sono esclusi da Git, mentre gli esempi pubblicabili risiedono sotto `docs/*-example`. |  |

### Configurazione

| ADR | Titolo | Status |
| ----- | -------- | -------- |
| DA-014 | La configurazione è espressa esclusivamente in formato TOML. |  |
| DA-015 | Ogni paziente possiede una sezione dedicata in `accounts.toml`. |  |
| DA-016 | L'UUID della chiavetta è il meccanismo ufficiale di identificazione dei dispositivi di deploy. |  |
| DA-017 | Gli errori di configurazione interrompono sempre l'esecuzione. |  |
| DA-018 | I percorsi dei documenti originali sono configurabili e non devono essere vincolati alla struttura interna del repository. |  |

### Modello Documentale

| ADR | Titolo | Status |
| ----- | -------- | -------- |
| DA-019 | L'identità tecnica del documento è basata su SHA256. |  |
| DA-020 | Il percorso del file è un metadato, non l'identità del documento. |  |
| DA-021 | I documenti originali non vengono modificati. |  |
| DA-022 | Le directory documentali sono categorie dinamiche. |  |
| DA-023 | La serie documentale è distinta dalla categoria. |  |
| DA-024 | Gli studi diagnostici possono collegare referti PDF, supporti DICOM originali e contenuti DICOM estratti. |  |
| DA-025 | I duplicati tecnici vengono segnalati ma non eliminati automaticamente. |  |

### Modello di Identità

| ADR | Titolo | Status |
| ----- | -------- | -------- |
| DA-026 | Le entità cliniche sono distinte dai documenti che le descrivono. |  |
| DA-027 | Medication e Therapy Episode sono entità differenti. |  |
| DA-028 | Observation Series e Document Series sono entità differenti. |  |
| DA-029 | Le campagne di monitoraggio sono entità autonome. |  |
| DA-030 | Ogni entità derivata deve registrare la propria provenienza. |  |
| DA-031 | I metadati curati costituiscono la sorgente autorevole delle entità cliniche. |  |
| DA-032 | I metadati curati sono organizzati per dominio e possono essere partizionati temporalmente. |  |
| DA-033 | Il modello deve supportare archivi sanitari multi-decennali senza richiedere riorganizzazioni strutturali. |  |
| DA-034 | Le procedure cliniche sono entità di primo livello e devono essere distinte sia dai documenti che le descrivono sia dagli eventi timeline che le rappresentano cronologicamente. |  |

### Pipeline di Ingestione

| ADR | Titolo | Status |
| ----- | -------- | -------- |
| DA-035 | La pipeline è incrementale per impostazione predefinita. |  |
| DA-036 | L'OCR viene eseguito solo quando necessario. |  |
| DA-037 | Le informazioni curate hanno sempre precedenza sulle informazioni derivate. |  |
| DA-038 | Le inferenze AI non sono autorevoli fino all'approvazione. |  |
| DA-039 | Ogni fase della pipeline deve poter essere rieseguita senza effetti collaterali. |  |
| DA-040 | Ogni informazione derivata deve conservare la propria provenienza. |  |
| DA-145 | I DICOM sono catalogati e non inviati alla pipeline OCR/testo ordinaria. |  |
| DA-146 | Le immagini sorgente sono documenti OCR tramite Tesseract durante l'ingestione Linux. |  |
| DA-147 | I path tecnici generici dei viewer restano manifest-only; gli entrypoint HTML DICOM consultabili vengono esportati come subtree relative dedicate. |  |
| DA-150 | Gli archivi vengono promossi a supporti DICOM solo in base al contenuto. |  |
| DA-152 | I supporti DICOM annidati nei contenitori vengono espansi ricorsivamente in staging. |  |
| DA-155 | Le istanze DICOM leggibili vengono raggruppate per StudyInstanceUID o DICOMDIR e coalescono record duplicati dello stesso studio. |  |
| DA-156 | La build incrementale riusa il testo estratto per documenti invariati e rigenera il database dall'inventario corrente. |  |
| DA-157 | Il frontend offline carica i dati essenziali come JavaScript locale per funzionare anche da `file://`. |  |
| DA-158 | L'export USB verso target esistenti sostituisce il contenuto del target senza rimuovere il mountpoint. |  |
| DA-159 | I contenuti Markdown vengono renderizzati in HTML statico durante la build con HTML grezzo disabilitato. |  |

### Database SQLite

| ADR | Titolo | Status |
| ----- | -------- | -------- |
| DA-041 | Procedure e Clinical Events sono entità distinte. |  |
| DA-042 | Observation Series e Observation Campaign sono entità distinte. |  |
| DA-043 | SQLite viene esportato integralmente sulla chiavetta USB. |  |
| DA-044 | La ricerca full-text utilizza FTS5. |  |
| DA-045 | Le chiavi esterne SQLite sono obbligatorie. |  |
| DA-153 | Il testo estratto dai documenti viene persistito in SQLite e indicizzato in FTS5. |  |

### Metadati Curati

| ADR | Titolo | Status |
| ----- | -------- | -------- |
| DA-046 | I metadati curati costituiscono la sorgente autorevole delle informazioni strutturate. |  |
| DA-047 | I metadati curati sono conservati esclusivamente in formato TOML. |  |
| DA-048 | I metadati sono organizzati per dominio funzionale. |  |
| DA-049 | I dati longitudinali possono essere partizionati temporalmente. |  |
| DA-050 | Le proposte AI sono conservate separatamente dai dati curati. |  |
| DA-051 | I metadati curati non sono rigenerabili. |  |
| DA-052 | Errori nei metadati curati interrompono la pipeline. |  |
| DA-053 | Documenti originali e metadati curati costituiscono insieme la sorgente autorevole dell'intero sistema. |  |

### Generazione e Assistenza AI

| ADR | Titolo | Status |
| ----- | -------- | -------- |
| DA-054 | L'AI è utilizzata esclusivamente durante build e manutenzione. |  |
| DA-055 | L'AI non possiede autorità clinica. |  |
| DA-056 | Le proposte AI richiedono sempre approvazione umana. |  |
| DA-057 | Le proposte AI vengono memorizzate in file TOML separati dai metadati curati. |  |
| DA-058 | Le funzionalità fondamentali del sistema non dipendono dall'AI. |  |
| DA-059 | Ogni informazione generata dall'AI deve conservare informazioni complete di provenienza. |  |
| DA-060 | Le elaborazioni AI devono utilizzare una cache incrementale per evitare rigenerazioni inutili di archivi storici di grandi dimensioni. |  |

### Ricerca

| ADR | Titolo | Status |
| ----- | -------- | -------- |
| DA-061 | La ricerca lessicale è obbligatoria. |  |
| DA-062 | La ricerca semantica è opzionale. |  |
| DA-063 | La ricerca deve funzionare completamente offline. |  |
| DA-064 | Gli embeddings vengono generati esclusivamente durante la build. |  |
| DA-065 | La ricerca interroga simultaneamente documenti ed entità cliniche. |  |
| DA-066 | I metadati curati sono indicizzati e ricercabili. |  |
| DA-067 | Le proposte AI non approvate non compaiono nei risultati standard. |  |
| DA-068 | La consultazione non richiede modelli AI attivi. |  |
| DA-069 | La ricerca deve rimanere utilizzabile anche in assenza completa di funzionalità semantiche. |  |
| DA-161 | La ricerca avanzata offline usa un indice contenuto separato, caricato on-demand da JavaScript locale, con parser booleano e sinonimi configurabili. | [adr-advanced-offline-search.md](adr-advanced-offline-search.md) |
| DA-162 | La UI di consultazione deve rendere cercabili e visibili documenti, metadati clinici curati e studi DICOM sintetici con risultati federati raggruppati. | [adr-federated-clinical-search-ui.md](adr-federated-clinical-search-ui.md) |

### Timeline Clinica

| ADR | Titolo | Status |
| ----- | -------- | -------- |
| DA-070 | La timeline è una vista derivata e non una sorgente autorevole. |  |
| DA-071 | La timeline supporta sia eventi puntuali sia intervalli temporali. |  |
| DA-072 | Le terapie sono rappresentate come intervalli temporali. |  |
| DA-073 | Le campagne osservative sono rappresentate come intervalli temporali. |  |
| DA-074 | Gli eventi manuali sono cittadini di prima classe della timeline. |  |
| DA-075 | Gli override manuali prevalgono sugli elementi generati automaticamente. |  |
| DA-076 | La timeline è completamente rigenerabile. |  |
| DA-077 | La consultazione della timeline non richiede componenti AI attivi. |  |
| DA-078 | La timeline deve funzionare completamente offline all'interno della chiavetta USB. |  |

### Frontend

| ADR | Titolo | Status |
| ----- | -------- | -------- |
| DA-079 | Il frontend è composto esclusivamente da risorse statiche. |  |
| DA-080 | Il frontend deve funzionare direttamente da file system senza backend. |  |
| DA-081 | Ogni paziente possiede un punto di ingresso HTML indipendente. |  |
| DA-082 | Il frontend deve funzionare completamente offline. |  |
| DA-083 | Nessuna dipendenza cloud è consentita durante la consultazione. |  |
| DA-084 | I grafici vengono generati localmente. |  |
| DA-085 | Il frontend costituisce un artefatto generato e completamente rigenerabile. |  |
| DA-086 | La consultazione degli studi diagnostici deve supportare l'apertura dei viewer DICOM eventualmente forniti con il supporto originale. |  |
| DA-087 | Il frontend utilizza file JSON statici generati durante la build e non interroga direttamente SQLite. |  |
| DA-088 | Il database SQLite viene comunque esportato sulla chiavetta come artefatto tecnico e diagnostico. |  |
| DA-089 | La chiavetta USB è considerata un supporto di sola lettura durante la consultazione. |  |
| DA-090 | La ricerca sulla chiavetta opera esclusivamente su indici pre-generati e non effettua indicizzazioni in tempo reale. |  |

### Costruzione Locale

| ADR | Titolo | Status |
| ----- | -------- | -------- |
| DA-091 | La build locale è l'unico meccanismo ufficiale di generazione degli artefatti. |  |
| DA-092 | La modalità incrementale è la modalità operativa predefinita. |  |
| DA-093 | Ogni paziente viene elaborato indipendentemente. |  |
| DA-094 | Le cache di build sono completamente rigenerabili. |  |
| DA-095 | I metadati curati vengono sempre validati prima dell'elaborazione. |  |
| DA-096 | La build genera un report e un manifest verificabili. |  |
| DA-148 | Il riepilogo build distingue documenti sorgente, derivati, istanze DICOM e record totali. |  |
| DA-151 | Il progresso dei comandi lunghi e' diagnostica interattiva su `stderr`. |  |
| DA-154 | `scan-documents` crea lo staging dei container per verifica manuale, salvo opt-out esplicito. |  |

### Artefatti Generati

| ADR | Titolo | Status |
| ----- | -------- | -------- |
| DA-097 | Gli artefatti generati non costituiscono sorgente autorevole. |  |
| DA-098 | SQLite viene conservato come artefatto tecnico indipendente. |  |
| DA-099 | Gli indici di ricerca vengono generati durante la build. |  |
| DA-100 | Gli artefatti AI sono opzionali e completamente rigenerabili. |  |
| DA-101 | Ogni build produce manifest e checksum verificabili. |  |
| DA-102 | Gli artefatti temporanei non vengono esportati sulla chiavetta USB. |  |
| DA-103 | La distribuzione USB opera esclusivamente sugli artefatti esportabili. |  |

### Distribuzione USB

| ADR | Titolo | Status |
| ----- | -------- | -------- |
| DA-104 | La distribuzione è separata dalla build. |  |
| DA-105 | Le chiavette sono identificate tramite UUID del filesystem. |  |
| DA-106 | La modalità incrementale è la modalità di distribuzione predefinita. |  |
| DA-107 | rsync è il meccanismo preferenziale di sincronizzazione. |  |
| DA-108 | Ogni paziente possiede un archivio completamente indipendente sulla chiavetta. |  |
| DA-109 | Le pagine START-HERE costituiscono il punto di ingresso ufficiale per la consultazione. |  |
| DA-110 | La distribuzione deve verificare l'integrità degli artefatti copiati. |  |
| DA-111 | Il filesystem raccomandato è exFAT. |  |
| DA-112 | L'intero contenuto della chiavetta deve poter essere rigenerato a partire dagli artefatti locali. |  |

### Sicurezza e Privacy

| ADR | Titolo | Status |
| ----- | -------- | -------- |
| DA-113 | La consultazione deve funzionare completamente offline. |  |
| DA-114 | Il frontend non utilizza cookie né sistemi di telemetria. |  |
| DA-115 | La chiavetta è considerata un supporto di sola lettura. |  |
| DA-116 | La cifratura della chiavetta non fa parte dei requisiti iniziali. |  |
| DA-117 | La modalità AI locale è la soluzione raccomandata. |  |
| DA-118 | La perdita degli artefatti generati non comporta perdita di dati autorevoli. |  |
| DA-119 | Documenti originali, metadati curati e configurazione locale costituiscono il nucleo minimo da preservare per il disaster recovery. |  |
| DA-120 | Ogni paziente mantiene un isolamento logico completo anche quando più archivi convivono sulla stessa chiavetta. |  |

### Operazioni e Manutenzione

| ADR | Titolo | Status |
| ----- | -------- | -------- |
| DA-121 | I documenti originali non vengono modificati dalla manutenzione ordinaria. |  |
| DA-122 | La build incrementale è il flusso operativo raccomandato. |  |
| DA-123 | I supporti DICOM vengono conservati integralmente. |  |
| DA-124 | La manutenzione deve preservare la compatibilità con archivi clinici pluridecennali. |  |
| DA-125 | La chiavetta USB è un supporto di distribuzione e non costituisce un backup. |  |
| DA-126 | I dati autorevoli da salvaguardare sono i percorsi configurati per documenti originali, metadati curati e configurazione locale. |  |
| DA-127 | Gli artefatti generati sono completamente rigenerabili e non richiedono backup obbligatorio. |  |
| DA-128 | Il disaster recovery si basa sul ripristino dei dati autorevoli locali seguito da una Costruzione Completa. |  |
| DA-129 | La sostituzione di una chiavetta richiede la registrazione del nuovo UUID e una distribuzione completa. |  |
| DA-130 | La strategia raccomandata prevede almeno un backup locale e un backup esterno indipendente. |  |
| DA-131 | La recuperabilità dell'archivio deve essere verificata periodicamente mediante test di ripristino. |  |

### Requisiti Tecnici

| ADR | Titolo | Status |
| ----- | -------- | -------- |
| DA-132 | Python costituisce il linguaggio di riferimento dell'implementazione iniziale. |  |
| DA-133 | SQLite è il database di riferimento. |  |
| DA-134 | TOML è il formato standard per configurazione e metadati curati. |  |
| DA-135 | Il frontend utilizza esclusivamente tecnologie web standard. |  |
| DA-136 | exFAT è il filesystem raccomandato per la distribuzione USB. |  |
| DA-137 | Le librerie specifiche possono essere sostituite senza modificare l'architettura. |  |
| DA-138 | La longevità dei dati prevale sulle scelte tecnologiche di implementazione. |  |
| DA-149 | L'OCR immagini preferisce `ita+eng` quando disponibile e ricade sul default Tesseract. |  |

### Questioni Aperte e Possibili Evoluzioni

| ADR | Titolo | Status |
| ----- | -------- | -------- |
| DA-139 | FHIR e HL7 sono considerati possibili standard di interoperabilità futura. |  |
| DA-140 | La consultazione assistita da AI non fa parte della versione iniziale. |  |
| DA-141 | La sincronizzazione cloud non fa parte della versione iniziale. |  |
| DA-142 | Le evoluzioni future non devono compromettere la consultazione offline. |  |
| DA-143 | Le evoluzioni future non devono compromettere la longevità degli archivi. |  |
| DA-144 | La semplicità operativa rimane un criterio prioritario nella valutazione delle nuove funzionalità. |  |
