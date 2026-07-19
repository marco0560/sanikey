"""AIFA medication-leaflet lookup and local download helpers."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from hashlib import sha256
from typing import TYPE_CHECKING, Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

if TYPE_CHECKING:
    from pathlib import Path

    from .models import Medication, MedicationLeaflet, MedicationLeafletExclusion

API_ROOT = "https://api.aifa.gov.it/aifa-bdf-eif-be/1.0.0/"
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
    active_ingredients : tuple[str, ...], optional
        Active ingredients declared by AIFA.
    form : str | None, optional
        Pharmaceutical form declared by AIFA.
    strength : str | None, optional
        Dosage and pharmaceutical form declared by AIFA.
    company : str | None, optional
        Marketing authorisation holder declared by AIFA.
    atc : tuple[str, ...], optional
        AIFA ATC descriptions.
    routes : tuple[str, ...], optional
        Routes of administration declared by AIFA.
    packages : tuple[str, ...], optional
        Available package descriptions declared by AIFA.
    mismatches : tuple[str, ...], optional
        Curated fields that require operator verification before confirmation.
    """

    title: str
    codice_sis: str
    aic6: str
    active_ingredients: tuple[str, ...] = ()
    form: str | None = None
    strength: str | None = None
    company: str | None = None
    atc: tuple[str, ...] = ()
    routes: tuple[str, ...] = ()
    packages: tuple[str, ...] = ()
    mismatches: tuple[str, ...] = ()


@dataclass(frozen=True)
class AifaCandidateSearch:
    """Represent the deterministic result of a multi-query AIFA search.

    Parameters
    ----------
    exact : tuple[AifaCandidate, ...]
        Candidates compatible with every populated curated field.
    review : tuple[AifaCandidate, ...]
        Plausible candidates requiring operator review.
    all_candidates : tuple[AifaCandidate, ...]
        All candidates returned by successful AIFA searches.
    """

    exact: tuple[AifaCandidate, ...] = ()
    review: tuple[AifaCandidate, ...] = ()
    all_candidates: tuple[AifaCandidate, ...] = ()


@dataclass(frozen=True)
class LeafletDownloadFailure:
    """Describe one failed AIFA FI or RCP download.

    Parameters
    ----------
    medication_id : str
        Curated medication identifier.
    kind : str
        AIFA document kind, either ``FI`` or ``RCP``.
    url : str
        Requested public AIFA URL.
    reason : str
        Short diagnostic returned or derived from the failed response.

    Returns
    -------
    None
    """

    medication_id: str
    kind: str
    url: str
    reason: str


@dataclass(frozen=True)
class LeafletDownloadResult:
    """Collect local AIFA download dates and failures for one build.

    Parameters
    ----------
    downloaded_at : dict[str, str]
        Successful local FI/RCP dates keyed by medication identifier.
    failures : tuple[LeafletDownloadFailure, ...]
        Failed FI or RCP downloads.

    Returns
    -------
    None
    """

    downloaded_at: dict[str, str]
    failures: tuple[LeafletDownloadFailure, ...] = ()


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

    search = lookup_aifa_candidate_search(medication)
    return None if search is None else search.exact


def lookup_aifa_candidate_search(
    medication: Medication,
    *,
    query: str | None = None,
) -> AifaCandidateSearch | None:
    """Search AIFA by commercial and active names, separating review results.

    Parameters
    ----------
    medication : sanikey.models.Medication
        Medication supplied by curated metadata.
    query : str | None, optional
        Explicit operator search text. It replaces the automatic queries.

    Returns
    -------
    AifaCandidateSearch | None
        Classified candidates, or ``None`` when every AIFA request failed.
    """

    queries = _lookup_queries(medication, query)
    if not queries:
        return AifaCandidateSearch()
    raw_candidates: list[AifaCandidate] = []
    available = False
    for lookup_query in queries:
        payload = _aifa_json(
            f"formadosaggio/ricerca?{urlencode({'query': lookup_query, 'page': 0})}"
        )
        if payload is None:
            continue
        available = True
        raw_candidates.extend(_candidates_from_payload(payload))
    if not available:
        return None
    ordered = _ordered_candidates(raw_candidates)
    classified = tuple(
        replace(candidate, mismatches=_candidate_mismatches(candidate, medication))
        for candidate in ordered
    )
    exact = tuple(candidate for candidate in classified if not candidate.mismatches)
    review = tuple(
        candidate
        for candidate in classified
        if candidate.mismatches and _candidate_is_plausible(candidate, medication)
    )
    return AifaCandidateSearch(exact, review, classified)


