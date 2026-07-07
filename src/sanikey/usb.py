"""USB export and validation."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .database import database_path

if TYPE_CHECKING:
    from pathlib import Path

    from .config import AccountsConfig, PersonConfig
    from .progress import ProgressReporter


@dataclass(frozen=True)
class UsbExportResult:
    """Result of a USB export.

    Parameters
    ----------
    root : pathlib.Path
        Export root.
    manifest : pathlib.Path
        Manifest path.
    patients : int
        Exported patient count.
    files : int
        Exported file count.
    """

    root: Path
    manifest: Path
    patients: int
    files: int


def usb_image_root(config: AccountsConfig) -> Path:
    """Return the canonical generated USB image directory.

    Parameters
    ----------
    config : AccountsConfig
        Loaded accounts configuration.

    Returns
    -------
    pathlib.Path
        ``exports/usb-image`` under the configuration repository root.
    """

    root = config.path.parent
    if root.name == "config":
        root = root.parent
    return root / "exports" / "usb-image"


def export_usb(
    config: AccountsConfig,
    target: Path,
    *,
    progress: ProgressReporter | None = None,
) -> UsbExportResult:
    """Export enabled patients through the canonical USB image.

    Parameters
    ----------
    config : AccountsConfig
        Loaded accounts configuration.
    target : pathlib.Path
        Target USB root or simulated USB directory. The complete USB image is
        first built under ``exports/usb-image`` and then mirrored here.
    progress : ProgressReporter | None, optional
        Optional interactive progress reporter.

    Returns
    -------
    UsbExportResult
        Export result.
    """

    image_root = usb_image_root(config)
    if progress is not None:
        progress.begin("export-usb prepare", total=1, interval=1)
    _reset_directory(image_root)
    patients = config.enabled_people()
    if progress is not None:
        progress.advance(1, total=1)
        progress.done(f"done image_root={image_root}")
    if progress is not None:
        progress.begin("export-usb image", total=len(patients), interval=1)
    for index, person in enumerate(patients, start=1):
        _export_patient(person, image_root)
        if progress is not None:
            progress.advance(index, total=len(patients))
    if progress is not None:
        progress.done(f"done patients={len(patients)}")
    _write_manifest(patients, image_root, progress=progress)
    if image_root.resolve() != target.resolve():
        _replace_tree(image_root, target, progress=progress)
    manifest = target / "SANIKEY-MANIFEST.json"
    return UsbExportResult(
        root=target,
        manifest=manifest,
        patients=len(patients),
        files=sum(1 for path in target.rglob("*") if path.is_file()),
    )


def validate_usb(target: Path) -> bool:
    """Validate a generated USB export.

    Parameters
    ----------
    target : pathlib.Path
        USB root or simulated USB directory.

    Returns
    -------
    bool
        ``True`` when the export has required files and matching checksums.
    """

    manifest = target / "SANIKEY-MANIFEST.json"
    if not manifest.is_file():
        return False
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    for patient in payload.get("patients", []):
        patient_id = patient["id"]
        if not (target / f"START-HERE-{patient['start_label']}.html").is_file():
            return False
        patient_root = target / "patients" / patient_id
        if not (patient_root / "medical_archive.db").is_file():
            return False
        if not (patient_root / "web" / "index.html").is_file():
            return False
    checksums = payload.get("checksums", {})
    for relative, expected in checksums.items():
        path = target / relative
        if not path.is_file() or _sha256(path) != expected:
            return False
    return True


def _export_patient(person: PersonConfig, target: Path) -> None:
    """Export one patient into the USB layout.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.
    target : pathlib.Path
        Target USB root.

    Returns
    -------
    None
    """

    label = _start_label(person.display_name)
    (target / f"START-HERE-{label}.html").write_text(
        _start_page(person),
        encoding="utf-8",
    )
    patient_root = target / "patients" / person.id
    patient_root.mkdir(parents=True, exist_ok=True)
    db_source = database_path(person)
    if db_source.is_file():
        shutil.copy2(db_source, patient_root / "medical_archive.db")
    _copy_tree(person.local_build / "web", patient_root / "web")
    _copy_tree(person.source_documents, patient_root / "documents")


def _copy_tree(source: Path, target: Path) -> None:
    """Copy a directory tree when present.

    Parameters
    ----------
    source : pathlib.Path
        Source directory.
    target : pathlib.Path
        Target directory.

    Returns
    -------
    None
    """

    if target.exists():
        shutil.rmtree(target)
    if source.is_dir():
        shutil.copytree(source, target)


def _reset_directory(target: Path) -> None:
    """Create an empty directory.

    Parameters
    ----------
    target : pathlib.Path
        Directory to recreate.

    Returns
    -------
    None
    """

    if target.exists():
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
    target.mkdir(parents=True)


def _replace_tree(
    source: Path,
    target: Path,
    *,
    progress: ProgressReporter | None = None,
) -> None:
    """Replace target contents with a copied tree.

    Parameters
    ----------
    source : pathlib.Path
        Source directory to copy.
    target : pathlib.Path
        Target directory whose contents are replaced.
    progress : ProgressReporter | None, optional
        Optional interactive progress reporter.

    Returns
    -------
    None
    """

    if target.exists():
        if not target.is_dir():
            target.unlink()
            _copy_tree_with_progress(source, target, progress=progress)
            return
        _clear_directory_contents(target)
    else:
        target.mkdir(parents=True)
    _copy_directory_contents(source, target, progress=progress)


def _copy_tree_with_progress(
    source: Path,
    target: Path,
    *,
    progress: ProgressReporter | None = None,
) -> None:
    """Copy one directory tree with optional per-file progress.

    Parameters
    ----------
    source : pathlib.Path
        Source directory.
    target : pathlib.Path
        Target directory.
    progress : ProgressReporter | None, optional
        Optional interactive progress reporter.

    Returns
    -------
    None
    """

    target.mkdir(parents=True)
    _copy_directory_contents(source, target, progress=progress)


def _copy_directory_contents(
    source: Path,
    target: Path,
    *,
    progress: ProgressReporter | None = None,
) -> None:
    """Copy directory contents with optional per-file progress.

    Parameters
    ----------
    source : pathlib.Path
        Source directory.
    target : pathlib.Path
        Existing target directory.
    progress : ProgressReporter | None, optional
        Optional interactive progress reporter.

    Returns
    -------
    None
    """

    files = sorted(path for path in source.rglob("*") if path.is_file())
    directories = sorted(path for path in source.rglob("*") if path.is_dir())
    if progress is not None:
        progress.begin("export-usb target", total=len(files), interval=20)
    for directory in directories:
        (target / directory.relative_to(source)).mkdir(parents=True, exist_ok=True)
    for index, path in enumerate(files, start=1):
        destination = target / path.relative_to(source)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        if progress is not None:
            progress.advance(index, total=len(files))
    if progress is not None:
        progress.done(f"done files={len(files)}")


def _clear_directory_contents(target: Path) -> None:
    """Remove every item inside a directory without removing the directory.

    Parameters
    ----------
    target : pathlib.Path
        Directory to empty.

    Returns
    -------
    None
    """

    for item in target.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()


def _write_manifest(
    people: tuple[PersonConfig, ...],
    target: Path,
    *,
    progress: ProgressReporter | None = None,
) -> Path:
    """Write USB manifest with checksums.

    Parameters
    ----------
    people : tuple[PersonConfig, ...]
        Exported people.
    target : pathlib.Path
        USB root.
    progress : ProgressReporter | None, optional
        Optional interactive progress reporter.

    Returns
    -------
    pathlib.Path
        Manifest path.
    """

    manifest = target / "SANIKEY-MANIFEST.json"
    files = sorted(item for item in target.rglob("*") if item.is_file())
    checksums: dict[str, str] = {}
    if progress is not None:
        progress.begin("export-usb manifest", total=len(files), interval=20)
    for index, path in enumerate(files, start=1):
        if path != manifest:
            checksums[str(path.relative_to(target))] = _sha256(path)
        if progress is not None:
            progress.advance(index, total=len(files))
    if progress is not None:
        progress.done(f"done files={len(files)}")
    payload = {
        "schema_version": 1,
        "patients": [
            {
                "id": person.id,
                "display_name": person.display_name,
                "start_label": _start_label(person.display_name),
                "usb_uuid": person.usb_uuid,
            }
            for person in people
        ],
        "checksums": checksums,
    }
    manifest.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def _start_page(person: PersonConfig) -> str:
    """Render a START-HERE page.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.

    Returns
    -------
    str
        HTML document.
    """

    return f"""<!doctype html>
<html lang="it">
<head><meta charset="utf-8"><title>SaniKey - {person.display_name}</title></head>
<body>
  <p><a href="patients/{person.id}/web/index.html">Apri archivio {person.display_name}</a></p>
</body>
</html>
"""


def _start_label(display_name: str) -> str:
    """Return a filesystem label for START-HERE files.

    Parameters
    ----------
    display_name : str
        Display name.

    Returns
    -------
    str
        Label with spaces replaced by hyphens.
    """

    return "-".join(part for part in display_name.split() if part)


def _sha256(path: Path) -> str:
    """Compute a SHA256 digest.

    Parameters
    ----------
    path : pathlib.Path
        File path.

    Returns
    -------
    str
        Hex digest.
    """

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
