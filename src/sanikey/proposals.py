"""Deterministic AI proposal interface for SaniKey v1."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, NoReturn

from .errors import ConfigError

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class Proposal:
    """Represent one non-authoritative proposal.

    Parameters
    ----------
    id : str
        Stable proposal identifier.
    kind : str
        Proposal kind.
    title : str
        Proposal title.
    body : str
        Proposal body.
    status : str
        Review status.
    source : str
        Proposal source provider.
    """

    id: str
    kind: str
    title: str
    body: str
    status: str
    source: str


def proposal_directory(metadata_directory: Path) -> Path:
    """Return the proposal directory under curated metadata.

    Parameters
    ----------
    metadata_directory : pathlib.Path
        Patient metadata directory.

    Returns
    -------
    pathlib.Path
        Proposal directory.
    """

    return metadata_directory / "proposed"


def generate_manual_proposals(metadata_directory: Path) -> tuple[Proposal, ...]:
    """Generate deterministic placeholder proposals for manual review.

    Parameters
    ----------
    metadata_directory : pathlib.Path
        Patient metadata directory.

    Returns
    -------
    tuple[Proposal, ...]
        Generated proposals.
    """

    generated_at = datetime.now(UTC).date().isoformat()
    proposal = Proposal(
        id=f"manual-review-{generated_at}",
        kind="clinical_summary",
        title="Manual review placeholder",
        body="Review source documents and curated metadata before approval.",
        status="proposed",
        source="manual-test-provider",
    )
    target = proposal_directory(metadata_directory) / "proposals.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_render_proposals((proposal,)), encoding="utf-8")
    return (proposal,)


def load_proposals(metadata_directory: Path) -> tuple[Proposal, ...]:
    """Load stored proposals.

    Parameters
    ----------
    metadata_directory : pathlib.Path
        Patient metadata directory.

    Returns
    -------
    tuple[Proposal, ...]
        Loaded proposals.

    Raises
    ------
    ConfigError
        If proposal storage is malformed.
    """

    path = proposal_directory(metadata_directory) / "proposals.toml"
    if not path.exists():
        return ()
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        message = f"invalid TOML in {path}: {exc}"
        raise ConfigError(message) from exc
    raw = data.get("proposal", [])
    if not isinstance(raw, list):
        _fail(f"{path}: proposal must be an array of tables")
    return tuple(
        _proposal_from_table(item, path, index) for index, item in enumerate(raw)
    )


def review_proposal(
    metadata_directory: Path, proposal_id: str, status: str
) -> Proposal:
    """Set a proposal review status.

    Parameters
    ----------
    metadata_directory : pathlib.Path
        Patient metadata directory.
    proposal_id : str
        Proposal id to update.
    status : str
        New status, either ``approved`` or ``rejected``.

    Returns
    -------
    Proposal
        Updated proposal.

    Raises
    ------
    ConfigError
        If the proposal does not exist or the status is invalid.
    """

    if status not in {"approved", "rejected"}:
        _fail(f"unsupported proposal status: {status}")
    proposals = list(load_proposals(metadata_directory))
    for index, proposal in enumerate(proposals):
        if proposal.id == proposal_id:
            updated = Proposal(
                id=proposal.id,
                kind=proposal.kind,
                title=proposal.title,
                body=proposal.body,
                status=status,
                source=proposal.source,
            )
            proposals[index] = updated
            target = proposal_directory(metadata_directory) / "proposals.toml"
            target.write_text(_render_proposals(tuple(proposals)), encoding="utf-8")
            return updated
    _fail(f"proposal not found: {proposal_id}")
    message = "unreachable"
    raise AssertionError(message)  # pragma: no cover


def _proposal_from_table(item: Any, path: Path, index: int) -> Proposal:
    """Parse a proposal table.

    Parameters
    ----------
    item : Any
        Raw TOML item.
    path : pathlib.Path
        Source path.
    index : int
        Item index.

    Returns
    -------
    Proposal
        Parsed proposal.
    """

    if not isinstance(item, dict):
        _fail(f"{path}: proposal {index} must be a table")
    return Proposal(
        id=_required_string(item, "id", path, index),
        kind=_required_string(item, "kind", path, index),
        title=_required_string(item, "title", path, index),
        body=_required_string(item, "body", path, index),
        status=_required_string(item, "status", path, index),
        source=_required_string(item, "source", path, index),
    )


def _render_proposals(proposals: tuple[Proposal, ...]) -> str:
    """Render proposals as TOML.

    Parameters
    ----------
    proposals : tuple[Proposal, ...]
        Proposals to render.

    Returns
    -------
    str
        TOML text.
    """

    lines: list[str] = []
    for proposal in proposals:
        lines.extend(
            (
                "[[proposal]]",
                f'id = "{_escape(proposal.id)}"',
                f'kind = "{_escape(proposal.kind)}"',
                f'title = "{_escape(proposal.title)}"',
                f'body = "{_escape(proposal.body)}"',
                f'status = "{_escape(proposal.status)}"',
                f'source = "{_escape(proposal.source)}"',
                "",
            )
        )
    return "\n".join(lines)


def _required_string(item: dict[str, Any], field: str, path: Path, index: int) -> str:
    """Return a required proposal string field.

    Parameters
    ----------
    item : dict[str, Any]
        Proposal table.
    field : str
        Field name.
    path : pathlib.Path
        Source file.
    index : int
        Proposal index.

    Returns
    -------
    str
        String value.
    """

    value = item.get(field)
    if not isinstance(value, str) or not value.strip():
        _fail(f"{path}: proposal {index} field {field} must be a non-empty string")
    return value.strip()


def _escape(value: str) -> str:
    """Escape a string for simple TOML output.

    Parameters
    ----------
    value : str
        String to escape.

    Returns
    -------
    str
        Escaped string.
    """

    return value.replace("\\", "\\\\").replace('"', '\\"')


def _fail(message: str) -> NoReturn:
    """Raise a proposal configuration error.

    Parameters
    ----------
    message : str
        Diagnostic message.

    Returns
    -------
    None

    Raises
    ------
    ConfigError
        Always raised.
    """

    raise ConfigError(message)
