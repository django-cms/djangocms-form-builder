"""Tests for file upload validation presets."""

from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings

from djangocms_form_builder.file_validation import (
    FileValidationError,
    validate_form_builder_file,
)
from djangocms_form_builder.file_validation_validators import (
    enforce_extension,
    enforce_max_size,
    enforce_mime_from_filename,
)


def preset_accept(_uploaded_file, *, user, request, field_name):
    """Test preset that allows any upload."""
    return None


def preset_reject(_uploaded_file, *, user, request, field_name):
    raise FileValidationError("Rejected by test preset.")


def filer_style_stub(file_name, file, owner, mime_type):
    """django-filer-style signature; records last call on the function."""
    filer_style_stub.last_call = (file_name, file, owner, mime_type)


def filer_style_reject(file_name, file, owner, mime_type):
    raise ValidationError("filer says no")


class DummyClassValidator:
    pass


class ValidateFormBuilderFileTests(SimpleTestCase):
    def test_empty_preset_keys_runs_nothing(self):
        f = SimpleUploadedFile("a.txt", b"hello", content_type="text/plain")
        validate_form_builder_file(
            f,
            [],
            user=None,
            request=None,
            field_name="doc",
        )

    @override_settings(
        DJANGOCMS_FORM_BUILDER_FILE_VALIDATION_PRESETS={
            "ok": {"label": "OK", "validate": f"{__name__}.preset_accept"},
        }
    )
    def test_preset_runs_callable(self):
        f = SimpleUploadedFile("a.txt", b"hello", content_type="text/plain")
        validate_form_builder_file(
            f,
            ["ok"],
            user=None,
            request=None,
            field_name="doc",
        )

    @override_settings(
        DJANGOCMS_FORM_BUILDER_FILE_VALIDATION_PRESETS={
            "no": {"label": "No", "validate": f"{__name__}.preset_reject"},
        }
    )
    def test_preset_raises_file_validation_error(self):
        f = SimpleUploadedFile("a.txt", b"hello", content_type="text/plain")
        with self.assertRaises(FileValidationError):
            validate_form_builder_file(
                f,
                ["no"],
                user=None,
                request=None,
                field_name="doc",
            )

    @override_settings(
        DJANGOCMS_FORM_BUILDER_FILE_VALIDATION_PRESETS={
            "first": {"label": "A", "validate": f"{__name__}.preset_accept"},
            "second": {"label": "B", "validate": f"{__name__}.preset_reject"},
        }
    )
    def test_multiple_keys_run_in_order(self):
        f = SimpleUploadedFile("a.txt", b"hello", content_type="text/plain")
        with self.assertRaises(FileValidationError):
            validate_form_builder_file(
                f,
                ["first", "second"],
                user=None,
                request=None,
                field_name="doc",
            )

    @override_settings(
        DJANGOCMS_FORM_BUILDER_FILE_VALIDATION_PRESETS={
            "small": {
                "label": "Small files only",
                "validate": (
                    "djangocms_form_builder.file_validation_validators."
                    "MaxSizePresetValidator"
                ),
                "validate_options": {"max_bytes": 5},
            },
        }
    )
    def test_class_preset_with_validate_options(self):
        f = SimpleUploadedFile("a.txt", b"hello world", content_type="text/plain")
        with self.assertRaises(FileValidationError):
            validate_form_builder_file(
                f,
                ["small"],
                user=None,
                request=None,
                field_name="doc",
            )
        ok = SimpleUploadedFile("b.txt", b"hi", content_type="text/plain")
        validate_form_builder_file(
            ok,
            ["small"],
            user=None,
            request=None,
            field_name="doc",
        )

    @override_settings(
        DJANGOCMS_FORM_BUILDER_FILE_VALIDATION_PRESETS={
            "filer": {
                "label": "Filer-style",
                "validate": f"{__name__}.filer_style_stub",
                "filer_validator": True,
            },
        }
    )
    def test_filer_validator_wraps_and_passes_arguments(self):
        f = SimpleUploadedFile("x.png", b"x", content_type="image/png")
        user = object()
        validate_form_builder_file(
            f,
            ["filer"],
            user=user,
            request=None,
            field_name="doc",
        )
        name, file_obj, owner, mime = filer_style_stub.last_call
        self.assertEqual(name, "x.png")
        self.assertIs(file_obj, f)
        self.assertIs(owner, user)
        self.assertEqual(mime, "image/png")

    @override_settings(
        DJANGOCMS_FORM_BUILDER_FILE_VALIDATION_PRESETS={
            "filer": {
                "label": "Filer-style",
                "validate": f"{__name__}.filer_style_stub",
                "filer_validator": True,
                "validate_options": {"mime_source": "guess"},
            },
        }
    )
    def test_filer_validator_mime_source_guess_ignores_content_type(self):
        f = SimpleUploadedFile(
            "doc.pdf",
            b"%PDF-1.4",
            content_type="text/plain",
        )
        validate_form_builder_file(
            f,
            ["filer"],
            user=None,
            request=None,
            field_name="doc",
        )
        _name, _file, _owner, mime = filer_style_stub.last_call
        self.assertEqual(mime, "application/pdf")

    @override_settings(
        DJANGOCMS_FORM_BUILDER_FILE_VALIDATION_PRESETS={
            "filer": {
                "label": "Filer-style",
                "validate": f"{__name__}.filer_style_reject",
                "filer_validator": True,
            },
        }
    )
    def test_filer_validator_propagates_validation_error(self):
        f = SimpleUploadedFile("a.txt", b"x", content_type="text/plain")
        with self.assertRaises(ValidationError):
            validate_form_builder_file(
                f,
                ["filer"],
                user=None,
                request=None,
                field_name="doc",
            )

    @override_settings(
        DJANGOCMS_FORM_BUILDER_FILE_VALIDATION_PRESETS={
            "bad": {
                "label": "Class with filer flag",
                "validate": f"{__name__}.DummyClassValidator",
                "filer_validator": True,
            },
        }
    )
    def test_filer_validator_with_class_raises_improperly_configured(self):
        f = SimpleUploadedFile("a.txt", b"x", content_type="text/plain")
        with self.assertRaises(ImproperlyConfigured):
            validate_form_builder_file(
                f,
                ["bad"],
                user=None,
                request=None,
                field_name="doc",
            )

    @override_settings(
        DJANGOCMS_FORM_BUILDER_FILE_VALIDATION_PRESETS={
            "boom": {
                "label": "Raises generic Exception",
                "validate": f"{__name__}.filer_style_raises_runtime",
                "filer_validator": True,
            },
        }
    )
    def test_filer_validator_wraps_non_validation_error(self):
        f = SimpleUploadedFile("a.txt", b"x", content_type="text/plain")
        with self.assertRaises(FileValidationError) as ctx:
            validate_form_builder_file(
                f,
                ["boom"],
                user=None,
                request=None,
                field_name="doc",
            )
        self.assertIn("runtime boom", str(ctx.exception))


def filer_style_raises_runtime(file_name, file, owner, mime_type):
    raise RuntimeError("runtime boom")


class BuiltinValidatorFunctionTests(SimpleTestCase):
    def test_enforce_max_size(self):
        f = SimpleUploadedFile("a.txt", b"123456", content_type="text/plain")
        with self.assertRaises(FileValidationError):
            enforce_max_size(f, 3, field_name="a")

    def test_enforce_extension(self):
        f = SimpleUploadedFile("a.exe", b"x", content_type="application/octet-stream")
        with self.assertRaises(FileValidationError):
            enforce_extension(f, [".pdf"], field_name="a")

    def test_enforce_mime_from_filename(self):
        f = SimpleUploadedFile("a.pdf", b"x", content_type="application/octet-stream")
        enforce_mime_from_filename(f, ["application/pdf"], field_name="a")
        bad = SimpleUploadedFile("a.txt", b"x", content_type="text/plain")
        with self.assertRaises(FileValidationError):
            enforce_mime_from_filename(bad, ["application/pdf"], field_name="a")
