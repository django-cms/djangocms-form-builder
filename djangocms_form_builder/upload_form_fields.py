"""Form fields for file and multi-file form builder plugins (validation hooks)."""

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .file_validation import allowed_extensions_for_accept_attribute


class MultiFileInput(forms.FileInput):
    """
    ``<input type="file" multiple>``.

    Django requires :attr:`allow_multiple_selected` on the widget class; passing
    only ``attrs={"multiple": True}`` raises ``ValueError`` (see Django's
    :class:`~django.forms.widgets.FileInput`).
    """

    allow_multiple_selected = True


class ValidatedFileField(forms.FileField):
    """FileField that stores validation preset metadata for form-level validation."""

    def __init__(
        self,
        *,
        preset_keys: list,
        field_name: str,
        **kwargs,
    ):
        self._preset_keys = preset_keys
        self._field_name = field_name
        super().__init__(**kwargs)
        accept = allowed_extensions_for_accept_attribute(self._preset_keys)
        if accept:
            self.widget.attrs["accept"] = accept


class MultipleUploadedFilesField(forms.Field):
    """Multiple file input with preset metadata for form-level validation."""

    needs_multipart_form = True

    default_error_messages = {
        "required": _("This field is required."),
    }

    def __init__(
        self,
        *,
        preset_keys: list,
        field_name: str,
        **kwargs,
    ):
        self._preset_keys = preset_keys
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
        return list(files)
