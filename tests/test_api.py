from __future__ import annotations

import contextlib
import io
import random
import unittest

import nanomarkup


class DecoderApiTests(unittest.TestCase):
    def test_unicode_whitespace_is_string_data(self) -> None:
        whitespace = [
            character
            for codepoint in range(0x110000)
            if not (0xD800 <= codepoint <= 0xDFFF)
            and (character := chr(codepoint)).isspace()
            and codepoint
            not in {
                *range(0x00, 0x09),
                0x0B,
                0x0C,
                *range(0x0E, 0x20),
                *range(0x7F, 0xA0),
            }
            and character not in {"\t", "\n", "\r", " "}
        ]
        self.assertEqual(len(whitespace), 18)
        for character in whitespace:
            with self.subTest(codepoint=f"U+{ord(character):04X}"):
                self.assertEqual(nanomarkup.loads(character), character)
                self.assertEqual(nanomarkup.loads(nanomarkup.dumps(character)), character)
                self.assertEqual(nanomarkup.loads(f":\n    {character}"), [character])
                self.assertEqual(nanomarkup.loads(f"|\n    {character}"), character)

    def test_public_version_information(self) -> None:
        self.assertEqual(nanomarkup.__version__, "0.1.0")
        self.assertEqual(nanomarkup.SPEC_VERSION, "1.0.0-rc.1")

    def test_input_forms_and_streams(self) -> None:
        source = b"..\n    city Bratislava"
        expected = {"city": "Bratislava"}
        self.assertEqual(nanomarkup.loads(source), expected)
        self.assertEqual(nanomarkup.loads(bytearray(source)), expected)
        self.assertEqual(nanomarkup.loads(memoryview(source)), expected)
        self.assertEqual(nanomarkup.loads(source.decode()), expected)
        self.assertEqual(nanomarkup.load(io.BytesIO(source)), expected)
        self.assertEqual(nanomarkup.load(io.StringIO(source.decode())), expected)

    def test_diagnostic_attributes(self) -> None:
        with self.assertRaises(nanomarkup.DecodeError) as raised:
            nanomarkup.loads(b"..\n    value ")
        error = raised.exception
        self.assertEqual(error.code, nanomarkup.ErrorCode.STRING)
        self.assertEqual((error.line, error.column, error.byte_offset), (2, 11, 13))
        self.assertIn("E_STRING at 2:11", str(error))

    def test_error_category_precedence(self) -> None:
        source = b'..\n    value "bad\\q"\n      # later indentation error\n'
        with self.assertRaises(nanomarkup.DecodeError) as raised:
            nanomarkup.loads(source)
        self.assertEqual(raised.exception.code, nanomarkup.ErrorCode.INDENT)

    def test_earliest_error_within_category(self) -> None:
        source = b'..\n    first "bad\\q"\n    second "also\\z"\n'
        with self.assertRaises(nanomarkup.DecodeError) as raised:
            nanomarkup.loads(source)
        self.assertEqual(raised.exception.code, nanomarkup.ErrorCode.ESCAPE)
        self.assertEqual(raised.exception.line, 2)

    def test_arbitrary_bytes_never_escape_as_internal_errors(self) -> None:
        randomizer = random.Random(20260723)
        samples = [bytes([value]) for value in range(256)]
        samples.extend(randomizer.randbytes(randomizer.randrange(65)) for _ in range(1_000))
        for source in samples:
            with contextlib.suppress(nanomarkup.DecodeError):
                nanomarkup.loads(source)


