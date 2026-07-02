# SaniKey - Archivio Medico Portatile

## 1. Obiettivo

SaniKey è un sistema multi-paziente per archiviazione, indicizzazione e consultazione di documentazione medica personale mediante chiavetta USB autonoma consultabile da browser.

Obiettivi:
- Conservazione documenti originali.
- Supporto PDF e studi DICOM.
- Ricerca full-text istantanea.
- Timeline clinica generata e revisionabile.
- Bozza di storia clinica assistita da AI e approvata dopo revisione.
- Nessuna installazione sul PC del medico.
- Supporto più membri della stessa famiglia sulla stessa chiavetta.

---

## 2. Architettura

Repository SaniKey
    -> Costruzione locale per paziente
    -> Esportazione USB
    -> Consultazione browser

Principi:
- Repository pubblico = codice, documentazione ed esempi pubblicabili.
- Configurazione reale e dati paziente = sorgente autorevole locale esclusa da Git.
- USB = artefatto generato.
- Dati curati separati dai dati rigenerabili.
- Ricerca lessicale obbligatoria.
- Ricerca semantica opzionale.

---

## 3. Modello Multi-Paziente

Ogni paziente possiede un archivio indipendente.

Esempio:

patients/
  patient-a/
  patient-b/

La chiavetta contiene:

START-HERE-Patient-A.html
START-HERE-Patient-B.html

patients/
  patient-a/
  patient-b/

Ogni archivio è consultabile indipendentemente.

---

## 4. Repository

sanikey/
  scripts/
  web/
  models/
  docs/
    config-example/
    patients-example/
    generated-example/

Le directory locali config/, patients/, generated/, exports/ e logs/ contengono
dati reali o artefatti derivati e sono escluse dal repository pubblico.

---

## 5. Configurazione

File:

config/accounts.toml

Esempio:

[global]
repository_version = "1"

[[person]]
id = "patient-a"
display_name = "Paziente A"
source_documents = "/percorso/assoluto/patient-a/documents"
metadata_directory = "/percorso/assoluto/patient-a/metadata"
local_build = "/percorso/assoluto/patient-a/generated"
usb_uuid = "1A2B-3C4D"

[[person]]
id = "patient-b"
display_name = "Paziente B"
source_documents = "/percorso/assoluto/patient-b/documents"
metadata_directory = "/percorso/assoluto/patient-b/metadata"
local_build = "/percorso/assoluto/patient-b/generated"
usb_uuid = "1A2B-3C4D"

Il campo usb_uuid identifica la chiavetta autorizzata.

I percorsi possono essere assoluti oppure relativi alla root del repository
quando la configurazione e' `config/accounts.toml`. Per dati locali non
versionati dentro il checkout si usa convenzionalmente `local-data/...`.

Non esistono percorsi predefiniti per dati reali.

---

## 6. Documenti

Convenzione:

AAAAMMGG Titolo.pdf

Esempi:

20240312 Analisi.pdf
20260921 Operazione Cataratta.pdf

Categorie libere organizzate in directory.

---

## 7. DICOM

Conservare:
- Supporto originale consegnato dall'ospedale, ISO o ZIP.
- Contenuto estratto come artefatto generato.
- Metadati DICOM.

Struttura:

Dischi/
  20250318_RMN_Anca.iso
  20250318_RMN_Anca.zip

generated/<patient>/dicom/
  20250318_RMN_Anca/

La scelta tra espansione automatica, opzionale in ingestion o manuale resta da
decidere.

Metadati:
- data
- modalità
- distretto
- provenienza
- numero immagini
- viewer presente

---

## 8. Database

Un database SQLite per paziente.

generated/<patient>/database/medical_archive.db

Tabelle principali:

documents
document_series
document_series_members
extracted_text
timeline_events
embeddings

FTS5 obbligatorio.

---

## 9. Serie Documentali

Consentono di raggruppare documenti correlati.

Esempi:

- Analisi
- Ecocardiogramma
- Visita Cardiologica
- RMN Anca

---

## 10. Metadati Curati

Formato TOML.

File:

document_tags.toml
problems.toml
medications.toml
clinical_summary.toml

Motivazione:
- sintassi rigorosa
- nessun problema di indentazione
- buona leggibilità

---

## 11. OCR

Pipeline:

PDF
 -> testo presente -> estrazione
 -> scansione -> OCR

Strumenti:
- PyMuPDF
- OCRmyPDF
- Tesseract

---

## 12. AI

Utilizzata esclusivamente in build.

Funzioni:
- proposta timeline
- proposta problemi clinici
- proposta storia clinica
- estrazione farmaci

Tutte le proposte richiedono approvazione.

---

## 13. Ricerca

### Lessicale

Obbligatoria.

Indicizza:
- titolo
- categoria
- tag
- testo OCR

### Semantica

Opzionale.

Basata su embeddings precomputati.

---

## 14. Frontend

Generato staticamente.

web/
  index.html
  app.js
  search.json
  timeline.json
  summary.json

Il browser non accede direttamente a SQLite.

---

## 15. Pagina Iniziale

Visualizza:
- dati paziente
- problemi clinici
- farmaci
- allergie
- ricerca
- timeline

---

## 16. Scheda Documento

Visualizza:
- data
- categoria
- serie
- tag
- estratto OCR

Azioni:
- Apri PDF
- Apri supporto DICOM originale
- Apri Cartella DICOM

---

## 17. Esportazione USB

Struttura:

USB/
  START-HERE-Patient-A.html
  START-HERE-Patient-B.html
  patients/
    patient-a/
      medical_archive.db
      web/
      documents/
    patient-b/
      medical_archive.db
      web/
      documents/

Contenuto completamente statico.

---

## 18. Manifest USB

SANIKEY-MANIFEST.toml

Contiene:
- versione
- timestamp generazione
- elenco pazienti
- UUID atteso

---

## 19. Deploy USB

Script:

deploy_usb.py

Funzioni:
- rileva chiavetta
- verifica UUID
- verifica spazio disponibile
- sincronizza contenuto
- valida risultato

Ordine preferenziale:

1. rsync
2. robocopy
3. shutil

---

## 20. Script

scan_documents.py
extract_text.py
process_dicom.py
build_database.py
generate_embeddings.py
generate_timeline.py
generate_clinical_summary.py
build_web.py
export_usb.py
validate_usb.py
deploy_usb.py
build_patient.py
build_all.py
list_patients.py
update_archive.py

---

## 21. Flusso Operativo

Aggiornamento:

update_archive.py
 -> scansione
 -> OCR
 -> DICOM
 -> SQLite
 -> FTS
 -> AI
 -> timeline
 -> frontend

Distribuzione:

deploy_usb.py
 -> verifica chiavetta
 -> controllo spazio
 -> sincronizzazione
 -> validazione

---

## 22. Obiettivo Finale

Il medico inserisce la chiavetta, apre il file START-HERE del paziente interessato e può:
- consultare storia clinica
- effettuare ricerche
- navigare timeline
- aprire PDF
- aprire studi DICOM

senza installare software e senza connessione Internet.
