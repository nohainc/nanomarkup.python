"""Public type definitions."""

from typing import TypeAlias

NanoValue: TypeAlias = str | dict[str, "NanoValue"] | list["NanoValue"]

