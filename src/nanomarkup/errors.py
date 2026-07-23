"""Exceptions and stable Nano Markup error categories."""

from __future__ import annotations

from enum import StrEnum


class ErrorCode(StrEnum):
    """Stable decoder error categories from Nano Markup 0.5-draft."""

    ENCODING = "E_ENCODING"
    TAB = "E_TAB"
    INDENT = "E_INDENT"
    SYNTAX = "E_SYNTAX"
    KEY = "E_KEY"
    DUPLICATE_KEY = "E_DUPLICATE_KEY"
    ESCAPE = "E_ESCAPE"
    STRING = "E_STRING"


class NanoMarkupError(ValueError):
    """Base class for Nano Markup errors."""


class DecodeError(NanoMarkupError):
    """A source document could not be decoded."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        byte_offset: int,
        line: int,
        column: int,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.byte_offset = byte_offset
        self.line = line
        self.column = column

    def __str__(self) -> str:
        return f"{self.code.value} at {self.line}:{self.column}: {self.message}"


class EncodeError(NanoMarkupError):
    """A Python value cannot be represented by Nano Markup."""
