"""Form fields for file and multi-file form builder plugins.

Each field validates itself: Django's normal field cleaning runs the configured
validation presets in :meth:`clean`, so per-field errors are collected the same
way as for any other form field. The owning form does not need to know about
uploads.
"""

import logging

from django import forms
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.utils.translation import gettext_lazy as _

from .file_validation import (
    allowed_extensions_for_accept_attribute,
    validate_form_builder_file,
)

logger = logging.getLogger(__name__)


def run_upload_preset_validation(
    uploaded_file,
    preset_keys,
    *,
    user,
    request,
    field_name,
):
    try:
        validate_form_builder_file(
            uploaded_file,
            preset_keys,
            user=user,
            request=request,
            field_name=field_name,
        )
    except ImproperlyConfigured:
        # log error for dev
        logger.exception(
            "File validation preset misconfigured for field %s",
            field_name,
        )
        # show the user a message
        raise ValidationError(
            _("This field could not be validated. Contact the site administrator."),
            code="preset_misconfigured",
        ) from None


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
            run_upload_preset_validation(
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

        file_field = forms.FileField(required=False)
        user = getattr(self._request, "user", None)
        cleaned_files = []
        errors = []
        for uploaded_file in files:
            try:
                cleaned = file_field.clean(uploaded_file)
                if self._preset_keys:
                    run_upload_preset_validation(
                        cleaned,
                        self._preset_keys,
                        user=user,
                        request=self._request,
                        field_name=self._field_name,
                    )
                cleaned_files.append(cleaned)
            except ValidationError as exc:
                if exc.code == "preset_misconfigured":
                    raise
                errors.append(exc)
        if errors:
            raise ValidationError(errors)
        return cleaned_files
