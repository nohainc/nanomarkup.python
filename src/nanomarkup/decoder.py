"""Nano Markup 0.5-draft data decoder."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import BinaryIO, Literal, TextIO, cast

from .errors import DecodeError, ErrorCode
from .types import NanoValue

_KEY_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*\Z")
_ERROR_PRIORITY = {
    ErrorCode.ENCODING: 0,
    ErrorCode.TAB: 1,
    ErrorCode.INDENT: 2,
    ErrorCode.SYNTAX: 3,
    ErrorCode.KEY: 4,
    ErrorCode.DUPLICATE_KEY: 5,
    ErrorCode.ESCAPE: 6,
    ErrorCode.STRING: 7,
}


@dataclass(frozen=True, slots=True)
class _Line:
    text: str
    number: int
    byte_start: int

    @property
    def leading_spaces(self) -> int:
        return len(self.text) - len(self.text.lstrip(" "))

    @property
    def is_blank(self) -> bool:
        return not self.text or self.text.isspace()


@dataclass(frozen=True, slots=True)
class _Diagnostic:
    code: ErrorCode
    message: str
    byte_offset: int
    line: int
    column: int


@dataclass(slots=True)
class _Frame:
    kind: Literal["mapping", "sequence"]
    level: int
    value: dict[str, NanoValue] | list[NanoValue]


def _source_position(data: bytes, offset: int) -> tuple[int, int]:
    safe_offset = min(max(offset, 0), len(data))
    line = data.count(b"\n", 0, safe_offset) + 1
    line_start = data.rfind(b"\n", 0, safe_offset) + 1
    prefix = data[line_start:safe_offset]
    if prefix.endswith(b"\r"):
        prefix = prefix[:-1]
    column = len(prefix.decode("utf-8", errors="replace")) + 1
    return line, column


def _raise_preparation_error(data: bytes, offset: int, message: str) -> None:
    line, column = _source_position(data, offset)
    raise DecodeError(
        ErrorCode.ENCODING,
        message,
        byte_offset=offset,
        line=line,
        column=column,
    )


def _validate_and_decode(source: str | bytes | bytearray | memoryview) -> tuple[bytes, str]:
    if isinstance(source, str):
        try:
            data = source.encode("utf-8")
        except UnicodeEncodeError as error:
            prefix = source[: error.start].encode("utf-8")
            line = source.count("\n", 0, error.start) + 1
            line_start = source.rfind("\n", 0, error.start) + 1
            raise DecodeError(
                ErrorCode.ENCODING,
                "source contains a value that is not a Unicode scalar",
                byte_offset=len(prefix),
                line=line,
                column=error.start - line_start + 1,
            ) from None
    elif isinstance(source, (bytes, bytearray, memoryview)):
        data = bytes(source)
    else:
        raise TypeError("source must be str, bytes, bytearray, or memoryview")

    encoding_errors: list[tuple[int, str]] = []
    if data.startswith(b"\xef\xbb\xbf"):
        encoding_errors.append((0, "UTF-8 byte-order marks are not permitted"))

    for offset, byte in enumerate(data):
        if byte <= 0x08 or 0x0B <= byte <= 0x0C or 0x0E <= byte <= 0x1F or byte == 0x7F:
            encoding_errors.append((offset, "source contains a forbidden control character"))
        elif byte == 0x0D and (offset + 1 == len(data) or data[offset + 1] != 0x0A):
            encoding_errors.append((offset, "a carriage return must be followed by a line feed"))

    try:
        text = data.decode("utf-8")
        decoded_prefix = text
    except UnicodeDecodeError as error:
        encoding_errors.append((error.start, "source is not valid UTF-8"))
        decoded_prefix = data[: error.start].decode("utf-8", errors="strict")
        text = ""

    byte_offset = 0
    for character in decoded_prefix:
        codepoint = ord(character)
        if 0x80 <= codepoint <= 0x9F:
            encoding_errors.append((byte_offset, "source contains a forbidden control character"))
        byte_offset += len(character.encode("utf-8"))

    if encoding_errors:
        offset, message = min(encoding_errors, key=lambda item: item[0])
        _raise_preparation_error(data, offset, message)

    tab_offset = data.find(b"\t")
    if tab_offset >= 0:
        line, column = _source_position(data, tab_offset)
        raise DecodeError(
            ErrorCode.TAB,
            "literal tabs are not permitted; use spaces or the quoted \\t escape",
            byte_offset=tab_offset,
            line=line,
            column=column,
        )

    return data, text


def _physical_lines(data: bytes) -> list[_Line]:
    lines: list[_Line] = []
    start = 0
    number = 1
    while start < len(data):
        end = data.find(b"\n", start)
        if end < 0:
            raw = data[start:]
            next_start = len(data)
        else:
            raw = data[start:end]
            next_start = end + 1
        if raw.endswith(b"\r"):
            raw = raw[:-1]
        lines.append(_Line(raw.decode("utf-8"), number, start))
        number += 1
        start = next_start
    return lines


class _Parser:
    def __init__(self, data: bytes, lines: list[_Line]) -> None:
        self.data = data
        self.lines = lines
        self.index = 0
        self.diagnostics: list[_Diagnostic] = []

    def add_error(
        self,
        code: ErrorCode,
        message: str,
        line: _Line | None = None,
        character_offset: int = 0,
    ) -> None:
        if line is None:
            byte_offset = len(self.data)
            source_line, column = _source_position(self.data, byte_offset)
        else:
            prefix = line.text[:character_offset]
            byte_offset = line.byte_start + len(prefix.encode("utf-8"))
            source_line = line.number
            column = character_offset + 1
        self.diagnostics.append(
            _Diagnostic(code, message, byte_offset, source_line, column)
        )

    def _skip_ignored(self) -> None:
        while self.index < len(self.lines):
            line = self.lines[self.index]
            if line.is_blank:
                self.index += 1
                continue
            spaces = line.leading_spaces
            if line.text[spaces:].startswith("#"):
                if spaces % 4:
                    self.add_error(
                        ErrorCode.INDENT,
                        "comment indentation must use complete four-space levels",
                        line,
                        spaces,
                    )
                self.index += 1
                continue
            break

    def _line_parts(self, line: _Line) -> tuple[int, str] | None:
        spaces = line.leading_spaces
        if spaces % 4:
            self.add_error(
                ErrorCode.INDENT,
                "indentation must use exactly four spaces per level",
                line,
                spaces,
            )
            return None
        return spaces // 4, line.text[spaces:]

    def _parse_quoted(self, text: str, line: _Line, start: int) -> str:
        result: list[str] = []
        index = 1
        escapes = {"\"": "\"", "\\": "\\", "n": "\n", "r": "\r", "t": "\t"}
        while index < len(text):
            character = text[index]
            if character == '"':
                if index != len(text) - 1:
                    self.add_error(
                        ErrorCode.STRING,
                        "a quoted string must occupy the complete scalar position",
                        line,
                        start + index + 1,
                    )
                return "".join(result)
            if character == "\\":
                if index + 1 >= len(text):
                    self.add_error(
                        ErrorCode.ESCAPE,
                        "an escape must be followed by a supported escape character",
                        line,
                        start + index,
                    )
                    index += 1
                    continue
                escaped = text[index + 1]
                if escaped not in escapes:
                    self.add_error(
                        ErrorCode.ESCAPE,
                        f"unsupported escape \\{escaped}",
                        line,
                        start + index,
                    )
                    index += 2
                    continue
                result.append(escapes[escaped])
                index += 2
                continue
            result.append(character)
            index += 1
        self.add_error(
            ErrorCode.STRING,
            "quoted string is missing its closing quotation mark",
            line,
            start + len(text),
        )
        return "".join(result)

    def _parse_scalar(self, text: str, line: _Line, start: int) -> str:
        if text.startswith('"'):
            return self._parse_quoted(text, line, start)
        if not text:
            self.add_error(ErrorCode.STRING, "a raw string cannot be empty", line, start)
            return ""
        if text.startswith(" "):
            self.add_error(
                ErrorCode.STRING,
                "an unquoted string cannot begin with an ASCII space",
                line,
                start,
            )
        if text.endswith(" "):
            self.add_error(
                ErrorCode.STRING,
                "an unquoted string cannot end with an ASCII space",
                line,
                start + len(text) - 1,
            )
        return text

    def _collect_multiline(self, header_level: int) -> str:
        prefix = " " * (4 * (header_level + 1))
        content: list[str] = []
        provisional_blanks = 0
        while self.index < len(self.lines):
            line = self.lines[self.index]
            if line.is_blank:
                provisional_blanks += 1
                self.index += 1
                continue
            if not line.text.startswith(prefix):
                break
            content.extend("" for _ in range(provisional_blanks))
            provisional_blanks = 0
            content.append(line.text[len(prefix) :])
            self.index += 1
        return "\n".join(content)

    def _check_key(self, key: str, line: _Line, start: int) -> bool:
        if _KEY_RE.fullmatch(key):
            return True
        self.add_error(
            ErrorCode.KEY,
            f"invalid mapping key {key!r}",
            line,
            start,
        )
        return False

    def _put_mapping(
        self,
        mapping: dict[str, NanoValue],
        key: str,
        value: NanoValue,
        line: _Line,
        start: int,
        *,
        valid_key: bool,
    ) -> None:
        if not valid_key:
            return
        if key in mapping:
            self.add_error(
                ErrorCode.DUPLICATE_KEY,
                f"duplicate mapping key {key!r}",
                line,
                start,
            )
            return
        mapping[key] = value

    def _mapping_entry(self, frame: _Frame, line: _Line, text: str, start: int) -> _Frame | None:
        mapping = cast(dict[str, NanoValue], frame.value)
        child_kind: Literal["mapping", "sequence"] | None = None
        key: str
        value: NanoValue

        if text.endswith("..") and " " not in text:
            key = text[:-2]
            value = {}
            child_kind = "mapping"
        elif text.endswith(":") and " " not in text:
            key = text[:-1]
            value = []
            child_kind = "sequence"
        elif text.endswith(" |"):
            key = text[:-2]
            value = self._collect_multiline(frame.level)
        elif " " not in text:
            key = text
            value = ""
        else:
            key, scalar = text.split(" ", 1)
            value = self._parse_scalar(scalar, line, start + len(key) + 1)

        valid_key = self._check_key(key, line, start)
        self._put_mapping(mapping, key, value, line, start, valid_key=valid_key)
        if child_kind is not None:
            return _Frame(
                child_kind,
                frame.level + 1,
                cast(dict[str, NanoValue] | list[NanoValue], value),
            )
        return None

    def _sequence_entry(self, frame: _Frame, line: _Line, text: str, start: int) -> _Frame | None:
        sequence = cast(list[NanoValue], frame.value)
        if text == "..":
            child_mapping: dict[str, NanoValue] = {}
            sequence.append(child_mapping)
            return _Frame("mapping", frame.level + 1, child_mapping)
        if text == ":":
            child_sequence: list[NanoValue] = []
            sequence.append(child_sequence)
            return _Frame("sequence", frame.level + 1, child_sequence)
        if text == "|":
            sequence.append(self._collect_multiline(frame.level))
            return None
        if text.startswith("#"):
            # Comments are normally removed by _skip_ignored; this is defensive.
            return None
        sequence.append(self._parse_scalar(text, line, start))
        return None

    def _parse_container(self, root: _Frame) -> None:
        stack = [root]
        while stack and self.index < len(self.lines):
            self._skip_ignored()
            if self.index >= len(self.lines):
                break
            line = self.lines[self.index]
            parts = self._line_parts(line)
            if parts is None:
                self.index += 1
                continue
            level, text = parts
            frame = stack[-1]
            if level < frame.level:
                stack.pop()
                continue
            if level > frame.level:
                self.add_error(
                    ErrorCode.INDENT,
                    "unexpected or skipped indentation level",
                    line,
                    line.leading_spaces,
                )
                self.index += 1
                continue

            self.index += 1
            start = line.leading_spaces
            if frame.kind == "mapping":
                child = self._mapping_entry(frame, line, text, start)
            else:
                child = self._sequence_entry(frame, line, text, start)
            if child is not None:
                stack.append(child)

    def _parse_root(self) -> NanoValue:
        self._skip_ignored()
        if self.index >= len(self.lines):
            return {}

        line = self.lines[self.index]
        parts = self._line_parts(line)
        if parts is None:
            level, text = line.leading_spaces // 4, line.text.lstrip(" ")
        else:
            level, text = parts
        if level != 0:
            self.add_error(
                ErrorCode.INDENT,
                "the document root must begin at indentation level zero",
                line,
                line.leading_spaces,
            )
        self.index += 1

        if text == "..":
            mapping: dict[str, NanoValue] = {}
            self._parse_container(_Frame("mapping", 1, mapping))
            return mapping
        if text == ":":
            sequence: list[NanoValue] = []
            self._parse_container(_Frame("sequence", 1, sequence))
            return sequence
        if text == "|":
            return self._collect_multiline(level)
        return self._parse_scalar(text, line, line.leading_spaces)

    def parse(self) -> NanoValue:
        value = self._parse_root()
        while self.index < len(self.lines):
            self._skip_ignored()
            if self.index >= len(self.lines):
                break
            line = self.lines[self.index]
            parts = self._line_parts(line)
            if parts is None:
                self.index += 1
                continue
            level, _ = parts
            if level:
                self.add_error(
                    ErrorCode.INDENT,
                    "unexpected indentation after the document root",
                    line,
                    line.leading_spaces,
                )
            else:
                self.add_error(
                    ErrorCode.SYNTAX,
                    "a document must contain exactly one root value",
                    line,
                    0,
                )
            self.index += 1

        if self.diagnostics:
            diagnostic = min(
                self.diagnostics,
                key=lambda item: (_ERROR_PRIORITY[item.code], item.byte_offset),
            )
            raise DecodeError(
                diagnostic.code,
                diagnostic.message,
                byte_offset=diagnostic.byte_offset,
                line=diagnostic.line,
                column=diagnostic.column,
            )
        return value


def loads(source: str | bytes | bytearray | memoryview) -> NanoValue:
    """Decode one Nano Markup document from text or raw UTF-8 bytes."""

    data, _ = _validate_and_decode(source)
    return _Parser(data, _physical_lines(data)).parse()


def load(stream: TextIO | BinaryIO) -> NanoValue:
    """Decode one Nano Markup document from an open text or binary stream."""

    source = stream.read()
    if not isinstance(source, (str, bytes, bytearray, memoryview)):
        raise TypeError("stream.read() must return str or bytes")
    return loads(source)

