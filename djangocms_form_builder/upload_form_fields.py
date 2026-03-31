"""Form fields for file and multi-file form builder plugins (validation hooks)."""

import typing

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .file_validation import (
    allowed_extensions_for_accept_attribute,
    validate_form_builder_file,
)

if typing.TYPE_CHECKING:
    from django.http import HttpRequest

    User = typing.Any


class MultiFileInput(forms.FileInput):
    """
    ``<input type="file" multiple>``.

    Django requires :attr:`allow_multiple_selected` on the widget class; passing
    only ``attrs={"multiple": True}`` raises ``ValueError`` (see Django's
    :class:`~django.forms.widgets.FileInput`).
    """

    allow_multiple_selected = True


class ValidatedFileField(forms.FileField):
    """FileField that runs validate_form_builder_file after Django's file checks."""

    def __init__(
        self,
        *,
        preset_keys: list,
        user: "User",
        request: typing.Optional["HttpRequest"],
        field_name: str,
        **kwargs,
    ):
        self._preset_keys = preset_keys
        self._user = user
        self._request = request
        self._field_name = field_name
        super().__init__(**kwargs)
        accept = allowed_extensions_for_accept_attribute(self._preset_keys)
        if accept:
            self.widget.attrs["accept"] = accept

    def clean(self, data, initial=None):
        f = super().clean(data, initial)
        if f:
            validate_form_builder_file(
                f,
                self._preset_keys,
                user=self._user,
                request=self._request,
                field_name=self._field_name,
            )
        return f


class MultipleUploadedFilesField(forms.Field):
    """Multiple file input with preset validation for each uploaded file."""

    needs_multipart_form = True

    default_error_messages = {
        "required": _("This field is required."),
    }

    def __init__(
        self,
        *,
        preset_keys: list,
        user: "User",
        request: typing.Optional["HttpRequest"],
        field_name: str,
        **kwargs,
    ):
        self._preset_keys = preset_keys
        self._user = user
        self._request = request
        self._field_name = field_name
        kwargs.setdefault("widget", MultiFileInput())
        super().__init__(**kwargs)
        accept = allowed_extensions_for_accept_attribute(self._preset_keys)
        if accept:
            self.widget.attrs["accept"] = accept

    def clean(self, value):
        if not value:
            if self.required:
                raise ValidationError(
                    self.error_messages["required"],
                    code="required",
                )
            return []
        files = value if isinstance(value, (list, tuple)) else [value]
        for f in files:
            validate_form_builder_file(
                f,
                self._preset_keys,
                user=self._user,
                request=self._request,
                field_name=self._field_name,
            )
            f.seek(0)
        return list(files)
