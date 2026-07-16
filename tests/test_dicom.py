"""DICOM catalog tests."""

from __future__ import annotations

import tarfile
import warnings
import zipfile
from datetime import datetime
from typing import TYPE_CHECKING

import sanikey.dicom as dicom_module
from sanikey.config import PersonConfig
from sanikey.dicom import catalog_dicom_studies
from sanikey.documents import scan_documents

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


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


def _write_dicom_file(
    path: Path,
    *,
    study_uid: str,
    study_date: str = "20260102",
    study_description: str = "Synthetic Study",
) -> None:
    """Write a minimal synthetic DICOM file.

    Parameters
    ----------
    path : pathlib.Path
        Output path.
    study_uid : str
        Study Instance UID.
    study_date : str, optional
        DICOM study date.
    study_description : str, optional
        DICOM study description.

    Returns
    -------
    None
    """

    from pydicom.dataset import FileDataset, FileMetaDataset
    from pydicom.uid import ExplicitVRLittleEndian, generate_uid

    file_meta = FileMetaDataset()
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    file_meta.MediaStorageSOPClassUID = generate_uid()
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.ImplementationClassUID = generate_uid()
    dataset = FileDataset(
        str(path),
        {},
        file_meta=file_meta,
        preamble=b"\0" * 128,
    )
    dataset.StudyInstanceUID = study_uid
    dataset.StudyDate = study_date
    dataset.StudyDescription = study_description
    dataset.SOPClassUID = file_meta.MediaStorageSOPClassUID
    dataset.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
    dataset.PatientName = "Synthetic^Patient"
    dataset.PatientID = "SYNTHETIC"
    dataset.ContentDate = study_date
    dataset.ContentTime = datetime.now().strftime("%H%M%S")
    dataset.save_as(path, enforce_file_format=True)


def test_catalog_dicom_studies_links_manual_expansion(tmp_path: Path) -> None:
    """Verify ISO support links to manually expanded generated directory.

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
    (person.source_documents / "20260102 Study.iso").write_bytes(b"iso")
    extracted = person.local_build / "dicom" / "20260102 Study"
    extracted.mkdir(parents=True)
    (extracted / "index.html").write_text("<html></html>", encoding="utf-8")

    studies = catalog_dicom_studies(person, scan_documents(person))

    assert len(studies) == 1
    assert studies[0].support_kind == "dicom_iso"
    assert studies[0].extracted_path == extracted
    assert studies[0].viewer_paths == (extracted / "index.html",)
    assert studies[0].warnings == ()


def test_catalog_dicom_studies_accepts_img_disk_images(tmp_path: Path) -> None:
    """Verify IMG disk images are cataloged as DICOM supports.

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
    (person.source_documents / "20260102 Study.img").write_bytes(b"img")

    studies = catalog_dicom_studies(person, scan_documents(person))

    assert len(studies) == 1
    assert studies[0].support_kind == "dicom_img"


def test_catalog_dicom_studies_warns_when_expansion_missing(tmp_path: Path) -> None:
    """Verify missing manual expansion is a warning, not deletion or failure.

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
    path = person.source_documents / "20260102 Study.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("DICOMDIR", "synthetic")

    studies = catalog_dicom_studies(person, scan_documents(person))

    assert len(studies) == 1
    assert studies[0].support_kind == "dicom_zip"
    assert studies[0].extracted_path is None
    assert studies[0].warnings


def test_catalog_dicom_studies_ignores_regular_zip_archives(tmp_path: Path) -> None:
    """Verify regular ZIP archives are not DICOM supports by extension alone.

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
    path = person.source_documents / "20260102 Archive.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("report.txt", "synthetic")

    studies = catalog_dicom_studies(person, scan_documents(person))

    assert studies == ()


def test_catalog_dicom_studies_detects_dicom_zip_by_magic(tmp_path: Path) -> None:
    """Verify ZIP members with DICOM magic are cataloged as DICOM support.

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
    path = person.source_documents / "20260102 Study.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("IM000001", (b"\0" * 128) + b"DICM")

    studies = catalog_dicom_studies(person, scan_documents(person))

    assert len(studies) == 1
    assert studies[0].support_kind == "dicom_zip"


def test_catalog_dicom_studies_detects_dicom_tar_xz_by_magic(
    tmp_path: Path,
) -> None:
    """Verify TAR.XZ members with DICOM magic are cataloged as DICOM support.

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
    payload = tmp_path / "IM000001"
    payload.write_bytes((b"\0" * 128) + b"DICM")
    path = person.source_documents / "20260102 Study.tar.xz"
    with tarfile.open(path, "w:xz") as archive:
        archive.add(payload, arcname="IM000001")

    studies = catalog_dicom_studies(person, scan_documents(person))

    assert len(studies) == 1
    assert studies[0].support_kind == "dicom_tar_xz"


