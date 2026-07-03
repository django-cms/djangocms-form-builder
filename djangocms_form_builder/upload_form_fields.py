"""Form fields for file and multi-file form builder plugins.

Each field validates itself: Django's normal field cleaning runs the configured
validation presets in :meth:`clean`, so per-field errors are collected the same
way as for any other form field. The owning form does not need to know about
uploads.
"""

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .file_validation import (
    allowed_extensions_for_accept_attribute,
    validate_form_builder_file,
)


class MultiFileInput(forms.FileInput):
    """
    ``<input type="file" multiple>``.

    Django requires :attr:`allow_multiple_selected` on the widget class; passing
    only ``attrs={"multiple": True}`` raises ``ValueError`` (see Django's
    :class:`~django.forms.widgets.FileInput`).
    """

    allow_multiple_selected = True


class ValidatedFileField(forms.FileField):
    """A ``FileField`` that runs the configured validation presets on upload."""

    def __init__(
        self,
        *,
        preset_keys: list,
        field_name: str,
        request=None,
        **kwargs,
    ):
        self._preset_keys = preset_keys
        self._field_name = field_name
        self._request = request
        super().__init__(**kwargs)
        accept = allowed_extensions_for_accept_attribute(self._preset_keys)
        if accept:
            self.widget.attrs["accept"] = accept

    def clean(self, data, initial=None):
        uploaded_file = super().clean(data, initial)
        if uploaded_file and self._preset_keys:
            # Raises (a subclass of) ValidationError on failure; the form binds it
            # to this field automatically.
            validate_form_builder_file(
                uploaded_file,
                self._preset_keys,
                user=getattr(self._request, "user", None),
                request=self._request,
                field_name=self._field_name,
            )
        return uploaded_file


class MultipleUploadedFilesField(forms.Field):
    """Multiple file input that validates each uploaded file against the presets."""

    widget = MultiFileInput

    default_error_messages = {
        "required": _("This field is required."),
        "too_many_files": _(
            'Too many files in "%(field)s": at most %(max)s allowed, '
            "but %(count)s were sent."
        ),
    }

    def __init__(
        self,
        *,
        preset_keys: list,
        max_files: int,
        field_name: str,
        request=None,
        **kwargs,
    ):
        self._preset_keys = preset_keys
        self._field_name = field_name
        self._max_files = max_files
        self._request = request
        kwargs.setdefault("widget", MultiFileInput())
        super().__init__(**kwargs)
        accept = allowed_extensions_for_accept_attribute(self._preset_keys)
        if accept:
            self.widget.attrs["accept"] = accept

    def clean(self, value):
        if not value:
            if self.required:
                raise ValidationError(self.error_messages["required"], code="required")
            return []
        files = list(value) if isinstance(value, (list, tuple)) else [value]

        if len(files) > self._max_files:
            raise ValidationError(
                self.error_messages["too_many_files"]
                % {
                    "field": self._field_name,
                    "max": self._max_files,
                    "count": len(files),
                },
                code="too_many_files",
            )

        if self._preset_keys:
            user = getattr(self._request, "user", None)
            errors = []
            for uploaded_file in files:
                try:
                    validate_form_builder_file(
                        uploaded_file,
                        self._preset_keys,
                        user=user,
                        request=self._request,
                        field_name=self._field_name,
                    )
                except ValidationError as exc:
                    errors.append(exc)
            if errors:
                # Collected so every bad file is reported, not just the first.
                raise ValidationError(errors)
        return files
