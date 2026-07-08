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
    from .documents import ExtractedText
    from .models import CuratedMetadata, DocumentRecord, Medication, TherapyEpisode


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

    Returns
    -------
    ExportResult
        Generated export paths.
    """

    data_dir = person.local_build / "web" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    ordered_documents = _ordered_documents(documents)
    documents_payload = [
        _document_payload(person, document, metadata) for document in ordered_documents
    ]
    search_payload = [
        *(_document_search_payload(document, metadata) for document in documents),
        *_metadata_search_payloads(metadata),
    ]
    timeline_events = _timeline_events(
        documents,
        metadata,
        order=person.ui.timeline_order,
    )
    timeline_payload = [asdict(event) for event in timeline_events]
    summary_payload = {
        "patient_id": person.id,
        "display_name": person.display_name,
        "ui": _ui_payload(person),
        "document_count": len(documents),
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
                person, document, metadata, text_by_document
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


def _content_search_document_payload(
    person: PersonConfig,
    document: DocumentRecord,
    metadata: CuratedMetadata,
    text: dict[str, str],
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

    Returns
    -------
    dict[str, Any]
        JSON-serializable document search payload.
    """

    return {
        **_document_payload(person, document, metadata),
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

    Returns
    -------
    dict[str, Any]
        JSON-serializable payload.
    """

    return {
        "id": document.document_id,
        "title": document.title,
        "date": document.date,
        "category": document.category,
        "kind": document.kind,
        "path": _document_display_path(person, document),
        "href": _document_href(person, document),
        "origin": document.origin,
        "container_id": document.container_id,
        "internal_path": document.internal_path,
        "tags": list(_document_tags(document, metadata)),
        "markdown_html": _document_markdown_html(document),
    }


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
    document: DocumentRecord,
    metadata: CuratedMetadata,
) -> dict[str, Any]:
    """Build lexical search payload.

    Parameters
    ----------
    document : DocumentRecord
        Document record.
    metadata : CuratedMetadata
        Curated metadata.

    Returns
    -------
    dict[str, Any]
        JSON-serializable payload.
    """

    tags = _document_tags(document, metadata)
    text = " ".join((document.title, document.category, " ".join(tags))).strip()
    return {
        "id": document.document_id,
        "type": "document",
        "title": document.title,
        "text": text,
        "tags": list(tags),
        "origin": document.origin,
        "container_id": document.container_id,
    }


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


def _metadata_search_payloads(metadata: CuratedMetadata) -> tuple[dict[str, Any], ...]:
    """Build lexical search payloads for curated clinical entities.

    Parameters
    ----------
    metadata : CuratedMetadata
        Curated metadata.

    Returns
    -------
    tuple[dict[str, Any], ...]
        JSON-serializable search entries.
    """

    entries: list[dict[str, Any]] = []
    entries.extend(
        _entity_search_payload(
            item_id=problem.id,
            item_type="problem",
            title=problem.title,
            parts=(problem.status,),
        )
        for problem in metadata.problems
    )
    entries.extend(
        _entity_search_payload(
            item_id=medication.id,
            item_type="medication",
            title=medication.name,
            parts=(
                medication.active_ingredient,
                medication.form,
                medication.strength_per_unit,
            ),
        )
        for medication in metadata.medications
    )
    entries.extend(
        _entity_search_payload(
            item_id=therapy.id,
            item_type="therapy",
            title=therapy.id,
            parts=(
                therapy.medication_id,
                therapy.start_date,
                therapy.end_date,
                therapy.dosage,
                therapy.role,
                " ".join(therapy.schedule) or None,
                therapy.instructions,
            ),
        )
        for therapy in metadata.therapies
    )
    entries.extend(
        _entity_search_payload(
            item_id=procedure.id,
            item_type="procedure",
            title=procedure.title,
            parts=(procedure.date, procedure.status),
        )
        for procedure in metadata.procedures
    )
    entries.extend(
        _entity_search_payload(
            item_id=observation.id,
            item_type="observation",
            title=observation.kind,
            parts=(observation.value, observation.date),
        )
        for observation in metadata.observations
    )
    return tuple(entries)


def _entity_search_payload(
    *,
    item_id: str,
    item_type: str,
    title: str,
    parts: tuple[str | None, ...],
) -> dict[str, Any]:
    """Build a curated entity search payload.

    Parameters
    ----------
    item_id : str
        Entity id.
    item_type : str
        Entity type.
    title : str
        Search result title.
    parts : tuple[str | None, ...]
        Optional text fragments.

    Returns
    -------
    dict[str, Any]
        JSON-serializable payload.
    """

    text = " ".join(item for item in (title, *parts) if item).strip()
    return {
        "id": item_id,
        "type": item_type,
        "title": title,
        "text": text,
        "tags": [],
    }


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