def test_catalog_dicom_studies_detects_dicom_7z_disk_image(tmp_path: Path) -> None:
    """Verify 7z archives with ISO members are cataloged as DICOM support.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    import py7zr

    person = _person(tmp_path)
    person.source_documents.mkdir(parents=True)
    source_file = tmp_path / "Study.iso"
    source_file.write_text("synthetic", encoding="utf-8")
    path = person.source_documents / "20260102 Study.7z"
    with py7zr.SevenZipFile(path, "w") as archive:
        archive.write(source_file, arcname="Study.iso")

    studies = catalog_dicom_studies(person, scan_documents(person))

    assert len(studies) == 1
    assert studies[0].support_kind == "dicom_7z"


def test_catalog_dicom_studies_detects_nested_dicom_zip(tmp_path: Path) -> None:
    """Verify ZIP archives with nested DICOM ZIP members are cataloged.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    import io

    person = _person(tmp_path)
    person.source_documents.mkdir(parents=True)
    nested_bytes = io.BytesIO()
    with zipfile.ZipFile(nested_bytes, "w") as nested:
        nested.writestr("Study/Slice0001.dcm", "synthetic")
    path = person.source_documents / "20260102 Nested Study.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("payload/study.zip", nested_bytes.getvalue())

    studies = catalog_dicom_studies(person, scan_documents(person))

    assert len(studies) == 1
    assert studies[0].support_kind == "dicom_zip"


def test_catalog_dicom_studies_detects_dicom_rar_by_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify RAR archives can be promoted to DICOM support.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.
    monkeypatch : pytest.MonkeyPatch
        Pytest monkeypatch fixture.

    Returns
    -------
    None
    """

    person = _person(tmp_path)
    person.source_documents.mkdir(parents=True)
    (person.source_documents / "20260102 Study.rar").write_bytes(b"rar")
    monkeypatch.setattr(dicom_module, "_rar_contains_dicom", lambda _path: True)

    studies = catalog_dicom_studies(person, scan_documents(person))

    assert len(studies) == 1
    assert studies[0].support_kind == "dicom_rar"
    assert studies[0].warnings == (
        "contenitore DICOM non espanso: non trovata directory manuale o staging",
    )


def test_catalog_dicom_studies_groups_files_by_study_instance_uid(
    tmp_path: Path,
) -> None:
    """Verify DICOM files with the same Study Instance UID form one study.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    person = _person(tmp_path)
    dicom_dir = person.source_documents / "dicom"
    dicom_dir.mkdir(parents=True)
    _write_dicom_file(
        dicom_dir / "IM000001.dcm",
        study_uid="1.2.826.0.1.3680043.10.543.1",
        study_description="Grouped Study",
    )
    _write_dicom_file(
        dicom_dir / "IM000002.dcm",
        study_uid="1.2.826.0.1.3680043.10.543.1",
        study_description="Grouped Study",
    )

    studies = catalog_dicom_studies(person, scan_documents(person))

    assert len(studies) == 1
    assert studies[0].support_kind == "dicom_study"
    assert studies[0].study_instance_uid == "1.2.826.0.1.3680043.10.543.1"
    assert studies[0].study_date == "2026-01-02"
    assert studies[0].study_description == "Grouped Study"
    assert studies[0].instance_count == 2


