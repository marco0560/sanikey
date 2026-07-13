"""Static JSON exports for frontend and offline search."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

from .markdown import render_markdown
from .models import TimelineEvent

if TYPE_CHECKING:
    from pathlib import Path

    from .config import PersonConfig
    from .dicom import DicomStudy
    from .documents import ExtractedText
    from .models import (
        ClinicalProblem,
        CuratedMetadata,
        DocumentRecord,
        Medication,
        Observation,
        Procedure,
        TherapyEpisode,
    )


@dataclass(frozen=True)
class ExportResult:
    """Result of JSON export generation.

    Parameters
    ----------
    data_dir : pathlib.Path
        Frontend data directory.
    documents : pathlib.Path
        Documents JSON path.
    search : pathlib.Path
        Search JSON path.
    timeline : pathlib.Path
        Timeline JSON path.
    summary : pathlib.Path
        Summary JSON path.
    data_script : pathlib.Path
        Frontend data JavaScript path for ``file://`` loading.
    content_search_script : pathlib.Path
        Advanced search data JavaScript path for ``file://`` loading.
    warning_messages : tuple[str, ...]
        Export warnings.
    """

    data_dir: Path
    documents: Path
    search: Path
    timeline: Path
    summary: Path
    data_script: Path
    content_search_script: Path
    warning_messages: tuple[str, ...] = ()


def generate_exports(
    person: PersonConfig,
    documents: tuple[DocumentRecord, ...],
    metadata: CuratedMetadata,
    extracted_text: tuple[ExtractedText, ...] = (),
    dicom_studies: tuple[DicomStudy, ...] = (),
) -> ExportResult:
    """Generate static JSON exports for one patient.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.
    documents : tuple[DocumentRecord, ...]
        Document records.
    metadata : CuratedMetadata
        Curated metadata.
    extracted_text : tuple[ExtractedText, ...], optional
        Extracted/OCR text records used by advanced frontend search.
    dicom_studies : tuple[DicomStudy, ...], optional
        Cataloged DICOM studies used by the frontend clinical dashboard.

    Returns
    -------
    ExportResult
        Generated export paths.
    """

    data_dir = person.local_build / "web" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    consultation_documents = _consultation_documents(documents)
    ordered_documents = _ordered_documents(consultation_documents)
    dicom_viewers = _dicom_viewers_by_support(dicom_studies)
    documents_payload = [
        _document_payload(person, document, metadata, dicom_viewers)
        for document in ordered_documents
    ]
    clinical_payload = _clinical_payload(person, metadata, dicom_studies)
    search_payload = [
        *(
            _document_search_payload(person, document, metadata, dicom_viewers)
            for document in consultation_documents
        ),
        *_metadata_search_payloads(clinical_payload),
    ]
    timeline_events = _timeline_events(
        consultation_documents,
        metadata,
        order=person.ui.timeline_order,
    )
    timeline_payload = [asdict(event) for event in timeline_events]
    summary_payload = {
        "patient_id": person.id,
        "display_name": person.display_name,
        "ui": _ui_payload(person),
        "document_count": len(consultation_documents),
        "problem_count": len(metadata.problems),
        "therapy_count": len(metadata.therapies),
        "procedure_count": len(metadata.procedures),
        "observation_count": len(metadata.observations),
        "clinical_summary": metadata.clinical_summary,
        "clinical_summary_html": render_markdown(metadata.clinical_summary),
    }
    documents_path = _write_json(
        data_dir / "documents.json",
        documents_payload,
    )
    search_path = _write_json(
        data_dir / "search.json",
        search_payload,
    )
    timeline_path = _write_json(
        data_dir / "timeline.json",
        timeline_payload,
    )
    summary_path = _write_json(
        data_dir / "summary.json",
        summary_payload,
    )
    data_script_path = _write_data_script(
        person.local_build / "web" / "data.js",
        {
            "documents": documents_payload,
            "clinical": clinical_payload,
            "search": search_payload,
            "timeline": timeline_payload,
            "summary": summary_payload,
        },
    )
    content_search_payload = _content_search_payload(
        person,
        ordered_documents,
        metadata,
        extracted_text,
        dicom_viewers,
    )
    content_search_script = _write_content_search_script(
        person.local_build / "web" / "content-search.js",
        content_search_payload,
    )
    warning_messages = _content_search_warning_messages(
        person,
        content_search_script,
    )
    _write_json(
        person.local_build / "search" / "search.json",
        json.loads(search_path.read_text(encoding="utf-8")),
    )
    _write_json(
        person.local_build / "timeline" / "timeline.json",
        json.loads(timeline_path.read_text(encoding="utf-8")),
    )
    _write_dicom_html_viewer_manifest(person, dicom_studies)
    return ExportResult(
        data_dir=data_dir,
        documents=documents_path,
        search=search_path,
        timeline=timeline_path,
        summary=summary_path,
        data_script=data_script_path,
        content_search_script=content_search_script,
        warning_messages=warning_messages,
    )


def _ui_payload(person: PersonConfig) -> dict[str, Any]:
    """Build the frontend-safe UI configuration payload.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.

    Returns
    -------
    dict[str, Any]
        JSON-serializable UI configuration.
    """

    background_href = None
    if person.ui.background_image is not None:
        background_href = (
            f"assets/background{person.ui.background_image.suffix.lower()}"
        )
    return {
        "accent_color": person.ui.accent_color,
        "density": person.ui.density,
        "default_tab": person.ui.default_tab,
        "timeline_order": person.ui.timeline_order,
        "document_link_mode": person.ui.document_link_mode,
        "subtitle": person.ui.subtitle,
        "background_image": background_href,
        "background_opacity": person.ui.background_opacity,
    }


def _write_data_script(target: Path, payload: dict[str, Any]) -> Path:
    """Write frontend data as JavaScript for direct ``file://`` loading.

    Parameters
    ----------
    target : pathlib.Path
        JavaScript output path.
    payload : dict[str, Any]
        Frontend data payload.

    Returns
    -------
    pathlib.Path
        Written JavaScript path.
    """

    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    target.write_text(
        f"window.SANIKEY_DATA = {encoded};\n",
        encoding="utf-8",
    )
    return target


def _write_content_search_script(target: Path, payload: dict[str, Any]) -> Path:
    """Write advanced search data as JavaScript for direct ``file://`` loading.

    Parameters
    ----------
    target : pathlib.Path
        JavaScript output path.
    payload : dict[str, Any]
        Advanced search payload.

    Returns
    -------
    pathlib.Path
        Written JavaScript path.
    """

    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    target.write_text(
        f"window.SANIKEY_CONTENT_SEARCH = {encoded};\n",
        encoding="utf-8",
    )
    return target


def _content_search_payload(
    person: PersonConfig,
    documents: tuple[DocumentRecord, ...],
    metadata: CuratedMetadata,
    extracted_text: tuple[ExtractedText, ...],
    dicom_viewers: dict[Path, dict[str, str]],
) -> dict[str, Any]:
    """Build the advanced offline search payload.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.
    documents : tuple[DocumentRecord, ...]
        Ordered document records.
    metadata : CuratedMetadata
        Curated metadata.
    extracted_text : tuple[ExtractedText, ...]
        Extracted/OCR text records.
    dicom_viewers : dict[pathlib.Path, dict[str, str]]
        Viewer metadata keyed by DICOM support path.

    Returns
    -------
    dict[str, Any]
        JSON-serializable advanced search payload.
    """

    text_by_document = {
        item.document_id: item.text for item in extracted_text if item.text
    }
    return {
        "schema_version": 1,
        "dictionary": _search_dictionary_payload(person),
        "documents": [
            _content_search_document_payload(
                person, document, metadata, text_by_document, dicom_viewers
            )
            for document in documents
            if document.document_id in text_by_document
        ],
    }


def _search_dictionary_payload(person: PersonConfig) -> dict[str, Any]:
    """Build the frontend search dictionary payload.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.

    Returns
    -------
    dict[str, Any]
        JSON-serializable dictionary payload.
    """

    dictionary = person.search.dictionary_data
    return {
        "terms": {key: list(values) for key, values in dictionary.terms.items()},
        "months": {key: list(values) for key, values in dictionary.months.items()},
    }


def _dicom_viewers_by_support(
    dicom_studies: tuple[DicomStudy, ...],
) -> dict[Path, dict[str, str]]:
    """Return DICOM viewer metadata keyed by support path.

    Parameters
    ----------
    dicom_studies : tuple[DicomStudy, ...]
        Cataloged DICOM studies.

    Returns
    -------
    dict[pathlib.Path, dict[str, str]]
        Viewer metadata for studies with browser-openable viewers.
    """

    viewers: dict[Path, dict[str, str]] = {}
    for study in dicom_studies:
        viewer_href = _dicom_html_viewer_href(study)
        if viewer_href is None:
            continue
        viewers[study.support_path] = {
            "study_id": study.study_id,
            "viewer_href": viewer_href,
        }
    return viewers


def _content_search_document_payload(
    person: PersonConfig,
    document: DocumentRecord,
    metadata: CuratedMetadata,
    text: dict[str, str],
    dicom_viewers: dict[Path, dict[str, str]],
) -> dict[str, Any]:
    """Build one advanced-search document payload.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.
    document : DocumentRecord
        Document record.
    metadata : CuratedMetadata
        Curated metadata.
    text : dict[str, str]
        Extracted text keyed by document id.
    dicom_viewers : dict[pathlib.Path, dict[str, str]]
        Viewer metadata keyed by DICOM support path.

    Returns
    -------
    dict[str, Any]
        JSON-serializable document search payload.
    """

    return {
        **_document_payload(person, document, metadata, dicom_viewers),
        "text": text[document.document_id],
    }


def _content_search_warning_messages(
    person: PersonConfig,
    content_search_script: Path,
) -> tuple[str, ...]:
    """Return content-search export warnings.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.
    content_search_script : pathlib.Path
        Generated advanced search script.

    Returns
    -------
    tuple[str, ...]
        Warning messages.
    """

    size_mb = content_search_script.stat().st_size / (1024 * 1024)
    threshold = person.search.advanced_index_warning_mb
    if size_mb <= threshold:
        return ()
    return (
        "advanced search index is large: "
        f"{size_mb:.1f} MiB exceeds configured warning threshold {threshold} MiB",
    )


def _document_payload(
    person: PersonConfig,
    document: DocumentRecord,
    metadata: CuratedMetadata,
    dicom_viewers: dict[Path, dict[str, str]],
) -> dict[str, Any]:
    """Build frontend document payload.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.
    document : DocumentRecord
        Document record.
    metadata : CuratedMetadata
        Curated metadata.
    dicom_viewers : dict[pathlib.Path, dict[str, str]]
        Viewer metadata keyed by DICOM support path.

    Returns
    -------
    dict[str, Any]
        JSON-serializable payload.
    """

    href = _document_href(person, document)
    viewer = dicom_viewers.get(document.path)
    payload = {
        "id": document.document_id,
        "title": document.title,
        "date": document.date,
        "category": document.category,
        "kind": document.kind,
        "path": _document_display_path(person, document),
        "href": href,
        "origin": document.origin,
        "container_id": document.container_id,
        "internal_path": document.internal_path,
        "tags": list(_document_tags(document, metadata)),
        "markdown_html": _document_markdown_html(document),
    }
    if viewer is not None:
        payload.update(
            {
                "viewer_href": viewer["viewer_href"],
                "dicom_study_id": viewer["study_id"],
                "support_href": href,
                "primary_href": viewer["viewer_href"],
                "primary_action": "Apri studio DICOM",
            }
        )
    return payload


def _consultation_documents(
    documents: tuple[DocumentRecord, ...],
) -> tuple[DocumentRecord, ...]:
    """Return document records suitable for human consultation lists.

    Parameters
    ----------
    documents : tuple[DocumentRecord, ...]
        Source and derived document records.

    Returns
    -------
    tuple[DocumentRecord, ...]
        Records excluding technical DICOM instance files.
    """

    return tuple(
        document for document in documents if not document.kind.startswith("dicom_")
    )


def _ordered_documents(
    documents: tuple[DocumentRecord, ...],
) -> tuple[DocumentRecord, ...]:
    """Return documents in consultation order.

    Parameters
    ----------
    documents : tuple[DocumentRecord, ...]
        Document records.

    Returns
    -------
    tuple[DocumentRecord, ...]
        Documents ordered from most recent to oldest, with undated documents
        last and title/path as deterministic tie-breakers.
    """

    by_title = sorted(
        documents,
        key=lambda item: (item.title.lower(), item.path.as_posix()),
    )
    return tuple(sorted(by_title, key=lambda item: item.date or "", reverse=True))


def _document_markdown_html(document: DocumentRecord) -> str | None:
    """Render Markdown document content for frontend display.

    Parameters
    ----------
    document : DocumentRecord
        Document record.

    Returns
    -------
    str | None
        Rendered HTML for Markdown documents, otherwise ``None``.
    """

    if document.path.suffix.lower() != ".md":
        return None
    return render_markdown(document.path.read_text(encoding="utf-8", errors="replace"))


def _document_display_path(person: PersonConfig, document: DocumentRecord) -> str:
    """Build a non-sensitive document path for frontend display.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.
    document : DocumentRecord
        Document record.

    Returns
    -------
    str
        Relative source path for original documents or container internal path
        for derived members.
    """

    if document.origin == "source":
        try:
            return document.path.relative_to(person.source_documents).as_posix()
        except ValueError:
            return document.path.name
    return document.internal_path or document.path.name


def _document_href(person: PersonConfig, document: DocumentRecord) -> str | None:
    """Build the frontend link to the exported original document.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.
    document : DocumentRecord
        Document record.

    Returns
    -------
    str | None
        Relative URL from ``web/index.html`` to the copied USB document, or
        ``None`` for derived container members that are not exported as
        independent original files.
    """

    if document.origin != "source":
        return None
    try:
        relative = document.path.relative_to(person.source_documents)
    except ValueError:
        return None
    return f"../documents/{relative.as_posix()}"


def _document_search_payload(
    person: PersonConfig,
    document: DocumentRecord,
    metadata: CuratedMetadata,
    dicom_viewers: dict[Path, dict[str, str]],
) -> dict[str, Any]:
    """Build lexical search payload.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.
    document : DocumentRecord
        Document record.
    metadata : CuratedMetadata
        Curated metadata.
    dicom_viewers : dict[pathlib.Path, dict[str, str]]
        Viewer metadata keyed by DICOM support path.

    Returns
    -------
    dict[str, Any]
        JSON-serializable payload.
    """

    tags = _document_tags(document, metadata)
    text = " ".join((document.title, document.category, " ".join(tags))).strip()
    href = _document_href(person, document)
    viewer = dicom_viewers.get(document.path)
    payload = {
        "id": document.document_id,
        "type": "document",
        "section": "documents",
        "title": document.title,
        "subtitle": " ".join(
            item for item in (document.date, document.category, document.kind) if item
        ),
        "date": document.date,
        "text": text,
        "tags": list(tags),
        "fields": [
            {"label": "Categoria", "value": document.category},
            {"label": "Tipo", "value": document.kind},
            {"label": "Percorso", "value": _document_display_path(person, document)},
        ],
        "href": href,
        "origin": document.origin,
        "container_id": document.container_id,
    }
    if viewer is not None:
        payload.update(
            {
                "viewer_href": viewer["viewer_href"],
                "dicom_study_id": viewer["study_id"],
                "support_href": href,
                "primary_href": viewer["viewer_href"],
                "primary_action": "Apri studio DICOM",
            }
        )
    return payload


def _document_tags(
    document: DocumentRecord,
    metadata: CuratedMetadata,
) -> tuple[str, ...]:
    """Return curated tags for one document.

    Parameters
    ----------
    document : DocumentRecord
        Document record.
    metadata : CuratedMetadata
        Curated metadata.

    Returns
    -------
    tuple[str, ...]
        Curated or derived tags.
    """

    path = document.path.as_posix()
    for key, tags in metadata.document_tags.items():
        normalized = key.replace("\\", "/")
        if path.endswith(f"/{normalized}") or document.path.name == normalized:
            return tags
    return document.tags


def _timeline_events(
    documents: tuple[DocumentRecord, ...],
    metadata: CuratedMetadata,
    *,
    order: str = "desc",
) -> tuple[TimelineEvent, ...]:
    """Build generated and curated timeline events.

    Parameters
    ----------
    documents : tuple[DocumentRecord, ...]
        Document records.
    metadata : CuratedMetadata
        Curated metadata.
    order : str, optional
        Timeline sort order, either ``desc`` or ``asc``.

    Returns
    -------
    tuple[TimelineEvent, ...]
        Timeline events sorted by date and title.
    """

    document_events = tuple(
        TimelineEvent(
            id=f"document-{document.document_id}",
            title=document.title,
            start_date=document.date,
            source="document",
            links=(document.document_id,),
        )
        for document in documents
        if document.date is not None
    )
    therapy_events = tuple(
        _therapy_timeline_event(therapy, metadata.medications)
        for therapy in metadata.therapies
        if therapy.start_date is not None
    )
    ordered = sorted(
        (*metadata.timeline_events, *therapy_events, *document_events),
        key=lambda item: (item.start_date or "", item.title),
    )
    if order == "asc":
        return tuple(ordered)
    return tuple(reversed(ordered))


def _clinical_payload(
    person: PersonConfig,
    metadata: CuratedMetadata,
    dicom_studies: tuple[DicomStudy, ...],
) -> dict[str, Any]:
    """Build frontend payloads for curated clinical entities.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.
    metadata : CuratedMetadata
        Curated metadata.
    dicom_studies : tuple[DicomStudy, ...]
        Cataloged DICOM studies.

    Returns
    -------
    dict[str, Any]
        JSON-serializable clinical dashboard payload.
    """

    medications = {
        medication.id: _medication_payload(medication)
        for medication in metadata.medications
    }
    return {
        "problems": [_problem_payload(problem) for problem in metadata.problems],
        "medications": list(medications.values()),
        "therapies": [
            _therapy_payload(therapy, medications) for therapy in metadata.therapies
        ],
        "procedures": [
            _procedure_payload(procedure) for procedure in metadata.procedures
        ],
        "observations": [
            _observation_payload(observation) for observation in metadata.observations
        ],
        "dicom_studies": [
            _dicom_study_payload(person, study) for study in dicom_studies
        ],
    }


def _problem_payload(problem: ClinicalProblem) -> dict[str, Any]:
    """Build one clinical problem frontend payload.

    Parameters
    ----------
    problem : ClinicalProblem
        Clinical problem model.

    Returns
    -------
    dict[str, Any]
        JSON-serializable payload.
    """

    return {
        "id": problem.id,
        "type": "problem",
        "title": problem.title,
        "status": problem.status,
        "text": " ".join((problem.title, problem.status)).strip(),
        "fields": [{"label": "Stato", "value": problem.status}],
    }


def _medication_payload(medication: Medication) -> dict[str, Any]:
    """Build one medication frontend payload.

    Parameters
    ----------
    medication : Medication
        Medication model.

    Returns
    -------
    dict[str, Any]
        JSON-serializable payload.
    """

    fields: list[dict[str, Any]] = [
        {"label": "Principio attivo", "value": medication.active_ingredient},
        {"label": "Forma", "value": medication.form},
        {"label": "Dosaggio per unita'", "value": medication.strength_per_unit},
    ]
    return {
        "id": medication.id,
        "type": "medication",
        "title": medication.name,
        "active_ingredient": medication.active_ingredient,
        "form": medication.form,
        "strength_per_unit": medication.strength_per_unit,
        "text": " ".join(
            item
            for item in (
                medication.name,
                medication.active_ingredient,
                medication.form,
                medication.strength_per_unit,
            )
            if item
        ).strip(),
        "fields": [field for field in fields if field["value"]],
    }


def _therapy_payload(
    therapy: TherapyEpisode,
    medications: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Build one therapy frontend payload.

    Parameters
    ----------
    therapy : TherapyEpisode
        Therapy episode.
    medications : dict[str, dict[str, Any]]
        Medication payloads keyed by medication id.

    Returns
    -------
    dict[str, Any]
        JSON-serializable payload.
    """

    medication = medications.get(therapy.medication_id, {})
    medication_name = str(medication.get("title") or therapy.medication_id)
    active_ingredient = medication.get("active_ingredient")
    schedule = ", ".join(therapy.schedule)
    fields: list[dict[str, Any]] = [
        {"label": "Farmaco", "value": medication_name},
        {"label": "Principio attivo", "value": active_ingredient},
        {"label": "Dosaggio", "value": therapy.dosage},
        {"label": "Schedula", "value": schedule},
        {"label": "Istruzioni", "value": therapy.instructions},
        {"label": "Ruolo", "value": therapy.role},
        {"label": "Inizio", "value": therapy.start_date},
        {"label": "Fine", "value": therapy.end_date},
    ]
    return {
        "id": therapy.id,
        "type": "therapy",
        "title": f"Terapia: {medication_name}",
        "medication_id": therapy.medication_id,
        "medication_name": medication_name,
        "active_ingredient": active_ingredient,
        "start_date": therapy.start_date,
        "end_date": therapy.end_date,
        "date": therapy.start_date,
        "dosage": therapy.dosage,
        "role": therapy.role,
        "schedule": list(therapy.schedule),
        "instructions": therapy.instructions,
        "text": " ".join(
            item
            for item in (
                therapy.id,
                medication_name,
                str(active_ingredient or ""),
                therapy.medication_id,
                therapy.start_date,
                therapy.end_date,
                therapy.dosage,
                therapy.role,
                schedule,
                therapy.instructions,
            )
            if item
        ).strip(),
        "fields": _visible_fields(fields),
    }


