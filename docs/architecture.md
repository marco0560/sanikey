# SaniKey - Archivio Medico Portatile

## 1. Obiettivo

SaniKey è un sistema di archiviazione, indicizzazione e consultazione di documentazione medica personale.

Il sistema è progettato per:

* conservare i documenti originali;
* supportare PDF, immagini disco DICOM e relativi contenuti estratti;
* generare automaticamente una timeline clinica;
* generare automaticamente una bozza di storia clinica;
* consentire ricerca full-text istantanea;
* consentire ricerca semantica opzionale;
* produrre una chiavetta USB completamente autonoma e consultabile tramite browser;
* non richiedere installazione di software sul computer del medico;
* preservare la separazione tra dati generati automaticamente e dati revisionati dall'utente.

---

# 2. Principi architetturali

## 2.1 Sorgente autorevole

La sorgente autorevole è il repository SaniKey.

La chiavetta USB è un artefatto generato.

```text
Repository SaniKey
    ↓
Build
    ↓
Chiavetta USB
```

Non si effettuano modifiche direttamente sulla chiavetta.

---

## 2.2 Dati rigenerabili

Sono considerati rigenerabili:

* database SQLite;
* OCR;
* indice full-text;
* timeline generata;
* ricerca semantica;
* JSON frontend.

Possono essere eliminati e ricostruiti in qualsiasi momento.

---

## 2.3 Dati curati

Sono considerati dati curati:

* classificazioni manuali;
* conferme/correzioni AI;
* storia clinica approvata;
* alias e serie documentali.

Devono essere conservati separatamente dai dati rigenerabili.

---

# 3. Struttura repository

```text
medical-archive/
│
├── documents/
│
├── metadata/
│
├── database/
│
├── generated/
│
├── web/
│
├── scripts/
│
├── models/
│
└── exports/
```

---

# 4. Struttura documenti

```text
documents/
│
├── AccessiPS/
├── Analisi/
├── Artrosi/
├── ASL-Generalista/
├── Cardiologo/
├── Dermatologo/
├── Diabete/
├── Ecografie-TAC-RMN-RX/
├── Fisiatra/
├── Gastroenterologia/
├── Genetista/
├── Invalidità/
├── Nefrologo/
├── Neurologia-Ortopedia/
├── Obesità/
├── Oculista/
├── OSAS-ORL-Pneumo/
├── Proctologo/
├── Psichiatria/
└── Terapia del dolore/
```

Convenzione file:

```text
AAAAMMGG Titolo.pdf
```

Esempi:

```text
20240312 Analisi.pdf
20260921 Operazione Cataratta.pdf
```

---

# 5. Gestione DICOM

## 5.1 Originale

```text
documents/
└── Ecografie-TAC-RMN-RX/
    └── Dischi/
        └── 20250318_RMN_Anca.iso
```

L'immagine disco viene sempre conservata.

---

## 5.2 Estrazione

```text
generated/dicom/
└── 20250318_RMN_Anca/
```

Contiene:

* DICOMDIR;
* file DICOM;
* viewer eventualmente presente.

---

## 5.3 Metadati indicizzati

* data esame;
* modalità (RMN/TAC/RX/ECO);
* distretto anatomico;
* struttura sanitaria;
* numero immagini;
* presenza viewer.

---

# 6. Database SQLite

Database:

```text
database/medical_archive.db
```

---

## 6.1 documents

```sql
CREATE TABLE documents (
    id INTEGER PRIMARY KEY,
    sha256 TEXT UNIQUE NOT NULL,
    path TEXT NOT NULL,
    filename TEXT NOT NULL,
    document_type TEXT NOT NULL,
    category TEXT NOT NULL,
    document_date TEXT,
    title TEXT,
    file_size INTEGER,
    created_at TEXT,
    updated_at TEXT
);
```

---

## 6.2 document_series

```sql
CREATE TABLE document_series (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT
);
```

Esempi:

```text
Analisi
Ecocardiogramma
Visita Cardiologica
RMN Anca
```

---

## 6.3 document_series_members

```sql
CREATE TABLE document_series_members (
    document_id INTEGER,
    series_id INTEGER,
    PRIMARY KEY(document_id, series_id)
);
```

---

## 6.4 extracted_text

```sql
CREATE TABLE extracted_text (
    document_id INTEGER PRIMARY KEY,
    content TEXT NOT NULL
);
```

---

## 6.5 FTS5

```sql
CREATE VIRTUAL TABLE documents_fts
USING fts5(
    title,
    category,
    content,
    tokenize='unicode61'
);
```

---

## 6.6 embeddings (opzionale)

```sql
CREATE TABLE embeddings (
    document_id INTEGER PRIMARY KEY,
    model TEXT NOT NULL,
    vector BLOB NOT NULL
);
```

---

## 6.7 timeline_events

```sql
CREATE TABLE timeline_events (
    id INTEGER PRIMARY KEY,
    document_id INTEGER,
    event_date TEXT,
    event_title TEXT,
    importance INTEGER
);
```

---

# 7. Metadati curati

Formato:

```text
metadata/*.toml
```

Motivazioni:

* sintassi rigorosa;
* assenza di problemi di indentazione;
* ottimo supporto Python;
* buona leggibilità.

