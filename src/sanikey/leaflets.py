"""AIFA medication-leaflet lookup and local download helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode
from urllib.request import urlopen

if TYPE_CHECKING:
    from pathlib import Path

    from .models import Medication, MedicationLeaflet

API_ROOT = "https://api.aifa.gov.it/aifa-bdf-eif-be/1.0.0/"
PORTAL_ROOT = "https://medicinali.aifa.gov.it/#/it"
DOWNLOAD_MANIFEST = "medication-leaflets.json"


@dataclass(frozen=True)
class AifaCandidate:
    """Represent one AIFA medicine candidate.

    Parameters
    ----------
    title : str
        AIFA medicine name.
    codice_sis : str
        AIFA organisation identifier.
    aic6 : str
        AIFA medicine identifier.
    """

    title: str
    codice_sis: str
    aic6: str


def find_aifa_candidates(medication: Medication) -> tuple[AifaCandidate, ...]:
    """Search AIFA candidates using the curated medication identity.

    Parameters
    ----------
    medication : sanikey.models.Medication
        Medication supplied by curated metadata.

    Returns
    -------
    tuple[AifaCandidate, ...]
        Deterministically ordered AIFA candidates.
    """

    candidates = lookup_aifa_candidates(medication)
    return candidates or ()


def lookup_aifa_candidates(medication: Medication) -> tuple[AifaCandidate, ...] | None:
    """Search AIFA and distinguish unavailable service from no candidates.

    Parameters
    ----------
    medication : sanikey.models.Medication
        Medication supplied by curated metadata.

    Returns
    -------
    tuple[AifaCandidate, ...] | None
        Candidates when AIFA answered, an empty tuple when none matches, or
        ``None`` when the service cannot be reached.
    """

    query = medication.name or medication.active_ingredient or ""
    if not query:
        return ()
    payload = _aifa_json(
        f"formadosaggio/ricerca?{urlencode({'query': query, 'page': 0})}"
    )
    if payload is None:
        return None
    content = payload.get("data", {}).get("content", [])
    candidates = []
    for item in content if isinstance(content, list) else []:
        medicine = item.get("medicinale", {}) if isinstance(item, dict) else {}
        code_sis = medicine.get("codiceSis")
        aic6 = medicine.get("aic6")
        title = medicine.get("denominazioneMedicinale")
        if all(isinstance(value, (str, int)) for value in (code_sis, aic6, title)):
            candidates.append(AifaCandidate(str(title), str(code_sis), str(aic6)))
    return tuple(sorted(set(candidates), key=lambda item: item.title.casefold()))


def medication_fingerprint(medication: Medication) -> str:
    """Return a stable lookup fingerprint for one curated medication.

    Parameters
    ----------
    medication : sanikey.models.Medication
        Curated medication identity.

    Returns
    -------
    str
        SHA-256 digest of the fields relevant to the AIFA search.
    """

    identity = "\x1f".join(
        value.strip().casefold()
        for value in (
            medication.name,
            medication.active_ingredient or "",
            medication.form or "",
            medication.strength_per_unit or "",
        )
    )
    return sha256(identity.encode("utf-8")).hexdigest()


def download_confirmed_leaflets(
    build_root: Path,
    references: tuple[MedicationLeaflet, ...],
) -> dict[str, str]:
    """Download FI and RCP documents for confirmed AIFA references.

    Parameters
    ----------
    build_root : pathlib.Path
        Patient generated-build directory.
    references : tuple[sanikey.models.MedicationLeaflet, ...]
        Confirmed AIFA references.

    Returns
    -------
    dict[str, str]
        ISO download date keyed by medication id for successful downloads.
    """

    result = leaflet_download_dates(build_root)
    changed = False
    for reference in references:
        target = build_root / "medication-leaflets" / reference.medication_id
        target.mkdir(parents=True, exist_ok=True)
        fi_updated = False
        for kind, filename in (("FI", "foglio-illustrativo.pdf"), ("RCP", "rcp.pdf")):
            url = f"{API_ROOT}organizzazione/{reference.codice_sis}/farmaci/{reference.aic6}/stampati/{kind}"
            try:
                with urlopen(url, timeout=30) as response:
                    content = response.read()
            except OSError:
                continue
            if content:
                target.joinpath(filename).write_bytes(content)
                changed = True
                fi_updated = fi_updated or kind == "FI"
        if fi_updated:
            result[reference.medication_id] = datetime.now(UTC).date().isoformat()
    if changed:
        _write_download_dates(build_root, result)
    return result


def leaflet_download_dates(build_root: Path) -> dict[str, str]:
    """Load successful local FI download dates from the generated build.

    Parameters
    ----------
    build_root : pathlib.Path
        Patient generated-build directory.

    Returns
    -------
    dict[str, str]
        ISO dates keyed by medication id. Malformed or absent state is ignored.
    """

    path = build_root / "manifests" / DOWNLOAD_MANIFEST
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    dates = payload.get("downloaded_at") if isinstance(payload, dict) else None
    if not isinstance(dates, dict):
        return {}
    return {
        medication_id: date
        for medication_id, date in dates.items()
        if isinstance(medication_id, str) and isinstance(date, str)
    }


def leaflet_urls(reference: MedicationLeaflet) -> dict[str, str]:
    """Return the public AIFA URLs for one confirmed reference.

    Parameters
    ----------
    reference : sanikey.models.MedicationLeaflet
        Confirmed AIFA reference.

    Returns
    -------
    dict[str, str]
        URLs keyed by document kind.
    """

    base = f"{PORTAL_ROOT}/organizzazione/{reference.codice_sis}/farmaci/{reference.aic6}/stampati"
    return {"aifa_fi_url": f"{base}/FI", "aifa_rcp_url": f"{base}/RCP"}


def write_confirmed_references(
    metadata_directory: Path, references: tuple[MedicationLeaflet, ...]
) -> Path:
    """Persist confirmed AIFA references for future local downloads.

    Parameters
    ----------
    metadata_directory : pathlib.Path
        Patient metadata directory.
    references : tuple[sanikey.models.MedicationLeaflet, ...]
        Confirmed references to persist.

    Returns
    -------
    pathlib.Path
        Written TOML path.
    """

    target = metadata_directory / "medication_leaflets.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for reference in sorted(references, key=lambda item: item.medication_id):
        lines.extend(
            (
                "[[leaflet]]",
                f'medication_id = "{reference.medication_id}"',
                f'codice_sis = "{reference.codice_sis}"',
                f'aic6 = "{reference.aic6}"',
                *(
                    (f'source_fingerprint = "{reference.source_fingerprint}"',)
                    if reference.source_fingerprint
                    else ()
                ),
                "",
            )
        )
    target.write_text("\n".join(lines), encoding="utf-8")
    return target


def _write_download_dates(build_root: Path, dates: dict[str, str]) -> None:
    """Persist successful local FI download dates for the generated export.

    Parameters
    ----------
    build_root : pathlib.Path
        Patient generated-build directory.
    dates : dict[str, str]
        ISO dates keyed by medication id.

    Returns
    -------
    None
    """

    target = build_root / "manifests" / DOWNLOAD_MANIFEST
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps({"downloaded_at": dict(sorted(dates.items()))}, indent=2) + "\n",
        encoding="utf-8",
    )


def _aifa_json(path: str) -> dict[str, Any] | None:
    """Read one JSON response from the public AIFA API.

    Parameters
    ----------
    path : str
        API-relative request path.

    Returns
    -------
    dict[str, typing.Any] | None
        Decoded JSON object, or ``None`` when the service is unavailable.
    """

    try:
        with urlopen(f"{API_ROOT}{path}", timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None