def _procedure_payload(procedure: Procedure) -> dict[str, Any]:
    """Build one procedure frontend payload.

    Parameters
    ----------
    procedure : Procedure
        Procedure model.

    Returns
    -------
    dict[str, Any]
        JSON-serializable payload.
    """

    return {
        "id": procedure.id,
        "type": "procedure",
        "title": procedure.title,
        "date": procedure.date,
        "status": procedure.status,
        "text": " ".join(
            item for item in (procedure.title, procedure.date, procedure.status) if item
        ).strip(),
        "fields": [
            field
            for field in (
                {"label": "Data", "value": procedure.date},
                {"label": "Stato", "value": procedure.status},
            )
            if field["value"]
        ],
    }


def _observation_payload(observation: Observation) -> dict[str, Any]:
    """Build one observation frontend payload.

    Parameters
    ----------
    observation : Observation
        Observation model.

    Returns
    -------
    dict[str, Any]
        JSON-serializable payload.
    """

    return {
        "id": observation.id,
        "type": "observation",
        "title": observation.kind,
        "date": observation.date,
        "value": observation.value,
        "text": " ".join(
            item
            for item in (observation.kind, observation.value, observation.date)
            if item
        ).strip(),
        "fields": [
            field
            for field in (
                {"label": "Valore", "value": observation.value},
                {"label": "Data", "value": observation.date},
            )
            if field["value"]
        ],
    }


