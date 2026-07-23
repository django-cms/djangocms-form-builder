import base64

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
    def entry_file_attr_name(key):
        encoded = base64.urlsafe_b64encode(str(key).encode()).decode().rstrip("=")
        return f"entry_file_{encoded}"

    @staticmethod
    def entry_file_key_from_attr(name):
        encoded = name.removeprefix("entry_file_")
        padding = (-len(encoded)) % 4
        return base64.urlsafe_b64decode(encoded + "=" * padding).decode()

    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        if obj:
            ro.extend(
                self.entry_file_attr_name(k) for k in obj.get_file_entry_data_keys()
            )
        return ro

    def get_fieldsets(self, request, obj=None):
        if obj:
            file_fields = [
                self.entry_file_attr_name(k) for k in obj.get_file_entry_data_keys()
            ]
            fieldsets = list(obj.get_admin_fieldsets())
            if file_fields:
                fieldsets.append(
                    (
                        _("Uploaded files"),
                        {
                            "fields": tuple(file_fields),
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
                key = self.entry_file_key_from_attr(name)
            except (ValueError, UnicodeDecodeError):
                raise AttributeError(
                    f"{type(self).__name__!r} object has no attribute {name!r}"
                ) from None

            def display(admin, obj, _key=key):
                return FormEntryAdmin.format_entry_file_field(obj, _key)

            display.short_description = key
            return display.__get__(self, type(self))
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