def _lookup_queries(medication: Medication, query: str | None) -> tuple[str, ...]:
    """Return normalized, de-duplicated AIFA search terms.

    Parameters
    ----------
    medication : sanikey.models.Medication
        Curated medication identity.
    query : str | None
        Explicit operator search text, when supplied.

    Returns
    -------
    tuple[str, ...]
        Search terms in deterministic priority order.
    """

    values = (
        (query,)
        if query is not None
        else (medication.name, medication.active_ingredient)
    )
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or not value.strip():
            continue
        normalized = _normalized_text(value)
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(value.strip())
    return tuple(result)


def _candidates_from_payload(payload: dict[str, Any]) -> tuple[AifaCandidate, ...]:
    """Extract AIFA candidates from one successful API response.

    Parameters
    ----------
    payload : dict[str, typing.Any]
        Decoded AIFA response.

    Returns
    -------
    tuple[AifaCandidate, ...]
        Unordered parsed candidates.
    """

    content = payload.get("data", {}).get("content", [])
    candidates = []
    for item in content if isinstance(content, list) else []:
        if not isinstance(item, dict):
            continue
        medicine = item.get("medicinale", {})
        medicine = medicine if isinstance(medicine, dict) else {}
        code_sis = medicine.get("codiceSis")
        aic6 = medicine.get("aic6")
        title = medicine.get("denominazioneMedicinale")
        if all(isinstance(value, (str, int)) for value in (code_sis, aic6, title)):
            packages = item.get("confezioni", [])
            candidates.append(
                AifaCandidate(
                    str(title),
                    str(code_sis),
                    str(aic6),
                    _string_tuple(item.get("principiAttiviIt")),
                    _optional_aifa_string(item.get("formaFarmaceutica")),
                    _optional_aifa_string(item.get("descrizioneFormaDosaggio")),
                    _optional_aifa_string(medicine.get("aziendaTitolare")),
                    _string_tuple(item.get("descrizioneAtc")),
                    _string_tuple(item.get("vieSomministrazione")),
                    tuple(
                        package_name
                        for package in packages
                        if isinstance(package, dict)
                        and (
                            package_name := _optional_aifa_string(
                                package.get("denominazionePackage")
                            )
                        )
                    ),
                )
            )
    return tuple(candidates)


def _ordered_candidates(candidates: list[AifaCandidate]) -> tuple[AifaCandidate, ...]:
    """De-duplicate and sort AIFA candidates for reproducible review.

    Parameters
    ----------
    candidates : list[AifaCandidate]
        Candidates returned by one or more AIFA requests.

    Returns
    -------
    tuple[AifaCandidate, ...]
        Sorted unique candidates.
    """

    return tuple(
        sorted(
            set(candidates),
            key=lambda item: (
                item.title.casefold(),
                item.strength or "",
                item.form or "",
            ),
        )
    )


def _candidate_matches_medication(
    candidate: AifaCandidate,
    medication: Medication,
) -> bool:
    """Check whether populated AIFA fields match the curated medication.

    Parameters
    ----------
    candidate : AifaCandidate
        AIFA formulation candidate.
    medication : sanikey.models.Medication
        Curated medication identity.

    Returns
    -------
    bool
        ``True`` when every populated curated field is also present and
        compatible in AIFA. Incomplete AIFA data is treated as no match so it
        cannot crowd the operator review with unrelated formulations.
    """

    return not _candidate_mismatches(candidate, medication)


