import re

from django.contrib import admin
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _

from .models import FormEntry


@admin.register(FormEntry)
class FormEntryAdmin(admin.ModelAdmin):
    date_hierarchy = "entry_created_at"
    list_display = ("__str__", "form_user", "entry_created_at")
    list_filter = ("form_name", "form_user", "entry_created_at")
    readonly_fields = ["form_name", "form_user"]

    def has_add_permission(self, request):
        return False

    def get_form(self, request, obj=None, **kwargs):
        if obj:
            kwargs["form"] = obj.get_admin_form()
        return super().get_form(request, obj, **kwargs)

    @staticmethod
    def _entry_file_attr_name(key):
        safe = re.sub(r"[^a-zA-Z0-9_]", "_", str(key))
        if safe and safe[0].isdigit():
            safe = "f_" + safe
        return f"entry_file_{safe}"

    def _ensure_entry_file_attr_map(self, obj):
        mapping = {}
        for key in obj.get_file_entry_data_keys():
            mapping[self._entry_file_attr_name(key)] = key
        self._entry_file_key_by_attr = mapping

    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        if obj:
            self._ensure_entry_file_attr_map(obj)
            ro.extend(self._entry_file_key_by_attr.keys())
        return ro

    def get_fieldsets(self, request, obj=None):
        if obj:
            self._ensure_entry_file_attr_map(obj)
            fieldsets = list(obj.get_admin_fieldsets())
            if self._entry_file_key_by_attr:
                fieldsets.append(
                    (
                        _("Uploaded files"),
                        {
                            "fields": tuple(self._entry_file_key_by_attr.keys()),
                        },
                    ),
                )
            return fieldsets
        return super().get_fieldsets(request, obj)

    @staticmethod
    def format_entry_file_field(obj, key):
        items = FormEntry.get_file_entry_items(obj.entry_data.get(key))
        if not items:
            return "—"
        if len(items) == 1:
            value = items[0]
            return format_html(
                '<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>',
                value["url"],
                value["filename"],
            )
        return format_html(
            "<ul>{}</ul>",
            format_html_join(
                "",
                '<li><a href="{}" target="_blank" rel="noopener noreferrer">{}</a></li>',
                ((d["url"], d["filename"]) for d in items),
            ),
        )

    def __getattr__(self, name):
        if name.startswith("entry_file_"):
            try:
                mapping = object.__getattribute__(self, "_entry_file_key_by_attr")
            except AttributeError:
                mapping = {}
            if name in mapping:
                key = mapping[name]

                def display(admin, obj, _key=key):
                    return FormEntryAdmin.format_entry_file_field(obj, _key)

                display.short_description = key
                bound = display.__get__(self, type(self))
                setattr(self, name, bound)
                return bound
        raise AttributeError(
            f"{type(self).__name__!r} object has no attribute {name!r}"
        )

    def save_model(self, request, obj, form, change):
        """
        Preserve file payload in ``entry_data`` when those keys are not in the
        entangled form (shown only as readonly links).
        """
        preserved = {}
        if change and obj.pk:
            previous = FormEntry.objects.filter(pk=obj.pk).only("entry_data").first()
            if previous:
                for k in previous.get_file_entry_data_keys():
                    preserved[k] = previous.entry_data[k]
        super().save_model(request, obj, form, change)
        if preserved:
            merged = dict(obj.entry_data)
            merged.update(preserved)
            if merged != obj.entry_data:
                obj.entry_data = merged
                obj.save(update_fields=["entry_data"])
