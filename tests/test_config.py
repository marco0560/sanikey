"""Configuration and privacy guard tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from sanikey.config import default_accounts_path, load_accounts, parse_accounts_data
from sanikey.errors import ConfigError, PrivacyError
from sanikey.privacy import validate_privacy


def _accounts_text(root: Path, *, enabled: bool = True) -> str:
    """Render a valid synthetic accounts file.

    Parameters
    ----------
    root : pathlib.Path
        Temporary root used for absolute paths.
    enabled : bool, optional
        Patient enabled flag.

    Returns
    -------
    str
        TOML configuration text.
    """

    return f"""
[global]
config_version = 1

[[person]]
id = "patient-a"
display_name = "Patient A"
source_documents = "{root / "source"}"
metadata_directory = "{root / "metadata"}"
local_build = "{root / "generated"}"
usb_uuid = "1A2B-3C4D"
enabled = {str(enabled).lower()}
"""


def test_load_accounts_accepts_valid_synthetic_config(tmp_path: Path) -> None:
    """Verify a complete accounts file loads deterministically.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    config_path = tmp_path / "accounts.toml"
    config_path.write_text(_accounts_text(tmp_path), encoding="utf-8")

    config = load_accounts(config_path)

    assert config.config_version == 1
    assert config.people[0].id == "patient-a"
    assert config.enabled_people()[0].display_name == "Patient A"


def test_default_accounts_path_uses_current_working_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify default accounts path uses the current directory by default.

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

    monkeypatch.chdir(tmp_path)

    assert default_accounts_path() == tmp_path / "config" / "accounts.toml"


