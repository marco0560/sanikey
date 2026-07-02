"""Static JSON exports for frontend and offline search."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

from .models import TimelineEvent

if TYPE_CHECKING:
    from pathlib import Path

    from .config import PersonConfig
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
    """

    data_dir: Path
    documents: Path
    search: Path
    timeline: Path
    summary: Path


def generate_exports(
    person: PersonConfig,
    documents: tuple[DocumentRecord, ...],
    metadata: CuratedMetadata,
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

    Returns
    -------
    ExportResult
        Generated export paths.
    """

    data_dir = person.local_build / "web" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    documents_path = _write_json(
        data_dir / "documents.json",
        [_document_payload(document, metadata) for document in documents],
    )
    search_path = _write_json(
        data_dir / "search.json",
        [
            *(_document_search_payload(document, metadata) for document in documents),
            *_metadata_search_payloads(metadata),
        ],
    )
    timeline_events = _timeline_events(documents, metadata)
    timeline_path = _write_json(
        data_dir / "timeline.json",
        [asdict(event) for event in timeline_events],
    )
    summary_path = _write_json(
        data_dir / "summary.json",
        {
            "patient_id": person.id,
            "display_name": person.display_name,
            "document_count": len(documents),
            "problem_count": len(metadata.problems),
            "therapy_count": len(metadata.therapies),
            "procedure_count": len(metadata.procedures),
            "observation_count": len(metadata.observations),
            "clinical_summary": metadata.clinical_summary,
        },
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
    )


def _document_payload(
    document: DocumentRecord,
    metadata: CuratedMetadata,
) -> dict[str, Any]:
    """Build frontend document payload.

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

    return {
        "id": document.document_id,
        "title": document.title,
        "date": document.date,
        "category": document.category,
        "kind": document.kind,
        "path": str(document.path),
        "tags": list(metadata.document_tags.get(document.path.name, document.tags)),
    }


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

    tags = metadata.document_tags.get(document.path.name, document.tags)
    text = " ".join((document.title, document.category, " ".join(tags))).strip()
    return {
        "id": document.document_id,
        "type": "document",
        "title": document.title,
        "text": text,
        "tags": list(tags),
    }


def _timeline_events(
    documents: tuple[DocumentRecord, ...],
    metadata: CuratedMetadata,
) -> tuple[TimelineEvent, ...]:
    """Build generated and curated timeline events.

    Parameters
    ----------
    documents : tuple[DocumentRecord, ...]
        Document records.
    metadata : CuratedMetadata
        Curated metadata.

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
    return tuple(
        sorted(
            (*metadata.timeline_events, *therapy_events, *document_events),
            key=lambda item: (item.start_date or "", item.title),
        )
    )


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
            parts=(medication.active_ingredient,),
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
