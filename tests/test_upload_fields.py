"""Tests for ValidatedFileField and MultipleUploadedFilesField."""

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, override_settings
from django.utils.datastructures import MultiValueDict

from djangocms_form_builder.file_validation import FileValidationError
from djangocms_form_builder.forms import SimpleFrontendForm
from djangocms_form_builder.upload_form_fields import (
    MultipleUploadedFilesField,
    ValidatedFileField,
)


def preset_accept(_uploaded_file, *, user, request, field_name):
    return None


def preset_reject(_uploaded_file, *, user, request, field_name):
    raise FileValidationError("no")


class ValidatedFileFieldTests(TestCase):
    @override_settings(
        DJANGOCMS_FORM_BUILDER_FILE_VALIDATION_PRESETS={
            "ok": {"label": "OK", "validate": f"{__name__}.preset_accept"},
        }
    )
    def test_clean_with_preset(self):
        f = SimpleUploadedFile("a.txt", b"x", content_type="text/plain")
        field = ValidatedFileField(
            preset_keys=["ok"],
            field_name="f",
            required=False,
        )
        self.assertEqual(field.clean(f), f)

    @override_settings(
        DJANGOCMS_FORM_BUILDER_FILE_VALIDATION_PRESETS={
            "ext": {
                "label": "PDF/DOC",
                "validate": f"{__name__}.preset_accept",
                "accept_extensions": [".pdf", "doc"],
            },
        }
    )
    def test_widget_sets_accept_from_extension_preset(self):
        field = ValidatedFileField(
            preset_keys=["ext"],
            field_name="f",
            required=False,
        )
        self.assertEqual(field.widget.attrs["accept"], ".doc,.pdf")

    @override_settings(
        DJANGOCMS_FORM_BUILDER_FILE_VALIDATION_PRESETS={
            "narrow": {
                "label": "PDF only",
                "validate": f"{__name__}.preset_accept",
                "accept_extensions": [".pdf"],
            },
            "wide": {
                "label": "PDF or DOC",
                "validate": f"{__name__}.preset_accept",
                "accept_extensions": [".pdf", ".doc"],
            },
        }
    )
    def test_widget_accept_intersects_multiple_extension_presets(self):
        field = ValidatedFileField(
            preset_keys=["wide", "narrow"],
            field_name="f",
            required=False,
        )
        self.assertEqual(field.widget.attrs["accept"], ".pdf")


class MultipleUploadedFilesFieldTests(TestCase):
    def test_clean_optional_allows_empty(self):
        field = MultipleUploadedFilesField(
            preset_keys=[],
            field_name="f",
            required=False,
        )
        self.assertEqual(field.clean(None), [])
        self.assertEqual(field.clean([]), [])

    def test_clean_required_rejects_empty(self):
        field = MultipleUploadedFilesField(
            preset_keys=[],
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
        field = MultipleUploadedFilesField(
            preset_keys=["ok"],
            field_name="f",
            required=True,
        )
        out = field.clean([a, b])
        self.assertEqual(len(out), 2)

    @override_settings(
        DJANGOCMS_FORM_BUILDER_FILE_VALIDATION_PRESETS={
            "ext": {
                "label": "PDF",
                "validate": f"{__name__}.preset_accept",
                "accept_extensions": [".pdf"],
            },
        }
    )
    def test_multi_widget_sets_accept(self):
        field = MultipleUploadedFilesField(
            preset_keys=["ext"],
            field_name="f",
            required=False,
        )
        self.assertEqual(field.widget.attrs.get("accept"), ".pdf")
        self.assertEqual(field.widget.attrs.get("multiple"), True)


class FormLevelUploadValidationTests(TestCase):
    @override_settings(
        DJANGOCMS_FORM_BUILDER_FILE_VALIDATION_PRESETS={
            "reject": {"label": "No", "validate": f"{__name__}.preset_reject"},
            "ok": {"label": "OK", "validate": f"{__name__}.preset_accept"},
        }
    )
    def test_simple_frontend_form_validates_file_field(self):
        class UploadForm(SimpleFrontendForm):
            attachment = ValidatedFileField(
                preset_keys=["reject"],
                field_name="attachment",
                required=True,
            )

            class Meta:
                options = {"login_required": False}

        request = RequestFactory().post("/")
        request.user = None
        form = UploadForm(
            data={},
            files=MultiValueDict({"attachment": [SimpleUploadedFile("a.txt", b"x")]}),
            request=request,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("attachment", form.errors)

    @override_settings(
        DJANGOCMS_FORM_BUILDER_FILE_VALIDATION_PRESETS={
            "reject": {"label": "No", "validate": f"{__name__}.preset_reject"},
        }
    )
    def test_simple_frontend_form_validates_multiple_file_field(self):
        class UploadForm(SimpleFrontendForm):
            attachments = MultipleUploadedFilesField(
                preset_keys=["reject"],
                field_name="attachments",
                required=False,
            )

            class Meta:
                options = {"login_required": False}

        request = RequestFactory().post("/")
        request.user = None
        files = [SimpleUploadedFile("a.txt", b"x"), SimpleUploadedFile("b.txt", b"y")]
        form = UploadForm(
            data={},
            files=MultiValueDict({"attachments": files}),
            request=request,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("attachments", form.errors)
