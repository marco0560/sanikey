# Pulizia repository 2026-08-02

Questo registro documenta gli oggetti rimossi per mantenere nel repository solo
codice, test, strumenti e documentazione utili allo sviluppo corrente.

## Ultima raggiungibilita'

Ogni oggetto in questo elenco era ancora raggiungibile nel commit
`44e53a42c9b5cc58cd76552e651ed27bfc91c04d`
(`fix(generation): reduced upper frame elemens in small and medium screens`),
immediatamente precedente a questa pulizia.

| Categoria | Oggetti rimossi | Motivo |
| --- | --- | --- |
| Script non integrati | `scripts/generate_github_snapshot.py`; `scripts/run_with_repo_python.sh` | Nessun invocatore in CI, hook, alias, test o guida operativa. |
| Wrapper CLI | `scripts/sanikey_command.py`; `scripts/list_patients.py`; `scripts/scan_documents.py`; `scripts/extract_text.py`; `scripts/process_dicom.py`; `scripts/build_database.py`; `scripts/generate_embeddings.py`; `scripts/generate_timeline.py`; `scripts/generate_clinical_summary.py`; `scripts/build_web.py`; `scripts/export_usb.py`; `scripts/validate_usb.py`; `scripts/deploy_usb.py`; `scripts/build_patient.py`; `scripts/build_all.py`; `scripts/update_archive.py` | Duplicavano la CLI ufficiale `uv run sanikey ...` e non partecipavano ai flussi eseguibili del repository. |
| Scaffold AI | `src/sanikey/proposals.py`; `tests/test_proposals.py` | Funzionalita' sperimentale dichiarata non utilizzabile per la consegna e priva di integrazione clinica. |
| Test dello scaffold | Casi proposal in `tests/test_cli.py` e `tests/test_exports.py` | Coprivano esclusivamente la superficie rimossa. |
| Documentazione storica | `docs/process/initial-implementation.md`; `docs/process/longitudinal-clinical-parameter-slices-implementation-plan.md`; `docs/process/sanikey-desktop-implementation-plan.md`; `docs/process/stato-dei-test.md` | Registro o piani superati, non necessari per il flusso di sviluppo corrente. |
| Specifiche superate | `docs/sanikey-high-level-spec.md`; `docs/sanikey-detailed-spec.md` | Duplicavano o contraddicevano la documentazione corrente, in particolare `docs/architecture.md` e le ADR attive. |
| ADR di spike | `docs/decisions/adr-cornerstone3d-offline-spike.md`; `docs/decisions/adr-dwv-offline-spike.md` | Esperimenti DICOM non adottati; la politica corrente resta nelle ADR attive e nel runbook DICOM. |

Le immagini non sono state incluse nella pulizia.
