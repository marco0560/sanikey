"""Module entrypoint for sanikey."""

from __future__ import annotations

from .cli import build_parser
from .errors import SaniKeyError


def main() -> int:
    """Parse CLI arguments and dispatch the selected command.

    Parameters
    ----------
    None

    Returns
    -------
    int
        Process exit status.
    """
    parser = build_parser()
    args = parser.parse_args()
    func = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        return 0
    try:
        return int(func(args))
    except (SaniKeyError, ValueError) as exc:
        print(f"ERRORE: {exc}")
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"ERRORE: errore inatteso: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
