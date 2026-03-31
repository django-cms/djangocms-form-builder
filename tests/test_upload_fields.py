"""Tests for ValidatedFileField and MultipleUploadedFilesField."""

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, SimpleTestCase, override_settings

from djangocms_form_builder.file_validation import FileValidationError
from djangocms_form_builder.upload_form_fields import (
    MultipleUploadedFilesField,
    ValidatedFileField,
)


def preset_accept(_uploaded_file, *, user, request, field_name):
    return None


def preset_reject(_uploaded_file, *, user, request, field_name):
    raise FileValidationError("no")


class ValidatedFileFieldTests(SimpleTestCase):
    @override_settings(
        DJANGOCMS_FORM_BUILDER_FILE_VALIDATION_PRESETS={
            "ok": {"label": "OK", "validate": f"{__name__}.preset_accept"},
        }
    )
    def test_clean_with_preset(self):
        f = SimpleUploadedFile("a.txt", b"x", content_type="text/plain")
        request = RequestFactory().get("/")
        field = ValidatedFileField(
            preset_keys=["ok"],
            user=None,
            request=request,
            field_name="f",
            required=False,
        )
        self.assertEqual(field.clean(f), f)

    @override_settings(
        DJANGOCMS_FORM_BUILDER_FILE_VALIDATION_PRESETS={
            "no": {"label": "No", "validate": f"{__name__}.preset_reject"},
        }
    )
    def test_clean_raises_when_preset_rejects(self):
        f = SimpleUploadedFile("a.txt", b"x", content_type="text/plain")
        request = RequestFactory().get("/")
        field = ValidatedFileField(
            preset_keys=["no"],
            user=None,
            request=request,
            field_name="f",
            required=True,
        )
        with self.assertRaises(FileValidationError):
            field.clean(f)

    @override_settings(
        DJANGOCMS_FORM_BUILDER_FILE_VALIDATION_PRESETS={
            "ext": {
                "label": "PDF/DOC",
                "validate": (
                    "djangocms_form_builder.file_validation_validators."
                    "ExtensionPresetValidator"
                ),
                "validate_options": {"allowed_extensions": [".pdf", "doc"]},
            },
        }
    )
    def test_widget_sets_accept_from_extension_preset(self):
        request = RequestFactory().get("/")
        field = ValidatedFileField(
            preset_keys=["ext"],
            user=None,
            request=request,
            field_name="f",
            required=False,
        )
        self.assertEqual(field.widget.attrs["accept"], ".doc,.pdf")

    @override_settings(
        DJANGOCMS_FORM_BUILDER_FILE_VALIDATION_PRESETS={
            "narrow": {
                "label": "PDF only",
                "validate": (
                    "djangocms_form_builder.file_validation_validators."
                    "ExtensionPresetValidator"
                ),
                "validate_options": {"allowed_extensions": [".pdf"]},
            },
            "wide": {
                "label": "PDF or DOC",
                "validate": (
                    "djangocms_form_builder.file_validation_validators."
                    "ExtensionPresetValidator"
                ),
                "validate_options": {"allowed_extensions": [".pdf", ".doc"]},
            },
        }
    )
    def test_widget_accept_intersects_multiple_extension_presets(self):
        request = RequestFactory().get("/")
        field = ValidatedFileField(
            preset_keys=["wide", "narrow"],
            user=None,
            request=request,
            field_name="f",
            required=False,
        )
        self.assertEqual(field.widget.attrs["accept"], ".pdf")


class MultipleUploadedFilesFieldTests(SimpleTestCase):
    def test_clean_optional_allows_empty(self):
        field = MultipleUploadedFilesField(
            preset_keys=[],
            user=None,
            request=None,
            field_name="f",
            required=False,
        )
        self.assertEqual(field.clean(None), [])
        self.assertEqual(field.clean([]), [])

    def test_clean_required_rejects_empty(self):
        field = MultipleUploadedFilesField(
            preset_keys=[],
            user=None,
            request=None,
            field_name="f",
            required=True,
        )
        required_message = str(field.error_messages["required"])
        with self.assertRaisesMessage(ValidationError, required_message):
            field.clean(None)
        with self.assertRaisesMessage(ValidationError, required_message):
            field.clean([])

    @override_settings(
        DJANGOCMS_FORM_BUILDER_FILE_VALIDATION_PRESETS={
            "ok": {"label": "OK", "validate": f"{__name__}.preset_accept"},
        }
    )
    def test_clean_validates_each_file(self):
        a = SimpleUploadedFile("a.txt", b"x", content_type="text/plain")
        b = SimpleUploadedFile("b.txt", b"y", content_type="text/plain")
        request = RequestFactory().get("/")
        field = MultipleUploadedFilesField(
            preset_keys=["ok"],
            user=None,
            request=request,
            field_name="f",
            required=True,
        )
        out = field.clean([a, b])
        self.assertEqual(len(out), 2)

    @override_settings(
        DJANGOCMS_FORM_BUILDER_FILE_VALIDATION_PRESETS={
            "ext": {
                "label": "PDF",
                "validate": (
                    "djangocms_form_builder.file_validation_validators."
                    "ExtensionPresetValidator"
                ),
                "validate_options": {"allowed_extensions": [".pdf"]},
            },
        }
    )
    def test_multi_widget_sets_accept(self):
        request = RequestFactory().get("/")
        field = MultipleUploadedFilesField(
            preset_keys=["ext"],
            user=None,
            request=request,
            field_name="f",
            required=False,
        )
        self.assertEqual(field.widget.attrs.get("accept"), ".pdf")
        self.assertEqual(field.widget.attrs.get("multiple"), True)
