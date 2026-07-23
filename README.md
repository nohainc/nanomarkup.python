# Nano Markup for Python

`nanomarkup` is a zero-runtime-dependency Python parser and serializer for
[Nano Markup](https://github.com/nohainc/nanomarkup.spec), a minimal,
human-readable structured data format.

> [!IMPORTANT]
> This release implements **Nano Markup 0.5-draft**. The language is unstable
> and may change incompatibly before 1.0. This package does not claim
> conformance to a stable Nano Markup standard.

## Installation

```console
python -m pip install nanomarkup
```

Python 3.11 or later is required.

## Python API

Nano Markup values map directly to Python values:

| Nano Markup | Python |
| --- | --- |
| String | `str` |
| Mapping | `dict[str, NanoValue]` |
| Sequence | `list[NanoValue]` |

All scalars remain strings. The decoder never infers numbers, booleans, nulls,
dates, or application-specific types.

```python
import nanomarkup

document = """\
..
    name Ariana
    age 12
    interests:
        cycling
        music
"""

value = nanomarkup.loads(document)
assert value == {
    "name": "Ariana",
    "age": "12",
    "interests": ["cycling", "music"],
}

encoded = nanomarkup.dumps(value)
assert nanomarkup.loads(encoded) == value

assert nanomarkup.__version__ == "0.1.0"
assert nanomarkup.SPEC_VERSION == "0.5-draft"
```

The API follows Python's standard serialization naming convention:

- `loads(source)` decodes a `str`, `bytes`, `bytearray`, or `memoryview`.
- `load(stream)` decodes an open text or binary stream.
- `dumps(value)` returns a Nano Markup string.
- `dump(value, stream)` writes to an open text stream.

Use binary input when decoding files so invalid UTF-8 can be diagnosed by the
Nano Markup decoder:

```python
with open("settings.nano", "rb") as source:
    settings = nanomarkup.load(source)

with open("settings.nano", "w", encoding="utf-8", newline="") as destination:
    nanomarkup.dump(settings, destination, newline="\n")
```

`dumps` and `dump` accept `newline="\n"` (the default) or
`newline="\r\n"`. Writer output does not end with an automatic final newline.
Mapping insertion order is retained for readability, although mapping order is
not part of the Nano Markup data model.

### Errors

Invalid input raises `DecodeError`, which provides the stable specification
category and source location:

```python
try:
    nanomarkup.loads(b"..\n   bad indentation")
except nanomarkup.DecodeError as error:
    print(error.code.value)   # E_INDENT
    print(error.byte_offset) # zero-based UTF-8 byte offset
    print(error.line)        # one-based line
    print(error.column)      # one-based Unicode column
```

Values outside the Nano Markup data model, invalid mapping keys, forbidden
characters, and cyclic containers raise `EncodeError`.

## Validator

Validate one or more files with the installed command:

```console
nanomarkup settings.nano other.nano
nanomarkup - < settings.nano
python -m nanomarkup settings.nano
nanomarkup --version
```

Each valid input is reported on standard output. Diagnostics use
`path:line:column: CODE: message` on standard error. Exit status is `0` when
all inputs are valid, `1` when a document is invalid, and `2` for usage or I/O
errors.

## Conformance and development

The `spec` Git submodule pins the official conformance suite at commit
`c36a19dd69aeb523350c9e725fa4f09045507ad0` (Nano Markup 0.5-draft).

```console
git clone --recurse-submodules https://github.com/nohainc/nanomarkup.python.git
cd nanomarkup.python
python -m pip install -e ".[dev]"
pytest
ruff check .
mypy
```

See [CHANGELOG.md](CHANGELOG.md) for release history.

### Publishing

Releases are built and published from tags matching the package version, such
as `v0.1.0`. Before the first release, configure a PyPI Trusted Publisher for
the `nohainc/nanomarkup.python` repository, workflow `release.yml`, and GitHub
environment `pypi`. Require manual approval for that environment. The workflow
uses short-lived OpenID Connect credentials and does not require a stored PyPI
API token.

The implementation provides data decoding and writing only. Comments,
whitespace, quote choice, source line endings, and mapping source order are
presentation metadata and are not preserved. There is no source-preserving
document API, schema system, implicit type conversion, or executable syntax.

No explicit parser resource caps are imposed. Applications accepting
untrusted documents should bound input size according to their environment.

## License

The Python implementation is licensed under the [MIT License](LICENSE).

The specification submodule and its conformance materials are separate works
licensed under the [Creative Commons Attribution 4.0 International License](https://github.com/nohainc/nanomarkup.spec/blob/c36a19dd69aeb523350c9e725fa4f09045507ad0/LICENSE).
See [NOTICE.md](NOTICE.md) for attribution and the pinned source revision.
