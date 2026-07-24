# Releasing

1. Confirm the pinned `spec` submodule is the intended immutable specification
   tag and that `SPEC_VERSION` names that exact version.
2. Set `__version__`, update `CHANGELOG.md`, and run `pytest`, `ruff check .`,
   `mypy`, `python -m build`, and `python -m twine check dist/*`.
3. Merge the reviewed release pull request only after every required check
   passes.
4. Create and push an annotated tag named `vX.Y.Z` on the reviewed merge
   commit. The tag must exactly match `__version__`.
5. Review the release workflow's built wheel, source distribution, metadata,
   and checksums. Approve the protected `pypi` environment only when they are
   correct.
6. Verify the PyPI project, install from PyPI in a clean environment, run
   `nanomarkup --version`, and verify the generated GitHub release.

The PyPI project must have a Trusted Publisher for repository
`nohainc/nanomarkup.python`, workflow `release.yml`, environment `pypi`. Never
store a long-lived PyPI token in GitHub.