def _candidate_mismatches(
    candidate: AifaCandidate,
    medication: Medication,
) -> tuple[str, ...]:
    """Return populated curated fields not confirmed by the AIFA candidate.

    Parameters
    ----------
    candidate : AifaCandidate
        AIFA formulation candidate.
    medication : sanikey.models.Medication
        Curated medication identity.

    Returns
    -------
    tuple[str, ...]
        Italian labels for fields requiring operator verification.
    """

    mismatches: list[str] = []
    if medication.active_ingredient and not _active_ingredients_match(
        candidate, medication
    ):
        mismatches.append("principio attivo")
    if medication.form and not (
        candidate.form
        and bool(_form_stems(candidate.form) & _form_stems(medication.form))
    ):
        mismatches.append("forma")
    if medication.strength_per_unit and not (
        candidate.strength
        and _dose_signatures(medication.strength_per_unit).issubset(
            _dose_signatures(candidate.strength)
        )
    ):
        mismatches.append("dosaggio")
    return tuple(mismatches)


def _active_ingredients_match(candidate: AifaCandidate, medication: Medication) -> bool:
    """Check component-wise compatibility of curated and AIFA active ingredients.

    Parameters
    ----------
    candidate : AifaCandidate
        AIFA formulation candidate.
    medication : sanikey.models.Medication
        Curated medication identity.

    Returns
    -------
    bool
        Whether every named curated component occurs in AIFA active ingredients.
    """

    components = _active_ingredient_components(medication.active_ingredient or "")
    haystack = " ".join(_normalized_text(item) for item in candidate.active_ingredients)
    return bool(components and haystack) and all(
        component in haystack for component in components
    )


def _active_ingredient_components(value: str) -> tuple[str, ...]:
    """Split curated active-ingredient text into normalized components.

    Parameters
    ----------
    value : str
        Curated active-ingredient text.

    Returns
    -------
    tuple[str, ...]
        Meaningful component names, including combinations joined by ``e``.
    """

    return tuple(
        component
        for item in re.split(r"\s*(?:,|\+|/|\be\b)\s*", value, flags=re.IGNORECASE)
        if (component := _normalized_text(item))
    )


def _candidate_is_plausible(candidate: AifaCandidate, medication: Medication) -> bool:
    """Return whether a non-exact candidate is relevant enough for review.

    Parameters
    ----------
    candidate : AifaCandidate
        Classified AIFA candidate.
    medication : sanikey.models.Medication
        Curated medication identity.

    Returns
    -------
    bool
        ``True`` for a matching active component or commercial medicine name.
    """

    return _active_ingredients_match(candidate, medication) or _commercial_names_match(
        candidate.title, medication.name
    )


def _commercial_names_match(candidate_name: str, medication_name: str) -> bool:
    """Compare commercial names without accepting short numeric fragments.

    Parameters
    ----------
    candidate_name : str
        AIFA medicine title.
    medication_name : str
        Curated medicine name.

    Returns
    -------
    bool
        Whether either normalized commercial name contains the other.
    """

    candidate = _normalized_text(candidate_name)
    medication = _normalized_text(medication_name)
    return (
        len(candidate) >= 4
        and bool(medication)
        and (candidate in medication or medication in candidate)
    )


def _normalized_text(value: str) -> str:
    """Normalize a medicine field for case-insensitive comparison.

    Parameters
    ----------
    value : str
        Source field value.

    Returns
    -------
    str
        Lowercase alphanumeric text with collapsed spacing.
    """

    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def _form_stems(value: str) -> set[str]:
    """Extract conservative form-name stems from a pharmaceutical form.

    Parameters
    ----------
    value : str
        Pharmaceutical form text.

    Returns
    -------
    set[str]
        Stems long enough to distinguish forms such as tablets and capsules.
    """

    tokens = _normalized_text(value).split()
    return {
        token.rstrip("aeiop")[:8] for token in tokens if len(token.rstrip("aeiop")) >= 4
    }


