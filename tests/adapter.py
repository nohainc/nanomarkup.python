"""Nano Markup conformance protocol v1 adapter."""

from __future__ import annotations

import json
import sys
from collections.abc import Sequence
from pathlib import Path

from nanomarkup import DecodeError, loads


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 2 or arguments[0] != "parse":
        print("usage: adapter.py parse PATH", file=sys.stderr)
        return 2
    try:
        value = loads(Path(arguments[1]).read_bytes())
    except DecodeError as error:
        result: dict[str, object] = {"ok": False, "error": error.code.value}
    except OSError as error:
        print(error, file=sys.stderr)
        return 2
    else:
        result = {"ok": True, "value": value}
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

