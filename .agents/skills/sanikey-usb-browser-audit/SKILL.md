---
name: sanikey-usb-browser-audit
description: Audit a mounted SaniKey USB export with Chrome headless. Use for post-build USB verification, responsive UI checks, broken links, console errors, non-viewable documents, DICOM fallback checks, and usability findings. Do not use for implementation changes.
---

# Audit USB SaniKey

## Operating Rules

- Treat the mounted USB as read-only. Do not run deploy, build, cleanup, or
  repair commands against it.
- Start from the actual mount path. Confirm `index.html` and patient exports
  exist before opening the browser.
- Use Chrome headless only for evidence gathering. `--allow-file-access-from-files`
  is permitted for the audit harness; it does not prove that a consultation
  browser needs or receives that flag.
- Report findings only. Do not modify the export or repository unless the user
  separately asks for a fix.

## Procedure

1. Record the mount root, patient ids, file counts, free space, and static
   validation result. Check all relative href targets and classify broken links
   by patient and feature.
2. Run the frontend at `1600x1000`, `1366x768`, and `390x844`. Capture a
   screenshot for each patient and viewport in a new directory below `/tmp`.
3. Use Chrome DevTools Protocol to collect uncaught exceptions, console errors,
   document overflow, active panes, visible section panels, and link targets.
4. Exercise the stable interaction contract when the controls exist: basic and
   advanced search, each help dialog and close button, section buttons in both
   panes, timeline detail links, original-document links, and DICOM actions.
5. Inspect exported data and filesystem targets. Flag an anomaly when a listed
   document has no usable local target, a DICOM study has neither native HTML
   viewer nor non-diagnostic preview nor `DICOMDIR`, or an external path leaks
   into the export.
6. Present findings by severity with patient, viewport, reproducible action,
   evidence path, and expected behavior. Separate confirmed defects from
   ambiguous clinical metadata and from expected non-diagnostic DICOM limits.

## Required Coverage

- At least one patient with documents, observations, therapy, and DICOM data;
  audit all patients when present.
- Wide desktop, older laptop, and mobile viewports.
- Relative link resolution, current-tab versus new-tab semantics, layout
  overflow, dialog dismissal, search results, pane targeting, and browser
  exceptions.
- DICOM cards: native viewer, preview fallback, professional-reader media, and
  absence of misleading individual DICOM-file listings.

## Findings Format

Use this structure:

```text
severity: high|medium|low
patient: <id>
viewport: wide|laptop|mobile|all
reproduction: <short action>
evidence: <local screenshot, console trace, or href>
impact: <clinical consultation or usability impact>
```

Do not call a generated JPEG preview a diagnostic DICOM viewer. Do not treat a
viewer supplied by the original media as reusable for unrelated studies.
