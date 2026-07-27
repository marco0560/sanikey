# Processo di Rilascio

SaniKey usa Semantic Release su GitHub, con lo stesso meccanismo di Fontshow.
Ogni push controllata su `main` viene analizzata dalla CI: un commit `fix` crea
una patch, un commit `feat` una minor e una modifica incompatibile una major.
La CI aggiorna `CHANGELOG.md`, crea il commit di rilascio, il tag `vX.Y.Z` e la
release GitHub. Non pubblica pacchetti su PyPI o TestPyPI.

## Controlli Locali

Prima di inviare `main`, verificare che il repository sia in uno stato
pubblicabile:

```bash
git release-audit
```

Quel guard controlla:

- contenuti candidati al commit privi di dati sanitari, percorsi privati e
  credenziali
- albero di lavoro pulito
- area di staging vuota
- branch non arretrato rispetto all'upstream
- ultimo tag di versione antenato di `HEAD`
- presenza della sezione `Unreleased` in `CHANGELOG.md`

## Versione, changelog e tag

I tag di rilascio rispettano `vX.Y.Z`, ma sono creati soltanto da GitHub
Semantic Release. Non creare tag manuali salvo una riparazione documentata.

Per inviare una modifica pronta al rilascio:

```bash
git rel
```

`git rel` e' l'unico percorso di push da `main`: aggiorna il ramo con
fast-forward, esegue l'audit e invia il ramo. Attendere il workflow `Release`,
quindi eseguire `git pull --ff-only && uv sync && uv run sanikey -V`; il comando
mostrerà la versione esatta del tag creato dalla CI, non una versione di sviluppo
`.postN`.
L'hook `pre-push` blocca una `git push` diretta su `main`; la sola eccezione
locale di emergenza e' `git push --no-verify`, da usare soltanto per recupero
operativo documentato. Prima di un rilascio si puo' verificare l'installazione
dei controlli con `git release-check`.

SaniKey fornisce anche `scripts/tag_guard.sh` per validare separatamente un tag
proposto.

## Workflow GitHub

Il workflow `.github/workflows/release.yml` segue il modello di Fontshow:
checkout completo, Node 22, `npm ci` e `npx semantic-release`. Semantic Release
genera changelog, tag e release GitHub. Il progetto non include un percorso
automatico o manuale di pubblicazione PyPI/TestPyPI.
