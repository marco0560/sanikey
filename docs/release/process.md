# Processo di Rilascio

Questo template usa un flusso conservativo di rilascio basato su tag.

## Controlli Locali

Prima di creare un tag di rilascio, verificare che il repository sia in uno
stato pubblicabile:

```bash
git release-audit
```

Quel guard controlla:

- albero di lavoro pulito
- area di staging vuota
- branch non arretrato rispetto all'upstream
- ultimo tag di versione antenato di `HEAD`
- presenza della sezione `Unreleased` in `CHANGELOG.md`

## Tagging

I tag di rilascio devono rispettare `vX.Y.Z`.

Esempio:

```bash
git tag v0.2.0
git push --follow-tags
```

Il template fornisce anche `scripts/tag_guard.sh` per validare separatamente un
tag proposto.

## GitHub Actions

Il repository generato include una procedura di rilascio che si attiva sui tag di
versione inviati e pubblica gli artefatti di distribuzione costruiti come
release GitHub.
