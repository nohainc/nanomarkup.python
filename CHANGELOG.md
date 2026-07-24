# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

- Updated to Nano Markup 0.6-draft.
- Preserved strings containing space-only logical lines by selecting quoted
  output instead of multiline syntax.
- Added a runnable decoded-value example.

## [0.1.0] - 2026-07-23

- Added a Nano Markup 0.5-draft parser for strings, mappings, and sequences.
- Added deterministic specification error categories and source locations.
- Added `load`, `loads`, `dump`, and `dumps` APIs using Python-native values.
- Added a validation CLI and conformance protocol adapter.
- Added the pinned official specification and conformance suite.
- Added typed-package metadata, tests, documentation, and CI for Python 3.11–3.14.
- Correctly preserved all permitted Unicode whitespace as string data.
- Added writer protocol and cross-implementation conformance coverage.

[Unreleased]: https://github.com/nohainc/nanomarkup.python/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/nohainc/nanomarkup.python/releases/tag/v0.1.0
