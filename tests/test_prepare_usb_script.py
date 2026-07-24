"""Tests for the standalone USB preparation script."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import ModuleType

    import pytest


def _script_module() -> ModuleType:
    """Load the USB preparation script as a module for direct testing.

    Parameters
    ----------
    None

    Returns
    -------
    types.ModuleType
        Imported USB preparation script module.
    """

    script_path = Path(__file__).parents[1] / "scripts" / "prepare_usb.py"
    spec = importlib.util.spec_from_file_location("prepare_usb", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _disk(module: ModuleType, *, start_sector: int = 2048) -> object:
    """Build one synthetic standard USB disk description.

    Parameters
    ----------
    module : types.ModuleType
        Imported USB preparation script module.
    start_sector : int, optional
        Synthetic partition start sector for a 512-byte logical sector size.

    Returns
    -------
    object
        Synthetic ``UsbDisk`` instance.
    """

    partition = module.Partition(
        path=Path("/dev/sdz1"),
        fstype="exfat",
        label="SANIKEY",
        uuid="ABCD-1234",
        mountpoints=(),
        start_sector=start_sector,
    )
    return module.UsbDisk(
        path=Path("/dev/sdz"),
        model="Test USB",
        size="64G",
        removable=True,
        partitions=(partition,),
        logical_sector_size=512,
        partition_table="dos",
    )


def test_conforming_partition_requires_mbr_exfat_label_and_one_mebibyte() -> None:
    """Verify compliance accepts exactly the required standard layout.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    module = _script_module()
    disk = _disk(module)

    assert module._conforming_partition(disk, "SANIKEY") == disk.partitions[0]
    assert (
        module._conforming_partition(_disk(module, start_sector=2049), "SANIKEY")
        is None
    )


def test_usb_inventory_requests_tree_and_preserves_partition_label(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify listing retains current labels from child partitions.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Pytest fixture used to replace the live ``lsblk`` command.

    Returns
    -------
    None
    """

    module = _script_module()
    commands: list[list[str]] = []
    payload = {
        "blockdevices": [
            {
                "path": "/dev/sdz",
                "type": "disk",
                "tran": "usb",
                "rm": True,
                "size": "64G",
                "log-sec": 512,
                "pttype": "dos",
                "children": [
                    {
                        "path": "/dev/sdz1",
                        "type": "part",
                        "fstype": "exfat",
                        "label": "SANIKEY",
                        "uuid": "ABCD-1234",
                        "mountpoints": ["/media/SANIKEY"],
                        "start": 2048,
                    }
                ],
            }
        ]
    }

    def fake_run(command: list[str], **_kwargs: object) -> object:
        """Return one synthetic tree-shaped ``lsblk`` result.

        Parameters
        ----------
        command : list[str]
            Requested ``lsblk`` command.
        _kwargs : object
            Unused subprocess keyword arguments.

        Returns
        -------
        object
            Result object exposing JSON output.
        """

        commands.append(command)
        return type("Result", (), {"stdout": json.dumps(payload)})()

    monkeypatch.setattr(module, "_command", lambda _name: "/usr/bin/lsblk")
    monkeypatch.setattr(module.subprocess, "run", fake_run)

    disks = module._usb_disks()

    assert "--tree" in commands[0]
    assert disks[0].partitions[0].label == "SANIKEY"


def test_format_disk_creates_mbr_partition_at_one_mebibyte(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify formatting commands create the required MBR/exFAT layout.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Pytest fixture used to replace disk-affecting helpers.

    Returns
    -------
    None
    """

    module = _script_module()
    commands: list[tuple[str, ...]] = []
    monkeypatch.setattr(module, "_run", commands.append)
    monkeypatch.setattr(module, "_current_disk", lambda _device: _disk(module))

    module._format_disk(Path("/dev/sdz"), "SANIKEY")

    assert commands == [
        (
            "parted",
            "--script",
            "/dev/sdz",
            "mklabel",
            "msdos",
            "mkpart",
            "primary",
            "exfat",
            "1MiB",
            "100%",
        ),
        ("partprobe", "/dev/sdz"),
        ("udevadm", "settle"),
        ("mkfs.exfat", "--check-written", "--volume-label", "SANIKEY", "/dev/sdz1"),
        ("udevadm", "settle"),
    ]


def test_verify_standard_format_runs_read_only_exfat_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify a compliant layout receives a non-mutating filesystem check.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Pytest fixture used to replace the external command helper.

    Returns
    -------
    None
    """

    module = _script_module()
    commands: list[tuple[str, ...]] = []
    monkeypatch.setattr(module, "_run", commands.append)

    module._verify_standard_format(_disk(module), "SANIKEY")

    assert commands == [("fsck.exfat", "--repair-no", "/dev/sdz1")]


def test_prepare_disk_does_not_modify_an_already_compliant_usb(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify a compliant USB is only checked and reported.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Pytest fixture used to block all mutating helpers.

    Returns
    -------
    None
    """

    module = _script_module()
    verified: list[object] = []
    reported: list[tuple[str, object]] = []

    monkeypatch.setattr(
        module, "_verify_standard_format", lambda *args: verified.append(args)
    )
    monkeypatch.setattr(module, "_print_result", lambda *args: reported.append(args))
    monkeypatch.setattr(
        module,
        "_require_root",
        lambda: (_ for _ in ()).throw(AssertionError("non deve richiedere root")),
    )

    disk = _disk(module)
    module._prepare_disk(disk, "SANIKEY")

    assert verified == [(disk, "SANIKEY")]
    assert reported == [("gia-conforme", disk.partitions[0])]
