"""Tests for serializing file fields into FormEntry JSON."""

import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from djangocms_form_builder.form_entry_data import serialize_cleaned_data_for_entry


class SerializeCleanedDataTests(TestCase):
    def test_passes_through_non_files(self):
        data = serialize_cleaned_data_for_entry({"a": "text", "b": 1})
        self.assertEqual(data, {"a": "text", "b": 1})

    def test_stores_upload_metadata(self):
        with self.settings(MEDIA_ROOT=tempfile.mkdtemp()):
            f = SimpleUploadedFile("note.txt", b"hello", content_type="text/plain")
            data = serialize_cleaned_data_for_entry({"attachment": f})
            self.assertIn("attachment", data)
            meta = data["attachment"]
            self.assertTrue(meta["_form_builder_file"])
            self.assertEqual(meta["filename"], "note.txt")
            self.assertIn("url", meta)

    def test_stores_multiple_uploads(self):
        with self.settings(MEDIA_ROOT=tempfile.mkdtemp()):
            a = SimpleUploadedFile("a.txt", b"a", content_type="text/plain")
            b = SimpleUploadedFile("b.txt", b"b", content_type="text/plain")
            data = serialize_cleaned_data_for_entry({"files": [a, b]})
            self.assertEqual(len(data["files"]), 2)
            self.assertTrue(data["files"][0]["_form_builder_file"])
