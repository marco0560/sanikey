#!/usr/bin/env python3
"""Prepare a removable USB disk for a SaniKey export."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REQUIRED_COMMANDS = (
    "blkid",
    "exfatlabel",
    "fsck.exfat",
    "lsblk",
    "mkfs.exfat",
    "parted",
    "partprobe",
    "udevadm",
    "umount",
)
DEFAULT_LABEL = "SANIKEY"


@dataclass(frozen=True)
class Partition:
    """One partition reported by ``lsblk``.

    Parameters
    ----------
    path : pathlib.Path
        Block-device path.
    fstype : str | None
        Detected filesystem type.
    label : str | None
        Detected filesystem label.
    uuid : str | None
        Detected filesystem UUID.
    mountpoints : tuple[str, ...]
        Active mountpoints of the partition.
    start_sector : int | None
        Partition start expressed in logical sectors.
    """

    path: Path
    fstype: str | None
    label: str | None
    uuid: str | None
    mountpoints: tuple[str, ...]
    start_sector: int | None


@dataclass(frozen=True)
class UsbDisk:
    """One whole USB disk and its partitions.

    Parameters
    ----------
    path : pathlib.Path
        Whole-disk device path.
    model : str | None
        Device model reported by ``lsblk``.
    size : str
        Human-readable device capacity.
    removable : bool
        Whether the kernel marks the device as removable.
    partitions : tuple[Partition, ...]
        Partitions directly contained by the disk.
    logical_sector_size : int | None
        Logical sector size in bytes reported by ``lsblk``.
    partition_table : str | None
        Partition-table type reported by ``lsblk``.
    """

    path: Path
    model: str | None
    size: str
    removable: bool
    partitions: tuple[Partition, ...]
    logical_sector_size: int | None
    partition_table: str | None


def main(argv: list[str] | None = None) -> int:
    """List or prepare one USB disk as a SaniKey exFAT volume.

    Parameters
    ----------
    argv : list[str] | None, optional
        Command-line arguments without the executable name. Uses
        :data:`sys.argv` when omitted.

    Returns
    -------
    int
        Zero on success, one after a declined confirmation, or two for errors.
    """

    args = _parse_args(argv)
    try:
        disks = _usb_disks()
        _print_disks(disks)
        if args.list:
            return 0
        _require_commands()
        disk = _select_disk(disks, args.device)
        _prepare_disk(disk, args.label)
    except (OSError, TypeError, ValueError, subprocess.SubprocessError) as exc:
        print(f"ERRORE: preparazione chiavetta non riuscita: {exc}", file=sys.stderr)
        return 2
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse the command-line options for USB preparation.

    Parameters
    ----------
    argv : list[str] | None
        Command-line arguments without the executable name.

    Returns
    -------
    argparse.Namespace
        Parsed device selection, list, and label options.
    """

    parser = argparse.ArgumentParser(
        description="Prepara una chiavetta USB con una partizione exFAT SaniKey."
    )
    parser.add_argument(
        "--device",
        type=Path,
        help="Disco USB intero, per esempio /dev/sdd; senza opzione apre un menu",
    )
    parser.add_argument(
        "--label",
        default=DEFAULT_LABEL,
        help=f"Etichetta exFAT desiderata (predefinita: {DEFAULT_LABEL})",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Mostra le chiavette USB rilevate e non modifica nulla",
    )
    args = parser.parse_args(argv)
    _validate_label(args.label)
    if args.list and args.device is not None:
        parser.error("--list non puo' essere usato con --device")
    return args


def _validate_label(label: str) -> None:
    """Validate an exFAT volume label before any disk operation.

    Parameters
    ----------
    label : str
        Requested exFAT volume label.

    Returns
    -------
    None

    Raises
    ------
    ValueError
        If the label is empty, too long, or contains a control character.
    """

    if not label or len(label) > 15 or any(character.isspace() for character in label):
        message = "l'etichetta exFAT deve contenere da 1 a 15 caratteri senza spazi"
        raise ValueError(message)


