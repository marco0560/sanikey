# Script

## `scripts/bootstrap_dev_environment.py`

Sincronizza l'ambiente gestito da uv, configura lo stato Git locale ed esegue
opzionalmente la validazione.

Lo script verifica la radice del repository ed esegue `uv pip check` dopo la
sincronizzazione delle dipendenze.

## `scripts/install_repo_git_config.py`

Installa la configurazione Git locale attesa dal progetto generato, inclusi
hook, template di commit e alias autorizzati.

## `scripts/run_repo_tool.py`

Esegue gli strumenti autorizzati del repository mantenendo cache e stato
temporaneo fuori dal checkout.

## `scripts/validate_repo.py`

Esegue la sequenza standard di validazione locale tramite
`scripts/run_repo_tool.py`.

Stato:

- installato come `git check` dallo script di bootstrap
- esegue `scripts/privacy_guard.py` per bloccare dati locali e path host-locali
  in file tracciati o nuovi non ignorati che finirebbero nel commit
- aggiorna l'indice Codira ed esegue `codira audit`
- esegue la suite di test sotto coverage ed emette `.coverage-report.json`
- esclude Semgrep per default; rigenerare con `--with-semgrep` per attivarlo

Il guard privacy controlla il contenuto che Git vede come tracciato o nuovo non
ignorato. Blocca directory private versionate, per esempio `local-data/` o
`config/`, e riferimenti a path locali dell'host come home directory
POSIX/Windows o path costruiti dalla variabile d'ambiente `HOME`. Non classifica
semanticamente qualunque testo clinico: dati reali, screenshot e log devono
restare fuori dai file tracciati.

## `scripts/privacy_guard.py`

Valida gli invarianti privacy applicabili al contenuto che può entrare in un
commit. Lo script è richiamato da `scripts/validate_repo.py`, ma può essere
eseguito anche direttamente per isolare una violazione.

## `scripts/coverage_summary.py`

Renderizza un riepilogo compatto della coverage da `.coverage-report.json` e
applica la soglia di coverage del repository.

## `scripts/clean_repo.py`

Rimuove artefatti ignorati di build e cache preservando directory locali
protette come `.venv`.

## `scripts/generate_cheatsheet.py`

Rigenera `docs/cheatsheet.md` dai frammenti marcati nella documentazione.

## `scripts/new_decision.py`

Crea una nuova nota decisionale in `docs/decisions/` e aggiorna l'indice.

## `scripts/pyproject_lint.py`

Esegue la validazione strutturale deterministica di `pyproject.toml`.

## `scripts/replace_usb_logo.py`

Sostituisce il logo in tutte le pagine paziente di una chiavetta SaniKey gia'
esportata, ricostruisce i checksum del manifest e valida il risultato. Accetta
un file SVG, il mountpoint della chiavetta e una percentuale opzionale per la
dimensione del logo:

```bash
uv run python scripts/replace_usb_logo.py immagini/SaniKey-logo-horizontal-transparent.svg /media/SANIKEY
uv run python scripts/replace_usb_logo.py immagini/SaniKey-logo-horizontal-transparent.svg /media/SANIKEY 150
```

Il comando agisce esclusivamente sui pazienti elencati nel manifest della
chiavetta e aggiorna `assets/sanikey-logo-horizontal-transparent.svg` per
ciascuno di essi. La
percentuale predefinita e' `100`: `150` ingrandisce il logo del 50%, mentre
`75` lo riduce al 75% della dimensione corrente.

## `scripts/release_audit.sh`

Esegue controlli conservativi di sicurezza prima di inviare tag o pubblicare.

Questo script implementa `git release-audit`.

## `scripts/tag_guard.sh`

Valida che un tag di rilascio rispetti il pattern atteso `vX.Y.Z`.

## `scripts/changelog_guard.sh`

Valida che `CHANGELOG.md` contenga la sezione attesa `Unreleased`.

## Script di Compatibilità SaniKey

La prima implementazione espone le operazioni principalmente tramite la CLI
`sanikey`. Gli script seguenti sono wrapper di compatibilità che delegano ai
sottocomandi CLI corrispondenti:

- `scripts/list_patients.py`
- `scripts/scan_documents.py`
- `scripts/extract_text.py`
- `scripts/process_dicom.py`
- `scripts/build_database.py`
- `scripts/generate_embeddings.py`
- `scripts/generate_timeline.py`
- `scripts/generate_clinical_summary.py`
- `scripts/build_web.py`
- `scripts/export_usb.py`
- `scripts/validate_usb.py`
- `scripts/deploy_usb.py`
- `scripts/build_patient.py`
- `scripts/build_all.py`
- `scripts/update_archive.py`

La configurazione reale resta sotto `config/`, directory ignorata da Git. Gli
esempi pubblici vivono sotto `docs/config-example/`, `docs/patients-example/` e
`docs/generated-example/`.
