from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from nanomarkup import DecodeError, loads

ROOT = Path(__file__).resolve().parents[1]
SPEC_TESTS = ROOT / "spec" / "tests"
MANIFEST = json.loads((SPEC_TESTS / "manifest.json").read_text(encoding="utf-8"))


class ConformanceTests(unittest.TestCase):
    def test_valid_fixtures(self) -> None:
        for case in MANIFEST["valid"]:
            with self.subTest(source=case["source"]):
                source = (SPEC_TESTS / case["source"]).read_bytes()
                expected = json.loads(
                    (SPEC_TESTS / case["expected"]).read_text(encoding="utf-8")
                )
                self.assertEqual(loads(source), expected)

    def test_invalid_fixtures(self) -> None:
        for case in MANIFEST["invalid"]:
            with self.subTest(source=case["source"]):
                with self.assertRaises(DecodeError) as raised:
                    loads((SPEC_TESTS / case["source"]).read_bytes())
                self.assertEqual(raised.exception.code.value, case["error"])

    def test_protocol_adapter(self) -> None:
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(ROOT / "src")
        cases = [MANIFEST["valid"][0], MANIFEST["invalid"][0]]
        for case in cases:
            fixture = SPEC_TESTS / case["source"]
            with self.subTest(source=case["source"]):
                result = subprocess.run(
                    [sys.executable, str(ROOT / "tests" / "adapter.py"), "parse", str(fixture)],
                    check=False,
                    capture_output=True,
                    text=True,
                    env=environment,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                payload = json.loads(result.stdout)
                if "expected" in case:
                    self.assertEqual(payload, {"ok": True, "value": loads(fixture.read_bytes())})
                else:
                    self.assertEqual(payload, {"ok": False, "error": case["error"]})


if __name__ == "__main__":
    unittest.main()

