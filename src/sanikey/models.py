"""Domain models shared across the SaniKey build pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class Provenance:
    """Describe where a generated fact came from.

    Parameters
    ----------
    source : str
        Source subsystem or file.
    reference : str
        Stable source reference.
    confidence : float | None, optional
        Optional confidence score for derived information.
    """

    source: str
    reference: str
    confidence: float | None = None


@dataclass(frozen=True)
class DocumentRecord:
    """Represent one original document.

    Parameters
    ----------
    document_id : str
        SHA256-based document identity.
    patient_id : str
        Owning patient id.
    path : pathlib.Path
        Original file path.
    title : str
        Human-readable title.
    category : str
        Category derived from source directory structure.
    kind : str
        Document kind such as ``pdf``, ``image``, ``archive``, or ``dicom_iso``.
    sha256 : str
        SHA256 digest of the original file.
    date : str | None, optional
        Optional ISO date derived from filename or metadata.
    series : str | None, optional
        Optional document series name.
    tags : tuple[str, ...]
        Curated or derived tags.
    origin : str
        Document origin, either ``source`` or ``container``.
    container_id : str | None, optional
        Parent container document id for extracted members.
    internal_path : str | None, optional
        Member path inside the parent container.
    """

    document_id: str
    patient_id: str
    path: Path
    title: str
    category: str
    kind: str
    sha256: str
    date: str | None = None
    series: str | None = None
    tags: tuple[str, ...] = ()
    origin: str = "source"
    container_id: str | None = None
    internal_path: str | None = None


@dataclass(frozen=True)
class ClinicalProblem:
    """Represent a curated clinical problem.

    Parameters
    ----------
    id : str
        Stable problem identifier.
    title : str
        Problem title.
    status : str
        Problem status.
    provenance : tuple[Provenance, ...]
        Evidence references.
    """

    id: str
    title: str
    status: str
    provenance: tuple[Provenance, ...] = ()


@dataclass(frozen=True)
class Medication:
    """Represent a medication identity.

    Parameters
    ----------
    id : str
        Stable medication identifier.
    name : str
        Medication name.
    active_ingredient : str | None, optional
        Active ingredient when known.
    form : str | None, optional
        Pharmaceutical form, for example ``compresse``.
    strength_per_unit : str | None, optional
        Active ingredient amount per unit, for example ``100 mg``.
    """

    id: str
    name: str
    active_ingredient: str | None = None
    form: str | None = None
    strength_per_unit: str | None = None


@dataclass(frozen=True)
class MedicationLeaflet:
    """Represent one confirmed AIFA medication-document reference.

    Parameters
    ----------
    medication_id : str
        Curated medication identifier.
    codice_sis : str
        AIFA organisation identifier.
    aic6 : str
        AIFA medicine identifier.
    downloaded_at : str | None, optional
        ISO date of the local document download.
    source_fingerprint : str | None, optional
        Stable fingerprint of the curated medication fields used for the lookup.
    """

    medication_id: str
    codice_sis: str
    aic6: str
    downloaded_at: str | None = None
    source_fingerprint: str | None = None


@dataclass(frozen=True)
class TherapyEpisode:
    """Represent one medication therapy interval.

    Parameters
    ----------
    id : str
        Stable therapy identifier.
    medication_id : str
        Linked medication identifier.
    start_date : str | None, optional
        ISO start date.
    end_date : str | None, optional
        ISO end date.
    dosage : str | None, optional
        Human-readable dosage.
    role : str | None, optional
        Therapeutic role or clinical indication, for example ``antipertensivo``.
    schedule : tuple[str, ...]
        Human-readable intake times or time bands.
    instructions : str | None, optional
        Free-text intake instructions.
    """

    id: str
    medication_id: str
    start_date: str | None = None
    end_date: str | None = None
    dosage: str | None = None
    role: str | None = None
    schedule: tuple[str, ...] = ()
    instructions: str | None = None


@dataclass(frozen=True)
class Procedure:
    """Represent a curated clinical procedure.

    Parameters
    ----------
    id : str
        Stable procedure identifier.
    title : str
        Procedure title.
    date : str | None, optional
        ISO date.
    status : str
        Procedure status.
    """

    id: str
    title: str
    date: str | None = None
    status: str = "unknown"


@dataclass(frozen=True)
class Observation:
    """Represent one observation value.

    Parameters
    ----------
    id : str
        Stable observation identifier.
    kind : str
        Observation kind.
    value : str
        Human-readable value.
    date : str | None, optional
        ISO observation date.
    """

    id: str
    kind: str
    value: str
    date: str | None = None


@dataclass(frozen=True)
class ObservationSeries:
    """Represent one longitudinal observation series.

    Parameters
    ----------
    id : str
        Stable series identifier.
    name : str
        Human-readable series name.
    value_type : str
        Value type, for example ``numeric`` or ``blood_pressure``.
    unit : str | None, optional
        Measurement unit.
    description : str | None, optional
        Free-text description.
    warn_duplicate_same_day : bool
        Whether same-day duplicates should be reported during import.
    """

    id: str
    name: str
    value_type: str
    unit: str | None = None
    description: str | None = None
    warn_duplicate_same_day: bool = True


@dataclass(frozen=True)
class ObservationPoint:
    """Represent one normalized observation point.

    Parameters
    ----------
    id : str
        Stable point identifier.
    series_id : str
        Referenced observation series id.
    observation_date : str
        ISO observation date.
    source_type : str
        Source kind, for example ``spreadsheet``.
    source_reference : str
        Human-readable source reference.
    numeric_value : float | None, optional
        Numeric value for numeric series.
    text_value : str | None, optional
        Textual value for text or categorical series.
    systolic : float | None, optional
        Systolic pressure value.
    diastolic : float | None, optional
        Diastolic pressure value.
    pulse : float | None, optional
        Pulse value.
    note : str | None, optional
        Optional free-text note.
    """

    id: str
    series_id: str
    observation_date: str
    source_type: str
    source_reference: str
    numeric_value: float | None = None
    text_value: str | None = None
    systolic: float | None = None
    diastolic: float | None = None
    pulse: float | None = None
    note: str | None = None


@dataclass(frozen=True)
class TimelineEvent:
    """Represent a timeline event or interval.

    Parameters
    ----------
    id : str
        Stable timeline identifier.
    title : str
        Event title.
    start_date : str | None, optional
        ISO start date.
    end_date : str | None, optional
        ISO end date.
    source : str
        Event source.
    links : tuple[str, ...]
        Related document or entity ids.
    """

    id: str
    title: str
    start_date: str | None = None
    end_date: str | None = None
    source: str = "manual"
    links: tuple[str, ...] = ()


@dataclass(frozen=True)
class CuratedMetadata:
    """Aggregate curated metadata for one patient.

    Parameters
    ----------
    problems : tuple[ClinicalProblem, ...]
        Curated clinical problems.
    medications : tuple[Medication, ...]
        Curated medication identities.
    medication_leaflets : tuple[MedicationLeaflet, ...]
        Confirmed AIFA references for local medication documents.
    therapies : tuple[TherapyEpisode, ...]
        Curated therapy episodes.
    procedures : tuple[Procedure, ...]
        Curated procedures.
    observations : tuple[Observation, ...]
        Curated observations.
    observation_series : tuple[ObservationSeries, ...]
        Normalized longitudinal observation series.
    observation_points : tuple[ObservationPoint, ...]
        Normalized longitudinal observation points.
    timeline_events : tuple[TimelineEvent, ...]
        Curated manual timeline events.
    document_tags : dict[str, tuple[str, ...]]
        Tags keyed by document filename or digest.
    clinical_summary : str | None
        Curated summary text.
    """

    problems: tuple[ClinicalProblem, ...] = ()
    medications: tuple[Medication, ...] = ()
    medication_leaflets: tuple[MedicationLeaflet, ...] = ()
    therapies: tuple[TherapyEpisode, ...] = ()
    procedures: tuple[Procedure, ...] = ()
    observations: tuple[Observation, ...] = ()
    observation_series: tuple[ObservationSeries, ...] = ()
    observation_points: tuple[ObservationPoint, ...] = ()
    timeline_events: tuple[TimelineEvent, ...] = ()
    document_tags: dict[str, tuple[str, ...]] = field(default_factory=dict)
    clinical_summary: str | None = None
