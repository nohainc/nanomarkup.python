"""Nano Markup 1.0.0 data writer."""

from __future__ import annotations

import re
from typing import Literal, TextIO, cast

from .errors import EncodeError
from .types import NanoValue

_KEY_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*\Z")
_Newline = Literal["\n", "\r\n"]
_Context = Literal["root", "mapping", "sequence"]


def _path_key(path: str, key: str) -> str:
    return f"{path}[{key!r}]"


def _validate_string(value: str, path: str) -> None:
    for index, character in enumerate(value):
        codepoint = ord(character)
        if (
            0x00 <= codepoint <= 0x08
            or 0x0B <= codepoint <= 0x0C
            or 0x0E <= codepoint <= 0x1F
            or 0x7F <= codepoint <= 0x9F
            or 0xD800 <= codepoint <= 0xDFFF
        ):
            raise EncodeError(
                f"{path} contains a character outside the Nano Markup data model at index {index}"
            )


def _validate_tree(value: object) -> None:
    active: set[int] = set()
    stack: list[tuple[object, str, bool]] = [(value, "$", False)]
    while stack:
        current, path, leaving = stack.pop()
        if leaving:
            active.remove(id(current))
            continue
        if type(current) is str:
            _validate_string(current, path)
            continue
        if type(current) not in (dict, list):
            raise EncodeError(
                f"{path} has unsupported type {type(current).__name__}; expected str, dict, or list"
            )
        identity = id(current)
        if identity in active:
            raise EncodeError(f"{path} contains a cyclic mapping or sequence")
        active.add(identity)
        stack.append((current, path, True))
        if type(current) is dict:
            mapping = cast(dict[object, object], current)
            for key, child in reversed(list(mapping.items())):
                if type(key) is not str:
                    raise EncodeError(f"{path} contains a non-string mapping key")
                if not _KEY_RE.fullmatch(key):
                    raise EncodeError(f"{_path_key(path, key)} uses an invalid Nano Markup key")
                stack.append((child, _path_key(path, key), False))
        else:
            sequence = cast(list[object], current)
            for index in range(len(sequence) - 1, -1, -1):
                stack.append((sequence[index], f"{path}[{index}]", False))


def _raw_is_safe(value: str, context: _Context) -> bool:
    if not value or value.startswith((" ", '"')) or value.endswith(" "):
        return False
    if "\t" in value or "\r" in value or "\n" in value:
        return False
    if context in ("root", "sequence"):
        return value not in {"..", ":", "|"} and not value.startswith("#")
    return True


def _quote(value: str) -> str:
    replacements = {
        "\\": "\\\\",
        '"': '\\"',
        "\n": "\\n",
        "\r": "\\r",
        "\t": "\\t",
    }
    return '"' + "".join(replacements.get(character, character) for character in value) + '"'


def _scalar(value: str, context: _Context) -> str:
    if _raw_is_safe(value, context):
        return value
    return _quote(value)


def _can_use_multiline(value: str) -> bool:
    lines = value.split("\n")
    return (
        "\n" in value
        and "\r" not in value
        and "\t" not in value
        and not value.endswith("\n")
        and all(not line or line.strip(" ") for line in lines)
    )


class _Writer:
    def __init__(self) -> None:
        self.lines: list[str] = []

    @staticmethod
    def _indent(level: int) -> str:
        return " " * (4 * level)

    def _multiline(self, header: str, value: str, content_level: int) -> None:
        self.lines.append(header)
        prefix = self._indent(content_level)
        for line in value.split("\n"):
            self.lines.append(prefix + line if line else "")

    def write(self, value: NanoValue) -> list[str]:
        tasks: list[tuple[NanoValue, int, _Context, str | None]] = [(value, 0, "root", None)]
        while tasks:
            current, level, context, key = tasks.pop()
            prefix = self._indent(level)
            if type(current) is dict:
                mapping = current
                if context == "root":
                    self.lines.append("..")
                elif context == "mapping":
                    self.lines.append(f"{prefix}{key}..")
                else:
                    self.lines.append(f"{prefix}..")
                for child_key, child in reversed(list(mapping.items())):
                    tasks.append((child, level + 1, "mapping", child_key))
                continue
            if type(current) is list:
                sequence = current
                if context == "root":
                    self.lines.append(":")
                elif context == "mapping":
                    self.lines.append(f"{prefix}{key}:")
                else:
                    self.lines.append(f"{prefix}:")
                for child in reversed(sequence):
                    tasks.append((child, level + 1, "sequence", None))
                continue

            string = cast(str, current)
            if context == "mapping":
                if string == "":
                    self.lines.append(f"{prefix}{key}")
                elif _can_use_multiline(string):
                    self._multiline(f"{prefix}{key}|", string, level + 1)
                else:
                    self.lines.append(f"{prefix}{key} {_scalar(string, 'mapping')}")
            elif _can_use_multiline(string):
                header = "|" if context == "root" else f"{prefix}|"
                self._multiline(header, string, level + 1)
            else:
                scalar_context: _Context = "root" if context == "root" else "sequence"
                self.lines.append(f"{prefix}{_scalar(string, scalar_context)}")
        return self.lines


def dumps(value: NanoValue, *, newline: _Newline = "\n") -> str:
    """Encode a Python Nano Markup value as a document string."""

    if newline not in ("\n", "\r\n"):
        raise ValueError("newline must be either '\\n' or '\\r\\n'")
    _validate_tree(value)
    return newline.join(_Writer().write(value))


def dump(value: NanoValue, stream: TextIO, *, newline: _Newline = "\n") -> None:
    """Encode a Python Nano Markup value into an open text stream."""

    stream.write(dumps(value, newline=newline))
