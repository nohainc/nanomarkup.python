"""Python support for the Nano Markup data format."""

from ._version import SPEC_VERSION, __version__
from .decoder import load, loads
from .encoder import dump, dumps
from .errors import DecodeError, EncodeError, ErrorCode, NanoMarkupError
from .types import NanoValue

__all__ = [
    "SPEC_VERSION",
    "DecodeError",
    "EncodeError",
    "ErrorCode",
    "NanoMarkupError",
    "NanoValue",
    "__version__",
    "dump",
    "dumps",
    "load",
    "loads",
]
