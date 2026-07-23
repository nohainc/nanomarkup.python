from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_cli(*arguments: str, stdin: bytes | None = None) -> subprocess.CompletedProcess[bytes]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "nanomarkup", *arguments],
        input=stdin,
        capture_output=True,
        check=False,
        env=environment,
    )


class CliTests(unittest.TestCase):
    def test_valid_file_and_stdin(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "valid.nano"
            path.write_bytes(b"..\n    name Ariana")
            result = run_cli(str(path), "-", stdin=b":\n    one")
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        output = result.stdout.decode()
        self.assertIn(f"{path}: valid", output)
        self.assertIn("-: valid", output)

    def test_invalid_document(self) -> None:
        result = run_cli("-", stdin=b"..\n   bad indentation")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, b"")
        self.assertIn(b"-:2:4: E_INDENT:", result.stderr)

    def test_io_error(self) -> None:
        result = run_cli("does-not-exist.nano")
        self.assertEqual(result.returncode, 2)
        self.assertIn(b"does-not-exist.nano", result.stderr)


if __name__ == "__main__":
    unittest.main()