def _dicom_study_payload(person: PersonConfig, study: DicomStudy) -> dict[str, Any]:
    """Build one DICOM study frontend payload.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.
    study : DicomStudy
        Cataloged DICOM study.

    Returns
    -------
    dict[str, Any]
        JSON-serializable payload.
    """

    title = study.study_description or study.support_path.name
    href = _document_href_from_path(person, study.support_path)
    viewer_href = _dicom_html_viewer_href(study)
    fields: list[dict[str, Any]] = [
        {"label": "Supporto", "value": study.support_path.name},
        {"label": "Tipo", "value": study.support_kind},
        {"label": "Data", "value": study.study_date},
        {"label": "UID", "value": study.study_instance_uid},
        {"label": "Istanze", "value": str(study.instance_count)},
        {"label": "Viewer HTML", "value": "disponibile" if viewer_href else None},
    ]
    return {
        "id": study.study_id,
        "type": "dicom_study",
        "title": title,
        "date": study.study_date,
        "support_kind": study.support_kind,
        "support_path": study.support_path.name,
        "study_instance_uid": study.study_instance_uid,
        "study_description": study.study_description,
        "instance_count": study.instance_count,
        "href": href,
        "viewer_href": viewer_href,
        "text": " ".join(
            item
            for item in (
                title,
                study.support_path.name,
                study.support_kind,
                study.study_date,
                study.study_instance_uid,
                "viewer html" if viewer_href else None,
                str(study.instance_count),
            )
            if item
        ).strip(),
        "fields": _visible_fields(fields),
    }


