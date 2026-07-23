"""Python support for the Nano Markup data format."""

from .decoder import load, loads
from .encoder import dump, dumps
from .errors import DecodeError, EncodeError, ErrorCode, NanoMarkupError
from .types import NanoValue

__all__ = [
    "DecodeError",
    "EncodeError",
    "ErrorCode",
    "NanoMarkupError",
    "NanoValue",
    "dump",
    "dumps",
    "load",
    "loads",
]

__version__ = "0.1.0"

