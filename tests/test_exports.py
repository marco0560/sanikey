"""Static JSON export tests."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from sanikey.config import PersonConfig, SearchConfig, SearchDictionary, UiConfig
from sanikey.dicom import DicomStudy
from sanikey.documents import ExtractedText, scan_documents
from sanikey.exports import generate_exports
from sanikey.metadata import load_curated_metadata
from sanikey.proposals import generate_manual_proposals

if TYPE_CHECKING:
    from pathlib import Path


def _person(tmp_path: Path) -> PersonConfig:
    """Build a synthetic patient config.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary test directory.

    Returns
    -------
    PersonConfig
        Patient configuration.
    """

    return PersonConfig(
        id="patient-a",
        display_name="Patient A",
        source_documents=tmp_path / "documents",
        metadata_directory=tmp_path / "metadata",
        local_build=tmp_path / "generated",
        usb_uuid="1A2B-3C4D",
    )


def test_generate_exports_writes_frontend_data(tmp_path: Path) -> None:
    """Verify static JSON exports include document, search, timeline, and summary data.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    person = _person(tmp_path)
    person.source_documents.mkdir(parents=True)
    laboratory = person.source_documents / "laboratory"
    laboratory.mkdir()
    (laboratory / "20260102 Report.txt").write_text(
        "synthetic",
        encoding="utf-8",
    )
    (laboratory / "20260103 Summary.md").write_text(
        "# Referto\n\n- Voce\n\n<script>alert(1)</script>",
        encoding="utf-8",
    )
    person.metadata_directory.mkdir()
    (person.metadata_directory / "clinical_summary.toml").write_text(
        """
summary = \"\"\"
# Sintesi clinica

- Ipertensione.

<script>alert(1)</script>
\"\"\"
""",
        encoding="utf-8",
    )
    (person.metadata_directory / "document_tags.toml").write_text(
        """
[tags]
"laboratory/20260102 Report.txt" = ["report"]
""",
        encoding="utf-8",
    )
    (person.metadata_directory / "timeline_events.toml").write_text(
        """
[[event]]
id = "therapy-interval"
title = "Therapy interval"
start_date = "2026-01-01"
end_date = "2026-01-31"
source = "manual"
links = ["therapy-a"]
""",
        encoding="utf-8",
    )

    result = generate_exports(
        person,
        scan_documents(person),
        load_curated_metadata(person.metadata_directory),
        (
            ExtractedText(
                document_id=scan_documents(person)[0].document_id,
                text="Creatinina nel testo OCR",
            ),
        ),
    )

    documents = json.loads(result.documents.read_text(encoding="utf-8"))
    search = json.loads(result.search.read_text(encoding="utf-8"))
    timeline = json.loads(result.timeline.read_text(encoding="utf-8"))
    summary = json.loads(result.summary.read_text(encoding="utf-8"))
    data_script = result.data_script.read_text(encoding="utf-8")
    content_search_script = result.content_search_script.read_text(encoding="utf-8")
    document_by_title = {item["title"]: item for item in documents}
    assert [item["title"] for item in documents] == ["Summary", "Report"]
    assert document_by_title["Report"]["tags"] == ["report"]
    assert document_by_title["Report"]["path"] == "laboratory/20260102 Report.txt"
    assert document_by_title["Report"]["href"] == (
        "../documents/laboratory/20260102 Report.txt"
    )
    assert not document_by_title["Report"]["href"].startswith("/")
    assert document_by_title["Summary"]["markdown_html"].startswith("<h1>Referto</h1>")
    assert "<script>" not in document_by_title["Summary"]["markdown_html"]
    assert "&lt;script&gt;" in document_by_title["Summary"]["markdown_html"]
    assert search[0]["text"] == "Report laboratory report"
    assert search[0]["href"] == "../documents/laboratory/20260102 Report.txt"
    assert [item["start_date"] for item in timeline] == [
        "2026-01-03",
        "2026-01-02",
        "2026-01-01",
    ]
    assert timeline[2]["id"] == "therapy-interval"
    assert timeline[2]["end_date"] == "2026-01-31"
    assert timeline[2]["links"] == ["therapy-a"]
    assert summary["document_count"] == 2
    assert summary["ui"]["default_tab"] == "documents"
    assert summary["ui"]["timeline_order"] == "desc"
    assert summary["clinical_summary_html"].startswith("<h1>Sintesi clinica</h1>")
    assert "<script>" not in summary["clinical_summary_html"]
    assert "&lt;script&gt;" in summary["clinical_summary_html"]
    assert data_script.startswith("window.SANIKEY_DATA = ")
    assert '"documents":' in data_script
    assert '"summary":' in data_script
    assert "/home/" not in data_script
    assert content_search_script.startswith("window.SANIKEY_CONTENT_SEARCH = ")
    assert "Creatinina nel testo OCR" in content_search_script
    assert "../documents/" in content_search_script
    assert "/home/" not in content_search_script