def _dicom_html_viewer_href(study: DicomStudy) -> str | None:
    """Build the frontend link to an exported DICOM HTML viewer.

    Parameters
    ----------
    study : DicomStudy
        Cataloged DICOM study.

    Returns
    -------
    str | None
        Relative URL from ``web/index.html`` to the copied viewer entrypoint.
    """

    if study.html_viewer_path is None or study.extracted_path is None:
        return None
    try:
        root = _dicom_html_viewer_root(study.html_viewer_path, study.extracted_path)
        relative = study.html_viewer_path.relative_to(root.parent)
    except ValueError:
        return None
    return f"../dicom-viewers/{study.study_id}/{relative.as_posix()}"


def _dicom_html_viewer_root(viewer_path: Path, extracted_path: Path) -> Path:
    """Return the copied subtree root for one HTML DICOM viewer.

    Parameters
    ----------
    viewer_path : pathlib.Path
        Viewer entrypoint path.
    extracted_path : pathlib.Path
        Extracted support root.

    Returns
    -------
    pathlib.Path
        Directory copied to the USB viewer area.
    """

    relative_parts = viewer_path.relative_to(extracted_path).parts
    lowered = tuple(part.lower() for part in relative_parts)
    if "ihe_pdi" in lowered:
        index = lowered.index("ihe_pdi")
        return extracted_path.joinpath(*relative_parts[: index + 1])
    return viewer_path.parent


