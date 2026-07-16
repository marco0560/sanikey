# DICOM handling

## Question

Ggive me a recap of what is the treatment of archives containing iso images or DICOM studies (possibly nested).
I Imagined a workflow for the doctor identical or close to what happens when she inserts the CD in the PC. Hilight the differences.

## Synthesis

Current SaniKey behavior is close only when the support contains a browser-openable HTML viewer. It is not equivalent to inserting the original CD and launching its native autorun/viewer.

## Archive And ISO Handling

- Source archives such as `.zip`, `.7z`, `.rar`, `.tar.xz`, `.iso`, `.img` are detected as container/support documents.
- `scan-documents`, `process-dicom` and `build-patient` stage supported containers by default under `local_build/staging/containers/`.
- `process-dicom --no-stage-containers` skips extraction and catalogs only source supports plus already existing expansions.
- If an archive contains a nested disk image, for example ZIP -> ISO -> DICOM tree, SaniKey recursively stages the nested image.
- Staging records all extracted members in the manifest for audit.
- Only clinically useful derived documents enter the document pipeline; technical/support paths can be filtered by configured `exclude_patterns`.
- DICOM instances are cataloged as DICOM records/studies, not shown as thousands of ordinary files.

## DICOM Study Handling

- SaniKey scans the staged support for DICOM files and `DICOMDIR`.
- It groups instances by `StudyInstanceUID` when possible.
- If `DICOMDIR` has usable study records, those are used too.
- The frontend shows aggregated DICOM study cards, with metadata such as date, UID and instance count.
- If a recognized HTML viewer exists, especially IHE PDI paths such as `IHE_PDI/PAGES/STUDIES/*.HTM`, SaniKey copies the required viewer subtree to USB under:
  `patients/<id>/dicom-viewers/<study_id>/...`
- The frontend exposes that as `Apri studio DICOM`.

## USB Export

- The original source support, for example `Referto TAC.zip`, may still be copied under `patients/<id>/documents/` unless excluded by ingestion patterns, but the clinical `Studi DICOM` pane does not advertise archive downloads as the primary workflow.
- Files excluded by `exclude_patterns` are not copied into `patients/<id>/documents/`.
- Recognized DICOM HTML viewers are copied separately via the DICOM viewer manifest, even though technical viewer paths are not ordinary ingested documents.
- Current UI shows `Apri studio DICOM` when `viewer_href` exists, omits non-viewable DICOM support records from the ordinary document pane, and flags cataloged studies without an HTML viewer as anomalies.

## Differences From Inserting The CD

- SaniKey does not launch native CD autorun programs or `.exe` viewers from the browser.
- Native Windows/Mac/Linux viewer applications from the CD are generally not executable from a static `file://` web frontend in a reliable or safe way.
- SaniKey does not emulate the full original CD environment.
- SaniKey only gives a near-CD workflow when the CD includes an HTML/static viewer that can run directly in the browser.
- If the CD only has a native executable viewer, SaniKey can preserve/catalog the support, but the doctor may need to open/download the original support manually outside the web UI.
- If the viewer depends on runtime files filtered by `exclude_patterns`, those files will not be in `patients/<id>/documents`; only recognized viewer subtrees copied through `dicom-viewers` are guaranteed to be present.

## Current workflow

So the intended doctor workflow now is:

1. Open USB `index.html`.
2. Search or open `Studi DICOM` when the section is available.
3. Click `Apri studio DICOM`.
4. If an HTML viewer was recognized, it opens directly in a new browser tab.
5. If no HTML viewer was recognized, the study remains visible in `Studi DICOM` as an anomaly to investigate, while the original support remains available for technical verification.