def test_catalog_dicom_studies_keeps_distinct_study_instance_uids(
    tmp_path: Path,
) -> None:
    """Verify distinct Study Instance UIDs form separate studies.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    person = _person(tmp_path)
    dicom_dir = person.source_documents / "dicom"
    dicom_dir.mkdir(parents=True)
    _write_dicom_file(
        dicom_dir / "IM000001.dcm",
        study_uid="1.2.826.0.1.3680043.10.543.1",
    )
    _write_dicom_file(
        dicom_dir / "IM000002.dcm",
        study_uid="1.2.826.0.1.3680043.10.543.2",
    )

    studies = catalog_dicom_studies(person, scan_documents(person))

    assert [study.study_instance_uid for study in studies] == [
        "1.2.826.0.1.3680043.10.543.1",
        "1.2.826.0.1.3680043.10.543.2",
    ]


def test_catalog_dicom_studies_reads_study_records_from_dicomdir(
    tmp_path: Path,
) -> None:
    """Verify DICOMDIR STUDY records become grouped DICOM studies.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
    from pydicom.uid import ExplicitVRLittleEndian, MediaStorageDirectoryStorage

    person = _person(tmp_path)
    person.source_documents.mkdir(parents=True)
    path = person.source_documents / "DICOMDIR"
    file_meta = FileMetaDataset()
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    file_meta.MediaStorageSOPClassUID = MediaStorageDirectoryStorage
    file_meta.MediaStorageSOPInstanceUID = "1.2.826.0.1.3680043.10.543.999"
    dataset = FileDataset(str(path), {}, file_meta=file_meta, preamble=b"\0" * 128)
    study_a = Dataset()
    study_a.DirectoryRecordType = "STUDY"
    study_a.StudyInstanceUID = "1.2.826.0.1.3680043.10.543.10"
    study_a.StudyDate = "20260102"
    study_a.StudyDescription = "First Study"
    study_b = Dataset()
    study_b.DirectoryRecordType = "STUDY"
    study_b.StudyInstanceUID = "1.2.826.0.1.3680043.10.543.20"
    study_b.StudyDate = "20260103"
    study_b.StudyDescription = "Second Study"
    dataset.DirectoryRecordSequence = [study_a, study_b]
    dataset.save_as(path, enforce_file_format=True)

    studies = catalog_dicom_studies(person, scan_documents(person))

    assert [(study.study_instance_uid, study.support_kind) for study in studies] == [
        ("1.2.826.0.1.3680043.10.543.10", "dicomdir_study"),
        ("1.2.826.0.1.3680043.10.543.20", "dicomdir_study"),
    ]
    assert [study.instance_count for study in studies] == [0, 0]


def test_catalog_dicom_studies_merges_dicomdir_and_file_uid(
    tmp_path: Path,
) -> None:
    """Verify DICOMDIR and file records for one UID become one study.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
    from pydicom.uid import ExplicitVRLittleEndian, MediaStorageDirectoryStorage

    person = _person(tmp_path)
    dicom_dir = person.source_documents / "dicom"
    dicom_dir.mkdir(parents=True)
    study_uid = "1.2.826.0.1.3680043.10.543.30"
    _write_dicom_file(
        dicom_dir / "IM000001.dcm",
        study_uid=study_uid,
        study_description="Instance Study",
    )
    path = dicom_dir / "DICOMDIR"
    file_meta = FileMetaDataset()
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    file_meta.MediaStorageSOPClassUID = MediaStorageDirectoryStorage
    file_meta.MediaStorageSOPInstanceUID = "1.2.826.0.1.3680043.10.543.998"
    dataset = FileDataset(str(path), {}, file_meta=file_meta, preamble=b"\0" * 128)
    study = Dataset()
    study.DirectoryRecordType = "STUDY"
    study.StudyInstanceUID = study_uid
    study.StudyDate = "20260102"
    study.StudyDescription = "Directory Study"
    dataset.DirectoryRecordSequence = [study]
    dataset.save_as(path, enforce_file_format=True)

    studies = catalog_dicom_studies(person, scan_documents(person))

    assert len(studies) == 1
    assert studies[0].support_kind == "dicom_study"
    assert studies[0].study_instance_uid == study_uid
    assert studies[0].instance_count == 1


def test_catalog_dicom_studies_suppresses_pydicom_value_warnings(
    tmp_path: Path,
    recwarn: pytest.WarningsRecorder,
) -> None:
    """Verify non-fatal pydicom value warnings do not leak to callers.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.
    recwarn : pytest.WarningsRecorder
        Warning recorder fixture.

    Returns
    -------
    None
    """

    person = _person(tmp_path)
    dicom_dir = person.source_documents / "dicom"
    dicom_dir.mkdir(parents=True)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        _write_dicom_file(
            dicom_dir / "IM000001.dcm",
            study_uid="1.2.826.0.1.3680043.10.543.40",
            study_description="x" * 76,
        )
    recwarn.clear()

    studies = catalog_dicom_studies(person, scan_documents(person))

    assert len(studies) == 1
    assert list(recwarn) == []


def test_catalog_dicom_studies_prefers_ihe_pdi_html_viewer(
    tmp_path: Path,
) -> None:
    """Verify DICOM cataloging exposes a browser-openable IHE PDI viewer.

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
    archive = person.source_documents / "20260102 TAC.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("DICOMDIR", b"")
    document = scan_documents(person)[0]
    extracted = person.local_build / "staging" / "containers" / document.document_id
    viewer = extracted / "IHE_PDI" / "PAGES" / "STUDIES" / "STUDY1.HTM"
    viewer.parent.mkdir(parents=True)
    viewer.write_text("<html>viewer</html>", encoding="utf-8")
    fallback = extracted / "index.html"
    fallback.write_text("<html>fallback</html>", encoding="utf-8")

    studies = catalog_dicom_studies(person, (document,))

    assert len(studies) == 1
    assert studies[0].html_viewer_path == viewer
    assert fallback in studies[0].viewer_paths