def _write_dicom_html_viewer_manifest(
    person: PersonConfig,
    dicom_studies: tuple[DicomStudy, ...],
) -> Path:
    """Write DICOM HTML viewer copy instructions for USB export.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.
    dicom_studies : tuple[DicomStudy, ...]
        Cataloged DICOM studies.

    Returns
    -------
    pathlib.Path
        Written manifest path.
    """

    entries = []
    for study in dicom_studies:
        if study.html_viewer_path is None or study.extracted_path is None:
            continue
        try:
            root = _dicom_html_viewer_root(study.html_viewer_path, study.extracted_path)
            relative_root = root.relative_to(root.parent)
            entrypoint = study.html_viewer_path.relative_to(root.parent)
        except ValueError:
            continue
        entries.append(
            {
                "study_id": study.study_id,
                "source_root": str(root),
                "relative_root": relative_root.as_posix(),
                "entrypoint": entrypoint.as_posix(),
            }
        )
    target = person.local_build / "manifests" / "dicom_html_viewers.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {"schema_version": 1, "viewers": entries},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return target


def _document_href_from_path(person: PersonConfig, path: Path) -> str | None:
    """Build an exported document href from a source path.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.
    path : pathlib.Path
        Candidate source path.

    Returns
    -------
    str | None
        Relative USB href or ``None`` when the path is not a source document.
    """

    try:
        relative = path.relative_to(person.source_documents)
    except ValueError:
        return None
    return f"../documents/{relative.as_posix()}"


