"""Proposal interface tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sanikey.proposals import (
    generate_manual_proposals,
    load_proposals,
    proposal_directory,
    review_proposal,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_generate_manual_proposals_writes_review_file(tmp_path: Path) -> None:
    """Verify deterministic proposal storage is written under metadata."""

    proposals = generate_manual_proposals(tmp_path)
    loaded = load_proposals(tmp_path)

    assert len(proposals) == 1
    assert loaded[0].source == "manual-test-provider"
    assert (proposal_directory(tmp_path) / "proposals.toml").is_file()


def test_review_proposal_updates_status(tmp_path: Path) -> None:
    """Verify proposal review changes only the proposal status."""

    proposal = generate_manual_proposals(tmp_path)[0]
    updated = review_proposal(tmp_path, proposal.id, "approved")
    loaded = load_proposals(tmp_path)

    assert updated.status == "approved"
    assert loaded[0].status == "approved"
    assert loaded[0].body == proposal.body