def _dose_signatures(value: str) -> set[tuple[str, str]]:
    """Extract normalized numeric dose-and-unit signatures from text.

    Parameters
    ----------
    value : str
        Dosage text from curated metadata or AIFA.

    Returns
    -------
    set[tuple[str, str]]
        Numeric value and unit pairs, preserving all stated quantities.
    """

    units = {
        "microgrammi": "mcg",
        "microgrammo": "mcg",
        "mcg": "mcg",
        "mg": "mg",
        "g": "g",
        "ml": "ml",
        "ui": "ui",
    }
    matches = re.findall(
        r"(\d+(?:[.,]\d+)?)\s*(microgrammi|microgrammo|mcg|mg|ml|ui|g)\b",
        value.casefold(),
    )
    return {
        (number.replace(",", ".").lstrip("0") or "0", units[unit])
        for number, unit in matches
    }


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


def _string_tuple(value: object) -> tuple[str, ...]:
    """Convert an AIFA array of strings to a normalized tuple.

    Parameters
    ----------
    value : object
        JSON value returned by AIFA.

    Returns
    -------
    tuple[str, ...]
        Non-empty strings in their source order.
    """

    if not isinstance(value, list):
        return ()
    return tuple(
        item.strip() for item in value if isinstance(item, str) and item.strip()
    )


def _optional_aifa_string(value: object) -> str | None:
    """Return a stripped AIFA string when present.

    Parameters
    ----------
    value : object
        JSON value returned by AIFA.

    Returns
    -------
    str | None
        Non-empty string, otherwise ``None``.
    """

    return value.strip() if isinstance(value, str) and value.strip() else None


def download_confirmed_leaflets(
    build_root: Path,
    references: tuple[MedicationLeaflet, ...],
) -> LeafletDownloadResult:
    """Download FI and RCP documents for confirmed AIFA references.

    Parameters
    ----------
    build_root : pathlib.Path
        Patient generated-build directory.
    references : tuple[sanikey.models.MedicationLeaflet, ...]
        Confirmed AIFA references.

    Returns
    -------
    LeafletDownloadResult
        Successful local FI/RCP dates and per-document failures. A medicine's
        existing local pair is retained unless both replacement PDFs validate.
    """

    result = leaflet_download_dates(build_root)
    changed = False
    failures: list[LeafletDownloadFailure] = []
    for reference in references:
        target = build_root / "medication-leaflets" / reference.medication_id
        downloaded, document_failures = _fetch_leaflet_documents(reference)
        failures.extend(document_failures)
        if len(downloaded) == 2:
            target.mkdir(parents=True, exist_ok=True)
            for filename, content in downloaded.items():
                temporary = target / f".{filename}.tmp"
                temporary.write_bytes(content)
                temporary.replace(target / filename)
            changed = True
            result[reference.medication_id] = datetime.now(UTC).date().isoformat()
    if changed:
        _write_download_dates(build_root, result)
    return LeafletDownloadResult(result, tuple(failures))


def probe_leaflet_documents(
    reference: MedicationLeaflet,
) -> tuple[LeafletDownloadFailure, ...]:
    """Check whether AIFA exposes valid FI and RCP PDFs for one reference.

    Parameters
    ----------
    reference : sanikey.models.MedicationLeaflet
        Confirmed or candidate AIFA medicine reference.

    Returns
    -------
    tuple[LeafletDownloadFailure, ...]
        Empty when both documents are valid PDFs, otherwise one failure for
        each unavailable or invalid document. Downloaded bytes are discarded.
    """

    _, failures = _fetch_leaflet_documents(reference)
    return failures