---

# 8. Tag manuali

File:

```text
metadata/document_tags.toml
```

Esempio:

```toml
[[document]]
sha256 = "abc123"

tags = [
  "diabete",
  "nefrologia"
]
```

---

# 9. Problemi clinici

File:

```text
metadata/problems.toml
```

Esempio:

```toml
[[problem]]
name = "Diabete tipo 2"

tags = [
  "diabete"
]
```

---

# 10. Farmaci

File:

```text
metadata/medications.toml
```

Esempio:

```toml
[[medication]]
name = "Metformina"
dose = "1000 mg"
status = "active"
```

---

# 11. Storia clinica

File:

```text
metadata/clinical_summary.toml
```

Generato da AI e revisionato dall'utente.

Esempio:

```toml
title = "Storia Clinica"

summary = """
Paziente con obesità severa,
diabete tipo 2,
OSAS,
artrosi anca destra.
"""
```

L'AI genera una nuova proposta.

L'utente approva o modifica.

La versione approvata è la sorgente autorevole.

---

# 12. OCR

Pipeline:

```text
PDF
 ├── contiene testo
 │     ↓
 │   estrazione
 │
 └── scansione
       ↓
    OCR
```

Strumenti consigliati:

* PyMuPDF
* OCRmyPDF
* Tesseract

L'OCR viene eseguito una sola volta.

---

# 13. Ricerca semantica (opzionale)

Pipeline:

```text
Testo
   ↓
Embedding
   ↓
SQLite
```

Funzione:

* supportare ricerche concettuali;
* non sostituire la ricerca lessicale.

La ricerca lessicale resta sempre disponibile.

---

# 14. Frontend

Artefatto finale:

```text
web/
├── index.html
├── app.js
├── search.json
├── timeline.json
├── summary.json
└── assets/
```

---

# 15. Home page

Contiene:

* dati paziente;
* problemi clinici;
* farmaci attivi;
* allergie;
* accesso ricerca;
* accesso timeline.

---

# 16. Ricerca

Ricerca istantanea su:

* titolo;
* categoria;
* tag;
* testo OCR.

Filtri:

* categoria;
* anno;
* tipo documento;
* serie documentale.

---

# 17. Timeline

Visualizzazione:

```text
2026
 ├─ Operazione Cataratta
 ├─ Visita Cardiologica
 │
2025
 ├─ RMN Anca
```

Ogni evento apre il documento.

---

# 18. Scheda documento

Mostra:

* data;
* categoria;
* serie documentale;
* tag;
* estratto OCR;
* documenti correlati.

Azioni:

```text
Apri PDF
Apri ISO
Apri cartella DICOM
```

---

# 19. Generazione chiavetta

Output:

```text
exports/USB/
│
├── index.html
├── assets/
├── data/
├── documenti/
└── STORIA_CLINICA.pdf
```

Il contenuto è completamente statico.

Nessuna installazione richiesta.

---

# 20. Script

## scan_documents.py

Responsabilità:

* scansione repository;
* calcolo SHA256;
* rilevamento modifiche.

---

## extract_text.py

Responsabilità:

* estrazione PDF;
* OCR.

---

## process_dicom.py

Responsabilità:

* estrazione ISO;
* lettura DICOMDIR;
* raccolta metadati.

---

## build_database.py

Responsabilità:

* popolamento SQLite;
* FTS5.

---

## generate_embeddings.py

Responsabilità:

* ricerca semantica opzionale.

---

## generate_timeline.py

Responsabilità:

* timeline automatica;
* proposte eventi.

---

## generate_clinical_summary.py

Responsabilità:

* proposta storia clinica;
* aggiornamento incrementale.

---

## build_web.py

Responsabilità:

* esportazione JSON;
* generazione frontend.

---

## export_usb.py

Responsabilità:

* costruzione artefatto finale.

---

## update_archive.py

Orchestratore principale.

Pipeline:

```text
scan_documents
      ↓
extract_text
      ↓
process_dicom
      ↓
build_database
      ↓
generate_embeddings
      ↓
generate_timeline
      ↓
generate_clinical_summary
      ↓
build_web
      ↓
export_usb
```

---

# 21. Questioni aperte

## Ricerca semantica

### Pro

* trova concetti correlati;
* migliora recupero documenti.

### Contro

* maggiore complessità;
* necessità di modello embedding.

Decisione proposta:

```text
Supportata ma opzionale.
```

---

## AI locale o cloud

### Locale

Pro:

* privacy.

Contro:

* più lenta.

### Cloud

Pro:

* migliore qualità.

Contro:

* dati sanitari fuori dal controllo locale.

Decisione da prendere in fase implementativa.

---

## Viewer DICOM

Decisione proposta:

```text
Non implementare viewer dedicato.
```

Il sistema:

* conserva ISO;
* conserva contenuto estratto;
* consente apertura dei file originali.

---

# 22. Obiettivo finale

Il medico inserisce la chiavetta e apre:

```text
index.html
```

Da quel momento può:

* consultare la storia clinica;
* cercare qualunque parola presente nei documenti;
* navigare la timeline;
* aprire PDF;
* aprire studi DICOM;
* consultare documenti correlati;

senza installare alcun software e senza dipendere da servizi online.
