"""Nano Markup conformance protocol v1 adapter."""

from __future__ import annotations

import json
import sys
from collections.abc import Sequence
from pathlib import Path

from nanomarkup import DecodeError, EncodeError, dumps, loads


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments or arguments[0] not in {"parse", "write"}:
        print("usage: adapter.py parse PATH | write PATH LF|CRLF", file=sys.stderr)
        return 2
    if arguments[0] == "write":
        if len(arguments) != 3 or arguments[2] not in {"LF", "CRLF"}:
            print("usage: adapter.py write PATH LF|CRLF", file=sys.stderr)
            return 2
        try:
            value = json.loads(Path(arguments[1]).read_text(encoding="utf-8"))
            source = dumps(value, newline="\n" if arguments[2] == "LF" else "\r\n")
        except (EncodeError, UnicodeError, json.JSONDecodeError):
            result: dict[str, object] = {"ok": False, "error": "E_VALUE"}
        except OSError as error:
            print(error, file=sys.stderr)
            return 2
        else:
            result = {"ok": True, "source": source}
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
        return 0
    if len(arguments) != 2:
        print("usage: adapter.py parse PATH", file=sys.stderr)
        return 2
    try:
        value = loads(Path(arguments[1]).read_bytes())
    except DecodeError as error:
        result = {"ok": False, "error": error.code.value}
    except OSError as error:
        print(error, file=sys.stderr)
        return 2
    else:
        result = {"ok": True, "value": value}
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
