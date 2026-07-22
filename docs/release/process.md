# Processo di Rilascio

SaniKey usa un flusso basato su tag e Trusted Publishing. Il tag costruisce e
allega gli artefatti alla release GitHub; la pubblicazione su TestPyPI o PyPI
è una scelta manuale e protetta da environment separati.

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

Per `0.8.0`:

```bash
git tag -a v0.8.0 -m "SaniKey 0.8.0"
git push --follow-tags
```

Il template fornisce anche `scripts/tag_guard.sh` per validare separatamente un
tag proposto.

## GitHub, TestPyPI e PyPI

Il workflow `.github/workflows/release.yml` costruisce sia sdist sia wheel,
esegue `twine check --strict` e allega i file alla release GitHub. Da
**Actions → Release → Run workflow**, scegliere il tag e una destinazione:

- `none`: ricostruisce e controlla gli artefatti senza pubblicarli;
- `testpypi`: carica su TestPyPI nell'environment GitHub `testpypi`;
- `pypi`: carica su PyPI nell'environment GitHub `pypi`.

Prima del primo upload, il proprietario del progetto deve configurare in
TestPyPI e PyPI un Trusted Publisher con questi valori:

| Campo | Valore |
| --- | --- |
| Owner GitHub | `marco0560` |
| Repository | `sanikey` |
| Workflow | `.github/workflows/release.yml` |
| Environment TestPyPI | `testpypi` |
| Environment PyPI | `pypi` |

Il workflow usa token OIDC effimeri (`id-token: write`); non salvare token API
PyPI nei secret del repository. Proteggere l'environment `pypi` con approvazione
manuale. TestPyPI è obbligatorio per ogni nuova versione prima di PyPI.

L'esito dell'upload non sostituisce il smoke test: installare `sanikey==X.Y.Z`
in un ambiente nuovo e verificare almeno `sanikey --help`. La checklist indica
i comandi esatti.
