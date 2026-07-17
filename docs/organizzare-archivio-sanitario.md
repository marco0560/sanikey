# Organizzare l'Archivio Sanitario

Questa guida descrive come predisporre i documenti sorgente di un paziente
prima di eseguire la build. SaniKey non richiede una tassonomia clinica fissa:
la struttura deve restare comprensibile anche senza il programma.

## Cosa e' Obbligatorio

- Conservare i file sotto la directory `source_documents` configurata per il
  paziente.
- Non collocare dati sanitari in directory versionate del repository.
- Mantenere i file che devono essere acquisiti fuori dai pattern di esclusione
  configurati in `accounts.toml`.

Il nome non deve rispettare un formato particolare per essere acquisito. Un
file senza data nel nome resta consultabile, ma la sua data non puo' essere
dedotta automaticamente.

## Nomi dei File Consigliati

Usare, quando si conosce la data del documento:

```text
AAAAMMGG Titolo leggibile.estensione
```

Per esempio:

```text
20260102 Referto laboratorio.pdf
20240312 Visita cardiologica.docx
```

SaniKey interpreta `AAAAMMGG` come data e usa il resto del nome, senza
estensione, come titolo. Gli underscore nel titolo sono mostrati come spazi,
quindi `20260102 Referto_Laboratorio.pdf` e' equivalente per la presentazione.

Questa convenzione e' consigliata, non obbligatoria. Non rinominare un file
quando il suo nome originale e' rilevante per la provenienza o per l'uso con un
programma del produttore.

## Cartelle e Chiavi di Ricerca

La prima directory sotto `documents/` diventa la **categoria** del documento.
La categoria e' memorizzata nel database, mostrata nell'interfaccia e ricercata
insieme a titolo, tag, tipo di file e testo estratto.

```text
documents/
  Cardiologia/
    Visite/20240312 Controllo.pdf
    Esami/20240418 Ecocardiogramma.pdf
  Laboratorio/
    20240503 Analisi sangue.pdf
```

In questo esempio le categorie ricercabili sono `Cardiologia` e `Laboratorio`.
`Visite` ed `Esami` non diventano categorie aggiuntive: sono comunque parte del
percorso e quindi possono essere trovate nella ricerca avanzata sul percorso.

Conviene scegliere nomi di categoria stabili, brevi e clinicamente chiari,
come `Cardiologia`, `Laboratorio`, `Ortopedia` o `Medico di base`. Evitare di
usare la categoria per informazioni gia' presenti nel nome del file o nei tag:
`Laboratorio` e' utile, mentre `Laboratorio 2024` rende la ricerca meno
coerente nel tempo.

Le categorie sono libere. SaniKey non richiede ne' impone un elenco di
specialita', medici o patologie.

## Directory di Servizio

Una directory con prefisso `_` resta in testa all'ordinamento alfabetico; il
prefisso non appare nel nome della categoria mostrata al medico.

Le convenzioni correnti sono:

| Directory | Contenuto |
| --- | --- |
| `_Archivi` | supporti compressi, immagini disco e altri container tecnici |
| `_Parametri` | sorgenti di misurazioni longitudinali |
| `_Terapia` | documenti della terapia corrente |

Le directory di servizio sono convenzioni consigliate. Le loro categorie
ricercabili sono rispettivamente `Archivi`, `Parametri` e `Terapia`.

## Archivi e Studi DICOM

Conservare il supporto ricevuto dall'ospedale, inclusi ISO, ZIP, TAR.XZ e gli
eventuali visualizzatori forniti. Metterlo normalmente in `_Archivi` e non
sostituirlo con il solo contenuto estratto: lo staging e gli artefatti DICOM
generati possono essere ricreati, mentre il supporto originale e' la sorgente
di verita'.

I PDF e gli altri documenti supportati contenuti negli archivi sono acquisiti
durante `build-patient` o `build-all`, salvo pattern di esclusione. Il comando
`extract-text` da solo non esegue lo staging degli archivi.

## Casi da Rivedere

- I file privi di data restano consultabili ma possono richiedere metadati
  curati per una timeline affidabile.
- I duplicati di contenuto sono rilevati dalla scansione; conservare una sola
  copia quando non serve dimostrare una provenienza distinta.
- I formati non supportati sono segnalati dalla scansione. Conservare comunque
  l'originale e valutare una conversione in PDF solo come copia di
  consultazione.
- Tag e metadati curati completano le categorie: non duplicare nei nomi delle
  cartelle informazioni che sono gia' piu' precise nei tag.
