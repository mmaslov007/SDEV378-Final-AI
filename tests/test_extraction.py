import unittest

from study_assistant.extraction import (
    extract_from_bytes,
    extract_from_plain_text,
    get_tesseract_command,
    is_tesseract_available,
    normalize_text,
)


class ExtractionTests(unittest.TestCase):
    def test_normalize_text_preserves_paragraph_breaks(self):
        text = " First   line \r\n\r\n\r\n Second\tline "

        self.assertEqual(normalize_text(text), "First line\n\nSecond line")

    def test_extract_from_plain_text_reports_character_count(self):
        result = extract_from_plain_text("Embeddings find related ideas.", "notes")

        self.assertTrue(result.has_text)
        self.assertEqual(result.source_type, "text")
        self.assertEqual(result.metadata["characters"], len(result.text))

    def test_extract_text_file_from_bytes(self):
        result = extract_from_bytes("study_notes.txt", b"OCR reads images.\nEmbeddings search text.")

        self.assertEqual(result.source_name, "study_notes.txt")
        self.assertIn("Embeddings search text.", result.text)
        self.assertEqual(result.warnings, [])

    def test_unsupported_file_type_returns_warning(self):
        result = extract_from_bytes("archive.zip", b"PK")

        self.assertFalse(result.has_text)
        self.assertEqual(result.source_type, "unsupported")
        self.assertIn("Unsupported file type", result.warnings[0])

    def test_tesseract_probe_returns_boolean(self):
        self.assertIsInstance(is_tesseract_available(), bool)

    def test_tesseract_command_probe_returns_string_or_none(self):
        command = get_tesseract_command()

        self.assertTrue(command is None or isinstance(command, str))


if __name__ == "__main__":
    unittest.main()
