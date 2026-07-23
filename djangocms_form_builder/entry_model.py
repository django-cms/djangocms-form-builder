import decimal

from django import forms
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db.models.signals import pre_delete
from django.utils.translation import gettext_lazy as _
from entangled.forms import EntangledModelForm

from .form_entry_data import delete_stored_files


class CSValues(forms.CharField):
    class CSVWidget(forms.TextInput):
        def format_value(self, value):
            return ", ".join(value)

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", CSValues.CSVWidget())
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        value = value.split(",")
        value = list(map(lambda x: x.strip(), value))
        return value


def _is_file_entry_value(value):
    """Whether ``value`` in ``entry_data`` is a stored file or list of files."""
    return bool(FormEntry.get_file_entry_items(value))


class FormEntry(models.Model):
    class Meta:
        verbose_name = _("Form entry")
        verbose_name_plural = _("Form entries")

    form_name = models.SlugField(
        verbose_name=_("Form"),
        blank=False,
    )
    form_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("User"),
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    entry_data = models.JSONField(
        default=dict,
        blank=True,
        encoder=DjangoJSONEncoder,
    )
    html_headers = models.JSONField(
        default=dict,
        blank=True,
    )
    entry_created_at = models.DateTimeField(auto_now_add=True)
    entry_updated_at = models.DateTimeField(auto_now=True)

    @staticmethod
    def get_file_entry_items(value):
        """
        Normalize an ``entry_data`` value representing one or many stored files.

        Returns a list of file metadata dicts, or an empty list when the value
        is not a file payload.
        """
        if isinstance(value, dict) and value.get("_form_builder_file"):
            return [value]
        if (
            isinstance(value, list)
            and value
            and isinstance(value[0], dict)
            and value[0].get("_form_builder_file")
        ):
            return value
        return []

    def get_file_entry_data_keys(self):
        """Keys in ``entry_data`` that hold uploaded file(s); shown in admin as readonly links."""
        return [k for k, v in self.entry_data.items() if _is_file_entry_value(v)]

    def get_admin_form(self):
        entangled_fields = []
        fields = {}
        for key, value in self.entry_data.items():
            if _is_file_entry_value(value):
                continue
            elif isinstance(value, str):
                entangled_fields.append(key)
                fields[key] = forms.CharField(
                    label=key,
                    widget=forms.TextInput if len(value) < 80 else forms.Textarea,
                    required=False,
                )
            elif isinstance(value, (list, tuple)):
                entangled_fields.append(key)
                fields[key] = CSValues(
                    label=key,
                    required=False,
                )
            elif isinstance(value, bool):
                entangled_fields.append(key)
                fields[key] = forms.BooleanField(
                    label=key,
                    required=False,
                )
            elif isinstance(value, decimal.Decimal):
                entangled_fields.append(key)
                fields[key] = forms.DecimalField(
                    label=key,
                    required=False,
                )
            elif isinstance(value, int):
                entangled_fields.append(key)
                fields[key] = forms.IntegerField(
                    label=key,
                    required=False,
                )

        fields["Meta"] = type(
            "Meta",
            (),
            {
                "model": FormEntry,
                "exclude": (),
                "entangled_fields": {"entry_data": entangled_fields},
                "untangled_fields": [
                    "form_name",
                    "form_user",
                ],
            },
        )
        return type("DynamicFormEntryForm", (EntangledModelForm,), fields)

    def get_mail_data(self):
        """
        Format json to display its content in an email.
        """
        data = []

        for label, value in self.entry_data.items():
            if _is_file_entry_value(value):
                data.append(
                    {
                        "label": label,
                        "files": [
                            {
                                "filename": f["filename"],
                                "url": f["url"],
                            }
                            for f in value
                        ],
                    }
                )
            else:
                data.append(
                    {
                        "label": label,
                        "value": value,
                    }
                )

        return data

    def get_admin_fieldsets(self):
        return (
            (
                None,
                {
                    "fields": (("form_name", "form_user"),),
                },
            ),
            (
                _("User-entered data"),
                {
                    "fields": tuple(
                        key
                        for key, value in self.entry_data.items()
                        if not _is_file_entry_value(value)
                        and isinstance(
                            value, (str, tuple, list, bool, decimal.Decimal, int)
                        )
                    )
                },
            ),
        )

    def __str__(self):
        return f"{self.form_name} ({self.pk})"


def delete_files_form(sender, **kwargs):
    form_instance = kwargs["instance"]
    delete_stored_files(form_instance.entry_data)


pre_delete.connect(
    delete_files_form, sender=FormEntry, dispatch_uid="formentry.delete_files_form"
)