class WriterApiTests(unittest.TestCase):
    def test_space_only_logical_lines_use_quoted_output(self) -> None:
        values = ["a\n \nb", "a\n   \nb", " \ntext", "text\n "]
        for value in values:
            with self.subTest(value=value):
                encoded = nanomarkup.dumps(value)
                self.assertTrue(encoded.startswith('"'))
                self.assertEqual(nanomarkup.loads(encoded), value)

    def test_round_trip_values(self) -> None:
        values: list[nanomarkup.NanoValue] = [
            "",
            "ordinary text",
            "..",
            "# heading",
            "first\n\nlast",
            "terminal newline\n",
            "tab\treturn\r",
            {"empty": "", "nested": {"age": "20"}, "items": ["one", "one", {}]},
            ["", "..", ":", "|", "# value", ["inner"]],
        ]
        for value in values:
            with self.subTest(value=value):
                self.assertEqual(nanomarkup.loads(nanomarkup.dumps(value)), value)

    def test_multiline_and_line_ending_output(self) -> None:
        value: nanomarkup.NanoValue = {"description": "first\nsecond", "status": "done"}
        lf = nanomarkup.dumps(value)
        crlf = nanomarkup.dumps(value, newline="\r\n")
        self.assertIn("description|\n        first", lf)
        self.assertNotIn("\r", lf)
        self.assertIn("\r\n", crlf)
        self.assertNotIn("\n", crlf.replace("\r\n", ""))
        self.assertFalse(lf.endswith("\n"))
        self.assertEqual(nanomarkup.loads(crlf), value)

    def test_mapping_pipe_header_and_scalar_boundary(self) -> None:
        source = "..\n    block|\n        first\n        second\n    marker |\n    suffix value |"
        self.assertEqual(
            nanomarkup.loads(source),
            {"block": "first\nsecond", "marker": "|", "suffix": "value |"},
        )
        self.assertEqual(nanomarkup.dumps({"marker": "|"}), "..\n    marker |")

    def test_dump_writes_text_stream(self) -> None:
        stream = io.StringIO()
        nanomarkup.dump(["one", "two"], stream)
        self.assertEqual(stream.getvalue(), ":\n    one\n    two")

    def test_rejects_values_outside_data_model(self) -> None:
        invalid: list[object] = [None, True, 1, 1.5, ("item",), {"bad key": "value"}, "bad\x00"]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(nanomarkup.EncodeError):
                nanomarkup.dumps(value)  # type: ignore[arg-type]

    def test_rejects_cycles_but_accepts_shared_values(self) -> None:
        cycle: list[nanomarkup.NanoValue] = []
        cycle.append(cycle)
        with self.assertRaises(nanomarkup.EncodeError):
            nanomarkup.dumps(cycle)

        shared: list[nanomarkup.NanoValue] = ["value"]
        value: list[nanomarkup.NanoValue] = [shared, shared]
        self.assertEqual(nanomarkup.loads(nanomarkup.dumps(value)), value)

    def test_rejects_invalid_newline(self) -> None:
        with self.assertRaises(ValueError):
            nanomarkup.dumps("value", newline="\r")  # type: ignore[arg-type]

    def test_generated_recursive_round_trips(self) -> None:
        randomizer = random.Random(20260723)
        strings = [
            "",
            "plain",
            " spaced ",
            "..",
            ":",
            "|",
            "# comment-like",
            "Žilina 🚲",
            "first\nsecond",
            "first\n\nlast",
            "terminal\n",
            "tab\tcarriage\r",
        ]

        def generate(depth: int) -> nanomarkup.NanoValue:
            if depth == 0 or randomizer.random() < 0.45:
                return randomizer.choice(strings)
            if randomizer.random() < 0.5:
                return [generate(depth - 1) for _ in range(randomizer.randrange(5))]
            return {f"key-{index}": generate(depth - 1) for index in range(randomizer.randrange(5))}

        for _ in range(200):
            value = generate(4)
            self.assertEqual(nanomarkup.loads(nanomarkup.dumps(value)), value)

    def test_deep_nesting_does_not_use_python_recursion(self) -> None:
        depth = 1_100
        value: nanomarkup.NanoValue = "leaf"
        for _ in range(depth):
            value = [value]
        decoded = nanomarkup.loads(nanomarkup.dumps(value))
        for _ in range(depth):
            self.assertIsInstance(decoded, list)
            decoded = decoded[0]  # type: ignore[index]
        self.assertEqual(decoded, "leaf")


if __name__ == "__main__":
    unittest.main()
