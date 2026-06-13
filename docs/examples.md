# Esempi

Le directory `docs/*-example` sono fixture pubblicabili che documentano la
struttura attesa senza esporre dati reali dei pazienti.

## Esempio di Configurazione

`docs/config-example/accounts.toml` mostra lo schema richiesto per la
configurazione locale:

```toml
[global]
config_version = 1

[[person]]
id = "patient-a"
display_name = "Paziente A"
source_documents = "/percorso/assoluto/esempio/patient-a/documents"
metadata_directory = "/percorso/assoluto/esempio/patient-a/metadata"
local_build = "/percorso/assoluto/esempio/patient-a/generated"
usb_uuid = "1A2B-3C4D"
enabled = true
```

Copia questa struttura in `config/accounts.toml` per l'uso reale, poi sostituisci
ogni percorso di esempio con un percorso assoluto privato.

## Esempio di Paziente

`docs/patients-example` contiene file di input sintetici:

```text
docs/patients-example/
  patient-a/
    documents/
      laboratory/
        20260102 Referto Sintetico.txt
    metadata/
      clinical_summary.toml
      document_tags.toml
```

Negli esempi di documentazione usare solo identificativi neutri e contenuti
sintetici.

## Esempio di Artefatti Generati

`docs/generated-example` documenta la forma degli artefatti generati che possono
essere pubblicati quando derivano da dati sintetici.

Gli artefatti generati da dati reali appartengono ai percorsi privati
configurati tramite `config/accounts.toml` e non devono essere committati.
