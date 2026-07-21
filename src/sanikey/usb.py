"""USB export and validation."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import unquote, urlparse

from .database import database_path
from .documents import is_excluded_source_path
from .errors import UsbError

if TYPE_CHECKING:
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
    _write_usb_index(patients, image_root)
    _write_manifest(patients, image_root, progress=progress)
    if image_root.resolve() != target.resolve():
        _validate_physical_target(config, image_root, target)
        _replace_tree(
            image_root,
            target,
            progress=progress,
            copy_strategy=config.usb.copy_strategy,
        )
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
    if not (target / "index.html").is_file():
        return False
    if not _validate_usb_index_links(target):
        return False
    for patient in payload.get("patients", []):
        patient_id = patient["id"]
        patient_root = target / "patients" / patient_id
        if not (patient_root / "medical_archive.db").is_file():
            return False
        if not (patient_root / "web" / "index.html").is_file():
            return False
        if not _validate_frontend_links(patient_root / "web"):
            return False
        if not _validate_therapy_leaflets(patient_root / "web"):
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

    patient_root = target / "patients" / person.id
    patient_root.mkdir(parents=True, exist_ok=True)
    db_source = database_path(person)
    if db_source.is_file():
        shutil.copy2(db_source, patient_root / "medical_archive.db")
    _copy_tree(person.local_build / "web", patient_root / "web")
    _copy_tree(
        person.local_build / "medication-leaflets", patient_root / "medication-leaflets"
    )
    _copy_source_documents(person, patient_root / "documents")
    _copy_tree(
        person.local_build / "rendered-documents", patient_root / "rendered-documents"
    )
    _copy_tree(person.local_build / "technical", patient_root / "technical")
    _copy_dicom_html_viewers(person.local_build, patient_root / "dicom-viewers")
    _copy_tree(person.local_build / "dicom-media", patient_root / "dicom-media")
    _copy_tree(person.local_build / "dicom-previews", patient_root / "dicom-previews")


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


def _copy_source_documents(person: PersonConfig, target: Path) -> None:
    """Copy source documents that are not excluded from ingestion.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.
    target : pathlib.Path
        Exported documents directory.

    Returns
    -------
    None
    """

    if target.exists():
        shutil.rmtree(target)
    if not person.source_documents.is_dir():
        return
    target.mkdir(parents=True, exist_ok=True)
    files = sorted(
        path
        for path in person.source_documents.rglob("*")
        if path.is_file() and not is_excluded_source_path(person, path)
    )
    for path in files:
        destination = target / path.relative_to(person.source_documents)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)


def _copy_dicom_html_viewers(local_build: Path, target: Path) -> None:
    """Copy generated DICOM HTML viewer subtrees into a patient USB area.

    Parameters
    ----------
    local_build : pathlib.Path
        Patient generated build root.
    target : pathlib.Path
        USB viewer root for the patient.

    Returns
    -------
    None
    """

    if target.exists():
        shutil.rmtree(target)
    manifest = local_build / "manifests" / "dicom_html_viewers.json"
    if not manifest.is_file():
        return
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    for entry in payload.get("viewers", []):
        if not isinstance(entry, dict):
            continue
        study_id = entry.get("study_id")
        source_root = entry.get("source_root")
        relative_root = entry.get("relative_root")
        if not isinstance(study_id, str):
            continue
        if not isinstance(source_root, str):
            continue
        if not isinstance(relative_root, str):
            continue
        source = Path(source_root)
        if not source.is_dir():
            continue
        destination = target / study_id / relative_root
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source, destination)


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
    copy_strategy: str = "python",
) -> None:
    """Replace target contents with a copied tree.

    With ``rsync-preferred``, retain an existing target directory so that
    ``rsync --delete`` can reuse unchanged files while removing obsolete ones.
    The Python strategy clears the target before copying.

    Parameters
    ----------
    source : pathlib.Path
        Source directory to copy.
    target : pathlib.Path
        Target directory whose contents are replaced.
    progress : ProgressReporter | None, optional
        Optional interactive progress reporter.
    copy_strategy : str, optional
        Copy strategy, either ``python`` or ``rsync-preferred``.

    Returns
    -------
    None
    """

    if target.exists():
        if not target.is_dir():
            target.unlink()
            _copy_tree_with_progress(source, target, progress=progress)
            return
        if copy_strategy == "rsync-preferred" and shutil.which("rsync") is not None:
            _rsync_directory_contents(source, target, progress=progress)
            return
        _clear_directory_contents(target)
    else:
        target.mkdir(parents=True)
    if copy_strategy == "rsync-preferred" and shutil.which("rsync") is not None:
        _rsync_directory_contents(source, target, progress=progress)
        return
    _copy_directory_contents(source, target, progress=progress)


def _rsync_directory_contents(
    source: Path,
    target: Path,
    *,
    progress: ProgressReporter | None = None,
) -> None:
    """Mirror directory contents with rsync.

    Parameters
    ----------
    source : pathlib.Path
        Source directory to copy.
    target : pathlib.Path
        Existing target directory.
    progress : ProgressReporter | None, optional
        Optional interactive progress reporter.

    Returns
    -------
    None

    Raises
    ------
    UsbError
        If rsync returns a non-zero exit status.
    """

    files = sorted(path for path in source.rglob("*") if path.is_file())
    if progress is not None:
        progress.begin("export-usb target", total=len(files), interval=20)
    rsync = shutil.which("rsync")
    if rsync is None:
        _copy_directory_contents(source, target, progress=progress)
        return
    completed = subprocess.run(
        [rsync, "-a", "--delete", f"{source}/", f"{target}/"],
        check=False,
        capture_output=True,
        text=True,
        timeout=3600,
    )
    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout or "rsync non riuscito").strip()
        error = f"copia USB rsync non riuscita: {message}"
        raise UsbError(error)
    if progress is not None:
        progress.advance(len(files), total=len(files))
        progress.done(f"done files={len(files)}")


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


def _validate_physical_target(
    config: AccountsConfig,
    image_root: Path,
    target: Path,
) -> None:
    """Validate a USB target before mirroring the image.

    Parameters
    ----------
    config : AccountsConfig
        Loaded accounts configuration.
    image_root : pathlib.Path
        Prepared USB image directory.
    target : pathlib.Path
        Target directory.

    Returns
    -------
    None

    Raises
    ------
    UsbError
        If the target does not satisfy configured deployment constraints.
    """

    target.mkdir(parents=True, exist_ok=True)
    required_bytes = _tree_size(image_root) + config.usb.min_free_space_mb * 1024 * 1024
    available = shutil.disk_usage(target).free
    if available < required_bytes:
        error = (
            "target USB con spazio libero insufficiente: "
            f"available={available} required={required_bytes}"
        )
        raise UsbError(error)
    mount_info = _find_mount_info(target)
    if mount_info is None:
        if config.usb.usb_uuid or config.usb.require_exfat:
            error = f"impossibile determinare informazioni filesystem per {target}"
            raise UsbError(error)
        return
    expected_uuid = _expected_usb_uuid(
        config,
        enforce_person_uuid=_is_likely_physical_target(target),
    )
    actual_uuid = mount_info.get("uuid")
    if expected_uuid is not None and actual_uuid != expected_uuid:
        error = (
            f"UUID filesystem USB non corrispondente: expected={expected_uuid} "
            f"actual={actual_uuid}"
        )
        raise UsbError(error)
    fstype = mount_info.get("fstype")
    if config.usb.require_exfat and fstype != "exfat":
        error = f"filesystem USB deve essere exFAT: actual={fstype or 'sconosciuto'}"
        raise UsbError(error)


def _expected_usb_uuid(
    config: AccountsConfig,
    *,
    enforce_person_uuid: bool,
) -> str | None:
    """Return the configured expected USB filesystem UUID.

    Parameters
    ----------
    config : AccountsConfig
        Loaded accounts configuration.
    enforce_person_uuid : bool
        Whether shared per-patient UUID values should be enforced.

    Returns
    -------
    str | None
        Explicit global UUID or the shared enabled-patient UUID.
    """

    if config.usb.usb_uuid is not None:
        return config.usb.usb_uuid
    if not enforce_person_uuid:
        return None
    enabled_uuids = {
        person.usb_uuid for person in config.enabled_people() if person.usb_uuid
    }
    if len(enabled_uuids) == 1:
        return next(iter(enabled_uuids))
    return None


def _is_likely_physical_target(target: Path) -> bool:
    """Return whether a target path looks like a mounted removable device.

    Parameters
    ----------
    target : pathlib.Path
        Export target.

    Returns
    -------
    bool
        ``True`` for common Linux removable-media mount roots.
    """

    resolved = target.expanduser().resolve(strict=False)
    return resolved.is_relative_to("/run/media") or resolved.is_relative_to("/media")


def _find_mount_info(target: Path) -> dict[str, str] | None:
    """Return filesystem metadata for a mounted target.

    Parameters
    ----------
    target : pathlib.Path
        Target path.

    Returns
    -------
    dict[str, str] | None
        ``findmnt`` metadata or ``None`` when unavailable.
    """

    if shutil.which("findmnt") is None:
        return None
    findmnt = shutil.which("findmnt")
    if findmnt is None:
        return None
    completed = subprocess.run(
        [findmnt, "--json", "--output", "TARGET,FSTYPE,UUID", "--target", str(target)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if completed.returncode != 0:
        return None
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return None
    filesystems = payload.get("filesystems", [])
    if not filesystems:
        return None
    selected = filesystems[0]
    return {
        "fstype": str(selected.get("fstype") or ""),
        "uuid": str(selected.get("uuid") or ""),
        "target": str(selected.get("target") or ""),
    }


def _tree_size(root: Path) -> int:
    """Return total file size for a directory tree.

    Parameters
    ----------
    root : pathlib.Path
        Directory to measure.

    Returns
    -------
    int
        Sum of file sizes in bytes.
    """

    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file())


def _validate_frontend_links(web_dir: Path) -> bool:
    """Validate generated frontend document links.

    Parameters
    ----------
    web_dir : pathlib.Path
        Patient web directory in a USB export.

    Returns
    -------
    bool
        ``True`` when all frontend hrefs are relative and resolve locally.
    """

    data_script = web_dir / "data.js"
    if not data_script.is_file():
        return False
    payload = data_script.read_text(encoding="utf-8")
    prefix = "window.SANIKEY_DATA = "
    if not payload.startswith(prefix) or not payload.endswith(";\n"):
        return False
    try:
        data = json.loads(payload.removeprefix(prefix).removesuffix(";\n"))
    except json.JSONDecodeError:
        return False
    return all(_validate_relative_href(web_dir, href) for href in _frontend_hrefs(data))


def _validate_therapy_leaflets(web_dir: Path) -> bool:
    """Validate local FI and RCP links for every therapy in frontend data.

    Parameters
    ----------
    web_dir : pathlib.Path
        Patient web directory in a USB export.

    Returns
    -------
    bool
        ``True`` when every therapy has complete local AIFA documents or an
        explicit ``non_aifa`` marker.
    """

    data_script = web_dir / "data.js"
    prefix = "window.SANIKEY_DATA = "
    try:
        payload = data_script.read_text(encoding="utf-8")
        data = json.loads(payload.removeprefix(prefix).removesuffix(";\n"))
    except (OSError, json.JSONDecodeError):
        return False
    clinical = data.get("clinical") if isinstance(data, dict) else None
    therapies = clinical.get("therapies", []) if isinstance(clinical, dict) else []
    if not isinstance(therapies, list):
        return False
    for therapy in therapies:
        if not isinstance(therapy, dict):
            return False
        if therapy.get("non_aifa") is True:
            continue
        leaflet = therapy.get("leaflet_href")
        rcp = therapy.get("rcp_href")
        if not isinstance(leaflet, str) or not isinstance(rcp, str):
            return False
        if not _validate_relative_href(web_dir, leaflet):
            return False
        if not _validate_relative_href(web_dir, rcp):
            return False
    return True


def _validate_usb_index_links(target: Path) -> bool:
    """Validate root USB index links.

    Parameters
    ----------
    target : pathlib.Path
        USB export root.

    Returns
    -------
    bool
        ``True`` when every root index href resolves inside the export.
    """

    index = target / "index.html"
    content = index.read_text(encoding="utf-8")
    hrefs = re.findall(r'href="([^"]+)"', content)
    return all(_validate_relative_href(target, href) for href in hrefs)


def _frontend_hrefs(value: object) -> tuple[str, ...]:
    """Collect href string values from a frontend payload.

    Parameters
    ----------
    value : object
        Decoded JSON payload fragment.

    Returns
    -------
    tuple[str, ...]
        Href values found recursively.
    """

    if isinstance(value, dict):
        hrefs = [
            item
            for key, item in value.items()
            if key.endswith("href") and isinstance(item, str)
        ]
        for child in value.values():
            hrefs.extend(_frontend_hrefs(child))
        return tuple(hrefs)
    if isinstance(value, list):
        list_hrefs: list[str] = []
        for child in value:
            list_hrefs.extend(_frontend_hrefs(child))
        return tuple(list_hrefs)
    return ()


def _validate_relative_href(web_dir: Path, href: str) -> bool:
    """Return whether an href is relative and points inside the patient export.

    Parameters
    ----------
    web_dir : pathlib.Path
        Patient web directory in a USB export.
    href : str
        Href value to validate.

    Returns
    -------
    bool
        ``True`` when the href resolves to an existing exported file.
    """

    parsed = urlparse(href)
    if parsed.scheme or href.startswith(("/", "\\")):
        return False
    target = (web_dir / unquote(parsed.path)).resolve(strict=False)
    patient_root = web_dir.parent.resolve(strict=False)
    try:
        target.relative_to(patient_root)
    except ValueError:
        return False
    return target.is_file()


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


def _write_usb_index(people: tuple[PersonConfig, ...], target: Path) -> Path:
    """Write the root USB entrypoint.

    Parameters
    ----------
    people : tuple[PersonConfig, ...]
        Exported people.
    target : pathlib.Path
        USB export root.

    Returns
    -------
    pathlib.Path
        Written root index path.
    """

    index = target / "index.html"
    if len(people) == 1:
        person = people[0]
        href = f"patients/{_escape_html(person.id)}/web/index.html"
        index.write_text(
            f"""<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="0; url={href}">
  <title>SaniKey - {_escape_html(person.display_name)}</title>
</head>
<body>
  <p><a href="{href}">Apri archivio {_escape_html(person.display_name)}</a></p>
</body>
</html>
""",
            encoding="utf-8",
        )
        return index
    links = "\n".join(
        f'    <li><a href="patients/{_escape_html(person.id)}/web/index.html">'
        f"{_escape_html(person.display_name)}</a></li>"
        for person in people
    )
    index.write_text(
        f"""<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SaniKey - Archivi pazienti</title>
  <style>
    body {{ font-family: system-ui, sans-serif; line-height: 1.5; margin: 2rem; }}
    main {{ max-width: 42rem; }}
    a {{ color: #1f5f8b; font-weight: 700; }}
    li {{ margin: 0.75rem 0; }}
  </style>
</head>
<body>
  <main>
    <h1>SaniKey</h1>
    <p>Seleziona il paziente da consultare.</p>
    <ul>
{links}
    </ul>
  </main>
</body>
</html>
""",
        encoding="utf-8",
    )
    return index


def _escape_html(value: str) -> str:
    """Escape minimal HTML text.

    Parameters
    ----------
    value : str
        Text to escape.

    Returns
    -------
    str
        Escaped text.
    """

    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


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