def _visible_fields(fields: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return fields with a present display value.

    Parameters
    ----------
    fields : list[dict[str, Any]]
        Field payloads.

    Returns
    -------
    list[dict[str, Any]]
        Field payloads whose ``value`` is not empty.
    """

    return [field for field in fields if field.get("value")]


def _metadata_search_payloads(
    clinical_payload: dict[str, Any],
) -> tuple[dict[str, Any], ...]:
    """Build lexical search payloads for curated clinical entities.

    Parameters
    ----------
    clinical_payload : dict[str, Any]
        Frontend clinical payload.

    Returns
    -------
    tuple[dict[str, Any], ...]
        JSON-serializable search entries.
    """

    entries: list[dict[str, Any]] = []
    section_by_type = {
        "problems": "problems",
        "medications": "medications",
        "therapies": "therapies",
        "procedures": "procedures",
        "observations": "observations",
        "dicom_studies": "dicom",
    }
    for key, section in section_by_type.items():
        entries.extend(
            _entity_search_payload(item, section=section)
            for item in clinical_payload.get(key, [])
        )
    return tuple(entries)


def _entity_search_payload(
    item: dict[str, Any],
    *,
    section: str,
) -> dict[str, Any]:
    """Build a curated entity search payload.

    Parameters
    ----------
    item : dict[str, Any]
        Frontend clinical entity payload.
    section : str
        Result section id.

    Returns
    -------
    dict[str, Any]
        JSON-serializable payload.
    """

    return {
        "id": item["id"],
        "type": item["type"],
        "section": section,
        "title": item["title"],
        "subtitle": _entity_subtitle(item),
        "date": item.get("date") or item.get("start_date"),
        "text": item.get("text", ""),
        "tags": [],
        "fields": item.get("fields", []),
    }


def _entity_subtitle(item: dict[str, Any]) -> str:
    """Return a compact entity subtitle.

    Parameters
    ----------
    item : dict[str, Any]
        Frontend clinical entity payload.

    Returns
    -------
    str
        Human-readable subtitle.
    """

    values = []
    for field in item.get("fields", ())[:3]:
        value = field.get("value")
        if value:
            values.append(str(value))
    return " | ".join(values)


def _therapy_timeline_event(
    therapy: TherapyEpisode,
    medications: tuple[Medication, ...],
) -> TimelineEvent:
    """Build a therapy timeline interval.

    Parameters
    ----------
    therapy : TherapyEpisode
        Therapy episode.
    medications : tuple[Medication, ...]
        Curated medications used to resolve display names.

    Returns
    -------
    TimelineEvent
        Timeline event for the therapy interval.
    """

    medication_names = {medication.id: medication.name for medication in medications}
    medication_name = medication_names.get(therapy.medication_id, therapy.medication_id)
    return TimelineEvent(
        id=f"therapy-{therapy.id}",
        title=f"Terapia: {medication_name}",
        start_date=therapy.start_date,
        end_date=therapy.end_date,
        source="therapy",
        links=(therapy.id, therapy.medication_id),
    )


def _write_json(path: Path, payload: Any) -> Path:
    """Write a JSON payload.

    Parameters
    ----------
    path : pathlib.Path
        Target path.
    payload : Any
        JSON-serializable payload.

    Returns
    -------
    pathlib.Path
        Written path.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return path
