"""Tests for the standalone USB logo replacement script."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import TYPE_CHECKING

from sanikey.usb import validate_usb

if TYPE_CHECKING:
    from types import ModuleType


def _script_module() -> ModuleType:
    """Load the standalone script as a module for direct testing.

    Parameters
    ----------
    None

    Returns
    -------
    types.ModuleType
        Imported logo replacement script module.
    """

    script_path = Path(__file__).parents[1] / "scripts" / "replace_usb_logo.py"
    spec = importlib.util.spec_from_file_location("replace_usb_logo", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_usb_export(target: Path) -> None:
    """Create a minimal valid two-patient USB export.

    Parameters
    ----------
    target : pathlib.Path
        USB export root to populate.

    Returns
    -------
    None
    """

    patients = ("patient-a", "patient-b")
    root_links = "\n".join(
        f'<a href="patients/{patient_id}/web/index.html">{patient_id}</a>'
        for patient_id in patients
    )
    (target / "index.html").parent.mkdir(parents=True, exist_ok=True)
    (target / "index.html").write_text(root_links, encoding="utf-8")
    for patient_id in patients:
        web = target / "patients" / patient_id / "web"
        assets = web / "assets"
        assets.mkdir(parents=True)
        (target / "patients" / patient_id / "medical_archive.db").write_bytes(b"db")
        (web / "index.html").write_text("<!doctype html>", encoding="utf-8")
        (web / "data.js").write_text("window.SANIKEY_DATA = {};\n", encoding="utf-8")
        (web / "style.css").write_text(".header-logo {}\n", encoding="utf-8")
        (assets / "sanikey-logo-horizontal-transparent.svg").write_text(
            "<svg/>\n", encoding="utf-8"
        )
    manifest = target / "SANIKEY-MANIFEST.json"
    checksums = {
        path.relative_to(target).as_posix(): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in sorted(target.rglob("*"))
        if path.is_file() and path != manifest
    }
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "patients": [{"id": patient_id} for patient_id in patients],
                "checksums": checksums,
            }
        ),
        encoding="utf-8",
    )


def test_replace_usb_logo_updates_every_patient_and_manifest(tmp_path: Path) -> None:
    """Verify the script replaces every logo and repairs all checksums.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    module = _script_module()
    target = tmp_path / "usb"
    source = tmp_path / "replacement.svg"
    source.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>\n', encoding="utf-8")
    _write_usb_export(target)

    assert module.main([str(source), str(target), "150"]) == 0
    assert validate_usb(target)
    for patient_id in ("patient-a", "patient-b"):
        web = target / "patients" / patient_id / "web"
        assert (web / "assets" / "sanikey-logo-horizontal-transparent.svg").read_text(
            encoding="utf-8"
        ) == source.read_text(encoding="utf-8")
        stylesheet = (web / "style.css").read_text(encoding="utf-8")
        assert "width: 15.1875rem;" in stylesheet
        assert "width: 29.25rem;" in stylesheet
    assert module.main([str(source), str(target), "75"]) == 0
    stylesheet = (target / "patients" / "patient-a" / "web" / "style.css").read_text(
        encoding="utf-8"
    )
    assert stylesheet.count("/* sanikey-logo-size: start */") == 1
    assert "width: 7.59375rem;" in stylesheet
    assert "width: 14.625rem;" in stylesheet
    payload = json.loads((target / "SANIKEY-MANIFEST.json").read_text(encoding="utf-8"))
    logo_key = "patients/patient-a/web/assets/sanikey-logo-horizontal-transparent.svg"
    assert (
        payload["checksums"][logo_key]
        == hashlib.sha256(source.read_bytes()).hexdigest()
    )
