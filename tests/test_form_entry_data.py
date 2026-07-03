"""Tests for serializing file fields into FormEntry JSON."""

import tempfile
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from djangocms_form_builder.entry_model import FormEntry
from djangocms_form_builder.form_entry_data import serialize_cleaned_data_for_entry


class SerializeCleanedDataTests(TestCase):
    def test_passes_through_non_files(self):
        data = serialize_cleaned_data_for_entry({"a": "text", "b": 1})
        self.assertEqual(data, {"a": "text", "b": 1})

    def test_passes_through_non_file_lists(self):
        cleaned_data = {"choices": ["a", "b"]}
        data = serialize_cleaned_data_for_entry(cleaned_data)
        self.assertEqual(data, cleaned_data)

    def test_stores_upload_metadata(self):
        with self.settings(MEDIA_ROOT=tempfile.mkdtemp()):
            f = SimpleUploadedFile("note.txt", b"hello", content_type="text/plain")
            data = serialize_cleaned_data_for_entry({"attachment": f})
            self.assertIn("attachment", data)
            meta = data["attachment"]
            self.assertTrue(meta["_form_builder_file"])
            self.assertEqual(meta["filename"], "note.txt")
            self.assertIn("url", meta)
            self.assertIn("name", meta)
            self.assertTrue(meta["name"].startswith("form_uploads/"))
            self.assertNotIn("path", meta)

    def test_stores_multiple_uploads(self):
        with self.settings(MEDIA_ROOT=tempfile.mkdtemp()):
            a = SimpleUploadedFile("a.txt", b"a", content_type="text/plain")
            b = SimpleUploadedFile("b.txt", b"b", content_type="text/plain")
            data = serialize_cleaned_data_for_entry({"files": [a, b]})
            self.assertEqual(len(data["files"]), 2)
            self.assertTrue(data["files"][0]["_form_builder_file"])
            self.assertIn("name", data["files"][0])
            self.assertNotIn("path", data["files"][0])


class DeleteEntryFilesTests(TestCase):
    @patch("djangocms_form_builder.entry_model.FILE_FIELD_STORAGE")
    def test_delete_entry_calls_storage_delete_for_single_file(self, mock_storage):
        entry = FormEntry.objects.create(
            form_name="upload",
            entry_data={
                "doc": {
                    "_form_builder_file": True,
                    "filename": "a.pdf",
                    "name": "form_uploads/abc_a.pdf",
                    "url": "/media/form_uploads/abc_a.pdf",
                },
            },
        )
        entry.delete()
        mock_storage.delete.assert_called_once_with("form_uploads/abc_a.pdf")

    @patch("djangocms_form_builder.entry_model.FILE_FIELD_STORAGE")
    def test_delete_entry_calls_storage_delete_for_each_multi_file(self, mock_storage):
        entry = FormEntry.objects.create(
            form_name="upload",
            entry_data={
                "files": [
                    {
                        "_form_builder_file": True,
                        "filename": "a.pdf",
                        "name": "form_uploads/a.pdf",
                        "url": "/media/form_uploads/a.pdf",
                    },
                    {
                        "_form_builder_file": True,
                        "filename": "b.pdf",
                        "name": "form_uploads/b.pdf",
                        "url": "/media/form_uploads/b.pdf",
                    },
                ],
            },
        )
        entry.delete()
        self.assertEqual(mock_storage.delete.call_count, 2)
        mock_storage.delete.assert_any_call("form_uploads/a.pdf")
        mock_storage.delete.assert_any_call("form_uploads/b.pdf")
