# Contributing

Bug reports and focused pull requests are welcome. For behavior changes, first
check whether the requested behavior is allowed by the stable Nano Markup
specification. Language changes belong in the specification repository.

Set up a development environment and run the complete checks:

```console
git clone --recurse-submodules https://github.com/nohainc/nanomarkup.python.git
cd nanomarkup.python
python -m pip install -e ".[dev]"
pytest
ruff check .
mypy
python -m build
python -m twine check dist/*
```

Add tests for every behavior change. Keep public API compatibility unless the
change is explicitly approved for a major release. All changes are submitted
through pull requests and require owner review.