def test_generate_exports_writes_advanced_search_dictionary_and_warning(
    tmp_path: Path,
) -> None:
    """Verify advanced search export includes dictionary data and size warnings.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    base = _person(tmp_path)
    person = PersonConfig(
        id=base.id,
        display_name=base.display_name,
        source_documents=base.source_documents,
        metadata_directory=base.metadata_directory,
        local_build=base.local_build,
        usb_uuid=base.usb_uuid,
        search=SearchConfig(
            dictionary_data=SearchDictionary(
                terms={"rx": ("radiografia",)},
                months={"marzo": ("03", "3")},
            ),
            advanced_index_warning_mb=1,
        ),
    )
    person.source_documents.mkdir(parents=True)
    (person.source_documents / "20260102 Report.txt").write_text(
        "synthetic",
        encoding="utf-8",
    )
    document = scan_documents(person)[0]

    result = generate_exports(
        person,
        (document,),
        load_curated_metadata(person.metadata_directory),
        (
            ExtractedText(
                document_id=document.document_id,
                text="Creatinina e radiografia torace",
            ),
        ),
    )

    payload_text = result.content_search_script.read_text(encoding="utf-8")
    assert '"rx": ["radiografia"]' in payload_text
    assert '"marzo": ["03", "3"]' in payload_text
    assert result.warning_messages == ()


def test_generate_exports_writes_dicom_html_viewer_payload(
    tmp_path: Path,
) -> None:
    """Verify DICOM HTML viewers are linked and recorded for USB export.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    person = _person(tmp_path)
    person.source_documents.mkdir(parents=True)
    support = person.source_documents / "20260102 TAC.zip"
    support.write_bytes(b"zip")
    extracted = person.local_build / "staging" / "containers" / "container-a"
    viewer = extracted / "IHE_PDI" / "PAGES" / "STUDIES" / "STUDY1.HTM"
    viewer.parent.mkdir(parents=True)
    viewer.write_text("<html>viewer</html>", encoding="utf-8")
    study = DicomStudy(
        study_id="study-a",
        patient_id=person.id,
        support_path=support,
        support_kind="dicom_zip",
        extracted_path=extracted,
        html_viewer_path=viewer,
    )

    result = generate_exports(
        person,
        scan_documents(person),
        load_curated_metadata(person.metadata_directory),
        dicom_studies=(study,),
    )

    data_script = result.data_script.read_text(encoding="utf-8")
    search = json.loads(result.search.read_text(encoding="utf-8"))
    manifest = json.loads(
        (person.local_build / "manifests" / "dicom_html_viewers.json").read_text(
            encoding="utf-8"
        )
    )
    dicom_search = next(item for item in search if item["type"] == "dicom_study")
    assert (
        '"viewer_href": "../dicom-viewers/study-a/IHE_PDI/PAGES/STUDIES/STUDY1.HTM"'
        in data_script
    )
    assert (
        dicom_search["viewer_href"]
        == "../dicom-viewers/study-a/IHE_PDI/PAGES/STUDIES/STUDY1.HTM"
    )
    assert manifest["viewers"] == [
        {
            "entrypoint": "IHE_PDI/PAGES/STUDIES/STUDY1.HTM",
            "relative_root": "IHE_PDI",
            "source_root": str(extracted / "IHE_PDI"),
            "study_id": "study-a",
        }
    ]