def _fetch_leaflet_documents(
    reference: MedicationLeaflet,
) -> tuple[dict[str, bytes], tuple[LeafletDownloadFailure, ...]]:
    """Retrieve and validate the FI/RCP pair for one AIFA reference.

    Parameters
    ----------
    reference : sanikey.models.MedicationLeaflet
        Confirmed or candidate AIFA medicine reference.

    Returns
    -------
    tuple[dict[str, bytes], tuple[LeafletDownloadFailure, ...]]
        PDF bytes keyed by local filename and any per-document failures.
    """

    downloaded: dict[str, bytes] = {}
    failures: list[LeafletDownloadFailure] = []
    for kind, filename in (("FI", "foglio-illustrativo.pdf"), ("RCP", "rcp.pdf")):
        url = _aifa_printed_url(reference, kind)
        try:
            request = Request(url, headers={"Accept": "application/pdf"})
            with urlopen(request, timeout=30) as response:
                content = response.read()
        except HTTPError as error:
            failures.append(
                LeafletDownloadFailure(
                    reference.medication_id,
                    kind,
                    url,
                    _aifa_http_error_reason(error),
                )
            )
            continue
        except OSError as error:
            failures.append(
                LeafletDownloadFailure(
                    reference.medication_id,
                    kind,
                    url,
                    f"errore di rete: {error}",
                )
            )
            continue
        if not content.startswith(b"%PDF-"):
            failures.append(
                LeafletDownloadFailure(
                    reference.medication_id,
                    kind,
                    url,
                    "risposta AIFA non in formato PDF",
                )
            )
            continue
        downloaded[filename] = content
    return downloaded, tuple(failures)


def _aifa_printed_url(reference: MedicationLeaflet, kind: str) -> str:
    """Build the direct public AIFA URL for one FI or RCP PDF.

    Parameters
    ----------
    reference : sanikey.models.MedicationLeaflet
        Confirmed AIFA medicine reference.
    kind : str
        AIFA document kind, either ``FI`` or ``RCP``.

    Returns
    -------
    str
        Direct AIFA document URL.

    Raises
    ------
    ValueError
        If ``kind`` is not a supported AIFA document kind.
    """

    if kind not in {"FI", "RCP"}:
        msg = f"tipo documento AIFA non supportato: {kind}"
        raise ValueError(msg)
    query = urlencode({"ts": kind})
    return (
        f"{API_ROOT}organizzazione/{reference.codice_sis}/farmaci/"
        f"{reference.aic6}/stampati?{query}"
    )


def _aifa_http_error_reason(error: HTTPError) -> str:
    """Return a short AIFA diagnostic from one failed HTTP response.

    Parameters
    ----------
    error : urllib.error.HTTPError
        HTTP failure raised while retrieving an AIFA document.

    Returns
    -------
    str
        Status and concise AIFA response detail when available.
    """

    detail = ""
    try:
        payload = json.loads(error.read().decode("utf-8", errors="replace"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        payload = None
    if isinstance(payload, dict):
        errors = payload.get("errors")
        if isinstance(errors, list):
            error_messages = [
                item.strip()
                for item in errors
                if isinstance(item, str) and item.strip()
            ]
            detail = "; ".join(error_messages)[:240]
        description = payload.get("description") or payload.get("message")
        if not detail and isinstance(description, str):
            detail = description.strip().replace("\n", " ")[:240]
    return f"HTTP {error.code}" + (f": {detail}" if detail else "")


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

    return {
        "aifa_fi_url": _aifa_printed_url(reference, "FI"),
        "aifa_rcp_url": _aifa_printed_url(reference, "RCP"),
    }


def write_confirmed_references(
    metadata_directory: Path,
    references: tuple[MedicationLeaflet, ...],
    exclusions: tuple[MedicationLeafletExclusion, ...] = (),
) -> Path:
    """Persist confirmed AIFA references for future local downloads.

    Parameters
    ----------
    metadata_directory : pathlib.Path
        Patient metadata directory.
    references : tuple[sanikey.models.MedicationLeaflet, ...]
        Confirmed references to persist.
    exclusions : tuple[sanikey.models.MedicationLeafletExclusion, ...], optional
        Curated markers for medications with no applicable AIFA leaflet.

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
    for exclusion in sorted(exclusions, key=lambda item: item.medication_id):
        lines.extend(
            (
                "[[unavailable]]",
                f'medication_id = "{exclusion.medication_id}"',
                f'reason = "{exclusion.reason}"',
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
