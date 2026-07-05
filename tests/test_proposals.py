"""Proposal interface tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from sanikey.errors import ConfigError
from sanikey.proposals import (
    Proposal,
    _render_proposals,
    generate_manual_proposals,
    load_proposals,
    proposal_directory,
    review_proposal,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_generate_manual_proposals_writes_review_file(tmp_path: Path) -> None:
    """Verify deterministic proposal storage is written under metadata.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    proposals = generate_manual_proposals(tmp_path)
    loaded = load_proposals(tmp_path)

    assert len(proposals) == 1
    assert loaded[0].source == "manual-test-provider"
    assert (proposal_directory(tmp_path) / "proposals.toml").is_file()


def test_load_proposals_returns_empty_when_file_is_missing(tmp_path: Path) -> None:
    """Verify missing proposal storage is treated as no proposals.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    assert load_proposals(tmp_path) == ()


def test_load_proposals_rejects_invalid_toml(tmp_path: Path) -> None:
    """Verify malformed proposal TOML is rejected.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    target = proposal_directory(tmp_path) / "proposals.toml"
    target.parent.mkdir(parents=True)
    target.write_text("[proposal\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="invalid TOML"):
        load_proposals(tmp_path)


def test_load_proposals_rejects_non_array_proposal_table(tmp_path: Path) -> None:
    """Verify proposal must be an array of tables.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    target = proposal_directory(tmp_path) / "proposals.toml"
    target.parent.mkdir(parents=True)
    target.write_text(
        """
[proposal]
id = "proposal-a"
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="proposal must be an array of tables"):
        load_proposals(tmp_path)


def test_load_proposals_rejects_non_table_entries(tmp_path: Path) -> None:
    """Verify each proposal entry must be a table.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    target = proposal_directory(tmp_path) / "proposals.toml"
    target.parent.mkdir(parents=True)
    target.write_text('proposal = ["bad"]\n', encoding="utf-8")

    with pytest.raises(ConfigError, match="proposal 0 must be a table"):
        load_proposals(tmp_path)


def test_load_proposals_rejects_empty_required_fields(tmp_path: Path) -> None:
    """Verify proposal string fields must be non-empty.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    target = proposal_directory(tmp_path) / "proposals.toml"
    target.parent.mkdir(parents=True)
    target.write_text(
        """
[[proposal]]
id = "proposal-a"
kind = "clinical_summary"
title = ""
body = "Body"
status = "proposed"
source = "manual"
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="field title must be a non-empty string"):
        load_proposals(tmp_path)


def test_review_proposal_updates_status(tmp_path: Path) -> None:
    """Verify proposal review changes only the proposal status.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    proposal = generate_manual_proposals(tmp_path)[0]
    updated = review_proposal(tmp_path, proposal.id, "approved")
    loaded = load_proposals(tmp_path)

    assert updated.status == "approved"
    assert loaded[0].status == "approved"
    assert loaded[0].body == proposal.body


def test_review_proposal_rejects_unsupported_status(tmp_path: Path) -> None:
    """Verify proposal review accepts only terminal statuses.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    proposal = generate_manual_proposals(tmp_path)[0]

    with pytest.raises(ConfigError, match="unsupported proposal status"):
        review_proposal(tmp_path, proposal.id, "proposed")


def test_review_proposal_rejects_unknown_id(tmp_path: Path) -> None:
    """Verify reviewing a missing proposal fails.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    generate_manual_proposals(tmp_path)

    with pytest.raises(ConfigError, match="proposal not found: missing"):
        review_proposal(tmp_path, "missing", "approved")


def test_render_proposals_escapes_toml_strings() -> None:
    """Verify proposal rendering escapes quotes and backslashes.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    rendered = _render_proposals(
        (
            Proposal(
                id='proposal-"a"',
                kind="clinical\\summary",
                title='Quote "Title"',
                body="Back\\slash",
                status="proposed",
                source="manual",
            ),
        )
    )

    assert 'id = "proposal-\\"a\\""' in rendered
    assert 'kind = "clinical\\\\summary"' in rendered
    assert 'title = "Quote \\"Title\\""' in rendered
