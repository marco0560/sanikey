"""Configuration and privacy guard tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from sanikey.config import load_accounts, parse_accounts_data
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


def test_parse_accounts_rejects_relative_paths() -> None:
    """Verify patient paths must be absolute.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    with pytest.raises(ConfigError, match="must be absolute"):
        parse_accounts_data(
            {
                "global": {"config_version": 1},
                "person": [
                    {
                        "id": "patient-a",
                        "display_name": "Patient A",
                        "source_documents": "relative/documents",
                        "metadata_directory": "/tmp/metadata",
                        "local_build": "/tmp/generated",
                        "usb_uuid": "1A2B-3C4D",
                    }
                ],
            },
            path=Path("accounts.toml"),
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
