## [0.10.1](https://github.com/marco0560/sanikey/compare/v0.10.0...v0.10.1) (2026-08-04)

### Bug Fixes

* **generation:** integrate longitudinal observations ([a5847e1](https://github.com/marco0560/sanikey/commit/a5847e10ece6a57424cb4737e41243ecd0ccae29))
* **generation:** reduced upper frame elemens in small and medium screens ([44e53a4](https://github.com/marco0560/sanikey/commit/44e53a42c9b5cc58cd76552e651ed27bfc91c04d))

## [0.10.0](https://github.com/marco0560/sanikey/compare/v0.9.2...v0.10.0) (2026-08-01)

### Features

* **build:** consolidate longitudinal parameter review ([a60cffd](https://github.com/marco0560/sanikey/commit/a60cffdacd9c7c834484467df489748b2c5f6534))

## [0.9.2](https://github.com/marco0560/sanikey/compare/v0.9.1...v0.9.2) (2026-07-30)

### Bug Fixes

* **dev:** bootstrap Fedora prerequisites ([1afe14d](https://github.com/marco0560/sanikey/commit/1afe14d1c6347ce52e7cb96e600674353af5f023))

## [0.9.1](https://github.com/marco0560/sanikey/compare/v0.9.0...v0.9.1) (2026-07-27)

### Bug Fixes

* **release:** enforce privacy guard in GitHub ([2efe14d](https://github.com/marco0560/sanikey/commit/2efe14dabc7db01e1378d67ed579243d6df34311))

## [0.9.0](https://github.com/marco0560/sanikey/compare/v0.8.2...v0.9.0) (2026-07-27)

### Features

* **dev:** add USB preparation workflow ([fa67c63](https://github.com/marco0560/sanikey/commit/fa67c630bdffc7f7d8300b9557c51e6316a756a1))
* **generation:** add longitudinal clinical parameter slices ([b463673](https://github.com/marco0560/sanikey/commit/b463673ce043f82f5dac10606a42072ff2e83d39))
* **release:** automate changelog and version tags ([9c389ca](https://github.com/marco0560/sanikey/commit/9c389caf29cb09f74e6940d6bd89b1584eed7b89))
* **release:** guard versioned main pushes ([4a00a7f](https://github.com/marco0560/sanikey/commit/4a00a7f903b0f8d2680b5a7a674641d245fe5732))

### Bug Fixes

* **ci:** install uv before release validation ([0e21416](https://github.com/marco0560/sanikey/commit/0e21416c0374667287dfb87d602a8a09fb057e67))
* **release:** align GitHub flow with Fontshow ([e98b46e](https://github.com/marco0560/sanikey/commit/e98b46e6b7d21bb70e36add6429bf109b60be1f1))
* **release:** unblock semantic GitHub releases ([e31e027](https://github.com/marco0560/sanikey/commit/e31e0279840885fb31465cd30d16e6fcbc19b0a1))
* **version:** resolve editable checkout versions from SCM ([c678f1c](https://github.com/marco0560/sanikey/commit/c678f1c862d0bdb234ed70e325d1c345e0429508))

# Changelog

## Unreleased

- Corretto il branding della descrizione PyPI: un solo wordmark e badge
  aggiornabile dopo la pubblicazione iniziale.

## 0.8.0 - 2026-07-22

- Prima release pubblica di SaniKey.
- Archivio sanitario locale con export USB statico, ricerca offline, terapia
  con fogli illustrativi AIFA, osservazioni e catalogazione DICOM.
- Documentazione riorganizzata attorno al percorso dalla prima configurazione
  alla chiavetta verificata.
- Pubblicazione riproducibile degli artefatti su GitHub, TestPyPI e PyPI.