def test_load_accounts_rejects_missing_file(tmp_path: Path) -> None:
    """Verify missing accounts files fail with ConfigError.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    with pytest.raises(ConfigError, match="accounts configuration not found"):
        load_accounts(tmp_path / "missing.toml")


def test_load_accounts_rejects_invalid_toml(tmp_path: Path) -> None:
    """Verify malformed TOML files fail with ConfigError.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    config_path = tmp_path / "accounts.toml"
    config_path.write_text("[global\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="invalid TOML"):
        load_accounts(config_path)


def test_load_accounts_resolves_relative_config_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify relative config paths still resolve data paths from the repo root.

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

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_path = config_dir / "accounts.toml"
    config_path.write_text(
        """
[global]
config_version = 1

[[person]]
id = "patient-a"
display_name = "Patient A"
source_documents = "local-data/patient-a/documents"
metadata_directory = "local-data/patient-a/metadata"
local_build = "local-data/generated/patient-a"
usb_uuid = "1A2B-3C4D"
""",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    config = load_accounts(Path("config/accounts.toml"))

    assert config.path == config_path
    assert config.people[0].source_documents == (
        tmp_path / "local-data" / "patient-a" / "documents"
    )


def test_parse_accounts_rejects_missing_real_paths() -> None:
    """Verify real-data paths have no implicit defaults.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    with pytest.raises(ConfigError, match="missing fields"):
        parse_accounts_data(
            {
                "global": {"config_version": 1},
                "person": [{"id": "patient-a", "display_name": "Patient A"}],
            },
            path=Path("accounts.toml"),
        )


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({"global": "bad", "person": []}, r"\[global\] must be a table"),
        ({"global": {}, "person": []}, r"\[global\].config_version is required"),
        (
            {"global": {"config_version": "1"}, "person": []},
            r"\[global\].config_version must be an integer",
        ),
        (
            {"global": {"config_version": 1}, "person": []},
            r"at least one \[\[person\]\] entry is required",
        ),
        (
            {"global": {"config_version": 1}, "person": "bad"},
            r"at least one \[\[person\]\] entry is required",
        ),
    ],
)
def test_parse_accounts_rejects_invalid_top_level_shapes(
    data: dict[str, object],
    message: str,
) -> None:
    """Verify invalid top-level configuration shapes are rejected.

    Parameters
    ----------
    data : dict[str, object]
        Parsed configuration data.
    message : str
        Expected diagnostic regex.

    Returns
    -------
    None
    """

    with pytest.raises(ConfigError, match=message):
        parse_accounts_data(data, path=Path("accounts.toml"))


def test_parse_accounts_accepts_repository_version_alias(tmp_path: Path) -> None:
    """Verify repository_version remains a supported version alias.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    config = parse_accounts_data(
        {
            "global": {"repository_version": 2},
            "person": [
                {
                    "id": "patient-a",
                    "display_name": "Patient A",
                    "source_documents": str(tmp_path / "source"),
                    "metadata_directory": str(tmp_path / "metadata"),
                    "local_build": str(tmp_path / "generated"),
                    "usb_uuid": "1A2B-3C4D",
                }
            ],
        },
        path=tmp_path / "accounts.toml",
    )

    assert config.config_version == 2


def test_parse_accounts_resolves_relative_paths_from_config_root(
    tmp_path: Path,
) -> None:
    """Verify patient paths can be relative to the repository root.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    config = parse_accounts_data(
        {
            "global": {"config_version": 1},
            "person": [
                {
                    "id": "patient-a",
                    "display_name": "Patient A",
                    "source_documents": "local-data/patient-a/documents",
                    "metadata_directory": "local-data/patient-a/metadata",
                    "local_build": "local-data/generated/patient-a",
                    "usb_uuid": "1A2B-3C4D",
                }
            ],
        },
        path=tmp_path / "config" / "accounts.toml",
    )

    assert config.people[0].source_documents == (
        tmp_path / "local-data" / "patient-a" / "documents"
    )
    assert config.people[0].metadata_directory == (
        tmp_path / "local-data" / "patient-a" / "metadata"
    )
    assert config.people[0].local_build == (
        tmp_path / "local-data" / "generated" / "patient-a"
    )


def test_parse_accounts_rejects_invalid_patient_id(tmp_path: Path) -> None:
    """Verify patient ids stay path-safe and stable.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    with pytest.raises(ConfigError, match="invalid id"):
        parse_accounts_data(
            {
                "global": {"config_version": 1},
                "person": [
                    {
                        "id": "Patient A",
                        "display_name": "Patient A",
                        "source_documents": str(tmp_path / "source"),
                        "metadata_directory": str(tmp_path / "metadata"),
                        "local_build": str(tmp_path / "generated"),
                        "usb_uuid": "1A2B-3C4D",
                    }
                ],
            },
            path=Path("accounts.toml"),
        )


def test_parse_accounts_rejects_non_table_person_entry() -> None:
    """Verify each person entry must be a table.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    with pytest.raises(ConfigError, match=r"\[\[person\]\] entry 0 must be a table"):
        parse_accounts_data(
            {"global": {"config_version": 1}, "person": ["bad"]},
            path=Path("accounts.toml"),
        )


def test_parse_accounts_rejects_non_boolean_enabled(tmp_path: Path) -> None:
    """Verify enabled must be boolean when provided.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    with pytest.raises(ConfigError, match="field enabled must be boolean"):
        parse_accounts_data(
            {
                "global": {"config_version": 1},
                "person": [
                    {
                        "id": "patient-a",
                        "display_name": "Patient A",
                        "source_documents": str(tmp_path / "source"),
                        "metadata_directory": str(tmp_path / "metadata"),
                        "local_build": str(tmp_path / "generated"),
                        "usb_uuid": "1A2B-3C4D",
                        "enabled": "yes",
                    }
                ],
            },
            path=tmp_path / "accounts.toml",
        )


def test_parse_accounts_rejects_empty_string_fields(tmp_path: Path) -> None:
    """Verify required string fields must be non-empty.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    with pytest.raises(ConfigError, match="field display_name must be a non-empty"):
        parse_accounts_data(
            {
                "global": {"config_version": 1},
                "person": [
                    {
                        "id": "patient-a",
                        "display_name": " ",
                        "source_documents": str(tmp_path / "source"),
                        "metadata_directory": str(tmp_path / "metadata"),
                        "local_build": str(tmp_path / "generated"),
                        "usb_uuid": "1A2B-3C4D",
                    }
                ],
            },
            path=tmp_path / "accounts.toml",
        )


def test_parse_accounts_rejects_duplicate_patient_ids(tmp_path: Path) -> None:
    """Verify duplicate patient ids are rejected.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    person = {
        "id": "patient-a",
        "display_name": "Patient A",
        "source_documents": str(tmp_path / "source"),
        "metadata_directory": str(tmp_path / "metadata"),
        "local_build": str(tmp_path / "generated"),
        "usb_uuid": "1A2B-3C4D",
    }

    with pytest.raises(ConfigError, match="duplicate patient id: patient-a"):
        parse_accounts_data(
            {"global": {"config_version": 1}, "person": [person, person]},
            path=tmp_path / "accounts.toml",
        )


def test_privacy_rejects_versioned_repo_paths(tmp_path: Path) -> None:
    """Verify configured real-data paths cannot point into versioned content.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    repo_root = Path.cwd()
    config_path = tmp_path / "accounts.toml"
    config_path.write_text(
        _accounts_text(tmp_path).replace(
            str(tmp_path / "source"),
            str(repo_root / "docs"),
        ),
        encoding="utf-8",
    )

    config = load_accounts(config_path)

    with pytest.raises(PrivacyError, match="versioned repository content"):
        validate_privacy(config, repo_root=repo_root)


def test_privacy_accepts_ignored_local_data_paths() -> None:
    """Verify configured local-data paths are accepted inside the checkout.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    repo_root = Path.cwd()
    config = parse_accounts_data(
        {
            "global": {"config_version": 1},
            "person": [
                {
                    "id": "patient-a",
                    "display_name": "Patient A",
                    "source_documents": "local-data/patient-a/documents",
                    "metadata_directory": "local-data/patient-a/metadata",
                    "local_build": "local-data/generated/patient-a",
                    "usb_uuid": "1A2B-3C4D",
                }
            ],
        },
        path=repo_root / "config" / "accounts.toml",
    )

    validate_privacy(config, repo_root=repo_root)
