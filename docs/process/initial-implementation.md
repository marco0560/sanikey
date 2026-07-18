# Registro dell'Implementazione Iniziale

Questo registro traccia fase per fase l'implementazione di SaniKey v1.

Branch: `initial-implementation`

Nota: il piano approvato indicava `feat/initial-implementation`, ma questo
checkout ha un conflitto di namespace Git per `feat/...`. Il branch dedicato è
quindi `initial-implementation`.

Ogni fase può essere marcata come completata solo dopo codice, test,
documentazione, validazione del repository e commit della fase.

## Elementi Rimandati

Gli elementi seguenti sono fuori ambito per questo branch di implementazione
iniziale e restano rimandati per scelta progettuale:

* provider AI locali o remoti reali;
* espansione automatica o opzionale di ISO e archivi DICOM riconosciuti dal contenuto;
* embedding semantici oltre a interfacce disabilitate stabili;
* cifratura USB;
* integrazione FHIR o HL7;
* pacchettizzazione mobile o PWA;
* sincronizzazione cloud;
* consultazione assistita da AI durante l'uso dell'archivio;
* pacchettizzazione desktop.

## Registro delle Fasi

| Fase | Ambito | Intervallo ADR | Completata | Evidenza di Validazione | Commit |
| ---- | ------ | -------------- | ---------- | ----------------------- | ------ |
| 01 | Preflight e registro | DA-001..DA-144 | [x] | `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/validate_repo.py` superato | `4b10c5b` |
| 02 | Configurazione core e guardia privacy | DA-008..DA-018, DA-113..DA-120 | [x] | `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/validate_repo.py` superato | `e10c88c` |
| 03 | Modelli di dominio e contratti metadati | DA-019..DA-053 | [x] | `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/validate_repo.py` superato | `23719b0` |
| 04 | Inventario documenti ed estrazione testo | DA-019..DA-040, DA-121..DA-124 | [x] | `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/validate_repo.py` superato | `4c5ec39` |
| 05 | Catalogo DICOM | DA-024, DA-086, DA-123 | [x] | `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/validate_repo.py` superato | `a7796e0` |
| 06 | Archivio SQLite | DA-001..DA-003, DA-041..DA-045, DA-098 | [x] | `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/validate_repo.py` superato | `5312bab` |
| 07 | Pipeline di build | DA-035..DA-040, DA-091..DA-103 | [x] | `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/validate_repo.py` superato | `e82e7df` |
| 08 | Interfaccia proposte AI | DA-054..DA-060, DA-100, DA-117 | [x] | `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/validate_repo.py` superato | `6b67c43` |
| 09 | Export ricerca, timeline e sommario | DA-061..DA-078, DA-099 | [x] | `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/validate_repo.py` superato | `16dd4c5` |
| 10 | Frontend statico | DA-079..DA-090, DA-113..DA-115 | [x] | `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/validate_repo.py` superato | `d3a3038` |
| 11 | Export e deploy USB | DA-004..DA-005, DA-104..DA-112, DA-125..DA-129 | [x] | `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/validate_repo.py` superato | `67f17ce` |
| 12 | Esempi, documentazione e accettazione finale | DA-013, DA-130..DA-144 | [x] | `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/validate_repo.py` superato | `9599181` |

La fase 08 ha consegnato soltanto lo scaffold sperimentale delle proposte. Il
ciclo completo di generazione da documenti, provenienza, revisione persistente
e promozione tipizzata verso i metadati curati e' un gap di prodotto aperto.
