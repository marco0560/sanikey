#!/usr/bin/env python3
"""Replace the consultation logo on an existing SaniKey USB export."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from sanikey.usb import validate_usb

MANIFEST_NAME = "SANIKEY-MANIFEST.json"
LOGO_RELATIVE_PATH = Path("assets/sanikey-logo-horizontal-transparent.svg")
STYLESHEET_NAME = "style.css"
HEADER_LOGO_WIDTH_REM = 10.125
FOOTER_LOGO_WIDTH_REM = 19.5
SIZE_OVERRIDE_START = "/* sanikey-logo-size: start */"
SIZE_OVERRIDE_END = "/* sanikey-logo-size: end */"


def main(argv: list[str] | None = None) -> int:
    """Replace the SVG logo in every patient consultation on a USB export.

    Parameters
    ----------
    argv : list[str] | None, optional
        Command-line arguments without the executable name. Uses
        :data:`sys.argv` when omitted.

    Returns
    -------
    int
        Zero after a successful replacement, otherwise one.
    """

    parser = argparse.ArgumentParser(
        description=(
            "Sostituisce il logo SVG in tutti gli archivi paziente della "
            "chiavetta e rigenera il manifest."
        )
    )
    parser.add_argument("svg", type=Path, help="File SVG da usare come logo")
    parser.add_argument("mountpoint", type=Path, help="Mountpoint della chiavetta")
    parser.add_argument(
        "percentuale",
        type=float,
        nargs="?",
        default=100.0,
        help="Scala del logo in percentuale, con 100 uguale alla dimensione corrente",
    )
    args = parser.parse_args(argv)
    try:
        patients = replace_usb_logo(args.svg, args.mountpoint, args.percentuale)
    except (OSError, TypeError, ValueError, ET.ParseError) as exc:
        print(f"ERRORE: sostituzione logo non riuscita: {exc}", file=sys.stderr)
        return 1
    print(
        "stato=ok "
        f"pazienti={patients} "
        f"logo={LOGO_RELATIVE_PATH.as_posix()} "
        f"scala={args.percentuale:g}%"
    )
    return 0


def replace_usb_logo(
    source_svg: Path,
    mountpoint: Path,
    scale_percent: float = 100.0,
) -> int:
    """Copy one SVG logo into every patient web directory and rebuild checksums.

    Parameters
    ----------
    source_svg : pathlib.Path
        SVG file selected as the replacement logo.
    mountpoint : pathlib.Path
        Root directory of an existing SaniKey USB export.
    scale_percent : float, optional
        Logo scale in percent relative to the generated default size.

    Returns
    -------
    int
        Number of patient logos replaced.

    Raises
    ------
    ValueError
        If the source is not a valid SVG, the USB export is incomplete, or the
        rebuilt export does not validate.
    """

    source = source_svg.expanduser().resolve(strict=True)
    target = mountpoint.expanduser().resolve(strict=True)
    _validate_svg(source)
    _validate_scale_percent(scale_percent)
    manifest_path = target / MANIFEST_NAME
    payload = _read_manifest(manifest_path)
    patient_ids = _patient_ids(payload)
    destinations = [
        target / "patients" / patient_id / "web" / LOGO_RELATIVE_PATH
        for patient_id in patient_ids
    ]
    stylesheets = [
        destination.parent.parent / STYLESHEET_NAME for destination in destinations
    ]
    for destination in destinations:
        if not destination.parent.is_dir():
            error = f"directory web paziente assente per il logo: {destination.parent}"
            raise ValueError(error)
    for stylesheet in stylesheets:
        if not stylesheet.is_file():
            error = f"foglio di stile paziente assente per il logo: {stylesheet}"
            raise ValueError(error)
    for destination in destinations:
        if destination.resolve(strict=False) != source:
            shutil.copy2(source, destination)
    for stylesheet in stylesheets:
        _write_logo_size_override(stylesheet, scale_percent)
    payload["checksums"] = _checksums(target, manifest_path)
    _write_manifest(manifest_path, payload)
    if not validate_usb(target):
        error = "la chiavetta non supera la validazione dopo la sostituzione"
        raise ValueError(error)
    return len(destinations)


def _validate_scale_percent(scale_percent: float) -> None:
    """Validate a positive finite logo scale percentage.

    Parameters
    ----------
    scale_percent : float
        Requested logo scale in percent.

    Returns
    -------
    None

    Raises
    ------
    ValueError
        If the percentage is not finite and strictly positive.
    """

    if not 0 < scale_percent < float("inf"):
        error = "la percentuale del logo deve essere un numero positivo"
        raise ValueError(error)


def _validate_svg(source: Path) -> None:
    """Validate that a source file is an SVG document.

    Parameters
    ----------
    source : pathlib.Path
        Candidate SVG source file.

    Returns
    -------
    None

    Raises
    ------
    ValueError
        If the path is not an SVG file or its root element is not ``svg``.
    """

    if source.suffix.lower() != ".svg":
        error = f"il logo deve avere estensione .svg: {source}"
        raise ValueError(error)
    root = ET.parse(source).getroot()
    if root.tag.rsplit("}", maxsplit=1)[-1].lower() != "svg":
        error = f"il file non contiene un elemento SVG: {source}"
        raise ValueError(error)


def _read_manifest(manifest_path: Path) -> dict[str, Any]:
    """Read the existing USB manifest as a JSON object.

    Parameters
    ----------
    manifest_path : pathlib.Path
        Manifest file in the USB root.

    Returns
    -------
    dict[str, typing.Any]
        Decoded manifest payload.

    Raises
    ------
    TypeError
        If the manifest root is not a JSON object.
    ValueError
        If the manifest is absent or cannot be decoded as JSON.
    """

    if not manifest_path.is_file():
        error = f"manifest USB assente: {manifest_path}"
        raise ValueError(error)
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        error = f"manifest USB non valido: {manifest_path}"
        raise ValueError(error) from exc
    if not isinstance(payload, dict):
        error = f"manifest USB non valido: {manifest_path}"
        raise TypeError(error)
    return payload


def _patient_ids(payload: dict[str, Any]) -> tuple[str, ...]:
    """Return the non-empty unique patient identifiers from a manifest.

    Parameters
    ----------
    payload : dict[str, typing.Any]
        Decoded USB manifest payload.

    Returns
    -------
    tuple[str, ...]
        Patient identifiers in manifest order.

    Raises
    ------
    ValueError
        If the manifest has no valid, unique patient identifiers.
    """

    patients = payload.get("patients")
    if not isinstance(patients, list) or not patients:
        error = "manifest USB senza pazienti"
        raise ValueError(error)
    patient_ids = tuple(
        patient.get("id")
        for patient in patients
        if isinstance(patient, dict) and isinstance(patient.get("id"), str)
    )
    if len(patient_ids) != len(patients) or any(
        not patient_id for patient_id in patient_ids
    ):
        error = "manifest USB con identificativi paziente non validi"
        raise ValueError(error)
    if len(set(patient_ids)) != len(patient_ids):
        error = "manifest USB con identificativi paziente duplicati"
        raise ValueError(error)
    return patient_ids


def _checksums(target: Path, manifest_path: Path) -> dict[str, str]:
    """Compute checksums for every export file except the manifest itself.

    Parameters
    ----------
    target : pathlib.Path
        USB export root.
    manifest_path : pathlib.Path
        Manifest file excluded from checksums.

    Returns
    -------
    dict[str, str]
        SHA-256 checksum by path relative to the USB root.
    """

    return {
        path.relative_to(target).as_posix(): _sha256(path)
        for path in sorted(target.rglob("*"))
        if path.is_file() and path != manifest_path
    }


def _sha256(path: Path) -> str:
    """Return the SHA-256 checksum of one file.

    Parameters
    ----------
    path : pathlib.Path
        File to hash.

    Returns
    -------
    str
        Lowercase hexadecimal SHA-256 digest.
    """

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_manifest(manifest_path: Path, payload: dict[str, Any]) -> None:
    """Write a manifest atomically after its checksums have been rebuilt.

    Parameters
    ----------
    manifest_path : pathlib.Path
        Destination manifest path.
    payload : dict[str, typing.Any]
        Manifest payload to serialize.

    Returns
    -------
    None
    """

    temporary = manifest_path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(manifest_path)


def _write_logo_size_override(stylesheet: Path, scale_percent: float) -> None:
    """Write one idempotent CSS override for the requested logo scale.

    Parameters
    ----------
    stylesheet : pathlib.Path
        Patient stylesheet to update.
    scale_percent : float
        Logo scale in percent relative to the generated default size.

    Returns
    -------
    None
    """

    scale = scale_percent / 100
    header_width = HEADER_LOGO_WIDTH_REM * scale
    footer_width = FOOTER_LOGO_WIDTH_REM * scale
    override = f"""{SIZE_OVERRIDE_START}
.header-logo {{
  height: auto;
  width: {header_width:g}rem;
}}

.footer-logo {{
  height: auto;
  width: {footer_width:g}rem;
}}
{SIZE_OVERRIDE_END}
"""
    content = stylesheet.read_text(encoding="utf-8")
    start = content.find(SIZE_OVERRIDE_START)
    end = content.find(SIZE_OVERRIDE_END, start)
    if start >= 0 and end >= start:
        end += len(SIZE_OVERRIDE_END)
        content = f"{content[:start].rstrip()}\n\n{override}{content[end:].lstrip()}"
    else:
        content = f"{content.rstrip()}\n\n{override}"
    temporary = stylesheet.with_suffix(".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(stylesheet)


if __name__ == "__main__":
    raise SystemExit(main())