def _require_commands() -> None:
    """Ensure all required external commands are installed.

    Parameters
    ----------
    None

    Returns
    -------
    None

    Raises
    ------
    ValueError
        If one or more required commands are unavailable.
    """

    missing = [
        command for command in REQUIRED_COMMANDS if shutil.which(command) is None
    ]
    if missing:
        message = f"comandi mancanti: {', '.join(missing)}"
        raise ValueError(message)


def _command(name: str) -> str:
    """Return the absolute path of one preflight-validated command.

    Parameters
    ----------
    name : str
        Executable name required by the script.

    Returns
    -------
    str
        Absolute executable path.

    Raises
    ------
    ValueError
        If a required executable disappeared after preflight.
    """

    executable = shutil.which(name)
    if executable is None:
        message = f"eseguibile non piu' disponibile: {name}"
        raise ValueError(message)
    return executable


def _usb_disks() -> tuple[UsbDisk, ...]:
    """Return currently attached whole USB disks from live ``lsblk`` data.

    Parameters
    ----------
    None

    Returns
    -------
    tuple[UsbDisk, ...]
        USB disks ordered by their kernel-reported path.

    Raises
    ------
    subprocess.CalledProcessError
        If ``lsblk`` fails while collecting the device inventory.
    json.JSONDecodeError
        If ``lsblk`` produces invalid JSON.
    TypeError
        If the device inventory does not contain a list of block devices.
    """

    result = subprocess.run(
        [
            _command("lsblk"),
            "--json",
            "--tree",
            "--output",
            "PATH,TYPE,TRAN,RM,SIZE,MODEL,FSTYPE,LABEL,UUID,MOUNTPOINTS,START,LOG-SEC,PTTYPE",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    devices = payload.get("blockdevices")
    if not isinstance(devices, list):
        message = "lsblk ha restituito un inventario dispositivi non valido"
        raise TypeError(message)
    disks = tuple(_usb_disk(item) for item in devices if _is_usb_disk(item))
    return tuple(sorted(disks, key=lambda disk: str(disk.path)))


def _is_usb_disk(item: Any) -> bool:
    """Return whether one raw ``lsblk`` item is a whole USB disk.

    Parameters
    ----------
    item : typing.Any
        Raw device description from ``lsblk``.

    Returns
    -------
    bool
        Whether the item can be safely considered a whole USB disk.
    """

    return (
        isinstance(item, dict)
        and item.get("type") == "disk"
        and item.get("tran") == "usb"
        and isinstance(item.get("path"), str)
    )


def _usb_disk(item: dict[str, Any]) -> UsbDisk:
    """Convert one validated raw ``lsblk`` disk item into a USB disk.

    Parameters
    ----------
    item : dict[str, typing.Any]
        Raw whole-disk description from ``lsblk``.

    Returns
    -------
    UsbDisk
        Normalized USB disk description.
    """

    children = item.get("children", [])
    partitions = (
        tuple(_partition(child) for child in children if _is_partition(child))
        if isinstance(children, list)
        else ()
    )
    return UsbDisk(
        path=Path(item["path"]),
        model=item.get("model") if isinstance(item.get("model"), str) else None,
        size=item.get("size") if isinstance(item.get("size"), str) else "sconosciuta",
        removable=bool(item.get("rm")),
        partitions=partitions,
        logical_sector_size=_integer_or_none(item.get("log-sec")),
        partition_table=item.get("pttype")
        if isinstance(item.get("pttype"), str)
        else None,
    )


def _is_partition(item: Any) -> bool:
    """Return whether one raw ``lsblk`` item is a partition.

    Parameters
    ----------
    item : typing.Any
        Raw device description from ``lsblk``.

    Returns
    -------
    bool
        Whether the item describes one partition with a device path.
    """

    return (
        isinstance(item, dict)
        and item.get("type") == "part"
        and isinstance(item.get("path"), str)
    )


def _partition(item: dict[str, Any]) -> Partition:
    """Convert one raw ``lsblk`` partition item into a normalized partition.

    Parameters
    ----------
    item : dict[str, typing.Any]
        Raw partition description from ``lsblk``.

    Returns
    -------
    Partition
        Normalized partition description.
    """

    mountpoints = item.get("mountpoints", [])
    return Partition(
        path=Path(item["path"]),
        fstype=item.get("fstype") if isinstance(item.get("fstype"), str) else None,
        label=item.get("label") if isinstance(item.get("label"), str) else None,
        uuid=item.get("uuid") if isinstance(item.get("uuid"), str) else None,
        mountpoints=tuple(point for point in mountpoints if isinstance(point, str))
        if isinstance(mountpoints, list)
        else (),
        start_sector=_integer_or_none(item.get("start")),
    )


def _integer_or_none(value: Any) -> int | None:
    """Return one non-negative integer raw ``lsblk`` field, when available.

    Parameters
    ----------
    value : typing.Any
        Raw ``lsblk`` JSON field.

    Returns
    -------
    int | None
        Parsed integer or ``None`` for unavailable or invalid values.
    """

    return value if isinstance(value, int) and value >= 0 else None


def _print_disks(disks: tuple[UsbDisk, ...]) -> None:
    """Print a concise current inventory of USB disks and partitions.

    Parameters
    ----------
    disks : tuple[UsbDisk, ...]
        USB disks to display.

    Returns
    -------
    None
    """

    if not disks:
        print("chiavette_usb=nessuna")
        return
    for index, disk in enumerate(disks, start=1):
        print(
            f"[{index}] disco={disk.path} dimensione={disk.size} "
            f"rimovibile={'si' if disk.removable else 'no'} "
            f"modello={disk.model or 'sconosciuto'}"
        )
        for partition in disk.partitions:
            mounts = ",".join(partition.mountpoints) or "-"
            print(
                f"    partizione={partition.path} fs={partition.fstype or '-'} "
                f"etichetta={partition.label or '-'} uuid={partition.uuid or '-'} "
                f"inizio_settore={partition.start_sector or '-'} mount={mounts}"
            )


def _select_disk(disks: tuple[UsbDisk, ...], device: Path | None) -> UsbDisk:
    """Select one listed USB disk through an explicit path or an interactive menu.

    Parameters
    ----------
    disks : tuple[UsbDisk, ...]
        USB disks eligible for selection.
    device : pathlib.Path | None
        Explicit whole-disk path, if supplied.

    Returns
    -------
    UsbDisk
        Selected USB disk.

    Raises
    ------
    ValueError
        If no USB disk is available or the requested selection is unsafe.
    """

    if not disks:
        message = "nessuna chiavetta USB rilevata"
        raise ValueError(message)
    if device is not None:
        requested = device.resolve(strict=False)
        for disk in disks:
            if disk.path == requested:
                return disk
        message = (
            f"dispositivo non selezionabile: {requested}; usare un disco USB elencato"
        )
        raise ValueError(message)
    if not sys.stdin.isatty():
        message = "specificare --device quando l'input non e' interattivo"
        raise ValueError(message)
    choice = input(
        "Numero della chiavetta da preparare (invio per annullare): "
    ).strip()
    if not choice:
        message = "operazione annullata"
        raise ValueError(message)
    try:
        return disks[int(choice) - 1]
    except (IndexError, ValueError) as exc:
        message = "selezione chiavetta non valida"
        raise ValueError(message) from exc


def _prepare_disk(disk: UsbDisk, label: str) -> None:
    """Inspect, relabel, or format one selected USB disk as required.

    Parameters
    ----------
    disk : UsbDisk
        Explicitly selected USB disk.
    label : str
        Desired exFAT volume label.

    Returns
    -------
    None

    Raises
    ------
    ValueError
        If root privileges are absent or the operator declines formatting.
    """

    partition = _conforming_partition(disk, label)
    if partition is not None:
        _verify_standard_format(disk, label)
        _print_result("gia-conforme", partition)
        return
    if _is_relabelable(disk):
        _require_root()
        partition = disk.partitions[0]
        _unmount(disk)
        _run(("exfatlabel", str(partition.path), label))
        current = _current_disk(disk.path)
        _verify_standard_format(current, label)
        _print_result("etichetta-aggiornata", current.partitions[0])
        return
    _require_root()
    _confirm_format(disk)
    _unmount(disk)
    _format_disk(disk.path, label)
    current = _current_disk(disk.path)
    _verify_standard_format(current, label)
    _print_result("formattata", current.partitions[0])


def _conforming_partition(disk: UsbDisk, label: str) -> Partition | None:
    """Return the single compliant exFAT partition, if present.

    Parameters
    ----------
    disk : UsbDisk
        USB disk to inspect.
    label : str
        Required exFAT label.

    Returns
    -------
    Partition | None
        The compliant partition, otherwise ``None``.
    """

    if len(disk.partitions) != 1:
        return None
    partition = disk.partitions[0]
    if (
        disk.partition_table == "dos"
        and partition.fstype == "exfat"
        and partition.label == label
        and _starts_at_one_mebibyte(disk, partition)
    ):
        return partition
    return None


def _is_relabelable(disk: UsbDisk) -> bool:
    """Return whether a USB disk needs only a non-destructive exFAT relabel.

    Parameters
    ----------
    disk : UsbDisk
        USB disk to inspect.

    Returns
    -------
    bool
        Whether exactly one existing partition already uses exFAT.
    """

    return (
        disk.partition_table == "dos"
        and len(disk.partitions) == 1
        and disk.partitions[0].fstype == "exfat"
        and _starts_at_one_mebibyte(disk, disk.partitions[0])
    )


def _starts_at_one_mebibyte(disk: UsbDisk, partition: Partition) -> bool:
    """Return whether a partition begins at exactly one mebibyte.

    Parameters
    ----------
    disk : UsbDisk
        Parent disk providing the logical sector size.
    partition : Partition
        Partition whose starting sector is inspected.

    Returns
    -------
    bool
        Whether the partition starts at byte offset ``1 MiB``.
    """

    if disk.logical_sector_size is None or partition.start_sector is None:
        return False
    return disk.logical_sector_size * partition.start_sector == 1024 * 1024


def _verify_standard_format(disk: UsbDisk, label: str) -> None:
    """Verify the required MBR, 1 MiB-aligned exFAT filesystem layout.

    Parameters
    ----------
    disk : UsbDisk
        USB disk to verify after inspection, relabeling, or formatting.
    label : str
        Required exFAT label.

    Returns
    -------
    None

    Raises
    ------
    ValueError
        If the expected one-partition MBR exFAT layout is absent.
    subprocess.CalledProcessError
        If the read-only exFAT structural check fails.
    """

    partition = _conforming_partition(disk, label)
    if partition is None:
        message = "layout USB non conforme: attesi MBR, exFAT e inizio a 1 MiB"
        raise ValueError(message)
    _run(("fsck.exfat", "--repair-no", str(partition.path)))


def _require_root() -> None:
    """Require root privileges before a command can alter a USB disk.

    Parameters
    ----------
    None

    Returns
    -------
    None

    Raises
    ------
    ValueError
        If the effective user is not root.
    """

    if os.geteuid() != 0:
        message = (
            "eseguire con sudo, per esempio: sudo uv run python scripts/prepare_usb.py"
        )
        raise ValueError(message)


def _confirm_format(disk: UsbDisk) -> None:
    """Require two exact interactive confirmations before erasing a USB disk.

    Parameters
    ----------
    disk : UsbDisk
        USB disk that will have its partition table replaced.

    Returns
    -------
    None

    Raises
    ------
    ValueError
        If stdin is not interactive or either confirmation does not match.
    """

    if not sys.stdin.isatty():
        message = "la formattazione richiede una sessione interattiva"
        raise ValueError(message)
    if disk.partitions:
        print("ATTENZIONE: la formattazione cancella tutte le partizioni e i dati.")
    first = input(f"Scrivi esattamente {disk.path} per continuare: ").strip()
    second = input(f"Scrivi esattamente FORMATTA {disk.path} per confermare: ").strip()
    if first != str(disk.path) or second != f"FORMATTA {disk.path}":
        message = "conferma formattazione non valida; nessuna modifica effettuata"
        raise ValueError(message)


def _unmount(disk: UsbDisk) -> None:
    """Unmount all mounted partitions of a selected USB disk.

    Parameters
    ----------
    disk : UsbDisk
        USB disk whose partitions may be mounted.

    Returns
    -------
    None

    Raises
    ------
    subprocess.CalledProcessError
        If any mounted partition cannot be cleanly unmounted.
    """

    for mountpoint in sorted(
        {point for partition in disk.partitions for point in partition.mountpoints},
        key=len,
        reverse=True,
    ):
        _run(("umount", mountpoint))


def _format_disk(device: Path, label: str) -> None:
    """Create one MBR exFAT partition on a selected whole USB disk.

    Parameters
    ----------
    device : pathlib.Path
        Whole USB disk device path.
    label : str
        Desired exFAT volume label.

    Returns
    -------
    None

    Raises
    ------
    subprocess.CalledProcessError
        If partitioning, kernel refresh, or formatting fails.
    ValueError
        If the new partition does not appear after the kernel refresh.
    """

    _run(
        (
            "parted",
            "--script",
            str(device),
            "mklabel",
            "msdos",
            "mkpart",
            "primary",
            "exfat",
            "1MiB",
            "100%",
        )
    )
    _run(("partprobe", str(device)))
    _run(("udevadm", "settle"))
    partition = _current_disk(device).partitions[0]
    _run(
        ("mkfs.exfat", "--check-written", "--volume-label", label, str(partition.path))
    )
    _run(("udevadm", "settle"))


def _current_disk(device: Path) -> UsbDisk:
    """Wait briefly for and return one USB disk with a sole partition.

    Parameters
    ----------
    device : pathlib.Path
        Whole USB disk path whose partition table was refreshed.

    Returns
    -------
    UsbDisk
        Current disk description with exactly one partition.

    Raises
    ------
    ValueError
        If exactly one partition is not visible after waiting.
    """

    for _ in range(10):
        for disk in _usb_disks():
            if disk.path == device and len(disk.partitions) == 1:
                return disk
        time.sleep(0.1)
    message = f"partizione unica non rilevata dopo la formattazione di {device}"
    raise ValueError(message)


def _print_result(status: str, partition: Partition) -> None:
    """Print the verified resulting filesystem identity and TOML update line.

    Parameters
    ----------
    status : str
        Final preparation status.
    partition : Partition
        Resulting exFAT partition.

    Returns
    -------
    None
    """

    uuid = _filesystem_uuid(partition.path)
    print(
        f"stato={status} partizione={partition.path} fs=exfat "
        f"etichetta={partition.label or '-'} uuid={uuid} montata=no"
    )
    print(f'usb_uuid = "{uuid}"')


def _filesystem_uuid(partition: Path) -> str:
    """Read the filesystem UUID that SaniKey should record after preparation.

    Parameters
    ----------
    partition : pathlib.Path
        Formatted exFAT partition path.

    Returns
    -------
    str
        Non-empty filesystem UUID reported by ``blkid``.

    Raises
    ------
    ValueError
        If the formatted filesystem has no UUID.
    subprocess.CalledProcessError
        If blkid cannot inspect the partition.
    """

    result = subprocess.run(
        (
            _command("blkid"),
            "--output",
            "value",
            "--match-tag",
            "UUID",
            str(partition),
        ),
        check=True,
        capture_output=True,
        text=True,
    )
    uuid = result.stdout.strip()
    if not uuid:
        message = f"UUID non disponibile per {partition}"
        raise ValueError(message)
    return uuid


def _run(command: tuple[str, ...]) -> None:
    """Run one checked external command without a shell.

    Parameters
    ----------
    command : tuple[str, ...]
        Executable and arguments to invoke.

    Returns
    -------
    None

    Raises
    ------
    subprocess.CalledProcessError
        If the command exits unsuccessfully.
    """

    subprocess.run(command, check=True)


if __name__ == "__main__":
    raise SystemExit(main())
