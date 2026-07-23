"""Command-line validation for Nano Markup documents."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from ._version import SPEC_VERSION, __version__
from .decoder import loads
from .errors import DecodeError


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nanomarkup",
        description="Validate Nano Markup 0.5-draft documents.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__} (Nano Markup {SPEC_VERSION})",
    )
    parser.add_argument("files", nargs="+", metavar="FILE", help="document path, or - for stdin")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Nano Markup validator."""

    arguments = _parser().parse_args(argv)
    if arguments.files.count("-") > 1:
        print("nanomarkup: standard input may be specified only once", file=sys.stderr)
        return 2

    status = 0
    for name in arguments.files:
        try:
            source = sys.stdin.buffer.read() if name == "-" else Path(name).read_bytes()
        except OSError as error:
            print(f"{name}: {error}", file=sys.stderr)
            status = 2
            continue
        try:
            loads(source)
        except DecodeError as error:
            print(
                f"{name}:{error.line}:{error.column}: {error.code.value}: {error.message}",
                file=sys.stderr,
            )
            if status != 2:
                status = 1
        else:
            print(f"{name}: valid")
    return status


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