def test_generate_exports_excludes_unapproved_proposals(tmp_path: Path) -> None:
    """Verify standard exports ignore non-authoritative proposals.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    person = _person(tmp_path)
    person.source_documents.mkdir(parents=True)
    (person.source_documents / "20260102 Report.txt").write_text(
        "synthetic",
        encoding="utf-8",
    )
    generate_manual_proposals(person.metadata_directory)

    result = generate_exports(
        person,
        scan_documents(person),
        load_curated_metadata(person.metadata_directory),
    )

    exported_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (result.documents, result.search, result.timeline, result.summary)
    )
    assert "Manual review placeholder" not in exported_text
    assert "manual-test-provider" not in exported_text


def test_generate_exports_indexes_curated_metadata_and_therapy_intervals(
    tmp_path: Path,
) -> None:
    """Verify curated entities are searchable and therapies become intervals.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    person = _person(tmp_path)
    person.source_documents.mkdir(parents=True)
    (person.source_documents / "20260102 Report.txt").write_text(
        "synthetic",
        encoding="utf-8",
    )
    person.metadata_directory.mkdir()
    (person.metadata_directory / "problems.toml").write_text(
        """
[[problem]]
id = "problem-a"
title = "Hypertension"
status = "active"
""",
        encoding="utf-8",
    )
    (person.metadata_directory / "medications.toml").write_text(
        """
[[medication]]
id = "drug-a"
name = "Drug A"
active_ingredient = "Ingredient A"
form = "compresse"
strength_per_unit = "100 mg"
""",
        encoding="utf-8",
    )
    (person.metadata_directory / "therapies.toml").write_text(
        """
[[therapy]]
id = "therapy-a"
medication_id = "drug-a"
start_date = "2026-01-03"
end_date = "2026-01-31"
dosage = "1 tablet"
schedule = ["risveglio", "cena"]
instructions = "dopo il pasto"
""",
        encoding="utf-8",
    )
    (person.metadata_directory / "procedures.toml").write_text(
        """
[[procedure]]
id = "procedure-a"
title = "Procedure A"
date = "2026-01-04"
status = "completed"
""",
        encoding="utf-8",
    )
    (person.metadata_directory / "observations.toml").write_text(
        """
[[observation]]
id = "observation-a"
kind = "weight"
value = "70 kg"
date = "2026-01-05"
""",
        encoding="utf-8",
    )

    result = generate_exports(
        person,
        scan_documents(person),
        load_curated_metadata(person.metadata_directory),
    )

    search = json.loads(result.search.read_text(encoding="utf-8"))
    data_script = result.data_script.read_text(encoding="utf-8")
    data = json.loads(
        data_script.removeprefix("window.SANIKEY_DATA = ").removesuffix(";\n")
    )
    timeline = json.loads(result.timeline.read_text(encoding="utf-8"))
    search_by_type = {item["type"]: item for item in search}
    therapy_event = next(item for item in timeline if item["source"] == "therapy")
    therapy = data["clinical"]["therapies"][0]

    assert set(search_by_type) == {
        "document",
        "problem",
        "medication",
        "therapy",
        "procedure",
        "observation",
    }
    assert search_by_type["problem"]["text"] == "Hypertension active"
    assert search_by_type["medication"]["text"] == (
        "Drug A Ingredient A compresse 100 mg"
    )
    assert search_by_type["therapy"]["text"] == (
        "therapy-a Drug A Ingredient A drug-a 2026-01-03 2026-01-31 "
        "1 tablet risveglio, cena dopo il pasto"
    )
    assert search_by_type["therapy"]["title"] == "Terapia: Drug A"
    assert search_by_type["therapy"]["section"] == "therapies"
    assert therapy["medication_name"] == "Drug A"
    assert therapy["active_ingredient"] == "Ingredient A"
    assert therapy["schedule"] == ["risveglio", "cena"]
    assert {"label": "Schedula", "value": "risveglio, cena"} in therapy["fields"]
    assert therapy_event["id"] == "therapy-therapy-a"
    assert therapy_event["title"] == "Terapia: Drug A"
    assert therapy_event["start_date"] == "2026-01-03"
    assert therapy_event["end_date"] == "2026-01-31"


