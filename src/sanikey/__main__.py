"""Module entrypoint for sanikey."""

from __future__ import annotations

from .cli import build_parser


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
    return int(func(args))


if __name__ == "__main__":
    raise SystemExit(main())