def test_generate_exports_includes_synthetic_dicom_study_cards(
    tmp_path: Path,
) -> None:
    """Verify DICOM studies become searchable frontend entities.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    person = _person(tmp_path)
    person.source_documents.mkdir(parents=True)
    support = person.source_documents / "20260102 TAC.zip"
    support.write_text("synthetic", encoding="utf-8")
    document = scan_documents(person)[0]
    study = DicomStudy(
        study_id="study-a",
        patient_id=person.id,
        support_path=document.path,
        support_kind="dicom_zip",
        study_instance_uid="1.2.3",
        study_date="2026-01-02",
        study_description="TAC torace",
        instance_count=42,
    )

    result = generate_exports(
        person,
        (document,),
        load_curated_metadata(person.metadata_directory),
        dicom_studies=(study,),
    )

    search = json.loads(result.search.read_text(encoding="utf-8"))
    data = json.loads(
        result.data_script.read_text(encoding="utf-8")
        .removeprefix("window.SANIKEY_DATA = ")
        .removesuffix(";\n")
    )
    dicom_search = next(item for item in search if item["type"] == "dicom_study")
    dicom_card = data["clinical"]["dicom_studies"][0]

    assert dicom_search["section"] == "dicom"
    assert dicom_search["title"] == "TAC torace"
    assert "1.2.3" in dicom_search["text"]
    assert dicom_card["instance_count"] == 42
    assert dicom_card["href"] == "../documents/20260102 TAC.zip"
    assert {"label": "Istanze", "value": "42"} in dicom_card["fields"]


def test_generate_exports_hides_technical_dicom_documents(tmp_path: Path) -> None:
    """Verify DICOM instance files are not listed as consultation documents.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    person = _person(tmp_path)
    person.source_documents.mkdir(parents=True)
    (person.source_documents / "20260102 Report.txt").write_text(
        "synthetic",
        encoding="utf-8",
    )
    (person.source_documents / "image.dcm").write_bytes(b"DICM")

    result = generate_exports(
        person,
        scan_documents(person),
        load_curated_metadata(person.metadata_directory),
    )

    documents = json.loads(result.documents.read_text(encoding="utf-8"))
    search = json.loads(result.search.read_text(encoding="utf-8"))
    data = json.loads(
        result.data_script.read_text(encoding="utf-8")
        .removeprefix("window.SANIKEY_DATA = ")
        .removesuffix(";\n")
    )

    assert [item["title"] for item in documents] == ["Report"]
    assert all(item["kind"] != "dicom_file" for item in documents)
    assert all(item.get("kind") != "dicom_file" for item in data["documents"])
    assert all(item["title"] != "image" for item in search)


def test_generate_exports_honors_ascending_timeline_order(tmp_path: Path) -> None:
    """Verify UI config can request oldest-first timeline export.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    base = _person(tmp_path)
    person = PersonConfig(
        id=base.id,
        display_name=base.display_name,
        source_documents=base.source_documents,
        metadata_directory=base.metadata_directory,
        local_build=base.local_build,
        usb_uuid=base.usb_uuid,
        ui=UiConfig(timeline_order="asc"),
    )
    person.source_documents.mkdir(parents=True)
    (person.source_documents / "20260102 Report.txt").write_text(
        "synthetic-a",
        encoding="utf-8",
    )
    (person.source_documents / "20260103 Followup.txt").write_text(
        "synthetic-b",
        encoding="utf-8",
    )

    result = generate_exports(
        person,
        scan_documents(person),
        load_curated_metadata(person.metadata_directory),
    )
    timeline = json.loads(result.timeline.read_text(encoding="utf-8"))

    assert [item["start_date"] for item in timeline] == [
        "2026-01-02",
        "2026-01-03",
    ]
